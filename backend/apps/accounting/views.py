from decimal import Decimal

from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import mixins, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.permissions import HasAnyRole, IsFinanceChecker, IsFinanceMaker
from apps.core.audit import log_action
from apps.core.viewset_guards import NO_DELETE, STAFF_ROLES
from apps.pools.models import Pool
from apps.pools.daily_close import assert_day_open
from apps.pools.period_lock import assert_period_open

from .chart import ACCOUNTS, REQUIRED_BY_MODEL
from .exports import generate_gl_csv
from .models import (
    CostClassification,
    IncomeExpenseEvent,
    IncomeExpenseEventStatus,
    IncomeExpenseEventType,
    AccountMapping,
    JournalBatch,
    ReconciliationBatch,
    ReconciliationStatus,
)
from .serializers import (
    AccountMappingSerializer,
    IncomeExpenseEventSerializer,
    JournalBatchSerializer,
    ReconciliationBatchSerializer,
)


class JournalBatchViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = JournalBatchSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # See apps/products/views.py etc. for why this must be a method
        # rather than a class-level `queryset = Model.objects.all()`
        # attribute (TenantScopedManager + import-time evaluation bug).
        queryset = JournalBatch.objects.all()
        pool_id = self.request.query_params.get("pool")
        if pool_id:
            queryset = queryset.filter(pool_id=pool_id)
        return queryset


