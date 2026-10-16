"""
Request tracing (BRD 14, observability). Every API request gets an id - the caller's `X-Request-ID` when it sends a
sensible one, otherwise a new one - returned in the response header and written, with the method, path, status, duration,
user and tenant, to the `apps.trace` log. A support case or an incident can then be followed across the logs by that id.
"""

import logging
import re
import time
import uuid

logger = logging.getLogger("apps.trace")
_SAFE_ID = re.compile(r"^[A-Za-z0-9._-]{8,64}$")


class RequestTraceMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        incoming = request.headers.get("X-Request-ID", "")
        request_id = incoming if _SAFE_ID.match(incoming) else uuid.uuid4().hex
        request.request_id = request_id
        started = time.perf_counter()
        response = self.get_response(request)
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        response["X-Request-ID"] = request_id
        if request.path.startswith("/api/"):
            user = getattr(request, "user", None)
            tenant = getattr(getattr(user, "tenant", None), "code", "") if getattr(user, "is_authenticated", False) else ""
            logger.info(
                "request_id=%s method=%s path=%s status=%s duration_ms=%s user=%s tenant=%s",
                request_id, request.method, request.path, response.status_code, elapsed_ms,
                getattr(user, "id", "") if getattr(user, "is_authenticated", False) else "-", tenant or "-",
            )
        return response
