from django.db import models

from apps.core.models import BaseModel


class Tenant(BaseModel):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50, unique=True)
    domain = models.CharField(max_length=255, unique=True, null=True, blank=True)
    data_residency = models.CharField(max_length=10)
    is_suspended = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class LegalEntity(BaseModel):
    tenant = models.ForeignKey(
        Tenant, on_delete=models.CASCADE, related_name="legal_entities"
    )
    name = models.CharField(max_length=255)
    registration_number = models.CharField(max_length=100, null=True, blank=True)
    jurisdiction = models.CharField(max_length=100)
    base_currency = models.CharField(max_length=10, default="PKR")
    timezone = models.CharField(max_length=50, default="Asia/Karachi")

    def __str__(self):
        return self.name


class DemoRequest(BaseModel):
    """
    An enquiry from the public website. It belongs to no tenant (the visitor is not a user yet) and is read only by
    the Platform Super Admin, who handles tenant onboarding.
    """

    INTERESTS = [
        ("bank_pool", "Islamic bank pool"),
        ("investment_pool", "Investment pool"),
        ("community_circle", "Community savings circle"),
        ("other", "Something else"),
    ]

    name = models.CharField(max_length=120)
    organisation = models.CharField(max_length=160)
    email = models.EmailField()
    interest = models.CharField(max_length=20, choices=INTERESTS, default="other")
    message = models.TextField(blank=True, default="")
    handled = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.organisation})"


class FeatureFlag(BaseModel):
    """A switch the platform administrator sets per tenant (BRD 3). A flag that was never set is off."""

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="feature_flags")
    key = models.SlugField(max_length=80)
    enabled = models.BooleanField(default=False)
    note = models.CharField(max_length=255, blank=True, default="")
    changed_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")

    class Meta:
        constraints = [models.UniqueConstraint(fields=["tenant", "key"], name="unique_flag_per_tenant")]
        ordering = ["key"]

    def __str__(self):
        return f"{self.tenant.code}:{self.key}={'on' if self.enabled else 'off'}"


def feature_enabled(tenant, key):
    return FeatureFlag.objects.filter(tenant=tenant, key=key, enabled=True, is_active=True).exists()


class EncryptionKeyRecord(BaseModel):
    """
    The register of the keys that protect a tenant's data: purpose, where the key lives and when it was last rotated.
    It holds NO key material: the key itself stays in the bank's KMS/HSM. Recording a rotation here is the administrator's
    attestation that the rotation was done there, and an overdue rotation is flagged.
    """

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="encryption_keys")
    purpose = models.CharField(max_length=120)
    provider = models.CharField(max_length=80, help_text="e.g. the bank's HSM or a cloud KMS")
    key_reference = models.CharField(max_length=255, help_text="The key's identifier in that system, never the key")
    rotation_interval_days = models.PositiveIntegerField(default=365)
    last_rotated_on = models.DateField(null=True, blank=True)
    retired = models.BooleanField(default=False)

    class Meta:
        ordering = ["purpose"]

    @property
    def rotation_due_on(self):
        from datetime import timedelta

        return self.last_rotated_on + timedelta(days=self.rotation_interval_days) if self.last_rotated_on else None

    @property
    def overdue(self):
        from django.utils import timezone

        if self.retired:
            return False
        due = self.rotation_due_on
        return due is None or due < timezone.localdate()
