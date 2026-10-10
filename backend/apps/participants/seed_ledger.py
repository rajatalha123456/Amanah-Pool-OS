"""
Demo participant ledger: participants, accounts, daily balances and the
allocation runs built from them.

Used by `manage.py seed_project_data`. Nothing here is hand-forged: runs are
created, submitted, Shariah-signed and approved through the real API, so every
signed run carries a genuine calculation hash, tied-out journal, reserve
movement and per-participant lines/statements.
"""

from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from rest_framework.test import APIClient

from apps.accounts.models import User, UserRole
from apps.core.context import set_current_tenant
from apps.pools.models import (
    BalanceImportBatch,
    BalanceImportBatchStatus,
    BalanceSource,
    DailyBalance,
    DailyBalanceStatus,
)

from .models import KYCStatus, Participant, ParticipantAccount

# (reference, name, class, base balance, tax status, zakat exempt, bank, bic, bank code)
PARTICIPANTS = [
    ("DEP-001", "Tariq Mehmood", "Retail Regular", "3000000", "filer", False, "Meezan Bank Ltd", "MEZNPKKA", "MEZN"),
    ("DEP-002", "Ayesha Siddiqui", "Retail Regular", "5500000", "filer", False, "Bank Alfalah Ltd", "ALFHPKKA", "ALFH"),
    ("DEP-003", "Imran Qureshi", "Retail Regular", "4200000", "non_filer", False, "HBL Islamic", "HABBPKKA", "HABB"),
    ("DEP-004", "Sana Rehman", "Retail Regular", "7300000", "filer", True, "Meezan Bank Ltd", "MEZNPKKA", "MEZN"),
    ("DEP-005", "Faisal Textile Mills (Pvt) Ltd", "Premium Saver", "9000000", "filer", False, "Bank Alfalah Ltd", "ALFHPKKA", "ALFH"),
    ("DEP-006", "Noor Fatima", "Premium Saver", "12000000", "filer", False, "Meezan Bank Ltd", "MEZNPKKA", "MEZN"),
    ("DEP-007", "Hassan Ali Trading Co.", "Premium Saver", "9000000", "non_filer", False, "HBL Islamic", "HABBPKKA", "HABB"),
    ("DEP-008", "Al-Baraka Family Endowment Trust", "HNW Depositor", "10000000", "filer", True, "Meezan Bank Ltd", "MEZNPKKA", "MEZN"),
    ("DEP-009", "Zubair Ahmad", "HNW Depositor", "8000000", "filer", False, "Bank Alfalah Ltd", "ALFHPKKA", "ALFH"),
    ("DEP-010", "Mariam Khalid", "HNW Depositor", "7000000", "filer", False, "Meezan Bank Ltd", "MEZNPKKA", "MEZN"),
    ("DEP-011", "Indus Valley Agro Ventures (Pvt) Ltd", "Corporate / Institutional", "15000000", "filer", False, "HBL Islamic", "HABBPKKA", "HABB"),
    ("DEP-012", "Karachi Logistics Holdings Ltd", "Corporate / Institutional", "10000000", "filer", False, "Meezan Bank Ltd", "MEZNPKKA", "MEZN"),
]

SEED_START = date(2026, 7, 1)
SEED_END = date(2026, 9, 30)
INVESTOR_EMAIL = "investor@novulabsdemo.test"


def make_pk_iban(bank_code, account_digits):
    """Builds a mathematically valid 24-character Pakistani IBAN (MOD-97)."""

    bban = f"{bank_code}{account_digits}"
    numeric = "".join(str(int(ch, 36)) for ch in f"{bban}PK00")
    check = 98 - (int(numeric) % 97)
    return f"PK{check:02d}{bban}"


def make_api_caller(tenant):
    """Returns call(user, method, url, payload=None) driving the real API as `user`."""

    client = APIClient(SERVER_NAME="localhost")
    client.defaults["HTTP_X_TENANT_CODE"] = tenant.code

    def call(user, method, url, payload=None):
        client.force_authenticate(user=user)
        send = getattr(client, method)
        response = send(url, payload, format="json") if payload is not None else send(url)
        set_current_tenant(tenant)  # the middleware clears the tenant after every request
        if response.status_code >= 400:
            raise RuntimeError(f"Seed call {method.upper()} {url} failed: {response.status_code} {response.data}")
        return response.data

    return call


def seed_circle_first_cycle(tenant, pool, members, *, maker, checker, pm_user):
    """
    Cycle 1 of the community circle through the real payout workflow: the
    contributions are already recorded, then request (maker) -> approve
    (independent checker) -> settle with a bank reference.
    """

    call = make_api_caller(tenant)
    base = "/api/v1/circles/payouts/"
    payout = call(
        pm_user, "post", f"{base}request-payout/{pool.id}/",
        {"member_id": str(members[0].id), "settlement_rail": "raast_rtgs", "payout_date": "2026-09-10"},
    )
    call(checker, "post", f"{base}{payout['id']}/approve/")
    call(maker, "post", f"{base}{payout['id']}/settle/", {"settlement_utr": "DEMO-RAAST-20260910-0001"})


