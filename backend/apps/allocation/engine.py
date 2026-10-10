"""
Pure profit-allocation calculation engine.

calculate_allocation() performs no database writes - it only reads
DailyBalance/WeightageBand/ProfitSharingRatio/ReservePolicy and returns a
plain dict of computed values. Persisting the result into AllocationRun/
AllocationLine is the caller's responsibility (see apps/allocation/views.py).

All monetary/ratio arithmetic uses Decimal, never float. Calculation is done
at full precision and amounts are rounded to 2 decimal places (ROUND_HALF_UP)
only at the output stage (BRD 7.3). Whatever the independent roundings do not
add up to is returned as `rounding_residual` so that

    distributable == per + irr + mudarib + sum(line allocations) + residual

always holds exactly; the residual is posted to the disclosed pool rounding
account, never silently absorbed by (or pushed to) an arbitrary participant.
"""

import hashlib
import json
from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.db.models import Q

from apps.pools.models import DailyBalance, DailyBalanceStatus

from .models import (
    PSRStatus,
    ProfitSharingRatio,
    ReservePolicy,
    ReserveType,
    WeightageBand,
    WeightageBandStatus,
)

TWO_PLACES = Decimal("0.01")
HUNDRED = Decimal("100")

# End-of-day balances are not delivered for non-business days; an account's
# last known balance is carried forward over such gaps. The look-back window
# only bounds how far before the period start we search for the opening balance.
CARRY_FORWARD_DAYS = 10
MAX_PERIOD_DAYS = 366


def _days_between(start, end):
    return [start + timedelta(days=offset) for offset in range((end - start).days + 1)]


def _load_entities(pool, start, end):
    """
    Groups the pool's end-of-day balances by participant account (or, for
    legacy rows without an account, by participant class) and returns
    {key: {"account", "participant_class", "series": {date: Decimal}}}.
    """

    rows = (
        DailyBalance.objects.filter(
            pool=pool,
            value_date__gte=start - timedelta(days=CARRY_FORWARD_DAYS),
            value_date__lte=end,
        )
        .exclude(status=DailyBalanceStatus.REJECTED)
        .select_related("account__participant")
    )

    entities = {}
    for row in rows:
        if row.account_id:
            key = ("account", str(row.account_id))
            participant_class = row.account.participant.participant_class
            account = row.account
        else:
            key = ("class", row.participant_class)
            participant_class = row.participant_class
            account = None

        entity = entities.setdefault(
            key, {"account": account, "participant_class": participant_class, "series": {}}
        )
        entity["series"][row.value_date] = entity["series"].get(row.value_date, Decimal("0")) + Decimal(
            row.balance_amount
        )
    return entities


def _daily_balances(entity, days, start):
    """Balance of the entity on each day of the period (last known balance carried forward)."""

    series = entity["series"]
    account = entity["account"]
    prior_dates = [d for d in series if d < start]
    last = series[max(prior_dates)] if prior_dates else Decimal("0")

    balances = []
    for day in days:
        if day in series:
            last = series[day]
        balance = last
        if account is not None:
            if day < account.opened_date or (account.closed_date and day > account.closed_date):
                balance = Decimal("0")
        balances.append(balance)
    return balances


def _round(value):
    return Decimal(value).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def _covers_date(value_date):
    """Q for `effective_from <= value_date <= (effective_to or infinity)`."""
    return Q(effective_from__lte=value_date) & (
        Q(effective_to__isnull=True) | Q(effective_to__gte=value_date)
    )


def reserve_headroom(policy, total_daily_funds):
    """
    Room left in a reserve before it reaches its cap. `cap_percentage` is the
    maximum reserve balance expressed as a percentage of total daily funds of
    the pool; a cap of 0 (or less) means the reserve is uncapped.
    """

    cap_pct = Decimal(policy.cap_percentage)
    if cap_pct <= 0:
        return None
    cap_amount = Decimal(total_daily_funds) * cap_pct / HUNDRED
    return max(Decimal("0"), cap_amount - Decimal(policy.current_balance))