class IncomeExpenseEventViewSet(viewsets.ModelViewSet):
    serializer_class = IncomeExpenseEventSerializer
    # Events are ledger facts: created by a maker, posted by an independent checker, never edited or deleted.
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        # See apps/products/views.py etc. for why this must be a method
        # rather than a class-level `queryset = Model.objects.all()`
        # attribute (TenantScopedManager + import-time evaluation bug).
        queryset = IncomeExpenseEvent.objects.all()
        pool_id = self.request.query_params.get("pool")
        if pool_id:
            queryset = queryset.filter(pool_id=pool_id)
        return queryset

    def get_permissions(self):
        if self.action == "create":
            return [IsAuthenticated(), IsFinanceMaker()]
        if self.action == "post_event":
            return [IsAuthenticated(), IsFinanceChecker()]
        if self.action in ("quarantine_to_charity", "reclassify", "scan_overhead_leakage"):
            return [IsAuthenticated(), HasAnyRole(["finance_maker", "shariah_secretariat"])()]
        return [IsAuthenticated(), HasAnyRole(STAFF_ROLES)()]

    def perform_create(self, serializer):
        assert_period_open(
            serializer.validated_data["pool"],
            serializer.validated_data["event_date"],
            what="an income/expense event",
        )
        assert_day_open(serializer.validated_data["pool"], serializer.validated_data["event_date"], what="an income/expense event")
        instance = serializer.save(tenant=self.request.user.tenant, created_by=self.request.user)
        log_action(
            tenant=instance.tenant,
            actor=self.request.user,
            action="create",
            model_name="IncomeExpenseEvent",
            object_id=str(instance.id),
            changes={
                "event_type": instance.event_type,
                "category": instance.category,
                "amount": str(instance.amount),
                "pool": str(instance.pool_id),
            },
            request=self.request,
        )

    @action(detail=True, methods=["post"], url_path="post")
    def post_event(self, request, pk=None):
        event = self.get_object()

        if event.status != IncomeExpenseEventStatus.PENDING:
            raise ValidationError(
                f"IncomeExpenseEvent must be in '{IncomeExpenseEventStatus.PENDING}' status to "
                f"post (current status: '{event.status}')."
            )

        assert_period_open(event.pool, event.event_date, what="an income/expense event")
        assert_day_open(event.pool, event.event_date, what="an income/expense event")

        if event.created_by_id == request.user.id:
            raise ValidationError("Maker-checker: the user who created an event cannot post it.")

        previous_status = event.status
        with transaction.atomic():
            event.status = IncomeExpenseEventStatus.POSTED
            event.posted_by = request.user
            event.posted_at = timezone.now()
            event.save(update_fields=["status", "posted_by", "posted_at", "updated_at"])

            # BR-005: non-permissible income never reaches participants - it is routed to purification.
            if event.event_type == IncomeExpenseEventType.INCOME and event.quarantined_to_charity:
                from apps.governance.models import PurificationEntry

                PurificationEntry.objects.get_or_create(
                    tenant=event.tenant,
                    income_event=event,
                    defaults={
                        "pool": event.pool,
                        "source_description": f"{event.category}: {event.description}"[:255],
                        "amount": event.amount,
                        "identified_date": event.event_date,
                    },
                )

        log_action(
            tenant=event.tenant,
            actor=request.user,
            action="post",
            model_name="IncomeExpenseEvent",
            object_id=str(event.id),
            changes={"status": {"before": previous_status, "after": event.status}},
            request=request,
        )
        return Response(self.get_serializer(event).data)

    @action(detail=False, methods=["get"], url_path="pool-summary")
    def pool_summary(self, request):
        """
        BRD Screen 03: Income & Expense Workbench Summary Deck.
        Aggregates Gross Income, Quarantined Non-Permissible Income,
        Approved Direct Expenses, and Bank Absorbed Overheads.
        """
        pool_id = request.query_params.get("pool")
        queryset = self.get_queryset()
        if pool_id:
            queryset = queryset.filter(pool_id=pool_id)

        income_events = queryset.filter(event_type=IncomeExpenseEventType.INCOME)
        expense_events = queryset.filter(event_type=IncomeExpenseEventType.EXPENSE)

        total_income_gross = sum((e.amount for e in income_events), Decimal("0.00"))
        non_permissible_income = sum(
            (e.amount for e in income_events if e.quarantined_to_charity or e.cost_classification == CostClassification.NON_PERMISSIBLE_INCOME),
            Decimal("0.00")
        )
        net_permissible_income = total_income_gross - non_permissible_income

        total_expenses_claimed = sum((e.amount for e in expense_events), Decimal("0.00"))
        approved_direct_expenses = sum((e.pool_chargeable_amount for e in expense_events if e.is_direct_expense), Decimal("0.00"))
        bank_absorbed_overheads = sum((e.bank_absorbed_amount for e in expense_events if e.is_overhead_leakage), Decimal("0.00"))

        net_distributable_profit = net_permissible_income - approved_direct_expenses

        overhead_leakage_items = expense_events.filter(is_overhead_leakage=True).count()
        quarantined_items_count = income_events.filter(quarantined_to_charity=True).count()
        pending_items_count = queryset.filter(status=IncomeExpenseEventStatus.PENDING).count()

        return Response({
            "pool_id": pool_id,
            "total_income_gross": float(total_income_gross),
            "non_permissible_income": float(non_permissible_income),
            "net_permissible_income": float(net_permissible_income),
            "total_expenses_claimed": float(total_expenses_claimed),
            "approved_direct_expenses": float(approved_direct_expenses),
            "bank_absorbed_overheads": float(bank_absorbed_overheads),
            "net_distributable_profit": float(net_distributable_profit),
            "overhead_leakage_detected": overhead_leakage_items > 0,
            "overhead_leakage_count": overhead_leakage_items,
            "quarantined_items_count": quarantined_items_count,
            "pending_items_count": pending_items_count,
            "total_records_count": queryset.count(),
        })

    @action(detail=True, methods=["post"], url_path="quarantine-to-charity")
    def quarantine_to_charity(self, request, pk=None):
        """
        Quarantines a non-permissible income line to the Charity account.
        """
        event = self.get_object()
        if event.event_type != IncomeExpenseEventType.INCOME:
            raise ValidationError("Only income items can be quarantined to charity.")
        if event.status != IncomeExpenseEventStatus.PENDING:
            raise ValidationError("A posted event is a ledger fact; correct it with a new event instead.")

        reason = request.data.get("reason", "Non-permissible income flagged by Shariah compliance.")
        event.cost_classification = CostClassification.NON_PERMISSIBLE_INCOME
        event.quarantined_to_charity = True
        event.pool_chargeable_amount = Decimal("0.00")
        event.shariah_note = f"Quarantined to Charity: {reason}"
        event.save(update_fields=[
            "cost_classification", "quarantined_to_charity",
            "pool_chargeable_amount", "shariah_note", "updated_at"
        ])

        log_action(
            tenant=event.tenant,
            actor=request.user,
            action="quarantine_to_charity",
            model_name="IncomeExpenseEvent",
            object_id=str(event.id),
            reason=reason,
            request=request,
        )
        return Response(self.get_serializer(event).data)

    @action(detail=True, methods=["post"], url_path="reclassify")
    def reclassify(self, request, pk=None):
        """
        Reclassifies an expense between direct_permissible and indirect_overhead.
        """
        event = self.get_object()
        new_classification = request.data.get("cost_classification")
        shariah_note = request.data.get("shariah_note", "")

        if new_classification not in CostClassification.values:
            raise ValidationError(f"Invalid cost classification: {new_classification}")
        if event.status != IncomeExpenseEventStatus.PENDING:
            raise ValidationError("A posted event is a ledger fact; correct it with a new event instead.")

        event.cost_classification = new_classification
        if shariah_note:
            event.shariah_note = shariah_note
        event.save()

        log_action(
            tenant=event.tenant,
            actor=request.user,
            action="reclassify_cost",
            model_name="IncomeExpenseEvent",
            object_id=str(event.id),
            reason=shariah_note or f"Reclassified to {new_classification}",
            request=request,
        )
        return Response(self.get_serializer(event).data)

    @action(detail=False, methods=["post"], url_path="scan-overhead-leakage")
    def scan_overhead_leakage(self, request):
        """
        Automated scan detecting overhead leakage attempts in pool expenses.
        """
        pool_id = request.data.get("pool") or request.query_params.get("pool")
        queryset = self.get_queryset().filter(
            event_type=IncomeExpenseEventType.EXPENSE, status=IncomeExpenseEventStatus.PENDING
        )
        if pool_id:
            queryset = queryset.filter(pool_id=pool_id)

        scanned = 0
        flagged = 0
        for event in queryset:
            scanned += 1
            # Trigger model save which runs overhead keyword verification
            event.save()
            if event.is_overhead_leakage:
                flagged += 1

        return Response({
            "scanned_count": scanned,
            "flagged_leakage_count": flagged,
            "status": "PASS" if flagged == 0 else "BREACHES_DETECTED",
            "message": f"Scanned {scanned} expense items. {flagged} indirect overhead leakage attempts flagged and redirected to Bank P&L absorption."
        })


