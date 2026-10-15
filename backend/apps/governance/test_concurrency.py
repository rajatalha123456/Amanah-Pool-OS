"""
Concurrency (audit F-08, BRD 7 / 10): two people acting on the same record at the same moment must not both succeed.
Real threads against the real database, so these use TransactionTestCase (the data is genuinely committed).
"""

import threading
from io import StringIO

from django.core.management import call_command
from django.db import connection
from django.test import TransactionTestCase
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounting.gl_handover import create_export
from apps.accounting.models import GLExport, JournalBatch
from apps.accounts.models import User
from apps.core.context import set_current_tenant
from apps.investments.models import DistributionRunStatus, InvestmentDistributionRun
from apps.tenants.models import Tenant


def run_together(jobs):
    """Runs each job in its own thread, released at the same instant; returns their results (or exceptions)."""
    barrier = threading.Barrier(len(jobs))
    results = [None] * len(jobs)

    def worker(i, job):
        try:
            barrier.wait(timeout=10)
            results[i] = job()
        except Exception as exc:  # noqa: BLE001 - the exception is the result under test
            results[i] = exc
        finally:
            connection.close()

    threads = [threading.Thread(target=worker, args=(i, job)) for i, job in enumerate(jobs)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=60)
    return results


class ConcurrencyTests(TransactionTestCase):
    def setUp(self):
        call_command("seed_project_data", tenant_code="CON-T", allow_non_debug=True, stdout=StringIO())
        self.tenant = Tenant.objects.get(code="CON-T")
        set_current_tenant(self.tenant)

    def tearDown(self):
        set_current_tenant(None)

    def user(self, role):
        return User.objects.filter(tenant=self.tenant, role=role).order_by("email").first()

    def api(self, role):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(self.user(role)).access_token}")
        return client

    def test_two_makers_exporting_at_once_never_send_the_same_batch_twice(self):
        pool = JournalBatch._base_manager.filter(tenant=self.tenant).first().pool
        maker = self.user("finance_maker")

        def export():
            set_current_tenant(self.tenant)
            return create_export(pool=pool, date_from=None, date_to=None, user=maker)

        results = run_together([export, export])
        made = [r for r in results if isinstance(r, GLExport)]
        refused = [r for r in results if not isinstance(r, GLExport)]
        self.assertEqual(len(made), 1, results)
        self.assertEqual(len(refused), 1, results)
        sent = sum(x.batches.count() for x in GLExport._base_manager.filter(tenant=self.tenant))
        self.assertEqual(sent, JournalBatch._base_manager.filter(pool=pool, status="posted").count())

    def test_two_signatories_releasing_the_same_distribution_at_once_release_it_once(self):
        run = InvestmentDistributionRun._base_manager.get(tenant=self.tenant, status=DistributionRunStatus.PENDING_APPROVAL)
        url = f"/api/v1/investments/distribution-runs/{run.pk}/"
        for role, verb, body in (("finance_checker", "check/", None), ("shariah_board", "shariah-sign-off/", {"note": "ok"})):
            response = self.api(role).post(url + verb, body, format="json", HTTP_X_TENANT_CODE="CON-T")
            self.assertEqual(response.status_code, 200, response.data)
            set_current_tenant(self.tenant)

        def release():
            return self.api("authorized_signatory").post(url + "approve/", {}, format="json", HTTP_X_TENANT_CODE="CON-T")

        responses = run_together([release, release])
        codes = sorted(getattr(r, "status_code", 500) for r in responses)
        self.assertEqual(codes, [200, 400], responses)
        set_current_tenant(self.tenant)
        self.assertEqual(JournalBatch._base_manager.filter(investment_run_id=run.pk).count(), 1, "the run was journalled twice")
        self.assertEqual(InvestmentDistributionRun._base_manager.get(pk=run.pk).status, DistributionRunStatus.SIGNED)

    def test_two_checkers_answering_the_same_export_or_suspense_item_at_once_succeed_once(self):
        from apps.accounting.gl_handover import confirm_export
        from apps.accounting.models import SuspenseItem
        from apps.accounting.suspense import approve_open, propose_open

        pool = JournalBatch._base_manager.filter(tenant=self.tenant).first().pool
        maker = self.user("finance_maker")
        export = create_export(pool=pool, date_from=None, date_to=None, user=maker)
        checker_a = self.user("finance_checker")

        def confirm():
            set_current_tenant(self.tenant)
            return confirm_export(GLExport._base_manager.get(pk=export.pk), checker_a, "ERP-1")

        results = run_together([confirm, confirm])
        self.assertEqual(sum(isinstance(r, GLExport) for r in results), 1, results)

        item = propose_open(pool=pool, side="unidentified_receipt", amount="50.00", description="race", user=maker)

        def approve():
            set_current_tenant(self.tenant)
            return approve_open(SuspenseItem._base_manager.get(pk=item.pk), checker_a)

        results = run_together([approve, approve])
        self.assertEqual(sum(isinstance(r, SuspenseItem) for r in results), 1, results)
        set_current_tenant(self.tenant)
        self.assertEqual(JournalBatch._base_manager.filter(pool=pool, id=SuspenseItem._base_manager.get(pk=item.pk).opening_journal_id).count(), 1)
        self.assertEqual(SuspenseItem._base_manager.filter(pool=pool, status="open").count(), 1, "the item was opened twice")
