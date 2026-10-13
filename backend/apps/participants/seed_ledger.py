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


def seed_participant_ledger(
    tenant, pool, *, maker, checker, board_user, pm_user, risk_user, investor_user, signatory, stdout=None
):
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
    from .consents import grant_consent

    for account, _ in accounts:
        grant_consent(
            participant=account.participant, purpose="data_processing", method="in_person",
            evidence_reference="", user=pm_user,
        )
    say(f"[OK] {len(accounts)} participants with verified KYC, accounts and data-processing consent seeded")

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

    from apps.accounting.models import IncomeExpenseEvent, IncomeExpenseEventType

    def post_event(event_type, category, amount, on, description):
        """Pool income/expense through the real maker (create) -> checker (post) flow."""
        event = IncomeExpenseEvent.objects.create(
            tenant=tenant, pool=pool, event_type=event_type, category=category, amount=Decimal(amount),
            event_date=on, description=description, created_by=maker,
        )
        call(checker, "post", f"/api/v1/accounting/income-expense-events/{event.id}/post/")
        return event

    def create_run(start, end):
        # No figures typed in: income and expenses are derived from the posted events (BR-005).
        data = call(
            maker, "post", base_url,
            {"pool": str(pool.id), "period_start": str(start), "value_date": str(end)},
        )
        return data["id"]

    INCOME, EXPENSE = IncomeExpenseEventType.INCOME, IncomeExpenseEventType.EXPENSE
    # July: 1,025,000 permissible income, 45,000 direct expense (about 12% a year on the 100M pool). The penalty income is
    # non-permissible (purified, never distributed) and the branch rent is bank overhead.
    post_event(INCOME, "Financing Profit", "650000.00", date(2026, 7, 12), "Sukuk coupon periodic rental accrual")
    post_event(INCOME, "Financing Profit", "375000.00", date(2026, 7, 24), "Engro Murabaha sales profit settlement")
    post_event(INCOME, "Penalty income", "9000.00", date(2026, 7, 27), "Late payment penalty received from customer")
    post_event(EXPENSE, "Direct Takaful", "45000.00", date(2026, 7, 28), "Asset protection takaful premium")
    post_event(EXPENSE, "Overhead", "24000.00", date(2026, 7, 29), "Branch rent allocation")
    # August: 1,125,000 income, 52,500 direct expense.
    post_event(INCOME, "Financing Profit", "750000.00", date(2026, 8, 14), "Ijarah rental income")
    post_event(INCOME, "Financing Profit", "375000.00", date(2026, 8, 27), "Murabaha profit settlement")
    post_event(EXPENSE, "Custody Fees", "52500.00", date(2026, 8, 30), "CDC sukuk custody fee")
    # September: 1,300,000 income, 60,000 direct expense.
    post_event(INCOME, "Financing Profit", "725000.00", date(2026, 9, 11), "Sukuk coupon periodic rental accrual")
    post_event(INCOME, "Financing Profit", "575000.00", date(2026, 9, 25), "Murabaha profit settlement")
    post_event(EXPENSE, "Direct Takaful", "60000.00", date(2026, 9, 27), "Asset protection takaful premium")

    def submit(run_id):
        call(maker, "post", f"{base_url}{run_id}/submit-for-checking/")

    def sign(run_id, note):
        # Approval ceremony: independent check -> Shariah review -> final release by the Authorized Signatory.
        call(checker, "post", f"{base_url}{run_id}/check/")
        call(board_user, "post", f"{base_url}{run_id}/shariah-sign-off/", {"note": note})
        call(signatory, "post", f"{base_url}{run_id}/approve/")

    # July 2026: signed, then a restatement rerun left awaiting approval (Restatement Wizard demo).
    july = create_run(date(2026, 7, 1), date(2026, 7, 31))
    submit(july)
    sign(july, "Certified for the demo data set (synthetic; not a real certification).")
    # A July accrual posted after the run was signed: the restatement re-derives the period (1,037,500).
    post_event(INCOME, "Financing Profit", "12500.00", date(2026, 7, 31), "Late CBS asset accrual adjustment")
    call(
        maker, "post", f"{base_url}{july}/restate/",
        {"restatement_reason": "[Regulatory Examination Finding] Late CBS asset accrual adjustment."},
    )

    # August 2026: signed, statements issued.
    august = create_run(date(2026, 8, 1), date(2026, 8, 31))
    submit(august)
    sign(august, "Certified for the demo data set (synthetic; not a real certification).")
    call(maker, "post", f"{base_url}{august}/generate-statements/")

    # September 2026: awaiting the Shariah Board / Finance Checker.
    september = create_run(date(2026, 9, 1), date(2026, 9, 30))
    submit(september)

    say("[OK] July (signed + restatement rerun), August (signed + statements) and September (pending) runs seeded")
    return {"july": july, "august": august, "september": september}


def seed_mudarabah_distribution(tenant, pool, capital_account, *, maker, checker, password):
    """
    Mudarabah profit distribution for an investment pool through the real workflow:
    August signed (journal posted), September awaiting the checker. The investor
    gets a portal login linked to their participant record (own data only).
    """

    from apps.accounts.models import User, UserRole
    from apps.allocation.models import PSRStatus, ProfitSharingRatio

    from .models import KYCStatus, Participant

    ProfitSharingRatio.objects.get_or_create(
        tenant=tenant, pool=pool, effective_from=date(2026, 1, 1),
        defaults={"depositor_share": Decimal("75.00"), "mudarib_share": Decimal("25.00"), "status": PSRStatus.APPROVED},
    )

    investor, _ = User.objects.get_or_create(
        email="mudarabah.investor@novulabsdemo.test",
        defaults={"tenant": tenant, "full_name": "Indus Valley Agro Ventures", "role": UserRole.INVESTOR_MEMBER},
    )
    investor.tenant, investor.role, investor.is_active = tenant, UserRole.INVESTOR_MEMBER, True
    investor.set_password(password)
    investor.save()

    participant = Participant.objects.create(
        tenant=tenant, reference="INV-P-003", full_name=capital_account.investor_name,
        participant_class="Corporate / Institutional", kyc_status=KYCStatus.VERIFIED, user=investor,
    )
    capital_account.participant = participant
    capital_account.save(update_fields=["participant", "updated_at"])

    call = make_api_caller(tenant)
    base = "/api/v1/investments/distribution-runs/"

    def draft(start, end, gross, expenses):
        data = call(
            maker, "post", base,
            {"pool": str(pool.id), "period_start": start, "period_end": end,
             "gross_income": gross, "direct_expenses": expenses},
        )
        call(maker, "post", f"{base}{data['id']}/submit-for-checking/")
        return data["id"]

    august = draft("2026-08-01", "2026-08-31", "2750000.00", "130000.00")
    # The full ceremony: independent check, Shariah review, release by the authorized signatory.
    secretariat = User.objects.filter(tenant=tenant, role=UserRole.SHARIAH_SECRETARIAT).order_by("email").first()
    signatory = User.objects.filter(tenant=tenant, role=UserRole.AUTHORIZED_SIGNATORY).order_by("email").first()
    call(checker, "post", f"{base}{august}/check/")
    call(secretariat, "post", f"{base}{august}/shariah-sign-off/", {"note": "Reviewed for the demo data."})
    call(signatory, "post", f"{base}{august}/approve/")
    draft("2026-09-01", "2026-09-30", "2900000.00", "140000.00")
