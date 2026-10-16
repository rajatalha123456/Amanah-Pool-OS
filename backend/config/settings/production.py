"""
Production settings for the amanah_pool_os project.
All secrets and environment-specific values come from environment variables.
"""

from decouple import config, Csv

from .base import *  # noqa: F401,F403

DEBUG = False

# MFA is mandatory outside development unless explicitly switched off.
ALLOW_SIMULATED_INTEGRATIONS = config("ALLOW_SIMULATED_INTEGRATIONS", default=False, cast=bool)
MFA_ENFORCED = config("MFA_ENFORCED", default=True, cast=bool)

ALLOWED_HOSTS = config("ALLOWED_HOSTS", cast=Csv())

CORS_ALLOWED_ORIGINS = config("CORS_ALLOWED_ORIGINS", cast=Csv())

# Behind a reverse proxy that terminates HTTPS (deploy/Caddyfile), Django learns the original scheme from this header.
# Only safe when the proxy is the sole way in, which the docker-compose setup guarantees (the API port is not published).
if config("BEHIND_TLS_PROXY", default=False, cast=bool):
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = config("SECURE_SSL_REDIRECT", default=True, cast=bool)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
