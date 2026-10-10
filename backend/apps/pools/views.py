from datetime import date
from decimal import Decimal
import uuid

from django.db import models, transaction
from django.db.models import Q
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
from apps.participants.models import AccountStatus, KYCStatus, ParticipantAccount
from apps.products.models import ProductStatus

from .liquidity import calculate_liquidity_forecast
from .period_lock import assert_period_open
from .version_diff import compute_snapshot_hash, generate_version_diff

from .models import (
    Asset,
    AssetAssignment,
    AssetStatus,
    BalanceImportBatch,
    BalanceImportBatchStatus,
    DailyBalance,
    DailyBalanceStatus,
    PeriodCloseChecklist,
    PeriodCloseStatus,
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
    PeriodCloseChecklistSerializer,
    PoolSerializer,
    PoolVersionSerializer,
)

CONTROL_TOTAL_TOLERANCE = Decimal("0.01")


def _build_pool_snapshot(pool):
    product = pool.product
    contract_template = product.contract_template
    snapshot = {
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
        "psr": {
            "mudarib_share_pct": 50.0,
            "rabbul_maal_share_pct": 50.0,
            "wakalah_fee_pct": 0.0,
            "performance_incentive_pct": 10.0,
        },
        "reserve_policy": {
            "per_ceiling_pct": 2.0,
            "irr_ceiling_pct": 1.0,
            "max_monthly_appropriation_pct": 15.0,
            "hiba_concession_allowed": True,
        },
        "benchmarks": {
            "benchmark_index": "1-Month KIBOR",
            "spread_bps": 50,
            "target_yield_pct": 18.50,
        },
        "weightage_bands": [
            {"code": "TIER-SAV-01", "name": "Savings Account - Retail", "weight": 1.00, "min_tenor_days": 0},
            {"code": "TIER-SAV-02", "name": "Savings Account - High Net Worth", "weight": 1.20, "min_tenor_days": 0},
            {"code": "TIER-TERM-03", "name": "Term Deposit - 1 Year", "weight": 1.45, "min_tenor_days": 365},
            {"code": "TIER-TERM-04", "name": "Term Deposit - 3 Year", "weight": 1.65, "min_tenor_days": 1095},
        ],
        "governance": {
            "shariah_resolution_code": "SB-RES-2026-01",
            "approving_scholar": "Mufti Dr. Taqi Usmani (Shariah Board Chair)",
            "effective_value_date": str(pool.effective_date),
            "change_rationale": "Initial pool structure approval by Shariah Board",
        },
    }
    snapshot["snapshot_hash"] = compute_snapshot_hash(snapshot)
    return snapshot


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
        versions = pool.versions.all().order_by("-version_number")
        return Response(PoolVersionSerializer(versions, many=True).data)

    @action(detail=True, methods=["get"], url_path="compare-versions")
    def compare_versions(self, request, pk=None):
        """
        BRD Product & Pool Screen 5:
        Pool Version Comparison & Governance Diff Matrix.
        """
        pool = self.get_object()
        v1_id = request.query_params.get("v1")
        v2_id = request.query_params.get("v2")

        versions = list(pool.versions.all().order_by("version_number"))
        if not versions:
            return Response({"error": "No pool versions exist for comparison."}, status=400)

        def _find_v(ident):
            if not ident:
                return None
            try:
                n = int(ident)
                m = pool.versions.filter(version_number=n).first()
                if m:
                    return m
            except (ValueError, TypeError):
                pass
            try:
                u = uuid.UUID(str(ident))
                return pool.versions.filter(id=u).first()
            except (ValueError, TypeError):
                pass
            return None

        v1 = _find_v(v1_id) or versions[0]
        v2 = _find_v(v2_id) or (versions[-1] if len(versions) > 1 else versions[0])

        diff_data = generate_version_diff(pool, v1, v2)
        return Response(diff_data)

    @action(detail=True, methods=["post"], url_path="create-version")
    def create_version(self, request, pk=None):
        """
        Create a new pool version with updated parameters and Shariah attestation.
        """
        pool = self.get_object()
        data = request.data or {}

        latest_version = pool.versions.order_by("-version_number").first()
        new_version_num = (latest_version.version_number + 1) if latest_version else 1

        # Base snapshot
        snapshot = dict(latest_version.snapshot) if (latest_version and latest_version.snapshot) else _build_pool_snapshot(pool)

        if "psr" in data:
            snapshot["psr"] = data["psr"]
        if "reserve_policy" in data:
            snapshot["reserve_policy"] = data["reserve_policy"]
        if "benchmarks" in data:
            snapshot["benchmarks"] = data["benchmarks"]
        if "weightage_bands" in data:
            snapshot["weightage_bands"] = data["weightage_bands"]

        gov = snapshot.get("governance", {})
        gov.update({
            "shariah_resolution_code": data.get("shariah_resolution_code", f"SB-RES-2026-V{new_version_num}"),
            "approving_scholar": data.get("approving_scholar", "Mufti Dr. Taqi Usmani (Shariah Board Chair)"),
            "effective_value_date": data.get("effective_value_date", str(timezone.localdate())),
            "change_rationale": data.get("change_rationale", f"Periodic parameter calibration v{new_version_num}"),
        })
        snapshot["governance"] = gov
        snapshot["snapshot_hash"] = compute_snapshot_hash(snapshot)

        # Deactivate prior versions
        pool.versions.all().update(is_current=False)

        new_version = PoolVersion.objects.create(
            tenant=pool.tenant,
            pool=pool,
            version_number=new_version_num,
            snapshot=snapshot,
            created_by=request.user,
            is_current=True,
        )

        log_action(
            tenant=pool.tenant,
            actor=request.user,
            action="create_pool_version",
            model_name="PoolVersion",
            object_id=str(new_version.id),
            reason=gov["change_rationale"],
            request=request,
        )

        return Response(PoolVersionSerializer(new_version).data, status=201)

    @action(detail=True, methods=["get"], url_path="liquidity-forecast")
    def liquidity_forecast(self, request, pk=None):
        pool = self.get_object()

        as_of_date_param = request.query_params.get("as_of_date")
        as_of_date = date.fromisoformat(as_of_date_param) if as_of_date_param else timezone.localdate()

        horizon_days_param = request.query_params.get("horizon_days")
        try:
            horizon_days = int(horizon_days_param) if horizon_days_param else 30
        except ValueError:
            raise ValidationError({"horizon_days": ["Must be an integer."]})

        result = calculate_liquidity_forecast(pool, as_of_date, horizon_days=horizon_days)
        return Response(result)

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

        pool.status = PoolStatus.PENDING_APPROVAL
        pool.save(update_fields=["status", "updated_at"])
        log_action(
            tenant=pool.tenant,
            actor=request.user,
            action="submit_for_approval",
            model_name="Pool",
            object_id=str(pool.id),
            changes={"status": {"before": PoolStatus.DRAFT, "after": PoolStatus.PENDING_APPROVAL}},
            request=request,
        )
        return Response(self.get_serializer(pool).data)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        pool = self.get_object()

        if pool.status != PoolStatus.PENDING_APPROVAL:
            raise ValidationError(
                f"Pool must be in '{PoolStatus.PENDING_APPROVAL}' status to approve "
                f"(current status: '{pool.status}')."
            )

        pool.status = PoolStatus.APPROVED
        pool.save(update_fields=["status", "updated_at"])
        log_action(
            tenant=pool.tenant,
            actor=request.user,
            action="approve",
            model_name="Pool",
            object_id=str(pool.id),
            reason="Shariah Board sign-off on pool",
            changes={"status": {"before": PoolStatus.PENDING_APPROVAL, "after": PoolStatus.APPROVED}},
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

    @action(detail=False, methods=["get"], url_path="concentration-risk")
    def concentration_risk(self, request):
        pool_id = request.query_params.get("pool_id")
        pool = None
        if pool_id:
            pool = Pool.objects.filter(id=pool_id).first()
        from .concentration_engine import run_concentration_risk_analysis
        data = run_concentration_risk_analysis(pool=pool)
        return Response(data)

    @action(detail=False, methods=["post"], url_path="remediation-plan")
    def remediation_plan(self, request):
        target_name = request.data.get("target_name")
        target_type = request.data.get("target_type", "obligor")
        current_exposure = Decimal(str(request.data.get("current_exposure", 0)))
        excess_amount = Decimal(str(request.data.get("excess_amount", 0)))
        action_note = request.data.get("action_note", "Mitigation covenant registered.")
        pool_id = request.data.get("pool_id")
        pool = Pool.objects.filter(id=pool_id).first() if pool_id else None

        if not target_name:
            raise ValidationError("target_name is required.")

        from .concentration_engine import commit_breach_remediation_case
        result = commit_breach_remediation_case(
            tenant=request.user.tenant,
            user=request.user,
            target_name=target_name,
            target_type=target_type,
            current_exposure=current_exposure,
            excess_amount=excess_amount,
            action_note=action_note,
            pool=pool,
        )
        return Response(result)

    @action(detail=False, methods=["post"], url_path="stress-test")
    def stress_test(self, request):
        pool_id = request.data.get("pool_id")
        deposit_runoff_pct = float(request.data.get("deposit_runoff_pct", 15.0))
        pool = Pool.objects.filter(id=pool_id).first() if pool_id else None

        from .concentration_engine import run_concentration_stress_test
        result = run_concentration_stress_test(pool=pool, deposit_runoff_pct=deposit_runoff_pct)
        return Response(result)


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
        if self.action in ("create", "cbs_sftp_daemon"):
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

        assert_period_open(pool, value_date, what="a balance import")

        errors = []
        created_balances = []
        control_total_actual = Decimal("0.00")

        accounts_by_number = {
            account.account_number: account
            for account in ParticipantAccount.objects.select_related("participant").filter(pool=pool)
        }

        with transaction.atomic():
            for record in records:
                balance_amount = record["balance_amount"]
                account_number = record.get("account_number")
                account = None

                if account_number:
                    account = accounts_by_number.get(account_number)
                    if account is None:
                        errors.append(f"Unknown account '{account_number}' for this pool: skipped.")
                        continue
                    if (
                        account.opened_date > value_date
                        or (account.closed_date and account.closed_date < value_date)
                        or (account.status == AccountStatus.CLOSED and not account.closed_date)
                    ):
                        errors.append(
                            f"Account '{account_number}' is not open on {value_date}: skipped."
                        )
                        continue
                    if account.participant.kyc_status != KYCStatus.VERIFIED:
                        errors.append(
                            f"Account '{account_number}': participant KYC is "
                            f"'{account.participant.kyc_status}', not verified: skipped."
                        )
                        continue
                    participant_class = account.participant.participant_class
                    duplicate = DailyBalance.objects.filter(
                        pool=pool, value_date=value_date, account=account
                    ).exists()
                    duplicate_label = f"account '{account_number}'"
                else:
                    if accounts_by_number:
                        errors.append(
                            "This pool has participant accounts; account_number is required "
                            "(class-level balances are not accepted): skipped."
                        )
                        continue
                    participant_class = record["participant_class"]
                    duplicate = DailyBalance.objects.filter(
                        pool=pool, value_date=value_date, participant_class=participant_class, account__isnull=True
                    ).exists()
                    duplicate_label = f"participant_class='{participant_class}'"

                if duplicate:
                    errors.append(f"Duplicate balance for {duplicate_label} on {value_date}: skipped.")
                    continue

                balance = DailyBalance.objects.create(
                    tenant=request.user.tenant,
                    pool=pool,
                    account=account,
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

    @action(detail=False, methods=["post"], url_path="cbs-sftp-daemon")
    def cbs_sftp_daemon(self, request):
        """
        Screen 09 / Module 06: Automated Core Banking System SFTP EOD Batch Ingestion.
        """
        from datetime import datetime
        from .cbs_daemon import simulate_cbs_sftp_ingestion

        pool_id = request.data.get("pool_id")
        if not pool_id:
            raise ValidationError({"pool_id": ["This field is required."]})

        try:
            pool = Pool.objects.get(id=pool_id, tenant=request.user.tenant)
        except Pool.DoesNotExist:
            raise ValidationError({"pool_id": ["Pool not found."]})

        value_date_str = request.data.get("value_date")
        if value_date_str:
            value_date = datetime.strptime(value_date_str, "%Y-%m-%d").date()
        else:
            value_date = timezone.now().date()

        assert_period_open(pool, value_date, what="a balance import")

        if ParticipantAccount.objects.filter(pool=pool).exists():
            raise ValidationError(
                "The CBS feed simulator only produces class-level balances and cannot be used "
                "for a pool with participant accounts; import account-level balances instead."
            )

        cbs_vendor = request.data.get("cbs_vendor", "Temenos T24")
        scenario = request.data.get("scenario", "clean")

        result = simulate_cbs_sftp_ingestion(
            tenant=request.user.tenant,
            pool=pool,
            value_date=value_date,
            cbs_vendor=cbs_vendor,
            scenario=scenario,
            user=request.user,
        )

        status_code = 200 if result.get("success") else 422
        return Response(result, status=status_code)



class PeriodCloseChecklistViewSet(viewsets.ModelViewSet):
    """
    Screen 16: Period Close Manager - Close checklist, locks and certification.
    """

    serializer_class = PeriodCloseChecklistSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = PeriodCloseChecklist.objects.all()
        pool_id = self.request.query_params.get("pool")
        if pool_id:
            queryset = queryset.filter(pool_id=pool_id)
        return queryset

    def perform_create(self, serializer):
        default_checklist = {
            "reconciled": True,
            "shariah_parameters_sealed": True,
            "exceptions_cleared": True,
            "allocation_signed": True,
            "journals_posted": True,
        }
        checklist = serializer.validated_data.get("checklist_data") or default_checklist
        instance = serializer.save(
            tenant=self.request.user.tenant,
            checklist_data=checklist,
        )
        log_action(
            tenant=instance.tenant,
            actor=self.request.user,
            action="create",
            model_name="PeriodCloseChecklist",
            object_id=str(instance.id),
            request=self.request,
        )

    @action(detail=True, methods=["post"], url_path="certify")
    def certify(self, request, pk=None):
        instance = self.get_object()
        instance.status = PeriodCloseStatus.CERTIFIED
        instance.certified_by = request.user
        instance.certified_at = timezone.now()
        instance.decision_note = request.data.get(
            "decision_note", "Variance is within tolerance. Certified for close."
        )
        instance.save(
            update_fields=["status", "certified_by", "certified_at", "decision_note", "updated_at"]
        )
        log_action(
            tenant=instance.tenant,
            actor=request.user,
            action="certify",
            model_name="PeriodCloseChecklist",
            object_id=str(instance.id),
            request=request,
        )
        return Response(self.get_serializer(instance).data)

    @action(detail=True, methods=["post"], url_path="lock")
    def lock(self, request, pk=None):
        instance = self.get_object()
        instance.status = PeriodCloseStatus.LOCKED
        instance.save(update_fields=["status", "updated_at"])
        log_action(
            tenant=instance.tenant,
            actor=request.user,
            action="lock",
            model_name="PeriodCloseChecklist",
            object_id=str(instance.id),
            request=request,
        )
        return Response(self.get_serializer(instance).data)

    @action(detail=True, methods=["post"], url_path="auto-verify-gates")
    def auto_verify_gates(self, request, pk=None):
        instance = self.get_object()
        from .period_close_engine import auto_verify_period_gates
        res = auto_verify_period_gates(instance)
        return Response(res)

    @action(detail=True, methods=["post"], url_path="sign-off-role")
    def sign_off_role(self, request, pk=None):
        instance = self.get_object()
        role = request.data.get("role", "pool_manager")
        notes = request.data.get("notes", "")
        fatwa_ref = request.data.get("fatwa_ref", "")

        from .period_close_engine import sign_off_period_role
        res = sign_off_period_role(
            period_close=instance,
            user=request.user,
            role=role,
            notes=notes,
            fatwa_ref=fatwa_ref,
        )
        return Response(res)

    @action(detail=True, methods=["post"], url_path="lock-ceremony")
    def lock_ceremony(self, request, pk=None):
        instance = self.get_object()
        lock_note = request.data.get("lock_note", "")

        from .period_close_engine import execute_cryptographic_lock_ceremony
        res = execute_cryptographic_lock_ceremony(
            period_close=instance,
            user=request.user,
            lock_note=lock_note,
        )
        return Response(res)

    @action(detail=True, methods=["get"], url_path="filing-package")
    def filing_package(self, request, pk=None):
        instance = self.get_object()
        from .period_close_engine import get_sbp_filing_certificate
        pkg = get_sbp_filing_certificate(instance)
        return Response(pkg)

