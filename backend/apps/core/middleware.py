from django.http import JsonResponse

from .context import set_current_tenant

EXEMPT_PATHS = (
    "/api/v1/health/",
    "/admin/",
)


class TenantMiddleware:
    """
    Resolves the current tenant from the X-Tenant-Code request header and
    attaches it to the request (request.tenant) and to a contextvar so it
    is reachable from models/managers without passing the request around.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if self._is_exempt(request.path):
            request.tenant = None
            return self.get_response(request)

        from apps.tenants.models import Tenant

        tenant_code = request.headers.get("X-Tenant-Code")

        if not tenant_code:
            return JsonResponse(
                {"detail": "X-Tenant-Code header is required."}, status=403
            )

        try:
            tenant = Tenant.objects.get(
                code=tenant_code, is_active=True, is_suspended=False
            )
        except Tenant.DoesNotExist:
            return JsonResponse(
                {"detail": "Unknown or suspended tenant."}, status=403
            )

        request.tenant = tenant
        set_current_tenant(tenant)

        try:
            response = self.get_response(request)
        finally:
            set_current_tenant(None)

        return response

    @staticmethod
    def _is_exempt(path):
        return any(path.startswith(exempt) for exempt in EXEMPT_PATHS)
