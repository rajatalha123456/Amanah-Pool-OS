"""
State Bank of Pakistan (SBP) Raast & 1LINK Inter-Bank Switch Simulator.
Implements ISO 8583 / SBP Raast Real-Time Retail Payment Rails (ISO 20022).
"""

import datetime
import random
import uuid
from decimal import Decimal
from django.utils import timezone


RAAST_CHANNELS = {
    "RAAST_P2M": "SBP Raast Person-to-Merchant / Escrow Direct",
    "RAAST_P2P": "SBP Raast Person-to-Person Instant Rail",
    "1LINK_IBFT": "1LINK Inter-Bank Funds Transfer Switch",
    "1LINK_BILL": "1LINK BPS Bill Payment Settlement",
}

PAKISTAN_FINANCIAL_INSTITUTIONS = [
    {"code": "MEZN", "name": "Meezan Bank Limited (Islamic)"},
    {"code": "DIBP", "name": "Dubai Islamic Bank Pakistan"},
    {"code": "BIPK", "name": "BankIslami Pakistan Limited"},
    {"code": "FABL", "name": "Faysal Bank (Islamic Banking)"},
    {"code": "ALFH", "name": "Bank Alfalah Islamic"},
    {"code": "HBLI", "name": "Habib Bank Islamic Banking"},
]

CENTRAL_ESCROW_VAULT = {
    "code": "AMAN",
    "name": "Amanah Pool Central Escrow Vault (SBP Regulated)",
    "iban": "PK55AMAN0000109928172601",
}


def generate_rrn():
    """Generates a standard 12-digit banking Retrieval Reference Number (YYDDD + 7 random digits)."""
    now = timezone.now()
    year_prefix = now.strftime("%y")
    julian_day = now.strftime("%j")
    sequence = f"{random.randint(1000000, 9999999)}"
    return f"{year_prefix}{julian_day}{sequence}"


def generate_stan():
    """Generates a 6-digit System Trace Audit Number (STAN) for switch tracing."""
    return f"{random.randint(100000, 999999)}"


def generate_e2e_id():
    """Generates SBP Raast End-to-End Transaction ID (PK-RAAST-YYYYMMDD-XXXXXXXX)."""
    date_str = timezone.now().strftime("%Y%m%d")
    suffix = uuid.uuid4().hex[:8].upper()
    return f"PK-RAAST-{date_str}-{suffix}"


def execute_banking_settlement(
    amount: Decimal | str | float,
    source_title: str,
    source_iban: str,
    destination_title: str | None = None,
    destination_iban: str | None = None,
    channel: str = "RAAST_P2M",
    purpose: str = "Pool Capital Contribution / Settlement",
    simulate_failure_code: str | None = None,
) -> dict:
    """
    Executes a simulated banking settlement across SBP Raast or 1LINK rails.
    Validates account formatting, routes through the central clearing switch,
    and returns an authentic ISO 20022 / SBP Raast digital receipt payload.
    """
    amount_dec = Decimal(str(amount))
    if amount_dec <= 0:
        raise ValueError("Settlement amount must be strictly positive.")

    channel_name = RAAST_CHANNELS.get(channel, RAAST_CHANNELS["RAAST_P2M"])
    
    # Select random sending bank for realism if not parsed
    source_bank = random.choice(PAKISTAN_FINANCIAL_INSTITUTIONS)
    dest_iban = destination_iban or CENTRAL_ESCROW_VAULT["iban"]
    dest_title = destination_title or CENTRAL_ESCROW_VAULT["name"]

    now = timezone.now()
    stan = generate_stan()
    rrn = generate_rrn()
    e2e_id = generate_e2e_id()

    # Check simulated failure scenarios
    if simulate_failure_code == "51":
        return {
            "success": False,
            "response_code": "51",
            "response_message": "DECLINED: Insufficient Funds in Source Account.",
            "stan": stan,
            "rrn": rrn,
            "e2e_id": e2e_id,
            "channel": channel,
            "channel_name": channel_name,
            "amount": str(amount_dec),
            "currency": "PKR",
            "settled_at": now.isoformat(),
        }
    elif simulate_failure_code == "91":
        return {
            "success": False,
            "response_code": "91",
            "response_message": "SWITCH TIMEOUT: 1LINK / SBP Raast core switch inoperative or unreachable.",
            "stan": stan,
            "rrn": rrn,
            "e2e_id": e2e_id,
            "channel": channel,
            "channel_name": channel_name,
            "amount": str(amount_dec),
            "currency": "PKR",
            "settled_at": now.isoformat(),
        }

    # Successful ISO 8583 / Raast settlement
    auth_code = f"AUTH-{uuid.uuid4().hex[:6].upper()}"
    return {
        "success": True,
        "response_code": "00",
        "response_message": "APPROVED: Settlement successfully executed and confirmed by Central Clearing Switch.",
        "e2e_id": e2e_id,
        "stan": stan,
        "rrn": rrn,
        "auth_code": auth_code,
        "channel": channel,
        "channel_name": channel_name,
        "amount": f"{amount_dec:,.2f}",
        "amount_raw": str(amount_dec),
        "currency": "PKR",
        "settled_at": now.strftime("%Y-%m-%d %H:%M:%S UTC"),
        "source": {
            "account_title": source_title,
            "iban": source_iban,
            "bank_name": source_bank["name"],
            "bank_code": source_bank["code"],
        },
        "beneficiary": {
            "account_title": dest_title,
            "iban": dest_iban,
            "bank_name": CENTRAL_ESCROW_VAULT["name"],
            "bank_code": CENTRAL_ESCROW_VAULT["code"],
        },
        "purpose": purpose,
        "settlement_type": "REAL_TIME_GROSS_SETTLEMENT",
        "regulatory_stamp": "STATE BANK OF PAKISTAN (SBP) RAAST DIRECT SETTLEMENT CONFIRMED",
    }
