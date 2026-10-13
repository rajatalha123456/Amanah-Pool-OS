"""The business events that notify people (BRD Sections 6, 13). Each call is best-effort."""

from .models import NotificationCategory as C
from .services import notify_email, notify_roles, notify_users

STAFF_ECONOMICS_ROLES = [
    "risk_compliance", "pool_manager", "finance_checker", "finance_maker", "shariah_board", "auditor",
]


# ---- allocation approval ceremony ------------------------------------------------------------
def _run_link(run):
    return f"/allocation-runs/{run.id}"


def _run_label(run):
    return f"{run.pool.code} {run.effective_period_start} to {run.value_date}"


def allocation_submitted(run, actor):
    notify_roles(
        run.tenant, ["finance_checker"], category=C.APPROVAL_REQUIRED, exclude=actor,
        title=f"Allocation run awaiting independent check: {_run_label(run)}",
        body="A maker submitted a profit allocation run for the independent check.",
        link=_run_link(run), related=("AllocationRun", run.id),
    )


def allocation_checked(run, actor):
    if run.shariah_review_required:
        roles, what = ["shariah_secretariat", "shariah_board"], "Shariah review"
    else:
        roles, what = ["authorized_signatory"], "final release"
    notify_roles(
        run.tenant, roles, category=C.APPROVAL_REQUIRED, exclude=actor,
        title=f"Allocation run awaiting {what}: {_run_label(run)}",
        body="The independent check is complete.", link=_run_link(run), related=("AllocationRun", run.id),
    )


def allocation_shariah_reviewed(run, actor):
    notify_roles(
        run.tenant, ["authorized_signatory"], category=C.APPROVAL_REQUIRED, exclude=actor,
        title=f"Allocation run awaiting final release: {_run_label(run)}",
        body="The Shariah review is complete.", link=_run_link(run), related=("AllocationRun", run.id),
    )


def allocation_released(run, actor):
    notify_users(
        run.tenant, [run.created_by, run.checked_by], category=C.APPROVAL_OUTCOME, exclude=actor,
        title=f"Allocation run released: {_run_label(run)}",
        body="The run was signed and its journal posted.", link=_run_link(run), related=("AllocationRun", run.id),
    )


def allocation_rejected(run, actor, reason):
    notify_users(
        run.tenant, [run.created_by, run.checked_by], category=C.APPROVAL_OUTCOME, exclude=actor,
        title=f"Allocation run rejected: {_run_label(run)}",
        body=f"Reason: {reason}", link=_run_link(run), related=("AllocationRun", run.id),
    )


# ---- investment distributions ----------------------------------------------------------------
def distribution_submitted(run, actor):
    notify_roles(
        run.tenant, ["finance_checker"], category=C.APPROVAL_REQUIRED, exclude=actor,
        title=f"Profit distribution awaiting approval: {run.pool.code} {run.period_start} to {run.period_end}",
        body="A maker submitted an investment-pool profit distribution.", link="/investments",
        related=("InvestmentDistributionRun", run.id),
    )


def distribution_checked(run, actor):
    notify_roles(
        run.tenant, ["shariah_secretariat", "shariah_board"], category=C.APPROVAL_REQUIRED, exclude=actor,
        title=f"Profit distribution awaiting Shariah review: {run.pool.code} {run.period_start} to {run.period_end}",
        body="The independent check is complete.", link="/investments", related=("InvestmentDistributionRun", run.id),
    )


def distribution_shariah_reviewed(run, actor):
    notify_roles(
        run.tenant, ["authorized_signatory"], category=C.APPROVAL_REQUIRED, exclude=actor,
        title=f"Profit distribution awaiting final release: {run.pool.code} {run.period_start} to {run.period_end}",
        body="Independent check and Shariah review are complete.", link="/investments",
        related=("InvestmentDistributionRun", run.id),
    )


def distribution_decided(run, actor, approved, reason=""):
    notify_users(
        run.tenant, [run.created_by], category=C.APPROVAL_OUTCOME, exclude=actor,
        title=f"Profit distribution {'approved' if approved else 'rejected'}: {run.pool.code}",
        body="" if approved else f"Reason: {reason}", link="/investments",
        related=("InvestmentDistributionRun", run.id),
    )


# ---- community-circle payouts ----------------------------------------------------------------
def payout_requested(payout, actor):
    notify_roles(
        payout.tenant, ["finance_checker"], category=C.APPROVAL_REQUIRED, exclude=actor,
        title=f"Circle payout awaiting approval: {payout.pool.code} cycle {payout.cycle_number}",
        body=f"{payout.member.member_name} - PKR {payout.amount}", link="/community-circles",
        related=("Payout", payout.id),
    )


def payout_decided(payout, actor, outcome, reason=""):
    notify_users(
        payout.tenant, [payout.requested_by], category=C.APPROVAL_OUTCOME, exclude=actor,
        title=f"Circle payout {outcome}: {payout.pool.code} cycle {payout.cycle_number}",
        body=reason, link="/community-circles", related=("Payout", payout.id),
    )


