"""
Depositor statement narrative generation.

generate_statement_narrative() is a simple template-based function for
now, matching BRD Screen #41's plain-language style. It's expected to
be replaced/enhanced later by a Disclosure Generator agent - this is
the interim implementation.
"""


def generate_statement_narrative(participant_class, opening_balance, profit_allocated, weightage, allocation_run):
    """
    Returns a plain-language explanation of how a participant class's
    profit share was calculated for one allocation run.
    """

    return (
        f"Your daily funds and approved weightage ({weightage}x) determined your share of "
        f"distributable pool profit. Based on a distributable amount of "
        f"{allocation_run.distributable_amount} and your class's weighted contribution, "
        f"you were allocated {profit_allocated} for this period."
    )
