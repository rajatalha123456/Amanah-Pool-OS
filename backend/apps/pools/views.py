from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.permissions import HasAnyRole, IsFinanceChecker, IsPoolManager, IsShariahBoard
from apps.core.audit import log_action
from apps.products.models import ProductStatus

from .models import Asset, AssetAssignment, AssetStatus, Pool, PoolStatus, PoolVersion
from .serializers import AssetAssignmentSerializer, AssetSerializer, PoolSerializer, PoolVersionSerializer


def _build_pool_snapshot(pool):
    product = pool.product
    contract_template = product.contract_template
    return {
        "product": {
            "id": str(product.id),
            "name": product.name,
            "code": product.code,
            "operating_model": product.operating_model,
            "status": product.status,
        },
        "contract_template": {
            "id": str(contract_template.id),
            "name": contract_template.name,
            "contract_type": contract_template.contract_type,
            "version": contract_template.version,
            "clauses": contract_template.clauses,
            "status": contract_template.status,
        },
    }


class PoolViewSet(viewsets.ModelViewSet):
    serializer_class = PoolSerializer

    def get_queryset(self):
        # See apps/products/views.py for why this must be a method rather
        # than a class-level `queryset = Model.objects.all()` attribute
        # (TenantScopedManager + import-time evaluation bug).
        return Pool.objects.all()

    def get_permissions(self):
        if self.action in ("create", "submit_for_approval", "open"):
            return [IsAuthenticated(), IsPoolManager()]
        if self.action == "approve":
            return [IsAuthenticated(), IsShariahBoard()]
        if self.action == "close":
            return [IsAuthenticated(), IsFinanceChecker()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        instance = serializer.save(tenant=self.request.user.tenant)
        log_action(
            tenant=instance.tenant,
            actor=self.request.user,
            action="create",
            model_name="Pool",
            object_id=str(instance.id),
            request=self.request,
        )

    @action(detail=True, methods=["get"])
    def versions(self, request, pk=None):
        pool = self.get_object()
        versions = pool.versions.all()
        return Response(PoolVersionSerializer(versions, many=True).data)

    @action(detail=True, methods=["post"], url_path="submit-for-approval")
    def submit_for_approval(self, request, pk=None):
        pool = self.get_object()

        if pool.status != PoolStatus.DRAFT:
            raise ValidationError(
                f"Pool must be in '{PoolStatus.DRAFT}' status to submit for approval "
                f"(current status: '{pool.status}')."
            )

        if pool.product.status != ProductStatus.APPROVED:
            raise ValidationError("Product must be approved first.")

        pool.status = PoolStatus.APPROVED
        pool.save(update_fields=["status", "updated_at"])
        log_action(
            tenant=pool.tenant,
            actor=request.user,
            action="submit_for_approval",
            model_name="Pool",
            object_id=str(pool.id),
            changes={"status": {"before": PoolStatus.DRAFT, "after": PoolStatus.APPROVED}},
            request=request,
        )
        return Response(self.get_serializer(pool).data)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        pool = self.get_object()

        if pool.status != PoolStatus.APPROVED:
            raise ValidationError(
                f"Pool must be in '{PoolStatus.APPROVED}' status to approve "
                f"(current status: '{pool.status}')."
            )

        # The substantive Shariah approval already happened at the Product
        # level (see apps.products.ProductViewSet.approve, BR-001). This is
        # a formal Pool-specific sign-off confirming that approval applies
        # to this pool; it does not change `status` (already "approved").
        log_action(
            tenant=pool.tenant,
            actor=request.user,
            action="approve",
            model_name="Pool",
            object_id=str(pool.id),
            reason="Shariah Board sign-off on pool",
            request=request,
        )
        return Response(self.get_serializer(pool).data)

    @action(detail=True, methods=["post"])
    def open(self, request, pk=None):
        pool = self.get_object()

        if pool.status != PoolStatus.APPROVED:
            raise ValidationError(
                f"Pool must be in '{PoolStatus.APPROVED}' status to open "
                f"(current status: '{pool.status}')."
            )

        pool.status = PoolStatus.OPEN
        pool.save(update_fields=["status", "updated_at"])

        version = PoolVersion.objects.create(
            tenant=pool.tenant,
            pool=pool,
            version_number=1,
            snapshot=_build_pool_snapshot(pool),
            created_by=request.user,
            is_current=True,
        )

        log_action(
            tenant=pool.tenant,
            actor=request.user,
            action="open",
            model_name="Pool",
            object_id=str(pool.id),
            changes={"status": {"before": PoolStatus.APPROVED, "after": PoolStatus.OPEN}},
            request=request,
        )
        log_action(
            tenant=pool.tenant,
            actor=request.user,
            action="create",
            model_name="PoolVersion",
            object_id=str(version.id),
            reason="Initial version created on pool open",
            request=request,
        )
        return Response(self.get_serializer(pool).data)

    @action(detail=True, methods=["post"])
    def close(self, request, pk=None):
        pool = self.get_object()

        if pool.status not in (PoolStatus.OPEN, PoolStatus.ALLOCATION):
            raise ValidationError(
                f"Pool must be in '{PoolStatus.OPEN}' or '{PoolStatus.ALLOCATION}' status to close "
                f"(current status: '{pool.status}')."
            )

        previous_status = pool.status
        pool.status = PoolStatus.CLOSED
        pool.closed_date = timezone.localdate()
        pool.save(update_fields=["status", "closed_date", "updated_at"])
        log_action(
            tenant=pool.tenant,
            actor=request.user,
            action="close",
            model_name="Pool",
            object_id=str(pool.id),
            changes={"status": {"before": previous_status, "after": PoolStatus.CLOSED}},
            request=request,
        )
        return Response(self.get_serializer(pool).data)


class AssetViewSet(viewsets.ModelViewSet):
    serializer_class = AssetSerializer

    def get_queryset(self):
        return Asset.objects.all()

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update"):
            return [IsAuthenticated(), HasAnyRole(["pool_manager", "finance_maker"])()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        instance = serializer.save(tenant=self.request.user.tenant)
        log_action(
            tenant=instance.tenant,
            actor=self.request.user,
            action="create",
            model_name="Asset",
            object_id=str(instance.id),
            request=self.request,
        )


class AssetAssignmentViewSet(viewsets.ModelViewSet):
    serializer_class = AssetAssignmentSerializer

    def get_queryset(self):
        queryset = AssetAssignment.objects.all()
        pool_id = self.request.query_params.get("pool")
        if pool_id:
            queryset = queryset.filter(pool_id=pool_id)
        return queryset

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "unassign"):
            return [IsAuthenticated(), IsPoolManager()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        instance = serializer.save(tenant=self.request.user.tenant, assigned_by=self.request.user)

        instance.asset.status = AssetStatus.ASSIGNED
        instance.asset.save(update_fields=["status", "updated_at"])

        log_action(
            tenant=instance.tenant,
            actor=self.request.user,
            action="create",
            model_name="AssetAssignment",
            object_id=str(instance.id),
            changes={"asset_status": {"before": AssetStatus.AVAILABLE, "after": AssetStatus.ASSIGNED}},
            request=self.request,
        )

    @action(detail=True, methods=["post"])
    def unassign(self, request, pk=None):
        assignment = self.get_object()

        if assignment.unassigned_date is not None:
            raise ValidationError("This assignment has already been unassigned.")

        assignment.unassigned_date = timezone.localdate()
        assignment.save(update_fields=["unassigned_date", "updated_at"])

        assignment.asset.status = AssetStatus.AVAILABLE
        assignment.asset.save(update_fields=["status", "updated_at"])

        log_action(
            tenant=assignment.tenant,
            actor=request.user,
            action="unassign",
            model_name="AssetAssignment",
            object_id=str(assignment.id),
            changes={"asset_status": {"before": AssetStatus.ASSIGNED, "after": AssetStatus.AVAILABLE}},
            request=request,
        )
        return Response(self.get_serializer(assignment).data)