# ---- pools -----------------------------------------------------------------------------------
def pool_submitted(pool, actor):
    notify_roles(
        pool.tenant, ["shariah_board"], category=C.APPROVAL_REQUIRED, exclude=actor,
        title=f"Pool awaiting Shariah approval: {pool.code}", body=pool.name, link=f"/pools/{pool.id}",
        related=("Pool", pool.id),
    )


def pool_approved(pool, actor):
    notify_roles(
        pool.tenant, ["pool_manager"], category=C.APPROVAL_OUTCOME, exclude=actor,
        title=f"Pool approved by the Shariah Board: {pool.code}", body="The pool can now be activated.",
        link=f"/pools/{pool.id}", related=("Pool", pool.id),
    )


# ---- arrears (BRD 6.5: respectful reminders) --------------------------------------------------
def arrears_flagged(arrears, actor):
    member = arrears.member
    notify_roles(
        arrears.tenant, ["risk_compliance", "pool_manager"], category=C.ARREARS_REMINDER, exclude=actor,
        title=f"Arrears recorded: {member.member_reference} cycle {arrears.cycle_number}",
        body=f"{member.member_name} has an outstanding contribution of PKR {arrears.expected_amount}.",
        link="/community-circles", related=("ArrearsRecord", arrears.id),
    )
    notify_email(
        arrears.tenant, member.email, category=C.ARREARS_REMINDER, related=("ArrearsRecord", arrears.id),
        title=f"Gentle reminder: contribution for cycle {arrears.cycle_number}",
        body=(
            f"Assalamu alaikum {member.member_name},\n\n"
            f"Our records show your contribution of PKR {arrears.expected_amount} for cycle {arrears.cycle_number} "
            "is still outstanding. If you have already paid, please disregard this note. If you are facing "
            "difficulty, please contact your circle organizer - hardship support is available and no penalty "
            "or additional charge applies.\n\nJazakAllah khair."
        ),
    )


# ---- economics change notice (BR-003) ---------------------------------------------------------
def economics_change(pool, actor, *, summary, impact, effective_from, notice_days):
    from apps.participants.models import ParticipantAccount

    body = (
        f"{summary}\nEffective from {effective_from} (notice period {notice_days} days).\n"
        f"Impact simulated on the last signed period: {impact}"
    )
    title = f"Pool economics change: {pool.code} effective {effective_from}"
    notify_roles(
        pool.tenant, STAFF_ECONOMICS_ROLES, category=C.ECONOMICS_CHANGE, exclude=actor, title=title,
        body=body, link=f"/pools/{pool.id}", related=("Pool", pool.id),
    )

    participants = {
        account.participant_id: account.participant
        for account in ParticipantAccount.objects.filter(pool=pool).select_related("participant__user")
    }.values()
    customer_body = (
        f"The profit-sharing terms of {pool.name} will change from {effective_from}. {summary} "
        "Please contact your relationship manager with any question."
    )
    for participant in participants:
        if participant.user_id:
            notify_users(
                pool.tenant, [participant.user], category=C.ECONOMICS_CHANGE, title=title,
                body=customer_body, related=("Pool", pool.id),
            )
        notify_email(
            pool.tenant, participant.email, category=C.ECONOMICS_CHANGE, title=title, body=customer_body,
            related=("Pool", pool.id),
        )


# ---- Musharakah negligence cases (BR-006) -----------------------------------------------------
def negligence_opened(case, actor):
    notify_roles(
        case.tenant, ["shariah_board", "risk_compliance"], category=C.APPROVAL_REQUIRED, exclude=actor,
        title=f"Negligence investigation opened: {case.pool.code}",
        body=f"{case.title}. Loss allocation for {case.period_start} to {case.period_end} is frozen until the Shariah Board determines the case.",
        link="/investments", related=("NegligenceCase", case.id),
    )


def negligence_determined(case, actor):
    verdict = (
        f"manager liable for PKR {case.liability_amount}" if case.status == "liable" else "manager cleared"
    )
    notify_roles(
        case.tenant, ["pool_manager", "risk_compliance", "finance_checker", "finance_maker"],
        category=C.APPROVAL_OUTCOME, exclude=actor, title=f"Negligence case determined: {case.pool.code} - {verdict}",
        body=case.determination_note, link="/investments", related=("NegligenceCase", case.id),
    )


# ---- governance configuration changes (maker-checker) -----------------------------------------
def config_change_submitted(change, actor):
    approvers = ["finance_checker", "authorized_signatory"] if change.kind == "rule_pack" else ["finance_checker"]
    notify_roles(
        change.tenant, approvers, category=C.APPROVAL_REQUIRED, exclude=actor,
        title=f"Configuration change awaiting approval: {change.get_kind_display()}",
        body=f"{change.get_operation_display()} proposed. Reason: {change.reason}", link="/governance-config",
        related=("ConfigChangeRequest", change.id),
    )
