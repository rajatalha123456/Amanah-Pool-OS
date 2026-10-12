"""
Verifiable payout-order draw (Qur'ah) for community circles.

Commit-reveal: `commit_draw` stores a secret server seed and publishes only its SHA-256
commitment; `execute_draw` takes a client seed (supplied by the organizer / members after the
commitment is public), derives the order, and reveals the server seed. The order is a pure function
of (server seed, client seed, participant list), so `verify_draw` lets anyone recompute it and check
that the seed matches the earlier commitment - the organizer cannot choose the outcome.
"""

import hashlib
import hmac
import secrets

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .models import CircleDraw, CircleMember, CircleMemberStatus, DrawStatus
from .rules import assert_rules_accepted


def commitment_of(server_seed, pool_code, sequence):
    return hashlib.sha256(f"{server_seed}:{pool_code}:{sequence}".encode()).hexdigest()


def derive_order(server_seed, client_seed, participants):
    """Deterministic Fisher-Yates shuffle keyed by HMAC-SHA256 (modulo bias is ~2^-250, negligible)."""
    order = list(participants)
    message_base = f"{client_seed}|{'|'.join(participants)}"
    for i in range(len(order) - 1, 0, -1):
        digest = hmac.new(server_seed.encode(), f"{message_base}|{i}".encode(), hashlib.sha256).digest()
        j = int.from_bytes(digest, "big") % (i + 1)
        order[i], order[j] = order[j], order[i]
    return order


def _undrawn(pool):
    return list(
        CircleMember.objects.select_for_update().filter(
            pool=pool, status=CircleMemberStatus.ACTIVE, payout_position__isnull=True
        )
    )


def commit_draw(pool, user=None):
    with transaction.atomic():
        if CircleDraw.objects.filter(pool=pool, status=DrawStatus.COMMITTED).exists():
            raise ValidationError("A draw is already committed for this circle; execute it first.")
        assert_rules_accepted(pool)
        members = _undrawn(pool)
        if not members:
            raise ValidationError("Every active member already has a payout position.")
        sequence = CircleDraw.objects.filter(pool=pool).count() + 1
        server_seed = secrets.token_hex(32)
        return CircleDraw.objects.create(
            tenant=pool.tenant, pool=pool, sequence=sequence, server_seed=server_seed,
            commitment=commitment_of(server_seed, pool.code, sequence),
            participants=sorted(m.member_reference for m in members), committed_by=user,
        )


def execute_draw(draw, client_seed, user=None):
    if draw.status != DrawStatus.COMMITTED:
        raise ValidationError("This draw has already been executed.")
    client_seed = (client_seed or "").strip()
    if len(client_seed) < 4:
        raise ValidationError({"client_seed": ["A client seed of at least 4 characters is required."]})
    pool = draw.pool
    with transaction.atomic():
        assert_rules_accepted(pool)
        members = {m.member_reference: m for m in _undrawn(pool)}
        if sorted(members) != draw.participants:
            raise ValidationError("Membership changed since the draw was committed; start a new draw.")
        order = derive_order(draw.server_seed, client_seed, draw.participants)
        start = CircleMember.objects.filter(pool=pool, payout_position__isnull=False).count()
        assignments = []
        for offset, reference in enumerate(order, start=1):
            members[reference].payout_position = start + offset
            assignments.append(
                {"member_reference": reference, "member_id": str(members[reference].id), "position": start + offset}
            )
        CircleMember.objects.bulk_update(list(members.values()), ["payout_position", "updated_at"])
        draw.client_seed = client_seed
        draw.assignments = assignments
        draw.status = DrawStatus.EXECUTED
        draw.executed_by = user
        draw.executed_at = timezone.now()
        draw.result_hash = hashlib.sha256(
            f"{draw.commitment}|{draw.server_seed}|{client_seed}|{order}".encode()
        ).hexdigest()
        draw.save()
    return draw


def verify_draw(draw):
    """Recomputes an executed draw from its revealed seeds."""
    if draw.status != DrawStatus.EXECUTED:
        return {"verified": False, "reason": "The draw has not been executed; the server seed is still hidden."}
    commitment_ok = draw.commitment == commitment_of(draw.server_seed, draw.pool.code, draw.sequence)
    order = derive_order(draw.server_seed, draw.client_seed, draw.participants)
    recorded = [a["member_reference"] for a in sorted(draw.assignments, key=lambda a: a["position"])]
    return {
        "verified": commitment_ok and order == recorded,
        "commitment_matches_seed": commitment_ok,
        "order_matches": order == recorded,
        "recomputed_order": order,
    }


def run_draw(pool, client_seed=None, user=None):
    """Single-step draw (commit + execute immediately). Prefer the two-step flow for real circles."""
    draw = execute_draw(commit_draw(pool, user), client_seed or secrets.token_hex(8), user)
    return {"seed": draw.server_seed, "assignments": draw.assignments, "draw_id": str(draw.id)}
