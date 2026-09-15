import logging

from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.http import Http404
from rest_framework import exceptions as drf_exceptions
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger("apps")

DEFAULT_ERROR_CODE = "error"

# Map DRF/Django exception classes to a stable machine-readable error code.
EXCEPTION_CODES = {
    drf_exceptions.ValidationError: "validation_error",
    drf_exceptions.AuthenticationFailed: "authentication_failed",
    drf_exceptions.NotAuthenticated: "not_authenticated",
    drf_exceptions.PermissionDenied: "permission_denied",
    DjangoPermissionDenied: "permission_denied",
    drf_exceptions.NotFound: "not_found",
    Http404: "not_found",
    drf_exceptions.MethodNotAllowed: "method_not_allowed",
    drf_exceptions.NotAcceptable: "not_acceptable",
    drf_exceptions.Throttled: "throttled",
    drf_exceptions.ParseError: "parse_error",
    drf_exceptions.UnsupportedMediaType: "unsupported_media_type",
}


def _error_code_for(exc):
    for exc_class, code in EXCEPTION_CODES.items():
        if isinstance(exc, exc_class):
            return code
    return DEFAULT_ERROR_CODE


def _extract_message_and_details(exc_detail):
    """
    DRF's exception.detail can be a plain string, a list, or a nested
    dict (field -> list of errors). Reduce it to a single top-level
    message plus a details payload that preserves the original shape
    for field-level consumers.
    """

    if isinstance(exc_detail, (list, dict)):
        details = exc_detail
        message = "Validation failed." if isinstance(exc_detail, dict) else str(exc_detail[0])
    else:
        details = None
        message = str(exc_detail)

    return message, details


def custom_exception_handler(exc, context):
    response = drf_exception_handler(exc, context)

    if response is None:
        # Unhandled exception (bug, DB error, etc.) - log with traceback and
        # return a generic 500 in our standard shape instead of leaking a
        # Django debug page or an unformatted DRF response.
        logger.exception("Unhandled exception in %s", context.get("view"))
        return Response(
            {
                "error": {
                    "code": "internal_server_error",
                    "message": "An unexpected error occurred.",
                    "details": None,
                }
            },
            status=500,
        )

    message, details = _extract_message_and_details(exc.detail)

    response.data = {
        "error": {
            "code": _error_code_for(exc),
            "message": message,
            "details": details,
        }
    }

    return response
