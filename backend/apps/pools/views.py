from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import (
    HasAnyRole,
    IsFinanceChecker,
    IsFinanceMaker,
    IsPoolManager,
    IsShariahBoard,
)
from apps.core.audit import log_action
from apps.core.exceptions_helper import create_exception_case
from apps.products.models import ProductStatus

from .models import (
    Asset,
    AssetAssignment,
    AssetStatus,
    BalanceImportBatch,
    BalanceImportBatchStatus,
    DailyBalance,
    DailyBalanceStatus,
    Pool,
    PoolStatus,
    PoolVersion,
)
from .serializers import (
    AssetAssignmentSerializer,
    AssetSerializer,
    BalanceImportBatchSerializer,
    BulkBalanceImportSerializer,
    DailyBalanceSerializer,
    PoolSerializer,
    PoolVersionSerializer,
)

CONTROL_TOTAL_TOLERANCE = Decimal("0.01")


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


class DailyBalanceViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = DailyBalanceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = DailyBalance.objects.all()
        pool_id = self.request.query_params.get("pool")
        if pool_id:
            queryset = queryset.filter(pool_id=pool_id)
        value_date = self.request.query_params.get("value_date")
        if value_date:
            queryset = queryset.filter(value_date=value_date)
        return queryset


class BalanceImportViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """
    POST creates a bulk balance import batch (BulkBalanceImportSerializer
    payload); GET lists BalanceImportBatch history, filterable by
    ?pool={pool_id}.
    """

    def get_queryset(self):
        queryset = BalanceImportBatch.objects.all()
        pool_id = self.request.query_params.get("pool")
        if pool_id:
            queryset = queryset.filter(pool_id=pool_id)
        return queryset

    def get_serializer_class(self):
        if self.action == "create":
            return BulkBalanceImportSerializer
        return BalanceImportBatchSerializer

    def get_permissions(self):
        if self.action == "create":
            return [IsAuthenticated(), HasAnyRole(["pool_manager", "finance_maker"])()]
        return [IsAuthenticated()]

    def create(self, request, *args, **kwargs):
        serializer = BulkBalanceImportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        pool = data["pool"]
        value_date = data["value_date"]
        control_total_expected = data.get("control_total_expected")
        records = data["records"]

        errors = []
        created_balances = []
        control_total_actual = Decimal("0.00")

        with transaction.atomic():
            for record in records:
                participant_class = record["participant_class"]
                balance_amount = record["balance_amount"]

                if DailyBalance.objects.filter(
                    pool=pool, value_date=value_date, participant_class=participant_class
                ).exists():
                    errors.append(
                        f"Duplicate balance for participant_class='{participant_class}' "
                        f"on {value_date}: skipped."
                    )
                    continue

                balance = DailyBalance.objects.create(
                    tenant=request.user.tenant,
                    pool=pool,
                    participant_class=participant_class,
                    value_date=value_date,
                    balance_amount=balance_amount,
                    status=DailyBalanceStatus.VALIDATED,
                )
                created_balances.append(balance)
                control_total_actual += balance_amount

            matched_records = len(created_balances)
            exception_count = len(errors)

            # A batch is only "balanced" when nothing was skipped (no
            # duplicate exceptions) AND, if a control total was supplied,
            # it matches the actual sum within tolerance. Any exception
            # (duplicate skip or control-total mismatch) marks the whole
            # batch "exception", even if the other check would have passed.
            control_total_matches = (
                control_total_expected is None
                or abs(control_total_actual - control_total_expected) <= CONTROL_TOTAL_TOLERANCE
            )

            batch_status = (
                BalanceImportBatchStatus.BALANCED
                if exception_count == 0 and control_total_matches
                else BalanceImportBatchStatus.EXCEPTION
            )

            batch = BalanceImportBatch.objects.create(
                tenant=request.user.tenant,
                pool=pool,
                value_date=value_date,
                total_records=len(records),
                matched_records=matched_records,
                exception_count=exception_count,
                control_total_expected=control_total_expected,
                control_total_actual=control_total_actual,
                status=batch_status,
                imported_by=request.user,
            )

        log_action(
            tenant=batch.tenant,
            actor=request.user,
            action="import",
            model_name="BalanceImportBatch",
            object_id=str(batch.id),
            changes={
                "total_records": batch.total_records,
                "matched_records": batch.matched_records,
                "exception_count": batch.exception_count,
                "control_total_expected": str(control_total_expected) if control_total_expected is not None else None,
                "control_total_actual": str(control_total_actual),
                "status": batch.status,
            },
            request=request,
        )

        if batch.status == BalanceImportBatchStatus.EXCEPTION:
            create_exception_case(
                tenant=batch.tenant,
                source_module="balance_import",
                source_object_id=str(batch.id),
                pool=pool,
                severity="medium",
                title=f"Control total mismatch on {value_date} for pool {pool.code}",
                description=(
                    f"Balance import batch {batch.id} for pool {pool.code} on {value_date} "
                    f"flagged as exception: {exception_count} skipped/duplicate record(s), "
                    f"control total expected={control_total_expected}, actual={control_total_actual}."
                ),
            )

        return Response(
            {
                "id": str(batch.id),
                "total_records": batch.total_records,
                "matched_records": batch.matched_records,
                "exception_count": batch.exception_count,
                "control_total_expected": batch.control_total_expected,
                "control_total_actual": batch.control_total_actual,
                "status": batch.status,
                "errors": errors,
            },
            status=201,
        )
