"""
BRD prohibitions that must hold by construction (R-003, R-004, R-010/R-169, R-110). These read the code and the models,
so a later change that adds a forbidden path fails here.
"""

import re
from pathlib import Path

from django.apps import apps as django_apps
from django.test import SimpleTestCase

APPS = Path(__file__).resolve().parents[1]
FORBIDDEN_CIRCLE_WORDS = re.compile(r"interest|riba|late_fee|late_charge|penalty|uplift|markup|profit_rate|apr|rate", re.I)
PROTECTED_TRAITS = re.compile(r"\b(gender|sex|religion|ethnic\w*|race|nationality|caste|disabilit\w*|marital|age|birth\w*)\b", re.I)


class CircleHasNoTimeValueTest(SimpleTestCase):
    def test_no_circle_model_field_carries_a_rate_charge_or_uplift(self):
        # "Circles: no interest or time-value uplift" - a circle pays out exactly the pot collected.
        offenders = []
        for model in django_apps.get_app_config("circles").get_models():
            for field in model._meta.get_fields():
                if FORBIDDEN_CIRCLE_WORDS.search(field.name):
                    offenders.append(f"{model.__name__}.{field.name}")
        self.assertEqual(offenders, [], "a circle model must not hold an interest, rate, late-charge or uplift field")

    def test_no_circle_serializer_or_view_accepts_such_a_field(self):
        offenders = []
        for name in ("serializers.py", "views.py", "payouts.py", "rules.py"):
            text = (APPS / "circles" / name).read_text(encoding="utf-8")
            for match in re.finditer(r"""["'](\w*(?:interest|late_fee|late_charge|penalty|uplift|markup)\w*)["']""", text, re.I):
                offenders.append(f"{name}: {match.group(1)}")
        self.assertEqual(offenders, [])


class AiCannotMoveMoneyTest(SimpleTestCase):
    def test_ai_agents_import_no_accounting_distribution_or_negligence_code(self):
        # R-004 (no journal posting) and R-003 (no loss waiver): the AI package has no path to those services.
        bad = re.compile(r"from\s+apps\.(accounting|investments)|import\s+apps\.(accounting|investments)|negligence|create_journal|post_adjustment|PurificationEntry\.objects\.(create|update)")
        offenders = []
        for path in (APPS / "ai_agents").rglob("*.py"):
            if "test" in path.name or "migrations" in path.parts:
                continue
            for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if bad.search(line):
                    offenders.append(f"{path.relative_to(APPS.parent)}:{n}: {line.strip()}")
        self.assertEqual(offenders, [])


class HardshipUsesNoProtectedTraitsTest(SimpleTestCase):
    def test_predictor_reads_only_behaviour_never_a_protected_trait(self):
        source = (APPS / "ai_agents" / "services" / "hardship_predictor.py").read_text(encoding="utf-8")
        code = "\n".join(l for l in source.splitlines() if not l.strip().startswith(("#", '"""')))
        self.assertIsNone(PROTECTED_TRAITS.search(re.sub(r'"""[\s\S]*?"""', "", code)))
