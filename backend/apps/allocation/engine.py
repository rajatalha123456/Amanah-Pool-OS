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
from decimal import ROUND_HALF_UP, Decimal

from django.db.models import Q

from apps.pools.models import DailyBalance

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


def calculate_allocation(pool, value_date, gross_income, direct_expenses):
    """
    Returns a dict with all computed values; does NOT save anything to DB.

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

    daily_balances = list(DailyBalance.objects.filter(pool=pool, value_date=value_date))
    if not daily_balances:
        raise ValueError(f"No DailyBalance records found for pool={pool} on {value_date}.")

    lines_input = []
    band_snapshot = []
    for balance in daily_balances:
        participant_class = balance.participant_class
        daily_funds = Decimal(balance.balance_amount)

        band = (
            WeightageBand.objects.filter(
                pool=pool,
                participant_class=participant_class,
                status=WeightageBandStatus.APPROVED,
            )
            .filter(_covers_date(value_date))
            .first()
        )

        if band is None:
            raise ValueError(
                f"No approved WeightageBand found for participant_class="
                f"'{participant_class}' on {value_date}."
            )

        weightage = Decimal(band.weightage)
        weighted_funds = daily_funds * weightage

        lines_input.append(
            {
                "participant_class": participant_class,
                "daily_funds": daily_funds,
                "weightage": weightage,
                "weighted_funds": weighted_funds,
            }
        )
        band_snapshot.append(
            {
                "id": str(band.id),
                "participant_class": participant_class,
                "weightage": str(band.weightage),
                "effective_from": band.effective_from.isoformat(),
            }
        )

    total_weighted_funds = sum((line["weighted_funds"] for line in lines_input), Decimal("0"))
    total_daily_funds = sum((line["daily_funds"] for line in lines_input), Decimal("0"))

    if total_weighted_funds == 0:
        raise ValueError("total_weighted_funds is zero; cannot allocate (division by zero).")

    psr = (
        ProfitSharingRatio.objects.filter(pool=pool, status=PSRStatus.APPROVED)
        .filter(_covers_date(value_date))
        .first()
    )

    if psr is None:
        raise ValueError(f"No approved ProfitSharingRatio found for pool={pool} on {value_date}.")

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
        lines.append(
            {
                "participant_class": line["participant_class"],
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

    lines = sorted(run.lines.all(), key=lambda line: line.participant_class)
    payload = {
        "pool_id": str(run.pool_id),
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
