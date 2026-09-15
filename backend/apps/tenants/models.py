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
