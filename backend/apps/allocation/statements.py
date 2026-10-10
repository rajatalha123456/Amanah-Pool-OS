"""
Depositor statement figures and narrative generation.

generate_statement_narrative() is a template-based plain-language explanation
(BRD Screen 41 / Disclosure Generator); it only ever describes a signed run.
"""

from decimal import Decimal

from apps.pools.models import DailyBalance, DailyBalanceStatus


def statement_balances(run, line):
    """
    Returns (opening_balance, closing_principal) for a statement line: the
    account's (or, for legacy class-level lines, the class's) last known
    end-of-day balance on or before the period start and the period end.
    """

    balances = DailyBalance.objects.filter(pool=run.pool).exclude(status=DailyBalanceStatus.REJECTED)
    account = line.account
    if account is not None:
        balances = balances.filter(account=account)
    else:
        balances = balances.filter(account__isnull=True, participant_class=line.participant_class)

    def balance_on(day):
        if account is not None and (day < account.opened_date or (account.closed_date and day > account.closed_date)):
            return Decimal("0.00")
        row = balances.filter(value_date__lte=day).order_by("-value_date").first()
        return Decimal(row.balance_amount) if row else Decimal("0.00")

    return balance_on(run.effective_period_start), balance_on(run.value_date)


def generate_statement_narrative(
    participant_class,
    opening_balance,
    profit_allocated,
    weightage,
    allocation_run,
    participant_name=None,
    average_funds=None,
):
    """
    Returns a plain-language explanation of how a participant's profit share
    was calculated for one allocation run.
    """

    who = participant_name or f"the {participant_class} class"
    days = (allocation_run.value_date - allocation_run.effective_period_start).days + 1
    funds_text = f" Your average daily funds over the period were {average_funds}." if average_funds is not None else ""
    return (
        f"For the {days}-day period {allocation_run.effective_period_start} to {allocation_run.value_date}, "
        f"{who} participated in the pool with an average weightage of {weightage}x.{funds_text} "
        f"Your daily funds and approved weightage determined your share of distributable pool profit: "
        f"on a distributable amount of {allocation_run.distributable_amount} you were allocated "
        f"{profit_allocated} for this period."
    )
