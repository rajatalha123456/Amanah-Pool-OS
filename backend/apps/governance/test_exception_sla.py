from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from apps.core.context import set_current_tenant
from apps.core.control_alerts import build_alerts
from apps.tenants.models import Tenant

from .models import ExceptionCase
from .sla import sla_breached, sla_due_on


class ExceptionSlaTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="SLA", code="SLA-T", data_residency="PK")
        set_current_tenant(self.tenant)

    def tearDown(self):
        set_current_tenant(None)

    def case(self, severity, age_days, status="open"):
        c = ExceptionCase.objects.create(tenant=self.tenant, source_module="manual", severity=severity, title="t", description="d", status=status)
        ExceptionCase._base_manager.filter(pk=c.pk).update(created_at=timezone.now() - timedelta(days=age_days))
        return ExceptionCase._base_manager.get(pk=c.pk)

    def test_a_critical_case_breaches_after_one_day_and_a_low_one_after_fourteen(self):
        self.assertFalse(sla_breached(self.case("critical", 1)))
        self.assertTrue(sla_breached(self.case("critical", 2)))
        self.assertFalse(sla_breached(self.case("low", 14)))
        self.assertTrue(sla_breached(self.case("low", 15)))

    def test_a_resolved_case_never_breaches_and_an_open_breach_raises_an_alert(self):
        self.assertFalse(sla_breached(self.case("critical", 30, status="resolved")))
        self.assertEqual(sla_due_on(self.case("high", 0)), (timezone.now() + timedelta(days=3)).date())
        self.case("critical", 5)
        codes = [a["code"] for a in build_alerts(self.tenant)]
        self.assertIn("exception_sla_breached", codes)


    def test_a_rule_pack_sets_its_own_time_limits(self):
        from datetime import date

        from apps.products.models import JurisdictionRulePack
        from .sla import sla_basis_for, sla_days

        JurisdictionRulePack.objects.create(
            tenant=self.tenant, code="PK", name="PK", version="1", effective_date=date(2026, 1, 1), is_active=True,
            is_default=True, rules_config={"exception_sla_days": {"critical": 2}},
        )
        case = self.case("critical", 0)
        self.assertEqual((sla_days(case), sla_basis_for(case)), (2, "rule pack"))
        self.assertFalse(sla_breached(self.case("critical", 2)))
        self.assertEqual(sla_days(self.case("low", 0)), 14)  # not set in the pack: the default
