from decimal import Decimal

from django.db import models

from apps.core.models import TenantScopedModel


class AIModelStatus(models.TextChoices):
	ACTIVE = "active", "Active"
	DISABLED = "disabled", "Disabled"


class ModelValidation(models.TextChoices):
	NOT_VALIDATED = "not_validated", "Not validated"
	VALIDATED = "validated", "Validated"
	EXPIRED = "expired", "Validation expired"


class AIModelRegistry(models.Model):
	model_name = models.CharField(max_length=100, unique=True)
	version = models.CharField(max_length=50)
	status = models.CharField(
		max_length=10,
		choices=AIModelStatus.choices,
		default=AIModelStatus.ACTIVE,
	)
	# Model inventory (BRD 9): who answers for it, what it is for, where it came from, whether it was validated, when it retires.
	owner = models.CharField(max_length=150, blank=True, default="")
	purpose = models.TextField(blank=True, default="")
	provenance = models.TextField(blank=True, default="")
	validation_status = models.CharField(max_length=15, choices=ModelValidation.choices, default=ModelValidation.NOT_VALIDATED)
	validated_on = models.DateField(null=True, blank=True)
	validation_reference = models.CharField(max_length=200, blank=True, default="")
	retirement_date = models.DateField(null=True, blank=True)
	# AI policy (BRD 5): outputs below this confidence are reported as low-confidence. Every output still needs a human
	# decision; the threshold never lets an output skip review.
	confidence_threshold = models.DecimalField(max_digits=4, decimal_places=3, default=Decimal("0.800"))
	disabled_reason = models.TextField(null=True, blank=True)
	disabled_by = models.ForeignKey(
		"accounts.User",
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name="disabled_ai_models",
	)
	disabled_at = models.DateTimeField(null=True, blank=True)

	def __str__(self):
		return f"{self.model_name} v{self.version} ({self.status})"


def is_ai_model_enabled(model_name):
	return AIModelRegistry.objects.filter(
		model_name=model_name,
		status=AIModelStatus.ACTIVE,
	).exists()


def is_ai_feature_allowed(model_name):
	"""Kill switch for features that work without a registry row: only an explicit DISABLED row blocks them."""
	return not AIModelRegistry.objects.filter(model_name=model_name, status=AIModelStatus.DISABLED).exists()


class Disposition(models.TextChoices):
	PENDING = "pending", "Awaiting human decision"
	ACCEPTED = "accepted", "Accepted"
	REJECTED = "rejected", "Rejected"
	OVERRIDDEN = "overridden", "Overridden with a different decision"


class AIRecommendation(TenantScopedModel):
	"""
	One AI output, recorded uniformly (BR-009): which model/version produced it, what was asked (prompt log),
	the sources it relied on, its confidence and reason, and the human disposition. The AI output itself is
	immutable; only the disposition fields can change, and only by a person.
	"""

	feature = models.CharField(max_length=50)
	model_name = models.CharField(max_length=100)
	model_version = models.CharField(max_length=50, blank=True, default="")
	requested_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, related_name="+")
	subject_type = models.CharField(max_length=50, blank=True, default="")
	subject_id = models.CharField(max_length=64, blank=True, default="")
	prompt_hash = models.CharField(max_length=64, blank=True, default="")
	prompt_text = models.TextField(blank=True, default="")  # truncated; the hash covers the full input
	output = models.JSONField(default=dict)
	sources = models.JSONField(default=list)
	confidence = models.DecimalField(max_digits=4, decimal_places=3, null=True, blank=True)
	reason = models.TextField(blank=True, default="")
	requires_human_review = models.BooleanField(default=True)
	is_fallback = models.BooleanField(default=False)
	latency_ms = models.IntegerField(default=0)
	disposition = models.CharField(max_length=12, choices=Disposition.choices, default=Disposition.PENDING)
	disposed_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
	disposed_at = models.DateTimeField(null=True, blank=True)
	disposition_note = models.TextField(blank=True, default="")

	_DISPOSITION_FIELDS = frozenset(
		{"disposition", "disposed_by", "disposed_at", "disposition_note", "disposed_by_id", "updated_at"}
	)

	def save(self, *args, **kwargs):
		from django.core.exceptions import ValidationError

		if not self._state.adding:
			update_fields = kwargs.get("update_fields")
			if update_fields is None or not set(update_fields) <= self._DISPOSITION_FIELDS:
				raise ValidationError("A recorded AI output is immutable; only its disposition may change.")
		super().save(*args, **kwargs)

	class Meta:
		ordering = ["-created_at"]
