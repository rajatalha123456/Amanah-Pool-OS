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
