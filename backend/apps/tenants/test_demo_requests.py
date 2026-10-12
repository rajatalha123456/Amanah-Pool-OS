from django.core.cache import cache
from rest_framework.test import APITestCase

from apps.accounts.models import User, UserRole
from apps.core.context import set_current_tenant
from apps.tenants.models import DemoRequest, Tenant

PUBLIC = "/api/v1/public/demo-requests/"
INBOX = "/api/v1/demo-requests/"
GOOD = {"name": "Visitor One", "organisation": "Example Bank", "email": "Visitor@Example.org", "interest": "bank_pool"}


class DemoRequestTests(APITestCase):
    def setUp(self):
        cache.clear()  # the throttle counts per address in the cache

    def test_a_visitor_can_ask_for_a_demo_without_logging_in(self):
        response = self.client.post(PUBLIC, GOOD, format="json")
        self.assertEqual(response.status_code, 201, response.content)
        stored = DemoRequest.objects.get()
        self.assertEqual((stored.email, stored.interest, stored.handled), ("visitor@example.org", "bank_pool", False))

    def test_bad_input_is_refused(self):
        for bad in ({**GOOD, "email": "nope"}, {**GOOD, "name": ""}, {**GOOD, "interest": "hack"}, {"name": "x"}):
            with self.subTest(bad=bad):
                self.assertEqual(self.client.post(PUBLIC, bad, format="json").status_code, 400)
        self.assertEqual(DemoRequest.objects.count(), 0)

    def test_a_filled_honeypot_stores_nothing(self):
        self.assertEqual(self.client.post(PUBLIC, {**GOOD, "website": "http://spam.example"}, format="json").status_code, 201)
        self.assertEqual(DemoRequest.objects.count(), 0)

    def test_submissions_are_throttled_per_address(self):
        codes = [self.client.post(PUBLIC, GOOD, format="json").status_code for _ in range(7)]
        self.assertEqual(codes[:5], [201] * 5)
        self.assertIn(429, codes[5:])

    def test_only_the_platform_admin_reads_the_inbox(self):
        self.client.post(PUBLIC, GOOD, format="json")
        tenant = Tenant.objects.create(name="T", code="T-1", data_residency="PK")
        set_current_tenant(tenant)
        admin = User.objects.create_user(email="a@x.com", password="p", full_name="A", role=UserRole.PLATFORM_SUPER_ADMIN, tenant=tenant)
        maker = User.objects.create_user(email="m@x.com", password="p", full_name="M", role=UserRole.FINANCE_MAKER, tenant=tenant)
        self.client.defaults["HTTP_X_TENANT_CODE"] = tenant.code
        self.client.force_authenticate(user=maker)
        self.assertEqual(self.client.get(INBOX).status_code, 403)
        self.client.force_authenticate(user=admin)
        listing = self.client.get(INBOX)
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(len(listing.data), 1)
        handled = self.client.post(f"{INBOX}{listing.data[0]['id']}/mark-handled/")
        self.assertTrue(handled.data["handled"])
        set_current_tenant(None)