def _reserve_amount(policy, base, total_daily_funds):
    """Full-precision reserve appropriation, limited by the policy's cap."""

    if policy is None or Decimal(policy.rate_percentage) <= 0 or base <= 0:
        return Decimal("0")

    amount = base * Decimal(policy.rate_percentage) / HUNDRED
    headroom = reserve_headroom(policy, total_daily_funds)
    if headroom is not None:
        amount = min(amount, headroom)
    return amount


def calculate_allocation(pool, value_date, gross_income, direct_expenses, period_start=None):
    """
    Returns a dict with all computed values; does NOT save anything to DB.

    The allocation covers the period [period_start, value_date] (a single day
    when period_start is omitted). Each participant account's *daily weighted
    funds* are averaged over the period - daily balance x the weightage band
    effective on that day - and profit is shared pro-rata to that average.

    Return shape:
        {
            "distributable": Decimal,
            "total_weighted_funds": Decimal,
            "depositor_pool_share": Decimal,
            "mudarib_share": Decimal,
            "per_amount": Decimal,
            "irr_amount": Decimal,
            "rounding_residual": Decimal,
            "is_loss": bool,
            "config_snapshot": dict,   # JSON-safe record of every rule used
            "lines": [
                {
                    "participant_class": str,
                    "daily_funds": Decimal,
                    "weightage": Decimal,
                    "weighted_funds": Decimal,
                    "allocated_amount": Decimal,
                },
                ...
            ],
        }

    Raises ValueError if: no DailyBalance found for (pool, value_date), no
    approved WeightageBand covers value_date for some participant_class
    that has a balance, no approved PSR covers value_date, or
    total_weighted_funds works out to zero (division-by-zero guard).
    """

    gross_income = Decimal(gross_income)
    direct_expenses = Decimal(direct_expenses)
    distributable = gross_income - direct_expenses

    period_start = period_start or value_date
    if period_start > value_date:
        raise ValueError("period_start cannot be after the period end date.")
    days = _days_between(period_start, value_date)
    if len(days) > MAX_PERIOD_DAYS:
        raise ValueError(f"An allocation period cannot exceed {MAX_PERIOD_DAYS} days.")
    day_count = Decimal(len(days))

    entities = _load_entities(pool, period_start, value_date)
    if not entities:
        raise ValueError(
            f"No DailyBalance records found for pool={pool} between {period_start} and {value_date}."
        )

    bands_by_class = {}
    for band in WeightageBand.objects.filter(
        pool=pool, status=WeightageBandStatus.APPROVED, effective_from__lte=value_date
    ).filter(Q(effective_to__isnull=True) | Q(effective_to__gte=period_start)):
        bands_by_class.setdefault(band.participant_class, []).append(band)

    def band_for(participant_class, day):
        for band in bands_by_class.get(participant_class, []):
            if band.effective_from <= day and (band.effective_to is None or band.effective_to >= day):
                return band
        return None

    lines_input = []
    used_bands = {}
    for entity in sorted(
        entities.values(),
        key=lambda e: (e["participant_class"], e["account"].account_number if e["account"] else ""),
    ):
        participant_class = entity["participant_class"]
        sum_balance = Decimal("0")
        sum_weighted = Decimal("0")
        for day, balance in zip(days, _daily_balances(entity, days, period_start)):
            if balance <= 0:
                continue
            band = band_for(participant_class, day)
            if band is None:
                raise ValueError(
                    f"No approved WeightageBand found for participant_class="
                    f"'{participant_class}' on {day}."
                )
            used_bands[str(band.id)] = band
            sum_balance += balance
            sum_weighted += balance * Decimal(band.weightage)

        if sum_balance == 0:
            continue

        average_funds = sum_balance / day_count
        average_weighted = sum_weighted / day_count
        account = entity["account"]
        lines_input.append(
            {
                "participant_class": participant_class,
                "account": account,
                "daily_funds": average_funds,
                "weightage": (average_weighted / average_funds).quantize(TWO_PLACES, rounding=ROUND_HALF_UP),
                "weighted_funds": average_weighted,
            }
        )

    if not lines_input:
        raise ValueError(
            f"No positive balances found for pool={pool} between {period_start} and {value_date}."
        )

    band_snapshot = [
        {
            "id": band_id,
            "participant_class": band.participant_class,
            "weightage": str(band.weightage),
            "effective_from": band.effective_from.isoformat(),
        }
        for band_id, band in used_bands.items()
    ]

    total_weighted_funds = sum((line["weighted_funds"] for line in lines_input), Decimal("0"))
    total_daily_funds = sum((line["daily_funds"] for line in lines_input), Decimal("0"))

    if total_weighted_funds == 0:
        raise ValueError("total_weighted_funds is zero; cannot allocate (division by zero).")

    def _psr_on(day):
        return (
            ProfitSharingRatio.objects.filter(pool=pool, status=PSRStatus.APPROVED)
            .filter(_covers_date(day))
            .first()
        )

    psr = _psr_on(value_date)
    if psr is None:
        raise ValueError(f"No approved ProfitSharingRatio found for pool={pool} on {value_date}.")
    psr_at_start = _psr_on(period_start)
    if psr_at_start is None or psr_at_start.pk != psr.pk:
        raise ValueError(
            "The approved profit-sharing ratio changes within this period; "
            "split the allocation at the PSR change date."
        )

    per_policy = ReservePolicy.objects.filter(
        pool=pool, reserve_type=ReserveType.PER, is_active=True
    ).first()
    irr_policy = ReservePolicy.objects.filter(
        pool=pool, reserve_type=ReserveType.IRR, is_active=True
    ).first()

    is_loss = distributable < 0
    per_raw = Decimal("0")
    irr_raw = Decimal("0")

    if is_loss:
        # Shariah loss waterfall (BRD 7.1 / BR-006): the Mudarib does not bear
        # capital loss and no reserve is appropriated; the loss is absorbed
        # by the capital providers pro-rata to their unweighted funds.
        mudarib_raw = Decimal("0")
        depositor_raw = distributable  # negative amount

        raw_line_amounts = [
            depositor_raw * (line["daily_funds"] / total_daily_funds if total_daily_funds > 0 else Decimal("0"))
            for line in lines_input
        ]
    else:
        # 1. PER is appropriated from distributable profit before the PSR split.
        per_raw = _reserve_amount(per_policy, distributable, total_daily_funds)
        net_after_per = distributable - per_raw

        # 2. PSR split.
        depositor_pre_irr = net_after_per * Decimal(psr.depositor_share) / HUNDRED
        mudarib_raw = net_after_per * Decimal(psr.mudarib_share) / HUNDRED

        # 3. IRR is appropriated from the depositors' share, after the Mudarib share.
        irr_raw = _reserve_amount(irr_policy, depositor_pre_irr, total_daily_funds)
        depositor_raw = depositor_pre_irr - irr_raw

        raw_line_amounts = [
            depositor_raw * (line["weighted_funds"] / total_weighted_funds) for line in lines_input
        ]

    lines = []
    for line, raw_amount in zip(lines_input, raw_line_amounts):
        account = line["account"]
        lines.append(
            {
                "participant_class": line["participant_class"],
                "account_id": str(account.id) if account else None,
                "account_number": account.account_number if account else None,
                "participant_name": account.participant.full_name if account else None,
                "daily_funds": _round(line["daily_funds"]),
                "weightage": line["weightage"],
                "weighted_funds": _round(line["weighted_funds"]),
                "allocated_amount": _round(raw_amount),
            }
        )

    per_amount = _round(per_raw)
    irr_amount = _round(irr_raw)
    mudarib_share = _round(mudarib_raw)
    distributable_rounded = _round(distributable)

    rounding_residual = distributable_rounded - (
        per_amount
        + irr_amount
        + mudarib_share
        + sum((line["allocated_amount"] for line in lines), Decimal("0"))
    )

    # Independent half-up roundings can differ from the exact total by at most
    # half a unit per rounded figure; anything larger means a calculation bug.
    max_residual = TWO_PLACES * (len(lines) + 3)
    if abs(rounding_residual) > max_residual:
        raise ValueError(
            f"Rounding residual {rounding_residual} exceeds the permitted tolerance {max_residual}."
        )

    config_snapshot = {
        "psr": {
            "id": str(psr.id),
            "depositor_share": str(psr.depositor_share),
            "mudarib_share": str(psr.mudarib_share),
            "effective_from": psr.effective_from.isoformat(),
        },
        "weightage_bands": sorted(band_snapshot, key=lambda b: b["participant_class"]),
        "reserves": {
            kind: (
                {
                    "id": str(policy.id),
                    "rate_percentage": str(policy.rate_percentage),
                    "cap_percentage": str(policy.cap_percentage),
                    "balance_before": str(policy.current_balance),
                }
                if policy
                else None
            )
            for kind, policy in (("per", per_policy), ("irr", irr_policy))
        },
        "total_daily_funds": str(_round(total_daily_funds)),
        "period": {
            "start": period_start.isoformat(),
            "end": value_date.isoformat(),
            "days": len(days),
        },
    }

    return {
        "distributable": distributable_rounded,
        "total_weighted_funds": _round(total_weighted_funds),
        "depositor_pool_share": _round(depositor_raw),
        "mudarib_share": mudarib_share,
        "per_amount": per_amount,
        "irr_amount": irr_amount,
        "rounding_residual": rounding_residual,
        "is_loss": is_loss,
        "config_snapshot": config_snapshot,
        "lines": lines,
    }


