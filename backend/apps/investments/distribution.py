"""
Mudarabah profit distribution engine for investment pools (BRD 6.4 / 7.1).

calculate_distribution() performs no writes. Rules:

* Distributable result = gross income - approved direct expenses.
* Profit: the Mudarib (manager) receives its approved PSR share of the
  profit - a share of profit, never of capital. The rest goes to the investors
  (Rabb-ul-Maal), shared pro-rata to each capital account's *time-weighted
  units* over the period (units held on each day, averaged), so someone who
  joined late or redeemed early earns only for the days they were invested.
* Loss: borne by the investors alone, pro-rata to the same units. The Mudarib
  bears no capital loss (its loss is its effort) and takes no share.
* Calculated at full precision; rounded to 2dp only at output. Whatever the
  roundings leave over is returned as `rounding_residual` (disclosed rounding
  account) and never silently pushed onto an investor.
"""

import hashlib
import json
from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.db.models import Q

from apps.allocation.models import PSRStatus, ProfitSharingRatio

from .models import CapitalAccount, NAVSnapshot, NAVSnapshotStatus, UnitMovement
from .negligence import liability_total, liable_cases, open_cases

TWO_PLACES = Decimal("0.01")
UNIT_PLACES = Decimal("0.000001")
RATIO_PLACES = Decimal("0.000000000001")
HUNDRED = Decimal("100")
MAX_PERIOD_DAYS = 366


def _round(value):
    return Decimal(value).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def average_units(account, movements, days):
    """
    Average units held by `account` over `days`. Opening units are derived as the
    current balance less every recorded movement, so accounts that pre-date the
    movement ledger are treated as holding their opening units from the start.
    """

    base = Decimal(account.units_held) - sum((m.units_delta for m in movements), Decimal("0"))
    total = Decimal("0")
    for day in days:
        held = base + sum((m.units_delta for m in movements if m.effective_date <= day), Decimal("0"))
        total += max(held, Decimal("0"))
    return total / Decimal(len(days))


