from django.db import models


class AIModelStatus(models.TextChoices):
	ACTIVE = "active", "Active"
	DISABLED = "disabled", "Disabled"


class AIModelRegistry(models.Model):
	model_name = models.CharField(max_length=100, unique=True)
	version = models.CharField(max_length=50)
	status = models.CharField(
		max_length=10,
		choices=AIModelStatus.choices,
		default=AIModelStatus.ACTIVE,
	)
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
