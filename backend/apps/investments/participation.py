"""Participation terms of a product (BRD section 5): minimum, cap, tenure, KYC tier and the number of participants."""

from datetime import timedelta
from decimal import Decimal

from django.db.models import Sum
from rest_framework.exceptions import ValidationError

from apps.participants.kyc_tiers import assert_tier_sufficient


def assert_subscription_terms(account, amount):
    product = account.pool.product
    if product.minimum_subscription is not None and amount < product.minimum_subscription:
        raise ValidationError({"amount": [f"The minimum subscription for this product is PKR {product.minimum_subscription}."]})
    if product.subscription_cap is not None:
        from .models import Subscription

        so_far = Subscription._base_manager.filter(capital_account=account).aggregate(t=Sum("amount"))["t"] or Decimal("0")
        if so_far + amount > product.subscription_cap:
            raise ValidationError(
                {"amount": [f"This would take the account to PKR {so_far + amount}; the cap per account is PKR {product.subscription_cap}."]}
            )
    profile = getattr(account, "investor_profile", None)
    assert_tier_sufficient(getattr(profile, "kyc_tier", "basic"), product.required_kyc_tier, "This product")


def assert_redemption_terms(account, dealing_date):
    product = account.pool.product
    if product.minimum_tenure_days:
        from .models import Subscription

        first = Subscription._base_manager.filter(capital_account=account).order_by("transaction_date").first()
        if first is not None:
            earliest = first.transaction_date + timedelta(days=product.minimum_tenure_days)
            if dealing_date < earliest:
                raise ValidationError(
                    {"transaction_date": [f"This product has a minimum holding of {product.minimum_tenure_days} days: the earliest dealing date is {earliest}."]}
                )
    from apps.pools.calendars import assert_working_day

    assert_working_day(account.pool, dealing_date, what="A redemption dealing date")


def assert_room_for_participant(pool, current_count, what="participants"):
    limit = pool.product.max_participants
    if limit is not None and current_count >= limit:
        raise ValidationError(f"This product allows at most {limit} {what} per pool; the pool is full.")
