"""
Contribution reminders for community circles (BRD 6.5: arrears -> respectful reminders).

Run daily (`python manage.py send_contribution_reminders`). For each open circle whose published rules carry a
first due date, cycle n is due on first_due_date + (n - 1) * cycle_days. A member who has not paid:
  - gets a gentle reminder in the days before a due date, and again once it has passed (e-mail if an address is
    held, plus in-app if they have a login);
  - when overdue, is also listed for Risk & Compliance / the pool manager, who decide whether to open an arrears
    record - nothing is flagged automatically and no penalty is ever added.
Each (member, cycle, kind) is sent once.
"""

from datetime import timedelta

from apps.core.context import set_current_tenant
from apps.notifications.models import Notification, NotificationCategory as C
from apps.notifications.services import notify_email, notify_roles, notify_users
from apps.pools.models import Pool, PoolStatus

from .models import CircleMember, CircleMemberStatus, Contribution, ContributionStatus
from .rules import current_rules

RELATED = "ContributionReminder"


def cycle_due_date(rules, cycle):
    return rules.first_due_date + timedelta(days=(cycle - 1) * rules.cycle_days)


def cycle_status(rules, today, total_cycles, days_before):
    """
    The cycles worth a reminder today as [(cycle, due_date, kind)]: the most recent cycle whose due date has passed
    ("overdue", for members who have not paid it) and the next cycle if it falls due within `days_before` days.
    A due date that is today still counts as upcoming; it is overdue from the next day.
    """
    if rules.first_due_date is None:
        return []
    passed = 0
    if today >= rules.first_due_date:
        passed = (today - rules.first_due_date).days // rules.cycle_days + 1
        if cycle_due_date(rules, passed) == today:
            passed -= 1
    out = []
    if 1 <= passed <= total_cycles:
        out.append((passed, cycle_due_date(rules, passed), "overdue"))
    upcoming = passed + 1
    if upcoming <= total_cycles and 0 <= (cycle_due_date(rules, upcoming) - today).days <= days_before:
        out.append((upcoming, cycle_due_date(rules, upcoming), "upcoming"))
    return out


def _already_sent(tenant, key):
    return Notification._base_manager.filter(tenant=tenant, related_model=RELATED, related_id=key).exists()


def _message(member, pool, rules, cycle, due, kind):
    if kind == "upcoming":
        return (
            f"Contribution for cycle {cycle} is due on {due}",
            f"Assalamu alaikum {member.member_name}, a gentle reminder that your contribution of "
            f"PKR {rules.contribution_amount} for {pool.name} is due on {due}. If you have already paid, "
            "please disregard this note.",
        )
    return (
        f"Gentle reminder: cycle {cycle} contribution",
        f"Assalamu alaikum {member.member_name}, our records show your contribution of "
        f"PKR {rules.contribution_amount} for {pool.name} (due {due}) is still outstanding. If you have "
        "paid, please disregard this note. If you are facing difficulty, contact your circle organizer - "
        "hardship support is available and no penalty or additional charge applies.",
    )


def _deliver(pool, member, key, title, body):
    related = (RELATED, key)
    if member.user_id:
        notify_users(pool.tenant, [member.user], category=C.ARREARS_REMINDER, title=title, body=body, link="/",
                     related=related, email=bool(member.user.email))
    elif member.email:
        notify_email(pool.tenant, member.email, category=C.ARREARS_REMINDER, title=title, body=body, related=related)
    else:
        # Nobody to write to: still record that the reminder was due so staff can follow up.
        Notification._base_manager.create(
            tenant=pool.tenant, category=C.ARREARS_REMINDER, title=title, body=body, related_model=RELATED, related_id=key
        )


def _remind_cycle(pool, rules, members, cycle, due, kind, today):
    paid = set(
        Contribution._base_manager.filter(member__pool=pool, cycle_number=cycle, status=ContributionStatus.RECEIVED)
        .values_list("member_id", flat=True)
    )
    count, overdue_refs = 0, []
    for member in members:
        key = f"{member.id}:{cycle}:{kind}"
        if member.id in paid or _already_sent(pool.tenant, key):
            continue
        title, body = _message(member, pool, rules, cycle, due, kind)
        _deliver(pool, member, key, title, body)
        count += 1
        if kind == "overdue":
            overdue_refs.append(member.member_reference)
    if overdue_refs:
        notify_roles(
            pool.tenant, ["risk_compliance", "pool_manager"], category=C.ARREARS_REMINDER,
            title=f"{len(overdue_refs)} overdue contribution(s) in {pool.name}, cycle {cycle}",
            body="Members: " + ", ".join(sorted(overdue_refs)) + ". Review and open an arrears record if needed.",
            link="/community-circles", related=(RELATED, f"{pool.id}:{cycle}:{today}"),
        )
    return count


def send_reminders(today, days_before=3):
    sent = {"upcoming": 0, "overdue": 0}
    pools = Pool._base_manager.filter(status=PoolStatus.OPEN, product__operating_model="community_circle")
    try:
        for pool in pools:
            set_current_tenant(pool.tenant)
            rules = current_rules(pool)
            if rules is None or rules.first_due_date is None:
                continue
            members = list(
                CircleMember._base_manager.filter(
                    pool=pool, status__in=[CircleMemberStatus.ACTIVE, CircleMemberStatus.PAID_OUT]
                ).select_related("user")
            )
            for cycle, due, kind in cycle_status(rules, today, len(members), days_before):
                sent[kind] += _remind_cycle(pool, rules, members, cycle, due, kind, today)
    finally:
        set_current_tenant(None)
    return sent
