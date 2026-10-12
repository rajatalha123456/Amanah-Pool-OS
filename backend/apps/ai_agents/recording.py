"""Uniform recording of AI outputs (BR-009). Recording never blocks the feature itself."""

import hashlib
import json
import logging
import time
from decimal import Decimal, InvalidOperation

from django.db.models import Avg, Count, Q
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .models import AIModelRegistry, AIRecommendation, Disposition

logger = logging.getLogger("apps")
PROMPT_STORE_LIMIT = 4000
OUTPUT_STORE_LIMIT = 200_000


class Timer:
    def __init__(self):
        self.start = time.monotonic()

    @property
    def ms(self):
        return int((time.monotonic() - self.start) * 1000)


def _confidence(value):
    try:
        number = Decimal(str(value))
    except (InvalidOperation, TypeError):
        return None
    return number if 0 <= number <= 1 else None


def record_ai_output(
    *, user, feature, model_name, prompt, output, sources=None, confidence=None, reason="",
    requires_review=True, is_fallback=False, latency_ms=0, subject_type="", subject_id="",
):
    """Returns the AIRecommendation id (str) or None if recording failed."""
    try:
        text = prompt if isinstance(prompt, str) else json.dumps(prompt, sort_keys=True, default=str)
        stored = json.loads(json.dumps(output, default=str))
        if len(json.dumps(stored)) > OUTPUT_STORE_LIMIT:
            stored = {"truncated": True, "keys": list(stored)[:50] if isinstance(stored, dict) else []}
        registry = AIModelRegistry.objects.filter(model_name=model_name).first()
        recommendation = AIRecommendation.objects.create(
            tenant=user.tenant, feature=feature, model_name=model_name,
            model_version=registry.version if registry else "", requested_by=user, subject_type=subject_type,
            subject_id=str(subject_id or ""), prompt_hash=hashlib.sha256(text.encode()).hexdigest(),
            prompt_text=text[:PROMPT_STORE_LIMIT], output=stored, sources=list(sources or []),
            confidence=_confidence(confidence), reason=reason, requires_human_review=requires_review,
            is_fallback=is_fallback, latency_ms=latency_ms,
        )
        return str(recommendation.id)
    except Exception:  # noqa: BLE001 - recording must never break the AI feature
        logger.exception("Failed to record AI output for %s", feature)
        return None


def dispose(recommendation, user, disposition, note):
    if disposition not in (Disposition.ACCEPTED, Disposition.REJECTED, Disposition.OVERRIDDEN):
        raise ValidationError({"disposition": ["Must be accepted, rejected or overridden."]})
    if recommendation.disposition != Disposition.PENDING:
        raise ValidationError("A human disposition has already been recorded for this recommendation.")
    if disposition != Disposition.ACCEPTED and not note.strip():
        raise ValidationError({"note": ["A reason is required when rejecting or overriding an AI recommendation."]})
    recommendation.disposition = disposition
    recommendation.disposed_by = user
    recommendation.disposed_at = timezone.now()
    recommendation.disposition_note = note
    recommendation.save(update_fields=["disposition", "disposed_by", "disposed_at", "disposition_note", "updated_at"])
    return recommendation


def metrics():
    """Per-model governance metrics over all recorded outputs of the caller's tenant."""
    rows = (
        AIRecommendation.objects.values("model_name")
        .annotate(
            total=Count("id"),
            pending=Count("id", filter=Q(disposition=Disposition.PENDING)),
            accepted=Count("id", filter=Q(disposition=Disposition.ACCEPTED)),
            rejected=Count("id", filter=Q(disposition=Disposition.REJECTED)),
            overridden=Count("id", filter=Q(disposition=Disposition.OVERRIDDEN)),
            fallback=Count("id", filter=Q(is_fallback=True)),
            low_confidence=Count("id", filter=Q(confidence__lt=Decimal("0.8"))),
            avg_confidence=Avg("confidence"),
            avg_latency_ms=Avg("latency_ms"),
        )
        .order_by("model_name")
    )
    result = []
    for row in rows:
        decided = row["accepted"] + row["rejected"] + row["overridden"]
        row["avg_confidence"] = round(float(row["avg_confidence"]), 3) if row["avg_confidence"] is not None else None
        row["avg_latency_ms"] = int(row["avg_latency_ms"] or 0)
        row["decided"] = decided
        row["acceptance_rate"] = round(row["accepted"] / decided, 3) if decided else None
        row["override_rate"] = round((row["rejected"] + row["overridden"]) / decided, 3) if decided else None
        row["fallback_rate"] = round(row["fallback"] / row["total"], 3) if row["total"] else None
        result.append(row)
    return result
