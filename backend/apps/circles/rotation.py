import secrets

from django.db import transaction

from .models import CircleMember, CircleMemberStatus


def run_draw(pool):
    """
    Randomly assigns payout_position to every "active" CircleMember of
    `pool` whose payout_position is currently null.

    Uses the `secrets` module (not `random`) because `random` is a
    Mersenne Twister PRNG - its output is predictable from enough past
    samples, which would let someone with knowledge of prior draws (or
    the process's PRNG state) infer or influence future draw order.
    `secrets` draws from the OS's cryptographically secure random source,
    so the order can't be predicted or manipulated in advance.

    A hex seed (secrets.token_hex()) is generated per draw and returned
    alongside the assignments purely as an audit/transparency record -
    it is stored (via the caller, in the AuditLog and later copied onto
    each Payout) so the draw can be pointed to later as evidence a
    member's position was assigned by this specific randomized run, not
    chosen after the fact. The seed itself does not (and, because
    `secrets` is not seedable in the way `random.seed()` is, cannot)
    deterministically reproduce the shuffle - it is an audit token, not
    a replayable RNG seed.

    New positions are appended after whatever positions are already
    assigned (i.e. this can be called incrementally as new members join
    an existing circle without disturbing earlier members' positions).

    Returns: {"seed": str, "assignments": [{"member_id": str, "position": int}]}
    """

    seed = secrets.token_hex(16)

    with transaction.atomic():
        members = list(
            CircleMember.objects.select_for_update()
            .filter(pool=pool, status=CircleMemberStatus.ACTIVE, payout_position__isnull=True)
        )

        # secrets.SystemRandom().shuffle uses the same os.urandom-backed
        # source as the rest of the `secrets` module, unlike the default
        # `random.shuffle` (Mersenne Twister).
        secrets.SystemRandom().shuffle(members)

        starting_position = (
            CircleMember.objects.filter(pool=pool, payout_position__isnull=False).count()
        )

        assignments = []
        for offset, member in enumerate(members, start=1):
            position = starting_position + offset
            member.payout_position = position
            assignments.append({"member_id": str(member.id), "position": position})

        CircleMember.objects.bulk_update(members, ["payout_position", "updated_at"])

    return {"seed": seed, "assignments": assignments}