@api_view(["GET"])
@permission_classes([IsAuthenticated, HasAnyRole(["finance_maker", "finance_checker"])])
def gl_export(request):
    pool_id = request.query_params.get("pool")
    pool = get_object_or_404(Pool, id=pool_id)

    date_from = request.query_params.get("date_from")
    date_to = request.query_params.get("date_to")

    csv_content = generate_gl_csv(pool, date_from=date_from, date_to=date_to)
    row_count = max(csv_content.count("\n") - 1, 0)

    log_action(
        tenant=pool.tenant,
        actor=request.user,
        action="gl_export",
        model_name="Pool",
        object_id=str(pool.id),
        changes={"pool": pool.code, "row_count": row_count, "date_from": date_from, "date_to": date_to},
        request=request,
    )

    filename = f"gl_export_{pool.code}_{date_from or 'all'}_{date_to or 'all'}.csv"
    response = HttpResponse(csv_content, content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


class ReconciliationBatchViewSet(viewsets.ModelViewSet):
    """
    Screen 11: Reconciliation Center - Core, Bank, Subledger and GL matching.
    A finance maker records a reconciliation; only a finance checker may clear its variance.
    """

    serializer_class = ReconciliationBatchSerializer
    http_method_names = NO_DELETE

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "auto_match"):
            return [IsAuthenticated(), HasAnyRole(["finance_maker"])()]
        if self.action == "clear_variance":
            return [IsAuthenticated(), HasAnyRole(["finance_checker"])()]
        return [IsAuthenticated(), HasAnyRole(STAFF_ROLES)()]

    def get_queryset(self):
        queryset = ReconciliationBatch.objects.all()
        pool_id = self.request.query_params.get("pool")
        if pool_id:
            queryset = queryset.filter(pool_id=pool_id)
        return queryset

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.tenant, performed_by=self.request.user)

    @action(detail=True, methods=["post"], url_path="auto-match")
    def auto_match(self, request, pk=None):
        """
        Records the result of a matching run. There is no automatic matcher against a live CBS/GL feed
        (that integration is future scope), so the counts and variance must come from the caller;
        a batch is MATCHED only when every record matched with zero variance.
        """
        batch = self.get_object()
        try:
            matched = int(request.data["matched_records"])
            exceptions = int(request.data["exception_count"])
            variance = Decimal(str(request.data["variance_amount"]))
        except (KeyError, TypeError, ValueError, ArithmeticError):
            raise ValidationError("matched_records, exception_count and variance_amount are required.")
        if matched < 0 or exceptions < 0 or matched + exceptions > batch.total_records:
            raise ValidationError("Matched records and exceptions must not exceed the batch's total records.")
        batch.matched_records = matched
        batch.exception_count = exceptions
        batch.variance_amount = variance
        balanced = matched == batch.total_records and exceptions == 0 and variance == 0
        batch.status = ReconciliationStatus.MATCHED if balanced else batch.status
        batch.control_total_status = "BalancedPASS" if balanced else "VarianceREVIEW"
        log_action(
            tenant=batch.tenant, actor=request.user, action="reconciliation_result", model_name="ReconciliationBatch",
            object_id=str(batch.id), changes={"matched": matched, "exceptions": exceptions, "variance": str(variance)},
            request=request,
        )
        batch.save(
            update_fields=[
                "matched_records",
                "exception_count",
                "variance_amount",
                "status",
                "control_total_status",
                "updated_at",
            ]
        )
        return Response(self.get_serializer(batch).data)

    @action(detail=True, methods=["post"], url_path="clear-variance")
    def clear_variance(self, request, pk=None):
        batch = self.get_object()
        notes = str(request.data.get("notes") or "").strip()
        if not notes:
            raise ValidationError({"notes": ["Explain how the variance was investigated and resolved."]})
        if batch.performed_by_id == request.user.id:
            raise ValidationError("Four-eyes rule: the person who recorded the reconciliation cannot clear it.")
        log_action(
            tenant=batch.tenant, actor=request.user, action="clear_variance", model_name="ReconciliationBatch",
            object_id=str(batch.id), reason=notes, request=request,
        )
        batch.status = ReconciliationStatus.CLEARED
        batch.notes = f"{batch.notes or ''}\n{notes}".strip()
        batch.save(update_fields=["status", "notes", "updated_at"])
        return Response(self.get_serializer(batch).data)



class AccountMappingViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """
    Logical pool account -> enterprise GL account. Finance owns the mapping (BRD 6.1: "Finance
    validates accounting mappings"). Journals already posted keep the names they were posted with.
    """

    serializer_class = AccountMappingSerializer

    def get_queryset(self):
        queryset = AccountMapping.objects.select_related("pool").all()
        pool_id = self.request.query_params.get("pool")
        if pool_id:
            queryset = queryset.filter(pool_id=pool_id)
        return queryset

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update"):
            return [IsAuthenticated(), HasAnyRole(["finance_maker", "finance_checker", "platform_super_admin"])()]
        return [IsAuthenticated(), HasAnyRole(
            ["finance_maker", "finance_checker", "platform_super_admin", "pool_manager", "risk_compliance", "auditor"]
        )()]

    # Maker-checker: these endpoints only PROPOSE a change (HTTP 202); a different finance checker
    # approves it under /governance/config-changes/ and only then is it applied.
    def create(self, request, *args, **kwargs):
        from apps.governance.config_changes import submit_change
        from apps.governance.models import ConfigChangeKind
        from apps.governance.views import ConfigChangeRequestSerializer

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        change = submit_change(kind=ConfigChangeKind.ACCOUNT_MAPPING, serializer=serializer, request=request)
        return Response(ConfigChangeRequestSerializer(change).data, status=202)

    def update(self, request, *args, **kwargs):
        from apps.governance.config_changes import submit_change
        from apps.governance.models import ConfigChangeKind
        from apps.governance.views import ConfigChangeRequestSerializer

        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        change = submit_change(
            kind=ConfigChangeKind.ACCOUNT_MAPPING, serializer=serializer, request=request, instance=instance
        )
        return Response(ConfigChangeRequestSerializer(change).data, status=202)

    @action(detail=False, methods=["get"])
    def catalog(self, request):
        """The logical accounts and which pool models must have them mapped before activation."""
        return Response(
            [
                {
                    "key": key,
                    "default_name": name,
                    "required_for": [model for model, keys in REQUIRED_BY_MODEL.items() if key in keys],
                }
                for key, name in ACCOUNTS.items()
            ]
        )
