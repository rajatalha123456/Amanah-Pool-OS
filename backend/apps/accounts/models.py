from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.db import models


class UserRole(models.TextChoices):
    PLATFORM_SUPER_ADMIN = "platform_super_admin", "Platform Super Admin"
    PRODUCT_MANAGER = "product_manager", "Product Manager"
    POOL_MANAGER = "pool_manager", "Pool Manager"
    FINANCE_MAKER = "finance_maker", "Finance Maker"
    FINANCE_CHECKER = "finance_checker", "Finance Checker"
    SHARIAH_SECRETARIAT = "shariah_secretariat", "Shariah Secretariat"
    SHARIAH_BOARD = "shariah_board", "Shariah Board"
    RISK_COMPLIANCE = "risk_compliance", "Risk & Compliance"
    AUDITOR = "auditor", "Auditor"
    INVESTOR_MEMBER = "investor_member", "Investor / Member"


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("Users must have an email address")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", UserRole.PLATFORM_SUPER_ADMIN)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True")

        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    username = None
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=255)
    role = models.CharField(max_length=30, choices=UserRole.choices)
    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.CASCADE,
        related_name="users",
        null=True,
        blank=True,
    )
    totp_secret = models.CharField(max_length=64, null=True, blank=True)
    mfa_enabled = models.BooleanField(default=False)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name", "role"]

    objects = UserManager()

    def __str__(self):
        return self.email
