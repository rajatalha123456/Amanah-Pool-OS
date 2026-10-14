"""
Role-specific home dashboards (BRD section 13: dashboards by audience).

Every figure is counted or summed from recorded data. A number that cannot be computed is returned as null (the screen shows
"-"), never as a placeholder. Each section lists metrics as {label, value, detail, link, tone}; `tone` is "attention" when the
number is something a person has to act on.
"""

from django.db.models import Sum
from django.utils import timezone

OPEN_EXCEPTION = ("open", "investigating")
OPEN_FINDING_EXCLUDED = ("resolved", "closed", "remediated")


def _m(label, value, detail="", link="", attention=False):
    return {
        "label": label, "value": None if value is None else str(value), "detail": detail, "link": link,
        "tone": "attention" if attention and value not in (None, 0, "0") else "normal",
    }


def _count(items):
    return items.count() if hasattr(items, "count") and callable(getattr(items, "filter", None)) else len(items)


# ---- builders (one per audience) ----------------------------------------------------------------------------------------
def pool_manager(tenant):
    from apps.accounting.models import IncomeExpenseEvent
    from apps.allocation.models import AllocationRun, ProfitSharingRatio
    from apps.pools.models import Asset, DailyBalance, PeriodCloseChecklist, Pool, PoolStatus

    pools = Pool._base_manager.filter(tenant=tenant)
    assets = Asset._base_manager.filter(tenant=tenant)
    by_type = {
        row["asset_type"]: row["total"]
        for row in assets.values("asset_type").annotate(total=Sum("face_value"))
    }
    latest = DailyBalance._base_manager.filter(tenant=tenant).order_by("-value_date").values_list("value_date", flat=True).first()
    funds = (
        DailyBalance._base_manager.filter(tenant=tenant, value_date=latest).aggregate(t=Sum("balance_amount"))["t"] if latest else None
    )
    income = IncomeExpenseEvent._base_manager.filter(tenant=tenant, event_type="income", status="posted").aggregate(t=Sum("amount"))["t"]
    expense = IncomeExpenseEvent._base_manager.filter(tenant=tenant, event_type="expense", status="posted").aggregate(t=Sum("amount"))["t"]
    open_periods = PeriodCloseChecklist._base_manager.filter(tenant=tenant).exclude(status="locked")
    return [
        {"title": "Daily funds and performance", "metrics": [
            _m("Latest recorded daily funds (PKR)", funds, f"as of {latest}" if latest else "no balances imported"),
            _m("Posted income (PKR)", income, "all posted events"),
            _m("Posted direct expenses (PKR)", expense, "all posted events"),
        ]},
        {"title": "Asset mix", "metrics": [
            _m(f"{t.replace('_', ' ').title()} assets (face value, PKR)", total) for t, total in sorted(by_type.items())
        ] or [_m("Assets", None, "none registered")]},
        {"title": "Pending items", "metrics": [
            _m("Pools awaiting activation", _count(pools.filter(status__in=[PoolStatus.DRAFT, PoolStatus.PENDING_APPROVAL, PoolStatus.APPROVED])), link="/pools", attention=True),
            _m("Draft profit-sharing ratios", _count(ProfitSharingRatio._base_manager.filter(tenant=tenant, status="draft")), attention=True),
            _m("Runs in the approval ceremony", _count(AllocationRun._base_manager.filter(tenant=tenant, status__in=["pending_approval", "checked", "shariah_review"])), link="/allocation-engine", attention=True),
            _m("Assets available (not assigned to a pool)", _count(assets.filter(status="available"))),
        ]},
        {"title": "Close readiness", "metrics": [
            _m("Periods not yet locked", _count(open_periods), link="/daily-operations", attention=True),
            _m("Periods certified, awaiting lock", _count(open_periods.filter(status="certified"))),
        ]},
    ]


