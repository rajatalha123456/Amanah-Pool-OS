"""
Development settings for the amanah_pool_os project.
"""

from decimal import Decimal

from .base import *  # noqa: F401,F403

DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "testserver"]

CORS_ALLOW_ALL_ORIGINS = True

SIMPLE_JWT = {
    **SIMPLE_JWT,
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=24),
}

# Development placeholder for the payout liquidity gate (no live nostro balance
# feed exists). Production must configure the real balance explicitly.
PAYOUT_SETTLEMENT_ACCOUNT_BALANCE = PAYOUT_SETTLEMENT_ACCOUNT_BALANCE or Decimal("1000000000")
