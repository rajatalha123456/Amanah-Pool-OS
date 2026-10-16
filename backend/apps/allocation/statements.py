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


def generate_statement_narratives(**kwargs):
    """
    The same explanation in English, Urdu and Arabic (BRD 9, Disclosure Generator). Every figure comes from the signed
    run; the Urdu and Arabic sentences are fixed templates (no machine translation), to be confirmed by a native
    reviewer before customer use.
    """

    run = kwargs["allocation_run"]
    who = kwargs.get("participant_name")
    days = (run.value_date - run.effective_period_start).days + 1
    start, end = run.effective_period_start, run.value_date
    weightage, profit, distributable = kwargs["weightage"], kwargs["profit_allocated"], run.distributable_amount
    average = kwargs.get("average_funds")

    who_ur = who or f"{kwargs['participant_class']} class"
    funds_ur = f" Is muddat mein aap ke ausat rozana funds {average} thay." if average is not None else ""
    urdu = (
        f"{start} se {end} tak {days} din ki muddat mein {who_ur} ne pool mein {weightage}x ke ausat weightage ke saath "
        f"hissa liya.{funds_ur} Aap ke rozana funds aur manzoor shuda weightage ne taqseem ke qabil munafay mein aap ka "
        f"hissa tay kiya: {distributable} ke qabil-e-taqseem munafay mein se is muddat ke liye aap ko {profit} mila."
    )
    urdu_script = (
        f"{start} سے {end} تک {days} دن کی مدت میں {who_ur} نے پول میں {weightage}x کے اوسط وزن کے ساتھ حصہ لیا۔"
        + (f" اس مدت میں آپ کے اوسط یومیہ فنڈز {average} تھے۔" if average is not None else "")
        + f" آپ کے یومیہ فنڈز اور منظور شدہ وزن نے قابلِ تقسیم منافع میں آپ کا حصہ طے کیا: {distributable} کے قابلِ تقسیم منافع"
        f" میں سے اس مدت کے لیے آپ کو {profit} ملا۔"
    )
    arabic = (
        f"خلال الفترة من {start} إلى {end} ({days} يومًا) شارك {who_ur} في الوعاء بمتوسط وزن ترجيحي {weightage}x."
        + (f" بلغ متوسط أموالكم اليومية خلال الفترة {average}." if average is not None else "")
        + f" حدّدت أموالكم اليومية والوزن المعتمد حصتكم من الربح القابل للتوزيع: من ربح قابل للتوزيع قدره {distributable}"
        f" خُصّص لكم {profit} عن هذه الفترة."
    )
    return {"en": generate_statement_narrative(**kwargs), "ur": urdu_script, "ur_roman": urdu, "ar": arabic}
