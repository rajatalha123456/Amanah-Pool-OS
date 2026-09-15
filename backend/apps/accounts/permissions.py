from rest_framework.permissions import BasePermission

from .models import UserRole


class HasRole(BasePermission):
    """
    Base class for a single-role permission check. Subclasses set `role`.
    """

    role = None

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == self.role
        )


class IsPlatformSuperAdmin(HasRole):
    role = UserRole.PLATFORM_SUPER_ADMIN


class IsProductManager(HasRole):
    role = UserRole.PRODUCT_MANAGER


class IsPoolManager(HasRole):
    role = UserRole.POOL_MANAGER


class IsFinanceMaker(HasRole):
    role = UserRole.FINANCE_MAKER


class IsFinanceChecker(HasRole):
    role = UserRole.FINANCE_CHECKER


class IsShariahSecretariat(HasRole):
    role = UserRole.SHARIAH_SECRETARIAT


class IsShariahBoard(HasRole):
    role = UserRole.SHARIAH_BOARD


class IsRiskCompliance(HasRole):
    role = UserRole.RISK_COMPLIANCE


class IsAuditor(HasRole):
    role = UserRole.AUDITOR


class IsInvestorOrMember(HasRole):
    role = UserRole.INVESTOR_MEMBER


def HasAnyRole(roles):
    """
    Factory returning a DRF permission class that allows any user whose
    role is in `roles`.

    Usage:
        permission_classes = [HasAnyRole(["pool_manager", "finance_checker"])]
    """

    class _HasAnyRole(BasePermission):
        allowed_roles = list(roles)

        def has_permission(self, request, view):
            return bool(
                request.user
                and request.user.is_authenticated
                and request.user.role in self.allowed_roles
            )

    return _HasAnyRole


class IsSameTenant(BasePermission):
    """
    Object-level permission for tenant-scoped models: only allows access
    when the object's tenant matches the requesting user's tenant.

    Intended for future tenant-scoped business models (BE-007+). Combine
    with a role-based permission class, e.g.:
        permission_classes = [IsAuthenticated, IsPoolManager, IsSameTenant]
    """

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        return getattr(obj, "tenant_id", None) == request.user.tenant_id
