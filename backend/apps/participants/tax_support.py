"""Tax and Zakat support for a participant (BRD 13: "tax/Zakat support" on the investor dashboard)."""

from decimal import Decimal

from apps.allocation.models import PayoutBatchRecord

from .models import Participant


def tax_support_for(user):
    """
    What the payout batches computed for this participant: gross profit, withholding at the pack's rate and Zakat
    where the pack enables it. These are computed amounts; the bank's own advice shows what was actually deducted.
    """
    participant = Participant.objects.filter(user=user).first()
    if participant is None:
        return None
    rows = []
    for batch in PayoutBatchRecord.objects.select_related("allocation_run__pool").order_by("-allocation_run__value_date"):
        for t in (batch.payload or {}).get("transactions", []):
            if participant.cnic_ntn and t.get("cnic_ntn") == participant.cnic_ntn and t.get("beneficiary_name") == participant.full_name:
                rows.append({
                    "period_end": str(batch.allocation_run.value_date), "pool": batch.allocation_run.pool.code,
                    "batch_status": batch.status, "gross_profit": str(Decimal(str(t["gross_profit"])).quantize(Decimal("0.01"))),
                    "tax_status": t.get("tax_status"), "wht_rate_pct": t.get("wht_rate_pct"),
                    "wht_amount": str(Decimal(str(t["wht_amount"])).quantize(Decimal("0.01"))),
                    "zakat_amount": str(Decimal(str(t["zakat_amount"])).quantize(Decimal("0.01"))),
                    "net_payout": str(Decimal(str(t["net_payout"])).quantize(Decimal("0.01"))),
                })
    total = lambda key: str(sum((Decimal(r[key]) for r in rows), Decimal("0")).quantize(Decimal("0.01")))  # noqa: E731
    return {
        "participant": participant.reference, "tax_status": participant.tax_status, "zakat_exempt": participant.zakat_exempt,
        "rows": rows, "totals": {"gross_profit": total("gross_profit"), "wht_amount": total("wht_amount"), "zakat_amount": total("zakat_amount")},
        "note": "Amounts are as computed in the payout batch of each period. Your bank advice shows what was actually deducted.",
    }
