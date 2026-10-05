"""
Pure profit-allocation calculation engine.

calculate_allocation() performs no database writes - it only reads
DailyBalance/WeightageBand/ProfitSharingRatio and returns a plain dict
of computed values. Persisting the result into AllocationRun/
AllocationLine is the caller's responsibility (see apps/allocation/views.py).

All monetary/ratio arithmetic uses Decimal, never float, and every
returned monetary value is rounded to 2 decimal places with
ROUND_HALF_UP.
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


def _round(value):
    return Decimal(value).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def _covers_date(value_date):
    """Q for `effective_from <= value_date <= (effective_to or infinity)`."""
    return Q(effective_from__lte=value_date) & (
        Q(effective_to__isnull=True) | Q(effective_to__gte=value_date)
    )


def calculate_allocation(pool, value_date, gross_income, direct_expenses):
    """
    Returns a dict with all computed values; does NOT save anything to DB.

    Return shape:
        {
            "distributable": Decimal,
            "total_weighted_funds": Decimal,
            "depositor_pool_share": Decimal,
            "mudarib_share": Decimal,
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

    total_weighted_funds = sum((line["weighted_funds"] for line in lines_input), Decimal("0"))

    if total_weighted_funds == 0:
        raise ValueError("total_weighted_funds is zero; cannot allocate (division by zero).")

    psr = (
        ProfitSharingRatio.objects.filter(pool=pool, status=PSRStatus.APPROVED)
        .filter(_covers_date(value_date))
        .first()
    )

    if psr is None:
        raise ValueError(f"No approved ProfitSharingRatio found for pool={pool} on {value_date}.")

    is_loss = distributable < 0
    per_amount = Decimal("0.00")
    irr_amount = Decimal("0.00")

    if is_loss:
        # Shariah Loss Waterfall (BRD Section 2, 4, 7):
        # Mudarib does not bear capital loss; Mudarib share = 0.
        # Capital loss is absorbed by capital providers strictly pro-rata by daily unweighted funds.
        mudarib_share = Decimal("0.00")
        depositor_pool_share = distributable  # negative amount
        total_daily_funds = sum((line["daily_funds"] for line in lines_input), Decimal("0"))

        lines = []
        for line in lines_input:
            loss_ratio = line["daily_funds"] / total_daily_funds if total_daily_funds > 0 else Decimal("0")
            loss_share = depositor_pool_share * loss_ratio
            lines.append(
                {
                    "participant_class": line["participant_class"],
                    "daily_funds": _round(line["daily_funds"]),
                    "weightage": line["weightage"],
                    "weighted_funds": _round(line["weighted_funds"]),
                    "allocated_amount": _round(loss_share),
                }
            )
    else:
        # 1. PER (Profit Equalization Reserve) Deduction (BRD Sec 5 & 7.1)
        # PER is deducted from Gross Pool Distributable Profit before Mudarib share
        per_policy = ReservePolicy.objects.filter(
            pool=pool, reserve_type=ReserveType.PER, is_active=True
        ).first()
        if per_policy and per_policy.rate_percentage > 0:
            per_amount = _round(distributable * (Decimal(per_policy.rate_percentage) / Decimal("100")))
            net_after_per = max(Decimal("0.00"), distributable - per_amount)
        else:
            net_after_per = distributable

        # 2. PSR Split (BRD Sec 7.1)
        depositor_share_pre_irr = net_after_per * (Decimal(psr.depositor_share) / Decimal("100"))
        mudarib_share = net_after_per * (Decimal(psr.mudarib_share) / Decimal("100"))

        # 3. IRR (Investment Risk Reserve) Deduction (BRD Sec 5 & 7.1)
        # IRR is deducted from Depositors' share after Mudarib share
        irr_policy = ReservePolicy.objects.filter(
            pool=pool, reserve_type=ReserveType.IRR, is_active=True
        ).first()
        if irr_policy and irr_policy.rate_percentage > 0:
            irr_amount = _round(depositor_share_pre_irr * (Decimal(irr_policy.rate_percentage) / Decimal("100")))
            depositor_pool_share = max(Decimal("0.00"), depositor_share_pre_irr - irr_amount)
        else:
            depositor_pool_share = depositor_share_pre_irr

        lines = []
        for line in lines_input:
            allocation_ratio = line["weighted_funds"] / total_weighted_funds
            allocated_amount = depositor_pool_share * allocation_ratio

            lines.append(
                {
                    "participant_class": line["participant_class"],
                    "daily_funds": _round(line["daily_funds"]),
                    "weightage": line["weightage"],
                    "weighted_funds": _round(line["weighted_funds"]),
                    "allocated_amount": _round(allocated_amount),
                }
            )

    return {
        "distributable": _round(distributable),
        "total_weighted_funds": _round(total_weighted_funds),
        "depositor_pool_share": _round(depositor_pool_share),
        "mudarib_share": _round(mudarib_share),
        "per_amount": _round(per_amount),
        "irr_amount": _round(irr_amount),
        "is_loss": is_loss,
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
