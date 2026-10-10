from decimal import Decimal
from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from apps.accounting.models import JournalBatch
from apps.allocation.engine import compute_run_hash
from apps.allocation.models import AllocationLine, AllocationRun, AllocationRunStatus, DepositorStatement, ReservePolicy
from apps.core.context import set_current_tenant
from apps.participants.models import Participant, ParticipantAccount
from apps.pools.models import DailyBalance
from apps.tenants.models import Tenant


class SeedProjectDataTests(TestCase):
    """The demo seed must build a coherent, genuinely signed participant ledger."""

    @classmethod
    def setUpTestData(cls):
        call_command("seed_project_data", tenant_code="SEED-TEST", stdout=StringIO())
        cls.tenant = Tenant.objects.get(code="SEED-TEST")

    def setUp(self):
        set_current_tenant(self.tenant)

    def tearDown(self):
        set_current_tenant(None)

    def test_participants_accounts_and_balances(self):
        self.assertEqual(Participant.objects.count(), 12)
        self.assertEqual(ParticipantAccount.objects.count(), 12)
        self.assertEqual(DailyBalance.objects.filter(account__isnull=False).count(), 12 * 92)
        self.assertEqual(DailyBalance.objects.filter(account__isnull=True).count(), 0)
        self.assertEqual(Participant.objects.filter(user__isnull=False).count(), 1)

    def test_runs_are_real_signed_and_sealed(self):
        statuses = sorted(AllocationRun.objects.values_list("status", flat=True))
        self.assertEqual(
            statuses,
            sorted(
                [
                    AllocationRunStatus.SIGNED,  # July
                    AllocationRunStatus.SIGNED,  # August
                    AllocationRunStatus.SIMULATED,  # July restatement rerun
                    AllocationRunStatus.PENDING_APPROVAL,  # September
                ]
            ),
        )
        for run in AllocationRun.objects.all():
            self.assertEqual(run.calculation_hash, compute_run_hash(run), run)
            self.assertEqual(run.lines.count(), 12)
            self.assertTrue(all(line.account_id for line in run.lines.all()))

        for run in AllocationRun.objects.filter(status=AllocationRunStatus.SIGNED):
            batch = JournalBatch.objects.get(allocation_run=run)
            self.assertEqual(batch.total_debit, batch.total_credit)

    def test_statements_and_reserves(self):
        august = AllocationRun.objects.get(value_date="2026-08-31")
        self.assertEqual(DepositorStatement.objects.filter(allocation_run=august).count(), 12)

        per = ReservePolicy.objects.get(reserve_type="per")
        signed_per = sum(
            run.per_amount for run in AllocationRun.objects.filter(status=AllocationRunStatus.SIGNED)
        )
        self.assertEqual(per.current_balance, Decimal("1250000.00") + signed_per)

    def test_lines_cover_every_account(self):
        run = AllocationRun.objects.get(value_date="2026-08-31")
        self.assertEqual(
            set(AllocationLine.objects.filter(allocation_run=run).values_list("account_id", flat=True)),
            set(ParticipantAccount.objects.values_list("id", flat=True)),
        )
