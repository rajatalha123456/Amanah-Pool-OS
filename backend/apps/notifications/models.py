from django.db import models
from django.utils import timezone

from apps.core.models import TenantScopedModel


class NotificationCategory(models.TextChoices):
    APPROVAL_REQUIRED = "approval_required", "Approval required"
    APPROVAL_OUTCOME = "approval_outcome", "Approval outcome"
    ARREARS_REMINDER = "arrears_reminder", "Arrears reminder"
    ECONOMICS_CHANGE = "economics_change", "Economics change notice"
    SYSTEM = "system", "System"


class EmailStatus(models.TextChoices):
    NOT_APPLICABLE = "not_applicable", "In-app only"
    SENT = "sent", "Sent"
    FAILED = "failed", "Failed"


class Notification(TenantScopedModel):
    """
    A message to a user (in-app) and/or an external address (email). Delivery status of the email
    is recorded (BRD Section 12: messaging "delivery status"); the in-app copy is always kept.
    """

    recipient_user = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, null=True, blank=True, related_name="notifications"
    )
    recipient_email = models.EmailField(blank=True, default="")
    category = models.CharField(max_length=30, choices=NotificationCategory.choices)
    title = models.CharField(max_length=255)
    body = models.TextField(blank=True, default="")
    # Frontend path to open when the notification is clicked (e.g. /allocation-runs/<id>).
    link = models.CharField(max_length=255, blank=True, default="")
    related_model = models.CharField(max_length=60, blank=True, default="")
    related_id = models.CharField(max_length=64, blank=True, default="")
    read_at = models.DateTimeField(null=True, blank=True)
    email_status = models.CharField(
        max_length=20, choices=EmailStatus.choices, default=EmailStatus.NOT_APPLICABLE
    )
    email_error = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["recipient_user", "read_at"], name="notif_user_read_idx")]

    def mark_read(self):
        if self.read_at is None:
            self.read_at = timezone.now()
            self.save(update_fields=["read_at", "updated_at"])

    def __str__(self):
        target = self.recipient_user.email if self.recipient_user_id else self.recipient_email
        return f"{self.category} -> {target}: {self.title}"