def calculate_distribution(pool, period_start, period_end, gross_income, direct_expenses, replaces_run=None):
    """
    Contract-aware distribution of an investment pool:

    * Mudarabah  - manager (Mudarib) takes its PSR share of profit; a loss falls on the investors only.
    * Wakalah    - the agent earns a fee on average invested funds whatever the result; the rest is shared
                   (the PSR Mudarib share is an incentive on profit after the fee) or, in a loss, borne by
                   the investors.
    * Musharakah - profit follows the PSR (managing partner vs investors); a loss follows the *capital
                   ratio* of all partners, the managing partner's own capital included (BR-006), except
                   the part a Shariah-Board liability determination assigns to the manager. A loss is
                   frozen while a negligence investigation covering the period is open.
    """

    if pool.product.operating_model != "investment_pool":
        raise ValueError("Profit distribution is only available for investment pools.")
    if period_start > period_end:
        raise ValueError("period_start cannot be after period_end.")
    days = [period_start + timedelta(days=i) for i in range((period_end - period_start).days + 1)]
    if len(days) > MAX_PERIOD_DAYS:
        raise ValueError(f"A distribution period cannot exceed {MAX_PERIOD_DAYS} days.")

    contract_type = pool.product.contract_template.contract_type
    is_musharakah = contract_type == "musharakah"
    is_wakalah = contract_type == "wakalah"

    gross_income = Decimal(gross_income)
    direct_expenses = Decimal(direct_expenses)
    distributable = gross_income - direct_expenses

    def psr_on(day):
        return (
            ProfitSharingRatio.objects.filter(pool=pool, status=PSRStatus.APPROVED, effective_from__lte=day)
            .filter(Q(effective_to__isnull=True) | Q(effective_to__gte=day))
            .first()
        )

    psr = psr_on(period_end)
    if psr is None:
        raise ValueError(f"No approved profit-sharing ratio found for pool={pool} on {period_end}.")
    start_psr = psr_on(period_start)
    if start_psr is None or start_psr.pk != psr.pk:
        raise ValueError(
            "The approved profit-sharing ratio changes within this period; split the distribution at the change date."
        )

    movements_by_account = {}
    for movement in UnitMovement.objects.filter(capital_account__pool=pool):
        movements_by_account.setdefault(movement.capital_account_id, []).append(movement)

    investor_entries, manager_units = [], Decimal("0")
    for account in CapitalAccount.objects.filter(pool=pool).order_by("investor_reference"):
        avg = average_units(account, movements_by_account.get(account.id, []), days)
        if avg <= 0:
            continue
        if is_musharakah and account.is_managing_partner:
            manager_units += avg
        else:
            investor_entries.append((account, avg))
    if not investor_entries:
        raise ValueError(f"No investor units were held in pool={pool} between {period_start} and {period_end}.")

    investor_units = sum((avg for _, avg in investor_entries), Decimal("0"))
    total_units = investor_units + manager_units

    # Wakalah fee on the average invested funds, valued at the latest published NAV.
    wakalah_fee_raw = Decimal("0")
    nav_used = None
    if is_wakalah and Decimal(psr.wakalah_fee_pct) > 0:
        nav = (
            NAVSnapshot.objects.filter(pool=pool, status=NAVSnapshotStatus.PUBLISHED, valuation_date__lte=period_end)
            .order_by("-valuation_date")
            .first()
        )
        if nav is None:
            raise ValueError("A published NAV on or before the period end is needed to value funds for the Wakalah fee.")
        nav_used = nav
        wakalah_fee_raw = (
            total_units * nav.nav_per_unit * Decimal(psr.wakalah_fee_pct) / HUNDRED * Decimal(len(days)) / Decimal(365)
        )

    result = distributable - wakalah_fee_raw
    is_loss = result < 0
    applied_cases = []

    if is_loss and is_musharakah:
        blocking = open_cases(pool, period_start, period_end)
        if blocking:
            raise ValueError(
                f"Loss allocation is frozen: negligence case '{blocking[0].title}' is still under investigation "
                f"for this period. A Shariah-Board determination is needed first."
            )

    if is_musharakah:
        if is_loss:
            applied_cases = liable_cases(pool, period_start, period_end, replaces_run)
            manager_liability = -liability_total(applied_cases, abs(result))  # negative: borne by the manager
            remaining = result - manager_liability  # still negative; shared by capital ratio
            manager_ratio = manager_units / total_units
            manager_raw = manager_liability + remaining * manager_ratio
            investor_raw = remaining * (1 - manager_ratio)
        else:
            manager_raw = result * Decimal(psr.mudarib_share) / HUNDRED
            investor_raw = result * Decimal(psr.depositor_share) / HUNDRED
    elif is_loss:
        manager_raw = wakalah_fee_raw  # zero for Mudarabah: the Mudarib never shares a capital loss
        investor_raw = result  # negative: borne by the capital providers only
    else:
        manager_raw = wakalah_fee_raw + result * Decimal(psr.mudarib_share) / HUNDRED
        investor_raw = result * Decimal(psr.depositor_share) / HUNDRED

    lines = []
    for account, avg in investor_entries:
        ratio = avg / investor_units
        lines.append(
            {
                "capital_account_id": str(account.id),
                "investor_reference": account.investor_reference,
                "investor_name": account.investor_name,
                "average_units": avg.quantize(UNIT_PLACES, rounding=ROUND_HALF_UP),
                "share_ratio": ratio.quantize(RATIO_PLACES, rounding=ROUND_HALF_UP),
                "allocated_amount": _round(investor_raw * ratio),
            }
        )

    distributable_r = _round(distributable)
    manager_share = _round(manager_raw)
    residual = distributable_r - (manager_share + sum((l["allocated_amount"] for l in lines), Decimal("0")))
    tolerance = TWO_PLACES * (len(lines) + 2)
    if abs(residual) > tolerance:
        raise ValueError(f"Rounding residual {residual} exceeds the permitted tolerance {tolerance}.")

    return {
        "distributable": distributable_r,
        "investor_share": _round(investor_raw),
        "manager_share": manager_share,
        "rounding_residual": residual,
        "total_average_units": investor_units.quantize(UNIT_PLACES, rounding=ROUND_HALF_UP),
        "is_loss": is_loss,
        "config_snapshot": {
            "contract_type": contract_type,
            "psr": {
                "id": str(psr.id),
                "investor_share": str(psr.depositor_share),
                "manager_share": str(psr.mudarib_share),
                "wakalah_fee_pct": str(psr.wakalah_fee_pct),
                "effective_from": psr.effective_from.isoformat(),
            },
            "period": {"start": period_start.isoformat(), "end": period_end.isoformat(), "days": len(days)},
            "wakalah": (
                {
                    "fee_pct": str(psr.wakalah_fee_pct),
                    "fee_amount": str(_round(wakalah_fee_raw)),
                    "nav_per_unit": str(nav_used.nav_per_unit) if nav_used else None,
                    "nav_date": nav_used.valuation_date.isoformat() if nav_used else None,
                }
                if is_wakalah
                else None
            ),
            "musharakah": (
                {
                    "manager_capital_units": str(manager_units.quantize(UNIT_PLACES)),
                    "total_capital_units": str(total_units.quantize(UNIT_PLACES)),
                    "manager_capital_ratio": str((manager_units / total_units).quantize(RATIO_PLACES)),
                    "liability_cases": [
                        {"id": str(case.id), "title": case.title, "liability_amount": str(case.liability_amount)}
                        for case in applied_cases
                    ],
                }
                if is_musharakah
                else None
            ),
        },
        "lines": lines,
    }


def run_hash_payload(run):
    lines = sorted(run.lines.all(), key=lambda line: str(line.capital_account_id))
    payload = {
        "pool_id": str(run.pool_id),
        "period_start": run.period_start.isoformat(),
        "period_end": run.period_end.isoformat(),
        "gross_income": str(run.gross_income),
        "direct_expenses": str(run.direct_expenses),
        "distributable": str(run.distributable_amount),
        "investor_share": str(run.investor_share),
        "manager_share": str(run.manager_share),
        "rounding_residual": str(run.rounding_residual),
        "total_average_units": str(run.total_average_units),
        "is_loss": bool(run.is_loss),
        "config_snapshot": run.config_snapshot or {},
        "lines": [
            {
                "capital_account_id": str(line.capital_account_id),
                "average_units": str(line.average_units),
                "share_ratio": str(line.share_ratio),
                "allocated_amount": str(line.allocated_amount),
            }
            for line in lines
        ],
    }
    if run.replaces_run_id:
        payload["restatement_of"] = str(run.replaces_run_id)
    return payload


def compute_run_hash(run):
    serialized = json.dumps(run_hash_payload(run), sort_keys=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
