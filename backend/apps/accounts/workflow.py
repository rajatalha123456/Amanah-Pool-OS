"""
Maker-checker separation helper.

Concept: for any workflow requiring independent maker/checker sign-off
(e.g. journal batch approval, allocation run approval — see BE-013),
the same user must never act as both maker and checker on the same
item. This module has no model/workflow of its own yet; it exists so
BE-013 has a single, already-reviewed place to import this rule from
rather than reimplementing it per approval type.
"""

from django.core.exceptions import ValidationError


def validate_maker_checker(maker_user, checker_user):
    """
    Raises ValidationError if the maker and checker are the same user.
    Call this wherever an approval step records both a maker and a
    checker (e.g. before persisting an approval/checker decision).
    """

    if maker_user.id == checker_user.id:
        raise ValidationError("Maker and checker cannot be the same user")
