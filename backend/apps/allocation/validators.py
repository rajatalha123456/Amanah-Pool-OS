from django.core.exceptions import ValidationError
from django.db.models import Q


def check_no_overlap(model_class, pool, effective_from, effective_to, exclude_id=None, extra_filter=None):
    """
    Enforces BR-002: effective-dated records (WeightageBand, PSR) for the
    same pool (and, when given, the same extra_filter - e.g. a
    WeightageBand's participant_class) must not have overlapping date
    ranges.

    Two ranges [a_from, a_to] and [b_from, b_to] (either `_to` may be
    null, meaning "open-ended") overlap when:
        a_from <= b_to (or b_to is null)
        AND
        b_from <= a_to (or a_to is null)

    Raises ValidationError if any existing record's range overlaps the
    given range.
    """

    queryset = model_class.objects.filter(pool=pool)

    if extra_filter:
        queryset = queryset.filter(**extra_filter)

    if exclude_id is not None:
        queryset = queryset.exclude(id=exclude_id)

    # (new_from <= existing_to OR existing_to is null)
    new_from_before_existing_end = Q(effective_to__isnull=True) | Q(effective_to__gte=effective_from)
    # (new_to >= existing_from OR new_to is null)
    new_to_after_existing_start = Q(effective_from__lte=effective_to) if effective_to is not None else Q()

    overlapping = queryset.filter(new_from_before_existing_end, new_to_after_existing_start)

    if overlapping.exists():
        conflict = overlapping.first()
        raise ValidationError(
            f"Effective date range overlaps with an existing {model_class.__name__} "
            f"(id={conflict.id}, {conflict.effective_from} to {conflict.effective_to or 'open-ended'}). "
            "Overlapping effective-dated records are not allowed (BR-002)."
        )