def finance(tenant):
    from apps.accounting.models import IncomeExpenseEvent, JournalBatch, ReconciliationBatch, SuspenseItem
    from apps.allocation.models import AllocationRun
    from apps.pools.models import AssetProvisionEntry, DailyClose, PeriodCloseChecklist

    last_signed = AllocationRun._base_manager.filter(tenant=tenant, status="signed").order_by("-value_date").first()
    return [
        {"title": "Reconciliation", "metrics": [
            _m("Batches with a flagged variance", _count(ReconciliationBatch._base_manager.filter(tenant=tenant, status="variance_flagged")), link="/daily-operations", attention=True),
            _m("Batches matched or cleared", _count(ReconciliationBatch._base_manager.filter(tenant=tenant, status__in=["matched", "cleared"]))),
        ]},
        {"title": "Suspense", "metrics": [
            _m("Items open in suspense", _count(SuspenseItem._base_manager.filter(tenant=tenant, status__in=["open", "clearing_proposed"])), link="/finance-ledger", attention=True),
            _m("Suspense proposals awaiting a checker", _count(SuspenseItem._base_manager.filter(tenant=tenant, status__in=["proposed", "clearing_proposed"])), link="/finance-ledger", attention=True),
        ]},
        {"title": "Journals and residuals", "metrics": [
            _m("Posted journal batches", _count(JournalBatch._base_manager.filter(tenant=tenant, status="posted")), link="/finance-ledger"),
            _m("Rounding residual of the last signed run (PKR)", last_signed.rounding_residual if last_signed else None, "disclosed rounding account"),
        ]},
        {"title": "Provisions and events awaiting a decision", "metrics": [
            _m("Provision entries pending approval", _count(AssetProvisionEntry._base_manager.filter(tenant=tenant, status="pending")), link="/risk-compliance", attention=True),
            _m("Income / expense events pending posting", _count(IncomeExpenseEvent._base_manager.filter(tenant=tenant, status="pending")), link="/daily-operations", attention=True),
        ]},
        {"title": "Close and restatements", "metrics": [
            _m("Daily closes prepared, awaiting a checker", _count(DailyClose._base_manager.filter(tenant=tenant, status="prepared")), link="/daily-operations", attention=True),
            _m("Daily closes with a failing gate", _count(DailyClose._base_manager.filter(tenant=tenant, status="open")), attention=True),
            _m("Periods not yet locked", _count(PeriodCloseChecklist._base_manager.filter(tenant=tenant).exclude(status="locked"))),
            _m("Restatement reruns awaiting approval", _count(AllocationRun._base_manager.filter(tenant=tenant, is_restatement=True, status__in=["simulated", "pending_approval", "checked", "shariah_review"])), attention=True),
        ]},
    ]


def shariah(tenant):
    from apps.governance.models import ExceptionCase, PurificationEntry, ShariahAuditFinding, ShariahAuditPlan
    from apps.products.models import ContractTemplate, ShariahDecision

    templates = ContractTemplate._base_manager.filter(tenant=tenant, status="approved")
    plans = ShariahAuditPlan._base_manager.filter(tenant=tenant)
    target = plans.aggregate(t=Sum("target_samples_count"))["t"] or 0
    tested = plans.aggregate(t=Sum("tested_samples_count"))["t"] or 0
    today = timezone.localdate()
    open_findings = ShariahAuditFinding._base_manager.filter(tenant=tenant).exclude(status__in=OPEN_FINDING_EXCLUDED)
    oldest = max(((today - f.created_at.date()).days for f in open_findings), default=None)
    return [
        {"title": "Approval queue", "metrics": [
            _m("Rulings in draft awaiting the Board", _count(ShariahDecision._base_manager.filter(tenant=tenant, status="draft")), link="/shariah-governance", attention=True),
            _m("Rulings in force", _count(ShariahDecision._base_manager.filter(tenant=tenant, status="approved"))),
        ]},
        {"title": "Exceptions and purification", "metrics": [
            _m("Open exceptions", _count(ExceptionCase._base_manager.filter(tenant=tenant, status__in=OPEN_EXCEPTION)), link="/shariah-governance", attention=True),
            _m("Non-permissible income awaiting disposition", _count(PurificationEntry._base_manager.filter(tenant=tenant, status="identified")), attention=True),
        ]},
        {"title": "Contract coverage", "metrics": [
            _m("Approved contract templates", _count(templates)),
            _m("... without a Shariah ruling", _count(templates.filter(shariah_decision__isnull=True)), attention=True),
        ]},
        {"title": "Review plan and findings", "metrics": [
            _m("Audit samples tested", f"{tested} of {target}" if target else None, "across all plans"),
            _m("Open findings", _count(open_findings), attention=True),
            _m("Age of the oldest open finding (days)", oldest),
        ]},
    ]


