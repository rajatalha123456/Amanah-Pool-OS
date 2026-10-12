"""KYC tiers: a product can require a higher tier of verification than the basic one."""

TIERS = ("basic", "standard", "enhanced")


def tier_rank(tier):
    return TIERS.index(tier) if tier in TIERS else 0


def assert_tier_sufficient(have, required, what="this product"):
    from rest_framework.exceptions import ValidationError

    if tier_rank(have) < tier_rank(required):
        raise ValidationError(f"{what} needs {required} KYC verification; this account is verified at {have} level.")
