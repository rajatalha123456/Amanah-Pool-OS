from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.permissions import HasAnyRole, IsPoolManager, IsShariahBoard
from apps.core.audit import log_action

from .engine import calculate_allocation, calculate_hash
from .models import (
    AllocationLine,
    AllocationRun,
    AllocationRunStatus,
    PSRStatus,
    ProfitSharingRatio,
    WeightageBand,
    WeightageBandStatus,
)
from .serializers import (
    AllocationRunInputSerializer,
    AllocationRunSerializer,
    PSRSerializer,
    WeightageBandSerializer,
)


class WeightageBandViewSet(viewsets.ModelViewSet):
    serializer_class = WeightageBandSerializer

    def get_queryset(self):
        # See apps/products/views.py and apps/pools/views.py for why this
        # must be a method rather than a class-level
        # `queryset = Model.objects.all()` attribute (TenantScopedManager +
        # import-time evaluation bug).
        queryset = WeightageBand.objects.all()
        pool_id = self.request.query_params.get("pool")
        if pool_id:
            queryset = queryset.filter(pool_id=pool_id)
        return queryset

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update"):
            return [IsAuthenticated(), IsPoolManager()]
        if self.action == "approve":
            return [IsAuthenticated(), IsShariahBoard()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        instance = serializer.save(tenant=self.request.user.tenant)
        log_action(
            tenant=instance.tenant,
            actor=self.request.user,
            action="create",
            model_name="WeightageBand",
            object_id=str(instance.id),
            request=self.request,
        )

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        band = self.get_object()

        if band.status != WeightageBandStatus.DRAFT:
            raise ValidationError(
                f"WeightageBand must be in '{WeightageBandStatus.DRAFT}' status to approve "
                f"(current status: '{band.status}')."
            )

        band.status = WeightageBandStatus.APPROVED
        band.save(update_fields=["status", "updated_at"])
        log_action(
            tenant=band.tenant,
            actor=request.user,
            action="approve",
            model_name="WeightageBand",
            object_id=str(band.id),
            changes={"status": {"before": WeightageBandStatus.DRAFT, "after": WeightageBandStatus.APPROVED}},
            request=request,
        )
        return Response(self.get_serializer(band).data)


class PSRViewSet(viewsets.ModelViewSet):
    serializer_class = PSRSerializer

    def get_queryset(self):
        queryset = ProfitSharingRatio.objects.all()
        pool_id = self.request.query_params.get("pool")
        if pool_id:
            queryset = queryset.filter(pool_id=pool_id)
        return queryset

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update"):
            return [IsAuthenticated(), IsPoolManager()]
        if self.action == "approve":
            return [IsAuthenticated(), IsShariahBoard()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        instance = serializer.save(tenant=self.request.user.tenant)
        log_action(
            tenant=instance.tenant,
            actor=self.request.user,
            action="create",
            model_name="ProfitSharingRatio",
            object_id=str(instance.id),
            request=self.request,
        )

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        psr = self.get_object()

        if psr.status != PSRStatus.DRAFT:
            raise ValidationError(
                f"ProfitSharingRatio must be in '{PSRStatus.DRAFT}' status to approve "
                f"(current status: '{psr.status}')."
            )

        psr.status = PSRStatus.APPROVED
        psr.save(update_fields=["status", "updated_at"])
        log_action(
            tenant=psr.tenant,
            actor=request.user,
            action="approve",
            model_name="ProfitSharingRatio",
            object_id=str(psr.id),
            changes={"status": {"before": PSRStatus.DRAFT, "after": PSRStatus.APPROVED}},
            request=request,
        )
        return Response(self.get_serializer(psr).data)


class AllocationRunViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = AllocationRunSerializer

    def get_queryset(self):
        # See apps/products/views.py, apps/pools/views.py for why this
        # must be a method rather than a class-level
        # `queryset = Model.objects.all()` attribute (TenantScopedManager +
        # import-time evaluation bug).
        queryset = AllocationRun.objects.all()
        pool_id = self.request.query_params.get("pool")
        if pool_id:
            queryset = queryset.filter(pool_id=pool_id)
        return queryset

    def get_permissions(self):
        if self.action in ("create", "simulate"):
            return [IsAuthenticated(), HasAnyRole(["pool_manager", "finance_maker"])()]
        return [IsAuthenticated()]

    def _run_calculation(self, request):
        input_serializer = AllocationRunInputSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        data = input_serializer.validated_data

        try:
            result = calculate_allocation(
                pool=data["pool"],
                value_date=data["value_date"],
                gross_income=data["gross_income"],
                direct_expenses=data["direct_expenses"],
            )
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc

        return data, result

    @action(detail=False, methods=["post"])
    def simulate(self, request):
        """
        Runs the allocation calculation and returns the result directly.
        Nothing is written to the database.
        """
        _, result = self._run_calculation(request)
        return Response(
            {
                "distributable": result["distributable"],
                "total_weighted_funds": result["total_weighted_funds"],
                "depositor_pool_share": result["depositor_pool_share"],
                "mudarib_share": result["mudarib_share"],
                "lines": result["lines"],
            }
        )

    def create(self, request, *args, **kwargs):
        """
        Runs the allocation calculation and persists it as an
        AllocationRun + AllocationLine rows, status="simulated".
        """
        data, result = self._run_calculation(request)

        hashable_data = {
            "pool_id": str(data["pool"].id),
            "value_date": data["value_date"].isoformat(),
            "gross_income": str(data["gross_income"]),
            "direct_expenses": str(data["direct_expenses"]),
            "distributable": str(result["distributable"]),
            "total_weighted_funds": str(result["total_weighted_funds"]),
            "depositor_pool_share": str(result["depositor_pool_share"]),
            "mudarib_share": str(result["mudarib_share"]),
            "lines": [
                {k: str(v) for k, v in line.items()} for line in result["lines"]
            ],
        }
        calculation_hash = calculate_hash(hashable_data)

        run = AllocationRun.objects.create(
            tenant=request.user.tenant,
            pool=data["pool"],
            value_date=data["value_date"],
            gross_income=data["gross_income"],
            direct_expenses=data["direct_expenses"],
            distributable_amount=result["distributable"],
            total_weighted_funds=result["total_weighted_funds"],
            depositor_pool_share=result["depositor_pool_share"],
            mudarib_share=result["mudarib_share"],
            status=AllocationRunStatus.SIMULATED,
            calculation_hash=calculation_hash,
            created_by=request.user,
        )

        AllocationLine.objects.bulk_create(
            [
                AllocationLine(
                    tenant=request.user.tenant,
                    allocation_run=run,
                    participant_class=line["participant_class"],
                    daily_funds=line["daily_funds"],
                    weightage=line["weightage"],
                    weighted_funds=line["weighted_funds"],
                    allocated_amount=line["allocated_amount"],
                )
                for line in result["lines"]
            ]
        )

        log_action(
            tenant=run.tenant,
            actor=request.user,
            action="create",
            model_name="AllocationRun",
            object_id=str(run.id),
            changes={
                "distributable_amount": str(run.distributable_amount),
                "total_weighted_funds": str(run.total_weighted_funds),
                "depositor_pool_share": str(run.depositor_pool_share),
                "mudarib_share": str(run.mudarib_share),
                "line_count": len(result["lines"]),
                "calculation_hash": calculation_hash,
            },
            request=request,
        )

        return Response(self.get_serializer(run).data, status=201)