def risk(tenant):
    from apps.governance.models import ExceptionCase, RelatedPartyTransaction
    from apps.participants.models import Participant

    high = ExceptionCase._base_manager.filter(tenant=tenant, status__in=OPEN_EXCEPTION, severity__in=["high", "critical"])
    return [
        {"title": "Limits and breaches", "metrics": [
            _m("High / critical exceptions open", _count(high), link="/risk-compliance", attention=True),
            _m("All open exceptions", _count(ExceptionCase._base_manager.filter(tenant=tenant, status__in=OPEN_EXCEPTION))),
        ]},
        {"title": "KYC and AML", "metrics": [
            _m("Participants with KYC pending", _count(Participant._base_manager.filter(tenant=tenant, kyc_status="pending")), link="/participants", attention=True),
            _m("Participants with KYC rejected", _count(Participant._base_manager.filter(tenant=tenant, kyc_status="rejected"))),
        ]},
        {"title": "Related parties", "metrics": [
            _m("Awaiting review", _count(RelatedPartyTransaction._base_manager.filter(tenant=tenant, disclosure_status="pending_review")), link="/risk-compliance", attention=True),
            _m("Recommended, awaiting elevated approval", _count(RelatedPartyTransaction._base_manager.filter(tenant=tenant, disclosure_status="recommended"))),
            _m("Failed the price test", _count([t for t in RelatedPartyTransaction._base_manager.filter(tenant=tenant) if t.price_test == "failed"]), attention=True),
        ]},
    ]


def auditor(tenant):
    from apps.allocation.models import AllocationRun
    from apps.core.models import AuditLog
    from apps.governance.models import ExceptionCase, ShariahAuditPlan
    from apps.pools.models import PoolVersion

    plans = ShariahAuditPlan._base_manager.filter(tenant=tenant)
    return [
        {"title": "Evidence available", "metrics": [
            _m("Signed allocation runs", _count(AllocationRun._base_manager.filter(tenant=tenant, status="signed")), link="/reports"),
            _m("Pool configuration versions", _count(PoolVersion._base_manager.filter(tenant=tenant))),
            _m("Audit-trail entries", _count(AuditLog._base_manager.filter(tenant=tenant)), link="/reports"),
        ]},
        {"title": "Exceptions and samples", "metrics": [
            _m("Open exceptions", _count(ExceptionCase._base_manager.filter(tenant=tenant, status__in=OPEN_EXCEPTION)), attention=True),
            _m("Audit plans", _count(plans)),
            _m("Samples tested", plans.aggregate(t=Sum("tested_samples_count"))["t"] or 0),
        ]},
    ]


def signatory(tenant):
    from apps.allocation.models import AllocationRun
    from apps.pools.models import PeriodCloseChecklist, Pool

    ready = AllocationRun._base_manager.filter(tenant=tenant, status__in=["checked", "shariah_review"])
    return [
        {"title": "Awaiting your release or lock", "metrics": [
            _m("Runs ready for final release", _count(ready), link="/allocation-engine", attention=True),
            _m("Periods certified, ready to lock", _count(PeriodCloseChecklist._base_manager.filter(tenant=tenant, status="certified")), link="/daily-operations", attention=True),
            _m("Frozen pools to review", _count(Pool._base_manager.filter(tenant=tenant, status="frozen")), attention=True),
        ]},
        {"title": "Released", "metrics": [
            _m("Signed runs", _count(AllocationRun._base_manager.filter(tenant=tenant, status="signed"))),
            _m("Periods locked", _count(PeriodCloseChecklist._base_manager.filter(tenant=tenant, status="locked"))),
        ]},
    ]


def product_manager(tenant):
    from apps.products.models import ContractTemplate, Product

    return [
        {"title": "Products", "metrics": [
            _m("Products in draft", _count(Product._base_manager.filter(tenant=tenant, status="draft")), link="/products-pools", attention=True),
            _m("Awaiting Shariah review", _count(Product._base_manager.filter(tenant=tenant, status="shariah_review"))),
            _m("Approved products", _count(Product._base_manager.filter(tenant=tenant, status__in=["approved", "active"]))),
        ]},
        {"title": "Contract templates", "metrics": [
            _m("Templates in draft", _count(ContractTemplate._base_manager.filter(tenant=tenant, status="draft")), attention=True),
            _m("Approved templates", _count(ContractTemplate._base_manager.filter(tenant=tenant, status="approved"))),
        ]},
    ]


AUDIENCES = {
    "pool_manager": ("Pool manager", pool_manager),
    "finance_maker": ("Finance", finance),
    "finance_checker": ("Finance", finance),
    "shariah_board": ("Shariah", shariah),
    "shariah_secretariat": ("Shariah", shariah),
    "risk_compliance": ("Risk and compliance", risk),
    "auditor": ("Auditor", auditor),
    "authorized_signatory": ("Release and lock", signatory),
    "product_manager": ("Product", product_manager),
}


def home_dashboard(user):
    entry = AUDIENCES.get(user.role)
    if entry is None:
        return None
    title, build = entry
    return {"audience": title, "role": user.role, "sections": build(user.tenant), "generated_at": timezone.now().isoformat()}
