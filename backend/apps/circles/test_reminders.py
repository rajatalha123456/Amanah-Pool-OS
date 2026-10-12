from datetime import date
from decimal import Decimal

from rest_framework.test import APITestCase

from apps.accounts.models import User, UserRole
from apps.core.context import set_current_tenant
from apps.notifications.models import Notification
from apps.pools.models import Pool, PoolStatus

from .models import CircleMember, Contribution
from .reminders import cycle_due_date, cycle_status, send_reminders
from .rules import publish_rules
from .tests import CircleRotationApiTests


class ContributionReminderTests(APITestCase):
    _make_pool = CircleRotationApiTests._make_pool

    def setUp(self):
        CircleRotationApiTests.setUp(self)
        set_current_tenant(self.tenant)
        Pool._base_manager.filter(pk=self.pool.pk).update(status=PoolStatus.OPEN)
        self.rules = publish_rules(
            pool=self.pool, user=self.pool_manager, contribution_amount=Decimal("1000"), cycle_days=30,
            order_policy="Draw", hardship_policy="Review", first_due_date=date(2026, 9, 5),
        )
        self.alice = CircleMember.objects.create(
            tenant=self.tenant, pool=self.pool, member_name="Alice", member_reference="M-A",
            joined_date=date(2026, 1, 1), email="alice@example.org",
        )
        self.bob = CircleMember.objects.create(
            tenant=self.tenant, pool=self.pool, member_name="Bob", member_reference="M-B", joined_date=date(2026, 1, 1)
        )

    def tearDown(self):
        set_current_tenant(None)

    def reminders(self):
        return Notification._base_manager.filter(related_model="ContributionReminder")

    def test_due_date_arithmetic(self):
        self.assertEqual(cycle_due_date(self.rules, 1), date(2026, 9, 5))
        self.assertEqual(cycle_due_date(self.rules, 3), date(2026, 11, 4))
        self.assertEqual(cycle_status(self.rules, date(2026, 9, 3), 2, 3), [(1, date(2026, 9, 5), "upcoming")])
        self.assertEqual(cycle_status(self.rules, date(2026, 9, 5), 2, 3), [(1, date(2026, 9, 5), "upcoming")])  # due today
        self.assertEqual(cycle_status(self.rules, date(2026, 9, 6), 2, 3), [(1, date(2026, 9, 5), "overdue")])
        self.assertEqual(cycle_status(self.rules, date(2026, 7, 1), 2, 3), [])

    def test_upcoming_reminder_goes_to_unpaid_members_once(self):
        Contribution.objects.create(
            tenant=self.tenant, member=self.bob, cycle_number=1, amount=Decimal("1000"), contribution_date=date(2026, 9, 2),
            status="received", payment_reference="R-B",
        )
        first = send_reminders(date(2026, 9, 3))
        self.assertEqual(first, {"upcoming": 1, "overdue": 0})  # Alice only; Bob has paid
        self.assertEqual(send_reminders(date(2026, 9, 3)), {"upcoming": 0, "overdue": 0})  # not repeated
        self.assertEqual(self.reminders().filter(recipient_email="alice@example.org").count(), 1)

    def test_nothing_is_sent_far_from_the_due_date(self):
        self.assertEqual(send_reminders(date(2026, 8, 20)), {"upcoming": 0, "overdue": 0})

    def test_overdue_members_are_reminded_gently_and_staff_are_told_but_nothing_is_flagged(self):
        sent = send_reminders(date(2026, 9, 8))
        self.assertEqual(sent["overdue"], 2)
        staff = self.reminders().filter(recipient_user__role__in=["risk_compliance", "pool_manager"])
        self.assertTrue(staff.exists())
        self.assertIn("no penalty", self.reminders().filter(recipient_email="alice@example.org").first().body)
        self.assertEqual(self.alice.arrears_records.count(), 0)