def calculate_hash(run_data):
    """
    Returns the SHA-256 hex digest of `run_data` serialized as a
    sort-keyed JSON string, for tamper-detection on a persisted
    AllocationRun. Any Decimal values are stringified first, since
    Decimal isn't natively JSON-serializable.
    """

    def _default(value):
        if isinstance(value, Decimal):
            return str(value)
        raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")

    serialized = json.dumps(run_data, sort_keys=True, default=_default)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def run_hash_payload(run):
    """
    Canonical payload hashed for an AllocationRun: every input, every rule
    version used (config_snapshot), every output amount and every line. Built
    from the persisted run so the same function seals a run at creation and
    re-verifies it at approval.
    """

    lines = sorted(run.lines.all(), key=lambda line: (line.participant_class, str(line.account_id or "")))
    payload = {
        "pool_id": str(run.pool_id),
        "period_start": run.effective_period_start.isoformat(),
        "value_date": run.value_date.isoformat(),
        "gross_income": str(run.gross_income),
        "direct_expenses": str(run.direct_expenses),
        "distributable": str(run.distributable_amount),
        "total_weighted_funds": str(run.total_weighted_funds),
        "depositor_pool_share": str(run.depositor_pool_share),
        "mudarib_share": str(run.mudarib_share),
        "per_amount": str(run.per_amount),
        "irr_amount": str(run.irr_amount),
        "rounding_residual": str(run.rounding_residual),
        "is_loss": bool(run.is_loss),
        "config_snapshot": run.config_snapshot or {},
        "lines": [
            {
                "participant_class": line.participant_class,
                "account_id": str(line.account_id) if line.account_id else None,
                "daily_funds": str(line.daily_funds),
                "weightage": str(line.weightage),
                "weighted_funds": str(line.weighted_funds),
                "allocated_amount": str(line.allocated_amount),
            }
            for line in lines
        ],
    }
    if run.replaces_run_id:
        payload["restatement_of"] = str(run.replaces_run_id)
    return payload


def compute_run_hash(run):
    return calculate_hash(run_hash_payload(run))