def seed_participant_ledger(tenant, pool, *, maker, checker, board_user, pm_user, risk_user, investor_user, stdout=None):
    def say(message):
        if stdout:
            stdout.write(message)

    investor_user_for = {"DEP-006": investor_user}  # one participant can log in to the portal

    accounts = []
    for index, (ref, name, p_class, base, tax_status, zakat_exempt, bank, bic, bank_code) in enumerate(
        PARTICIPANTS, start=1
    ):
        participant = Participant.objects.create(
            tenant=tenant,
            reference=ref,
            full_name=name,
            participant_class=p_class,
            kyc_status=KYCStatus.VERIFIED,
            cnic_ntn=f"42101-{1000000 + index * 7919:07d}-{index % 9}",
            iban=make_pk_iban(bank_code, f"{(index * 104729) % 10**16:016d}"),
            bank_name=bank,
            bic=bic,
            tax_status=tax_status,
            zakat_exempt=zakat_exempt,
            default_channel="raast" if index % 3 else "one_link",
            nominee_name="Family nominee",
            user=investor_user_for.get(ref),
        )
        account = ParticipantAccount.objects.create(
            tenant=tenant,
            participant=participant,
            pool=pool,
            account_number=f"AMN-{pool.code}-{index:04d}",
            opened_date=date(2026, 1, 1),
        )
        accounts.append((account, Decimal(base)))
    say(f"[OK] {len(accounts)} participants with verified KYC and accounts seeded")

    # Daily end-of-day balances for the whole seeded window (Jul - Sep 2026).
    # Balances drift deterministically within +/-0.5% so averages differ from closing values.
    rows = []
    day = SEED_START
    day_index = 0
    while day <= SEED_END:
        for account_index, (account, base) in enumerate(accounts):
            drift = Decimal(((day_index * 7 + account_index * 3) % 11) - 5) / Decimal(1000)
            amount = (base * (Decimal(1) + drift)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            rows.append(
                DailyBalance(
                    tenant=tenant,
                    pool=pool,
                    account=account,
                    participant_class=account.participant.participant_class,
                    value_date=day,
                    balance_amount=amount,
                    source=BalanceSource.FILE_IMPORT,
                    status=DailyBalanceStatus.VALIDATED,
                )
            )
        day += timedelta(days=1)
        day_index += 1
    DailyBalance.objects.bulk_create(rows, batch_size=500)

    last_day_total = sum(r.balance_amount for r in rows if r.value_date == date(2026, 9, 28))
    BalanceImportBatch.objects.create(
        tenant=tenant,
        pool=pool,
        value_date=date(2026, 9, 28),
        total_records=len(accounts),
        matched_records=len(accounts),
        exception_count=0,
        control_total_expected=last_day_total,
        control_total_actual=last_day_total,
        status=BalanceImportBatchStatus.BALANCED,
        imported_by=maker,
    )
    say(f"[OK] {len(rows)} daily account balances seeded ({SEED_START} to {SEED_END})")

    # Allocation runs through the real workflow.
    call = make_api_caller(tenant)

    base_url = "/api/v1/allocation/allocation-runs/"

    def create_run(start, end, gross, expenses):
        data = call(
            maker, "post", base_url,
            {"pool": str(pool.id), "period_start": str(start), "value_date": str(end),
             "gross_income": gross, "direct_expenses": expenses},
        )
        return data["id"]

    def submit(run_id):
        call(maker, "post", f"{base_url}{run_id}/submit-for-checking/")

    def sign(run_id, note):
        call(board_user, "post", f"{base_url}{run_id}/shariah-sign-off/", {"note": note})
        call(checker, "post", f"{base_url}{run_id}/approve/")

    # July 2026: signed, then a restatement rerun left awaiting approval (Restatement Wizard demo).
    july = create_run(date(2026, 7, 1), date(2026, 7, 31), "4100000.00", "180000.00")
    submit(july)
    sign(july, "Certified conforming to AAOIFI FAS-30 and SBP IBD Circular 03/2012.")
    call(
        maker, "post", f"{base_url}{july}/restate/",
        {"restatement_reason": "[Regulatory Examination Finding] Late CBS asset accrual adjustment.",
         "gross_income": "4150000.00"},
    )

    # August 2026: signed, statements issued.
    august = create_run(date(2026, 8, 1), date(2026, 8, 31), "4500000.00", "210000.00")
    submit(august)
    sign(august, "Certified conforming to AAOIFI FAS-30 and SBP IBD Circular 03/2012.")
    call(maker, "post", f"{base_url}{august}/generate-statements/")

    # September 2026: awaiting the Shariah Board / Finance Checker.
    september = create_run(date(2026, 9, 1), date(2026, 9, 30), "5200000.00", "240000.00")
    submit(september)

    say("[OK] July (signed + restatement rerun), August (signed + statements) and September (pending) runs seeded")
    return {"july": july, "august": august, "september": september}
