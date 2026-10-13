from datetime import date, timedelta
from decimal import Decimal
from unittest import mock

from django.core import mail
from django.urls import reverse
from django.utils import timezone
from rest_framework import status

from apps.accounts.models import UserRole
from apps.allocation.models import PSRStatus, ProfitSharingRatio, WeightageBand, WeightageBandStatus
from apps.allocation.test_participant_ledger import ParticipantLedgerTestBase
from apps.circles.models import ArrearsRecord, CircleMember
from apps.pools.models import Pool, PoolStatus
from apps.products.models import ContractTemplate, JurisdictionRulePack, Product

from .models import EmailStatus, Notification, NotificationCategory
from .services import notify_users


class NotificationBase(ParticipantLedgerTestBase):
    def inbox(self, user):
        return list(Notification.objects.filter(recipient_user=user))

    def titles(self, user):
        return [n.title for n in self.inbox(user)]


class ApprovalNudgeTests(NotificationBase):
    def test_each_ceremony_stage_notifies_the_next_owner_only(self):
        run_id = self.create_run()
        self.authenticate(self.maker)
        base = reverse("allocation-run-detail", args=[run_id])
        self.client.post(base + "submit-for-checking/")
        self.assertTrue(any("independent check" in t for t in self.titles(self.checker)))
        self.assertEqual(self.inbox(self.signatory), [])  # not yet their turn
        self.assertEqual(self.inbox(self.maker), [])  # nobody nudges the actor

        from apps.allocation.ceremony_helpers import sign_run_days

        sign_run_days(run_id)
        self.authenticate(self.checker)
        self.client.post(base + "check/")
        self.assertTrue(any("final release" in t for t in self.titles(self.signatory)))  # investment pool: no Shariah stage

        self.authenticate(self.signatory)
        self.client.post(base + "approve/")
        outcome = self.inbox(self.maker)
        self.assertEqual(len(outcome), 1)
        self.assertEqual(outcome[0].category, NotificationCategory.APPROVAL_OUTCOME)
        self.assertIn("released", outcome[0].title)
        self.assertEqual(outcome[0].link, f"/allocation-runs/{run_id}")

    def test_rejection_tells_the_maker_the_reason(self):
        run_id = self.create_run()
        self.authenticate(self.maker)
        base = reverse("allocation-run-detail", args=[run_id])
        self.client.post(base + "submit-for-checking/")
        self.authenticate(self.checker)
        self.client.post(base + "reject/", {"rejection_reason": "Income not final"}, format="json")
        rejected = [n for n in self.inbox(self.maker) if "rejected" in n.title]
        self.assertEqual(len(rejected), 1)
        self.assertIn("Income not final", rejected[0].body)

    def test_a_notification_failure_never_blocks_the_business_action(self):
        run_id = self.create_run()
        self.authenticate(self.maker)
        with mock.patch("apps.notifications.services.Notification.objects.create", side_effect=RuntimeError("db down")):
            response = self.client.post(reverse("allocation-run-detail", args=[run_id]) + "submit-for-checking/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class InboxApiTests(NotificationBase):
    def setUp(self):
        super().setUp()
        notify_users(self.tenant, [self.maker, self.checker], category=NotificationCategory.SYSTEM, title="Hello")
        notify_users(self.tenant, [self.maker], category=NotificationCategory.SYSTEM, title="Second")

    def test_users_see_only_their_own_notifications(self):
        self.authenticate(self.maker)
        self.assertEqual(len(self.client.get(reverse("notification-list")).data), 2)
        self.authenticate(self.checker)
        data = self.client.get(reverse("notification-list")).data
        self.assertEqual([n["title"] for n in data], ["Hello"])
        # Someone else's notification is simply not found.
        other = Notification.objects.get(recipient_user=self.maker, title="Hello")
        self.assertEqual(
            self.client.post(reverse("notification-mark-read", args=[other.id])).status_code, status.HTTP_404_NOT_FOUND
        )

    def test_unread_count_and_mark_read(self):
        self.authenticate(self.maker)
        self.assertEqual(self.client.get(reverse("notification-unread-count")).data["count"], 2)
        first = self.client.get(reverse("notification-list")).data[0]
        self.client.post(reverse("notification-mark-read", args=[first["id"]]))
        self.assertEqual(self.client.get(reverse("notification-unread-count")).data["count"], 1)
        unread = self.client.get(reverse("notification-list"), {"unread": "true"}).data
        self.assertEqual(len(unread), 1)
        self.assertEqual(self.client.post(reverse("notification-mark-all-read")).data["marked"], 1)
        self.assertEqual(self.client.get(reverse("notification-unread-count")).data["count"], 0)

    def test_notifications_are_read_only_through_the_api(self):
        self.authenticate(self.maker)
        self.assertEqual(
            self.client.post(reverse("notification-list"), {"title": "x"}, format="json").status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )


class ArrearsReminderTests(NotificationBase):
    def setUp(self):
        super().setUp()
        circle_product = Product.objects.create(
            tenant=self.tenant, name="Circle", code="CIR", operating_model="community_circle",
            contract_template=ContractTemplate.objects.create(
                tenant=self.tenant, name="Q", contract_type="qard", version="1", clauses={}
            ),
        )
        self.circle = Pool.objects.create(
            tenant=self.tenant, name="Circle 1", code="CIR-1", product=circle_product, effective_date=date(2026, 1, 1)
        )
        self.risk = self._user("risk2", UserRole.RISK_COMPLIANCE)
        self.member = CircleMember.objects.create(
            tenant=self.tenant, pool=self.circle, member_name="Sana Rehman", member_reference="M-1",
            joined_date=date(2026, 1, 1), payout_position=1, email="sana@example.com",
        )

    def flag(self, member=None):
        self.authenticate(self.risk)
        return self.client.post(
            reverse("circle-member-flag-arrears", args=[(member or self.member).id]),
            {"cycle_number": 2, "expected_amount": "5000.00"}, format="json",
        )

    def test_flagging_arrears_sends_a_respectful_email_and_alerts_staff(self):
        mail.outbox.clear()
        self.assertEqual(self.flag().status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.to, ["sana@example.com"])
        self.assertIn("hardship", message.body.lower())
        self.assertIn("no penalty", message.body.lower())  # BR-007: never a late fee
        record = Notification.objects.get(recipient_email="sana@example.com")
        self.assertEqual(record.email_status, EmailStatus.SENT)
        self.assertTrue(any("Arrears recorded" in t for t in self.titles(self.pool_manager)))

    def test_a_failed_email_is_recorded_and_does_not_fail_the_request(self):
        with mock.patch("apps.notifications.services.send_mail", side_effect=OSError("smtp down")):
            self.assertEqual(self.flag().status_code, status.HTTP_201_CREATED)
        record = Notification.objects.get(recipient_email="sana@example.com")
        self.assertEqual(record.email_status, EmailStatus.FAILED)
        self.assertIn("smtp down", record.email_error)
        self.assertEqual(ArrearsRecord.objects.count(), 1)

    def test_member_without_an_email_only_alerts_staff(self):
        self.member.email = ""
        self.member.save()
        mail.outbox.clear()
        self.flag()
        self.assertEqual(len(mail.outbox), 0)
        self.assertFalse(Notification.objects.exclude(recipient_email="").exists())


class EconomicsChangeNoticeTests(NotificationBase):
    """BR-003: economics changes on a live pool need notice, an impact simulation and notifications."""

    def setUp(self):
        super().setUp()
        self.board = self._user("boardmember", UserRole.SHARIAH_BOARD)
        JurisdictionRulePack.objects.create(
            tenant=self.tenant, code="PK-SBP", name="SBP", version="1", effective_date=date(2025, 1, 1),
            is_default=True, rules_config={"notice_period_days": 30},
        )
        self.pool.status = PoolStatus.OPEN
        self.pool.save()
        self.ali.email = "ali@example.com"
        self.ali.save()
        # An existing signed run gives the impact simulation something to run on.
        self.sign_run()
        ProfitSharingRatio.objects.filter(pool=self.pool).update(effective_to=timezone.localdate() + timedelta(days=39))

    def draft_psr(self, effective_from):
        return ProfitSharingRatio.objects.create(
            tenant=self.tenant, pool=self.pool, depositor_share=Decimal("60.00"), mudarib_share=Decimal("40.00"),
            effective_from=effective_from, status=PSRStatus.DRAFT,
        )

    def approve_psr(self, psr):
        self.authenticate(self.board)
        return self.client.post(f"/api/v1/allocation/psr-schedules/{psr.id}/approve/")

    def test_a_change_inside_the_notice_period_is_refused(self):
        psr = self.draft_psr(timezone.localdate() + timedelta(days=10))
        response = self.approve_psr(psr)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("30 days", str(response.data))
        psr.refresh_from_db()
        self.assertEqual(psr.status, PSRStatus.DRAFT)

    def test_a_change_with_proper_notice_is_approved_simulated_and_announced(self):
        mail.outbox.clear()
        psr = self.draft_psr(timezone.localdate() + timedelta(days=40))
        response = self.approve_psr(psr)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        staff = [n for n in self.inbox(self.pool_manager) if n.category == NotificationCategory.ECONOMICS_CHANGE]
        self.assertEqual(len(staff), 1)
        self.assertIn("Mudarib share would be", staff[0].body)  # the impact simulation is attached
        self.assertIn("effective", staff[0].title.lower())

        # The participant with a portal login and the one with only an email are both told.
        self.assertTrue(any(n.category == NotificationCategory.ECONOMICS_CHANGE for n in self.inbox(self.investor_b)))
        self.assertEqual([m.to for m in mail.outbox], [["ali@example.com"]])

        from apps.core.models import AuditLog

        audit = AuditLog.objects.filter(model_name="ProfitSharingRatio", action="approve").latest("created_at")
        self.assertIn("economics_change_impact", audit.changes)

    def test_a_pool_that_is_not_live_yet_is_not_subject_to_notice(self):
        self.pool.status = PoolStatus.APPROVED
        self.pool.save()
        psr = self.draft_psr(timezone.localdate())
        self.assertEqual(self.approve_psr(psr).status_code, status.HTTP_200_OK)
        self.assertEqual(
            [n for n in self.inbox(self.pool_manager) if n.category == NotificationCategory.ECONOMICS_CHANGE], []
        )

    def test_weightage_changes_are_covered_too(self):
        band = WeightageBand.objects.create(
            tenant=self.tenant, pool=self.pool, participant_class="retail", weightage=Decimal("1.20"),
            effective_from=timezone.localdate() + timedelta(days=5), status=WeightageBandStatus.DRAFT,
        )
        self.authenticate(self.board)
        refused = self.client.post(f"/api/v1/allocation/weightage-bands/{band.id}/approve/")
        self.assertEqual(refused.status_code, status.HTTP_400_BAD_REQUEST)
        WeightageBand.objects.filter(pk=band.pk).update(effective_from=timezone.localdate() + timedelta(days=40))
        # An older open-ended band for the class must end before the new one starts.
        WeightageBand.objects.filter(pool=self.pool, participant_class="retail", status="approved").update(
            effective_to=timezone.localdate() + timedelta(days=39)
        )
        self.assertEqual(
            self.client.post(f"/api/v1/allocation/weightage-bands/{band.id}/approve/").status_code, status.HTTP_200_OK
        )
        self.assertTrue(
            any("Weightage change" in n.body for n in self.inbox(self.pool_manager) if n.category == NotificationCategory.ECONOMICS_CHANGE)
        )
