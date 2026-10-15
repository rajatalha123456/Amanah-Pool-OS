"""
Control alerts (BRD 14, observability): what has been left undone for too long. Every alert is counted from recorded data
and names the screen where it is resolved. Nothing is estimated.
"""

from datetime import timedelta

from django.utils import timezone


def _alert(code, severity, title, count, link, detail=""):
    return {"code": code, "severity": severity, "title": title, "count": count, "link": link, "detail": detail}


def build_alerts(tenant, today=None):
    from apps.accounting.models import SuspenseItem
    from apps.governance.models import ConfigChangeRequest
    from apps.pools.models import DailyClose, Pool
    from apps.tenants.models import EncryptionKeyRecord

    today = today or timezone.localdate()
    alerts = []

    stale_changes = ConfigChangeRequest._base_manager.filter(
        tenant=tenant, status="pending", created_at__lt=timezone.now() - timedelta(days=3)
    ).count()
    if stale_changes:
        alerts.append(_alert("config_change_waiting", "warning", "Proposed configuration changes waiting more than 3 days",
                             stale_changes, "/governance-config", "A different approver has not yet decided them."))

    old_suspense = SuspenseItem._base_manager.filter(
        tenant=tenant, status__in=["open", "clearing_proposed"], opened_on__lt=today - timedelta(days=30)
    ).count()
    if old_suspense:
        alerts.append(_alert("suspense_ageing", "critical", "Suspense items older than 30 days", old_suspense,
                             "/finance-ledger", "Unexplained money must be cleared before the period closes."))

    unsigned = 0
    for pool in Pool._base_manager.filter(tenant=tenant, status="open"):
        latest = DailyClose._base_manager.filter(pool=pool, status="signed").order_by("-value_date").values_list("value_date", flat=True).first()
        if latest is None or latest < today - timedelta(days=3):
            unsigned += 1
    if unsigned:
        alerts.append(_alert("daily_close_late", "warning", "Open pools with no signed daily close in the last 3 days", unsigned,
                             "/daily-operations", "A run cannot be checked or released without a signed close."))

    overdue_keys = [k for k in EncryptionKeyRecord.objects.filter(tenant=tenant, is_active=True) if k.overdue]
    if overdue_keys:
        alerts.append(_alert("key_rotation_overdue", "critical", "Encryption keys past their rotation date", len(overdue_keys),
                             "/administration", ", ".join(k.purpose for k in overdue_keys)[:200]))

    order = {"critical": 0, "warning": 1}
    return sorted(alerts, key=lambda a: order[a["severity"]])
