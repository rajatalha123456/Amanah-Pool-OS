import hashlib
import uuid
from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.permissions import HasAnyRole, IsFinanceChecker, IsFinanceMaker, IsPoolManager, IsRiskCompliance
from apps.accounts.approval_matrix import assert_may_approve
from apps.core.audit import log_action
from apps.notifications import events
from apps.participants.models import KYCStatus
from apps.pools.models import Pool
from apps.products.shariah import shariah_decision_for

from .models import (
    ArrearsRecord,
    ArrearsStatus,
    CircleMember,
    CircleDraw,
    CircleMemberStatus,
    CircleProposal,
    CircleVote,
    Contribution,
    ContributionStatus,
    Payout,
    PayoutStatus,
    ProposalStatus,
    SettlementRailType,
    VoteDecision,
)
from .rules import current_rules
from .payouts import build_preflight, create_payout_request, next_cycle_number, next_recipient
from .rotation import execute_draw as _execute_draw
from .models import CircleDraw, DrawStatus


def _reveal_committed_draw(pool, client_seed, user):
    """Reveals the draw already committed for this circle with the members' seed (commit first, then reveal)."""
    draw = CircleDraw.objects.filter(pool=pool, status=DrawStatus.COMMITTED).order_by("sequence").first()
    if draw is None:
        raise ValidationError(
            "There is no committed draw. Commit (seal) the draw first, then reveal it with the members' seed."
        )
    executed = _execute_draw(draw, client_seed, user)
    return {"seed": executed.server_seed, "assignments": executed.assignments, "draw_id": str(executed.id)}
from .serializers import (
    ArrearsRecordSerializer,
    CircleMemberSerializer,
    CircleProposalSerializer,
    CircleVoteSerializer,
    ContributionSerializer,
    PayoutSerializer,
)


# Roles that may see payout pre-flight data (members never do).
PAYOUT_READ_ROLES = ["pool_manager", "finance_maker", "finance_checker", "risk_compliance", "auditor", "shariah_board"]
CIRCLE_READ_ROLES = PAYOUT_READ_ROLES + ["shariah_secretariat", "platform_super_admin"]


def get_circle_pool(pool_id):
    try:
        val = uuid.UUID(str(pool_id))
        return Pool.objects.get(pk=val)
    except (ValueError, AttributeError, Pool.DoesNotExist):
        try:
            return Pool.objects.get(code=pool_id)
        except Pool.DoesNotExist:
            raise ValidationError(f"Circle Pool '{pool_id}' not found.")


class ContributionViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """
    Read-only: Contributions are only ever created via
    CircleMemberViewSet.record_contribution(). retrieve() backs the
    member-facing contribution receipt page.
    """

    serializer_class = ContributionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Contribution.objects.all()
        member_id = self.request.query_params.get("member")
        pool_id = self.request.query_params.get("pool")
        if member_id:
            queryset = queryset.filter(member_id=member_id)
        if pool_id:
            queryset = queryset.filter(member__pool_id=pool_id)
        return queryset


class PayoutViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """
    Payout execution, lifecycle tracking, and Screen 09 Payout Release Ceremony.
    """

    serializer_class = PayoutSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Payout.objects.all().select_related("member", "pool", "disbursed_by", "secondary_approved_by")
        pool_id = self.request.query_params.get("pool")
        member_id = self.request.query_params.get("member")
        if pool_id:
            queryset = queryset.filter(pool_id=pool_id)
        if member_id:
            queryset = queryset.filter(member_id=member_id)
        return queryset

    def get_permissions(self):
        if self.action == "ceremony_readiness":
            return [IsAuthenticated(), HasAnyRole(PAYOUT_READ_ROLES)()]
        if self.action == "request_payout":
            return [IsAuthenticated(), HasAnyRole(["pool_manager", "finance_maker"])()]
        if self.action in ("approve", "reject"):
            return [IsAuthenticated(), IsFinanceChecker()]
        if self.action == "settle":
            return [IsAuthenticated(), HasAnyRole(["finance_maker", "finance_checker"])()]
        return [IsAuthenticated()]

    @action(detail=False, methods=["get"], url_path="ceremony-readiness/(?P<pool_id>[^/.]+)")
    def ceremony_readiness(self, request, pool_id=None):
        """Live pre-flight for the next payout of a circle: real data and real checks only."""
        pool = get_circle_pool(pool_id)
        rail = request.query_params.get("settlement_rail") or SettlementRailType.RAAST_RTGS

        cycle_number = next_cycle_number(pool)
        recipient = next_recipient(pool)

        active = CircleMember.objects.filter(pool=pool, status=CircleMemberStatus.ACTIVE)
        received = Contribution.objects.filter(
            member__pool=pool, cycle_number=cycle_number, status=ContributionStatus.RECEIVED
        )
        received_ids = set(received.values_list("member_id", flat=True))
        pending_members = [
            {"id": str(m.id), "name": m.member_name, "reference": m.member_reference}
            for m in active
            if m.id not in received_ids
        ]

        preflight = build_preflight(pool, recipient, cycle_number, rail) if recipient else None
        decision = shariah_decision_for(pool)
        open_payout = Payout.objects.filter(
            pool=pool, status__in=[PayoutStatus.PENDING, PayoutStatus.APPROVED]
        ).first()

        return Response(
            {
                "pool": {
                    "id": str(pool.id),
                    "name": pool.name,
                    "code": pool.code,
                    "status": pool.status,
                    "total_members": CircleMember.objects.filter(pool=pool).count(),
                },
                "cycle_number": cycle_number,
                "next_recipient": (
                    {
                        "member_id": str(recipient.id),
                        "member_name": recipient.member_name,
                        "member_reference": recipient.member_reference,
                        "payout_position": recipient.payout_position,
                        "kyc_status": recipient.kyc_status,
                        "iban": recipient.iban,
                        "bank_name": recipient.bank_name,
                    }
                    if recipient
                    else None
                ),
                "pot_summary": {
                    "total_collected_pot": float(sum((c.amount for c in received), Decimal("0.00"))),
                    "total_active_members": active.count(),
                    "received_count": len(received_ids & set(active.values_list("id", flat=True))),
                    "pending_count": len(pending_members),
                    "pending_members": pending_members,
                    "is_pot_fully_funded": not pending_members and active.exists(),
                },
                "checks": preflight["checks"] if preflight else [],
                "can_request": bool(preflight and preflight["ok"]),
                "shariah_decision": (
                    {"decision_code": decision.decision_code, "title": decision.title} if decision else None
                ),
                "open_payout": PayoutSerializer(open_payout).data if open_payout else None,
                "settlement_rails_options": [
                    {"key": key, "title": label} for key, label in SettlementRailType.choices
                ],
                "historical_payouts": PayoutSerializer(
                    Payout.objects.filter(pool=pool).order_by("-payout_date", "-created_at")[:5], many=True
                ).data,
            }
        )

    def _locked(self, payout):
        """Re-reads the payout under a row lock so two concurrent decisions cannot both pass the status check."""
        return Payout._base_manager.select_for_update(of=("self",)).select_related("pool", "member").get(pk=payout.pk)

    @action(detail=False, methods=["post"], url_path="request-payout/(?P<pool_id>[^/.]+)")
    def request_payout(self, request, pool_id=None):
        pool = get_circle_pool(pool_id)
        member = CircleMember.objects.filter(pk=request.data.get("member_id"), pool=pool).first()
        if member is None:
            raise ValidationError({"member_id": ["Recipient member not found in this pool."]})

        payout = create_payout_request(
            pool=pool,
            member=member,
            user=request.user,
            rail=request.data.get("settlement_rail") or SettlementRailType.RAAST_RTGS,
            payout_date=request.data.get("payout_date") or timezone.localdate(),
            cycle_number=request.data.get("cycle_number"),
        )
        log_action(
            tenant=pool.tenant,
            actor=request.user,
            action="payout_requested",
            model_name="Payout",
            object_id=str(payout.id),
            changes={
                "member": member.member_reference,
                "cycle_number": payout.cycle_number,
                "amount": str(payout.amount),
                "settlement_rail": payout.settlement_rail,
            },
            request=request,
        )
        events.payout_requested(payout, request.user)
        return Response(PayoutSerializer(payout).data, status=201)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def approve(self, request, pk=None):
        payout = self._locked(self.get_object())
        if payout.status != PayoutStatus.PENDING:
            raise ValidationError(f"Only a pending payout can be approved (current status: '{payout.status}').")
        if payout.requested_by_id == request.user.id:
            raise ValidationError("Dual approval: the requester cannot approve their own payout.")
        assert_may_approve(request.user, payout.tenant_id, "payout_approve", payout.amount)

        # Re-check the pre-conditions at approval time - things may have changed since the request.
        preflight = build_preflight(payout.pool, payout.member, payout.cycle_number, payout.settlement_rail)
        failed = [
            f"{c['label']}: {c['detail']}".rstrip(": ")
            for c in preflight["checks"]
            if not c["passed"] and c["key"] not in ("no_open_payout", "member_has_turn")
        ]
        if failed:
            raise ValidationError({"preflight": failed})
        if preflight["amount"] != payout.amount:
            raise ValidationError("The collected pot changed after the request; reject and re-request the payout.")

        decision = shariah_decision_for(payout.pool)
        payout.status = PayoutStatus.APPROVED
        payout.secondary_approved_by = request.user
        payout.secondary_approved_at = timezone.now()
        payout.shariah_compliance_status = "approved_decision"
        payout.shariah_certificate_number = decision.decision_code
        payout.save()
        log_action(
            tenant=payout.tenant,
            actor=request.user,
            action="payout_approved",
            model_name="Payout",
            object_id=str(payout.id),
            changes={"shariah_decision": decision.decision_code, "amount": str(payout.amount)},
            request=request,
        )
        events.payout_decided(payout, request.user, "approved")
        return Response(PayoutSerializer(payout).data)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def reject(self, request, pk=None):
        payout = self._locked(self.get_object())
        if payout.status not in (PayoutStatus.PENDING, PayoutStatus.APPROVED):
            raise ValidationError(f"Payout cannot be rejected in status '{payout.status}'.")
        reason = (request.data.get("reason") or "").strip()
        if not reason:
            raise ValidationError({"reason": ["A reason is required."]})
        payout.status = PayoutStatus.REJECTED
        payout.rejection_reason = reason
        payout.save()
        log_action(
            tenant=payout.tenant,
            actor=request.user,
            action="payout_rejected",
            model_name="Payout",
            object_id=str(payout.id),
            reason=reason,
            request=request,
        )
        events.payout_decided(payout, request.user, "rejected", reason)
        return Response(PayoutSerializer(payout).data)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def settle(self, request, pk=None):
        """Records that the approved payout was settled, with the bank's own settlement reference."""
        payout = self._locked(self.get_object())
        if payout.status != PayoutStatus.APPROVED:
            raise ValidationError(f"Only an approved payout can be settled (current status: '{payout.status}').")

        utr = (request.data.get("settlement_utr") or "").strip()
        if payout.settlement_rail == SettlementRailType.INTERNAL_BOOK:
            utr = utr or f"BOOK-{uuid.uuid4().hex[:10].upper()}"  # internal ledger reference
        elif not utr:
            raise ValidationError(
                {"settlement_utr": ["The bank's settlement reference (UTR/RRN) is required to confirm settlement."]}
            )

        with transaction.atomic():
            payout.status = PayoutStatus.DISBURSED
            payout.disbursed_by = request.user
            payout.settlement_utr = utr
            payout.biometric_auth_ref = (request.data.get("biometric_auth_ref") or "").strip() or None
            payout.ceremony_hash = hashlib.sha256(
                "|".join(
                    [
                        str(payout.id),
                        payout.pool.code,
                        payout.member.member_reference,
                        str(payout.amount),
                        str(payout.cycle_number),
                        payout.settlement_rail,
                        utr,
                        str(payout.requested_by_id),
                        str(payout.secondary_approved_by_id),
                        str(request.user.id),
                        payout.shariah_certificate_number or "",
                        str(payout.payout_date),
                    ]
                ).encode("utf-8")
            ).hexdigest()
            payout.save()

            payout.member.status = CircleMemberStatus.PAID_OUT
            payout.member.save(update_fields=["status", "updated_at"])

        log_action(
            tenant=payout.tenant,
            actor=request.user,
            action="payout_settled",
            model_name="Payout",
            object_id=str(payout.id),
            changes={"settlement_utr": utr, "ceremony_hash": payout.ceremony_hash},
            request=request,
        )
        events.payout_decided(payout, request.user, "settled")
        return Response(PayoutSerializer(payout).data)

    @action(detail=True, methods=["get"], url_path="receipt")
    def receipt(self, request, pk=None):
        payout = self.get_object()
        return Response(
            {
                "payout_id": str(payout.id),
                "circle_name": payout.pool.name,
                "circle_code": payout.pool.code,
                "recipient_name": payout.member.member_name,
                "recipient_reference": payout.member.member_reference,
                "cycle_number": payout.cycle_number,
                "amount": float(payout.amount),
                "payout_date": str(payout.payout_date),
                "status": payout.status,
                "settlement_rail": payout.settlement_rail,
                "settlement_utr": payout.settlement_utr,
                "recipient_iban": payout.recipient_iban,
                "recipient_bank": payout.recipient_bank,
                "requested_by": payout.requested_by.full_name if payout.requested_by else None,
                "secondary_approved_by": payout.secondary_approved_by.full_name if payout.secondary_approved_by else None,
                "secondary_approved_at": str(payout.secondary_approved_at) if payout.secondary_approved_at else None,
                "settled_by": payout.disbursed_by.full_name if payout.disbursed_by else None,
                "shariah_certificate_number": payout.shariah_certificate_number,
                "biometric_auth_ref": payout.biometric_auth_ref,
                "ceremony_hash": payout.ceremony_hash,
            }
        )


class CircleMemberViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = CircleMemberSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # See apps/products/views.py etc. for why this must be a method
        # rather than a class-level `queryset = Model.objects.all()`
        # attribute (TenantScopedManager + import-time evaluation bug).
        queryset = CircleMember.objects.all()
        pool_id = self.request.query_params.get("pool")
        if pool_id:
            queryset = queryset.filter(pool_id=pool_id)
        return queryset

    def get_permissions(self):
        if self.action in ("my_circles", "accept_rules", "my_proposals", "cast_vote"):
            return [IsAuthenticated(), HasAnyRole(["investor_member"])()]
        if self.action == "link_login":
            return [IsAuthenticated(), IsPoolManager()]
        if self.action == "create":
            return [IsAuthenticated(), IsPoolManager()]
        if self.action == "run_draw":
            return [IsAuthenticated(), IsPoolManager()]
        if self.action == "record_contribution":
            return [IsAuthenticated(), IsFinanceMaker()]
        if self.action == "verify_kyc":
            return [IsAuthenticated(), IsRiskCompliance()]
        if self.action == "verify_mandate":
            return [IsAuthenticated(), IsFinanceChecker()]
        if self.action == "flag_arrears":
            return [IsAuthenticated(), IsRiskCompliance()]
        if self.action in ("update", "partial_update", "swap_turns", "execute_provably_fair_draw"):
            return [IsAuthenticated(), IsPoolManager()]
        return [IsAuthenticated(), HasAnyRole(CIRCLE_READ_ROLES)()]

    @action(detail=False, methods=["get"], url_path="my-circles")
    def my_circles(self, request):
        """Self-service: the caller's own memberships, contributions, payouts and rules status - nothing of other members."""
        from .models import RulesAcceptance

        result = []
        members = CircleMember.objects.filter(user=request.user).select_related("pool")
        for member in members:
            rules = current_rules(member.pool)
            accepted = bool(rules and RulesAcceptance.objects.filter(member=member, rules=rules).exists())
            contributions = Contribution.objects.filter(member=member).order_by("cycle_number")
            payouts = Payout.objects.filter(member=member).order_by("cycle_number")
            result.append({
                "member_id": str(member.id), "member_reference": member.member_reference,
                "pool": str(member.pool_id), "pool_code": member.pool.code, "pool_name": member.pool.name,
                "status": member.status, "payout_position": member.payout_position,
                "rules": None if rules is None else {
                    "version": rules.version, "contribution_amount": str(rules.contribution_amount),
                    "cycle_days": rules.cycle_days, "schedule_note": rules.schedule_note,
                    "order_policy": rules.order_policy, "hardship_policy": rules.hardship_policy,
                    "content_hash": rules.content_hash, "accepted": accepted,
                },
                "contributions": [
                    {"cycle_number": c.cycle_number, "amount": str(c.amount), "date": str(c.contribution_date),
                     "status": c.status, "payment_reference": c.payment_reference} for c in contributions
                ],
                "ledger": self._pool_ledger(member.pool),
                "payouts": [
                    {"cycle_number": p.cycle_number, "amount": str(p.amount), "date": str(p.payout_date),
                     "status": p.status} for p in payouts
                ],
            })
        return Response(result)

    @staticmethod
    def _pool_ledger(pool):
        """The circle's transparent ledger (BRD 6.5): per cycle what was collected and who received the pot."""
        cycles = {}
        for c in Contribution.objects.filter(member__pool=pool, status=ContributionStatus.RECEIVED):
            row = cycles.setdefault(c.cycle_number, {"cycle_number": c.cycle_number, "received": 0, "collected": Decimal("0")})
            row["received"] += 1
            row["collected"] += c.amount
        payouts = {p.cycle_number: p for p in Payout.objects.filter(pool=pool).select_related("member")}
        for number, payout in payouts.items():
            cycles.setdefault(number, {"cycle_number": number, "received": 0, "collected": Decimal("0")})
        rows = []
        for number in sorted(cycles):
            row, payout = cycles[number], payouts.get(number)
            rows.append({
                "cycle_number": number, "contributions_received": row["received"], "collected": str(row["collected"]),
                "payout": None if payout is None else {
                    "recipient": payout.member.member_reference, "amount": str(payout.amount), "status": payout.status,
                    "date": str(payout.payout_date),
                },
            })
        return rows

    @action(detail=False, methods=["get"], url_path="my-proposals")
    def my_proposals(self, request):
        """Proposals of the circles the caller belongs to, with the caller's own vote. Tallies show once closed."""
        out = []
        for member in CircleMember.objects.filter(user=request.user).select_related("pool"):
            for proposal in CircleProposal.objects.filter(pool=member.pool).order_by("-created_at"):
                mine = CircleVote.objects.filter(proposal=proposal, member=member).first()
                closed = proposal.status != ProposalStatus.OPEN
                tally = None
                if closed:
                    votes = CircleVote.objects.filter(proposal=proposal)
                    tally = {d: votes.filter(decision=d).count() for d in VoteDecision.values}
                out.append({
                    "id": str(proposal.id), "pool_name": member.pool.name, "title": proposal.title,
                    "description": proposal.description, "status": proposal.status,
                    "voting_deadline": str(proposal.voting_deadline), "my_vote": mine.decision if mine else None,
                    "can_vote": (
                        not closed and mine is None and member.status == CircleMemberStatus.ACTIVE
                        and timezone.localdate() <= proposal.voting_deadline
                    ),
                    "tally": tally,
                })
        return Response(out)

    @action(detail=False, methods=["post"], url_path="cast-vote")
    def cast_vote(self, request):
        """A member votes with their own login: the vote is bound to the caller's membership, never to a chosen member."""
        from .voting import cast_vote

        proposal = CircleProposal.objects.filter(pk=request.data.get("proposal")).first()
        member = CircleMember.objects.filter(user=request.user, pool_id=proposal.pool_id).first() if proposal else None
        if proposal is None or member is None:
            raise ValidationError({"proposal": ["Unknown proposal."]})  # never reveal other circles
        vote = cast_vote(
            proposal=proposal, member=member, decision=str(request.data.get("decision") or ""), method="portal",
            evidence_reference="", recorder=request.user,
        )
        log_action(
            tenant=proposal.tenant, actor=request.user, action="vote_by_member", model_name="CircleVote",
            object_id=str(vote.id), changes={"proposal_id": str(proposal.id), "decision": vote.decision}, request=request,
        )
        return Response({"voted": True, "decision": vote.decision}, status=201)

    @action(detail=False, methods=["post"], url_path="accept-rules")
    def accept_rules(self, request):
        """A member accepts the current rules with their own login (e-signature / OTP reference required)."""
        from .rules import record_acceptance

        member = CircleMember.objects.filter(user=request.user, pool_id=request.data.get("pool")).first()
        if member is None:
            raise ValidationError({"pool": ["You are not a member of this circle."]})
        acceptance = record_acceptance(
            member=member, user=request.user, method=request.data.get("method", "e_sign"),
            evidence_reference=str(request.data.get("evidence_reference", "")),
        )
        log_action(
            tenant=member.tenant, actor=request.user, action="circle.rules_accepted_by_member", model_name="CircleMember",
            object_id=str(member.id), changes={"rules": str(acceptance.rules_id)}, request=request,
        )
        return Response({"accepted": True, "rules_version": acceptance.rules.version}, status=201)

    @action(detail=True, methods=["post"], url_path="link-login")
    def link_login(self, request, pk=None):
        """Pool manager links a member to an existing member-role user of the same tenant."""
        from apps.accounts.models import User

        member = self.get_object()
        email = str(request.data.get("email", "")).strip().lower()
        user = User.objects.filter(tenant=member.tenant, email__iexact=email, role="investor_member").first()
        if user is None:
            raise ValidationError({"email": ["No member-role user with this email exists in this tenant."]})
        if CircleMember.objects.filter(pool=member.pool, user=user).exclude(pk=member.pk).exists():
            raise ValidationError({"email": ["This login is already linked to another member of this circle."]})
        member.user = user
        member.save(update_fields=["user", "updated_at"])
        log_action(
            tenant=member.tenant, actor=request.user, action="circle.member_login_linked", model_name="CircleMember",
            object_id=str(member.id), changes={"user": str(user.id)}, request=request,
        )
        return Response({"linked": True})

    def perform_update(self, serializer):
        member = serializer.instance
        if member.status != CircleMemberStatus.ACTIVE:
            raise ValidationError("Only an active member's details can be changed.")
        if Payout.objects.filter(member=member, status__in=[PayoutStatus.PENDING, PayoutStatus.APPROVED]).exists():
            raise ValidationError("Bank details cannot change while a payout to this member is in progress.")
        before = {field: getattr(member, field) for field in serializer.validated_data}
        saved = serializer.save()
        log_action(
            tenant=saved.tenant, actor=self.request.user, action="update", model_name="CircleMember",
            object_id=str(saved.id),
            changes={field: {"before": str(before[field]), "after": str(getattr(saved, field))} for field in before},
            request=self.request,
        )

    def perform_create(self, serializer):
        from apps.investments.participation import assert_room_for_participant

        pool = serializer.validated_data["pool"]
        assert_room_for_participant(
            pool, CircleMember.objects.filter(pool=pool).exclude(status=CircleMemberStatus.WITHDRAWN).count(), "members"
        )
        instance = serializer.save(tenant=self.request.user.tenant)
        log_action(
            tenant=instance.tenant,
            actor=self.request.user,
            action="create",
            model_name="CircleMember",
            object_id=str(instance.id),
            changes={"member_reference": instance.member_reference, "member_name": instance.member_name},
            request=self.request,
        )

    @action(detail=False, methods=["post"], url_path="run-draw/(?P<pool_id>[^/.]+)")
    def run_draw(self, request, pool_id=None):
        try:
            pool = Pool.objects.get(pk=pool_id)
        except Pool.DoesNotExist:
            raise ValidationError("Pool not found.")

        # The seal must be published before the members' seed exists, so a one-step draw is not allowed: this endpoint
        # reveals the draw that was committed earlier (circles/draws/commit/).
        result = _reveal_committed_draw(pool, request.data.get("client_seed"), request.user)

        log_action(
            tenant=pool.tenant,
            actor=request.user,
            action="run_draw",
            model_name="Pool",
            object_id=str(pool.id),
            changes={"seed": result["seed"], "assignments": result["assignments"]},
            request=request,
        )
        return Response(result)

    @action(detail=False, methods=["get"], url_path="draw-room-status/(?P<pool_id>[^/.]+)")
    def draw_room_status(self, request, pool_id=None):
        """
        BRD Screen 08: Rotation / Draw Room Status.
        Provides next eligible recipient, cycle cadence, rotation ladder,
        and cryptographic provably fair verification details.
        """
        pool = get_circle_pool(pool_id)

        members = CircleMember.objects.filter(pool=pool).order_by("payout_position", "joined_date")
        total_members = members.count()

        paid_out_count = members.filter(status=CircleMemberStatus.PAID_OUT).count()
        current_cycle = paid_out_count + 1

        next_member = members.filter(
            status=CircleMemberStatus.ACTIVE, payout_position__isnull=False
        ).order_by("payout_position").first()

        rules = current_rules(pool)
        latest_contrib = Contribution.objects.filter(member__pool=pool).first()
        base = rules.contribution_amount if rules else (latest_contrib.amount if latest_contrib else None)
        monthly_contrib = float(base) if base is not None else None
        total_pot = monthly_contrib * max(total_members, 1) if monthly_contrib is not None else None

        ladder = []
        for m in members:
            pos = m.payout_position
            status_label = "UPCOMING"
            if m.status == CircleMemberStatus.PAID_OUT:
                status_label = "DISBURSED"
            elif next_member and m.id == next_member.id:
                status_label = "READY_FOR_DRAW_DISBURSEMENT"

            ladder.append({
                "member_id": str(m.id),
                "member_reference": m.member_reference,
                "member_name": m.member_name,
                "payout_position": pos,
                "status": m.status,
                "status_label": status_label,
                "pot_amount": total_pot,
                "joined_date": str(m.joined_date),
            })

        last_draw = CircleDraw.objects.filter(pool=pool).order_by("-sequence").first()

        return Response({
            "circle": {
                "id": str(pool.id),
                "name": pool.name,
                "code": pool.code,
                "status": pool.status,
                "total_members": total_members,
                "monthly_contribution": monthly_contrib,
                "total_pot_payout": total_pot,
            },
            "current_cycle": current_cycle,
            "next_recipient": {
                "member_id": str(next_member.id),
                "member_name": next_member.member_name,
                "member_reference": next_member.member_reference,
                "payout_position": next_member.payout_position,
                "pot_payout": total_pot,
            } if next_member else None,
            "has_undrawn_members": members.filter(payout_position__isnull=True).exists(),
            "rotation_ladder": ladder,
            "provably_fair": {
                "server_seed_hash": last_draw.commitment if last_draw else None,
                "draw_status": last_draw.status if last_draw else None,
                "draw_id": str(last_draw.id) if last_draw else None,
                "algorithm": "Commit-reveal: SHA-256 seed commitment + HMAC-SHA256 Fisher-Yates order",
                "shariah_zero_riba_rule": "Rule BR-007 Enforced: Zero markup, zero discount, zero interest uplift on turn allocation.",
                "verification_endpoint": f"/api/v1/circles/draws/{last_draw.id}/verify/" if last_draw else None,
            },
        })

    @action(detail=False, methods=["post"], url_path="execute-provably-fair-draw/(?P<pool_id>[^/.]+)")
    def execute_provably_fair_draw(self, request, pool_id=None):
        """
        Executes a Provably Fair Digital Draw (Qur'ah) using cryptographically
        secure randomization, linking client entropy with server seed.
        """
        pool = get_circle_pool(pool_id)

        client_seed = request.data.get("client_seed")
        force_reshuffle = request.data.get("force_reshuffle", False)

        with transaction.atomic():
            if force_reshuffle:
                raise ValidationError(
                    "Re-draws are not allowed (they would let the outcome be chosen). "
                    "Use a mutual-consent turn swap instead."
                )

            result = _reveal_committed_draw(pool, client_seed, request.user)

        audit_hash = CircleDraw.objects.get(pk=result["draw_id"]).result_hash

        log_action(
            tenant=pool.tenant,
            actor=request.user,
            action="provably_fair_draw",
            model_name="Pool",
            object_id=str(pool.id),
            changes={"draw_seed": result["seed"], "client_seed": client_seed, "audit_hash": audit_hash},
            request=request,
        )

        return Response({
            "status": "SUCCESS",
            "server_seed": result["seed"],
            "client_seed": client_seed,
            "provably_fair_hash": audit_hash,
            "assignments": result["assignments"],
            "message": "Provably Fair Digital Qur'ah executed successfully. Member positions cryptographically allocated.",
        })

    @action(detail=False, methods=["post"], url_path="swap-turns/(?P<pool_id>[^/.]+)")
    def swap_turns(self, request, pool_id=None):
        """
        Rule BR-007 Mutual Consent Emergency Turn Swap.
        Strictly zero financial markup or compensation permitted.
        """
        pool = get_circle_pool(pool_id)

        member_a_id = request.data.get("member_a_id")
        member_b_id = request.data.get("member_b_id")
        reason = str(request.data.get("reason") or "").strip()
        consent_reference = str(request.data.get("consent_reference") or "").strip()
        if not reason or not consent_reference:
            raise ValidationError(
                "A turn swap needs a reason and a reference to both members' recorded consent (BR-007 mutual consent)."
            )

        if not member_a_id or not member_b_id:
            raise ValidationError("Both member_a_id and member_b_id are required.")

        with transaction.atomic():
            m_a = CircleMember.objects.select_for_update().get(id=member_a_id, pool=pool)
            m_b = CircleMember.objects.select_for_update().get(id=member_b_id, pool=pool)

            if m_a.status == CircleMemberStatus.PAID_OUT or m_b.status == CircleMemberStatus.PAID_OUT:
                raise ValidationError("Cannot swap turns with a member who has already received their payout.")

            pos_a = m_a.payout_position
            pos_b = m_b.payout_position

            m_a.payout_position = None
            m_a.save(update_fields=["payout_position", "updated_at"])

            m_b.payout_position = pos_a
            m_b.save(update_fields=["payout_position", "updated_at"])

            m_a.payout_position = pos_b
            m_a.save(update_fields=["payout_position", "updated_at"])

        log_action(
            tenant=pool.tenant,
            actor=request.user,
            action="swap_turns",
            model_name="Pool",
            object_id=str(pool.id),
            changes={
                "member_a": m_a.member_reference,
                "member_b": m_b.member_reference,
                "new_pos_a": pos_b,
                "new_pos_b": pos_a,
                "reason": reason,
                "consent_reference": consent_reference,
            },
            request=request,
        )

        return Response({
            "status": "SUCCESS",
            "message": f"Turn swap completed between {m_a.member_name} (now Turn #{pos_b}) and {m_b.member_name} (now Turn #{pos_a}) under Rule BR-007 (Zero financial markup).",
            "member_a": {"id": str(m_a.id), "new_position": pos_b},
            "member_b": {"id": str(m_b.id), "new_position": pos_a},
        })

    @action(detail=True, methods=["post"], url_path="record-contribution")
    def record_contribution(self, request, pk=None):
        member = self.get_object()

        amount = request.data.get("amount")
        contribution_date = request.data.get("contribution_date")
        cycle_number = request.data.get("cycle_number")

        errors = {}
        if not amount:
            errors["amount"] = ["This field is required."]
        if not contribution_date:
            errors["contribution_date"] = ["This field is required."]
        if not cycle_number:
            errors["cycle_number"] = ["This field is required."]
        if errors:
            raise ValidationError(errors)

        from datetime import date as _date

        from apps.pools.lifecycle import assert_not_frozen
        from apps.pools.period_lock import assert_period_open

        from .rules import current_rules

        assert_not_frozen(member.pool, "contributions")
        try:
            amount = Decimal(str(amount))
            cycle_number = int(cycle_number)
            contribution_date = _date.fromisoformat(str(contribution_date))
        except (ArithmeticError, TypeError, ValueError):
            raise ValidationError("A valid amount, cycle number and date (YYYY-MM-DD) are required.")
        payment_reference = str(request.data.get("payment_reference") or "").strip()
        if not payment_reference:
            raise ValidationError({"payment_reference": ["The bank / Raast reference of the receipt is required."]})
        # A paid-out member keeps contributing until the circle ends; a withdrawn member does not.
        if member.status == CircleMemberStatus.WITHDRAWN:
            raise ValidationError("Contributions are recorded only for members still in the circle.")
        total_cycles = CircleMember.objects.filter(pool=member.pool).exclude(status=CircleMemberStatus.WITHDRAWN).count()
        if not 1 <= cycle_number <= max(total_cycles, 1):
            raise ValidationError({"cycle_number": [f"The circle runs cycles 1 to {total_cycles}."]})
        rules = current_rules(member.pool)
        if rules is not None and amount != rules.contribution_amount:
            raise ValidationError(
                {"amount": [f"The circle rules (v{rules.version}) set the contribution at {rules.contribution_amount}."]}
            )
        if amount <= 0:
            raise ValidationError({"amount": ["The amount must be positive."]})
        if Contribution.objects.filter(member=member, cycle_number=cycle_number).exists():
            raise ValidationError(f"{member.member_reference} already has a contribution for cycle {cycle_number}.")
        assert_period_open(member.pool, contribution_date, what="a contribution")

        contribution = Contribution.objects.create(
            tenant=member.tenant,
            member=member,
            amount=amount,
            contribution_date=contribution_date,
            cycle_number=cycle_number,
            status=ContributionStatus.RECEIVED,
            payment_reference=payment_reference,
            recorded_by=request.user,
        )

        log_action(
            tenant=member.tenant,
            actor=request.user,
            action="record_contribution",
            model_name="Contribution",
            object_id=str(contribution.id),
            changes={
                "member_id": str(member.id),
                "cycle_number": contribution.cycle_number,
                "amount": str(contribution.amount),
                "status": contribution.status,
            },
            request=request,
        )
        return Response(ContributionSerializer(contribution).data, status=201)

    @action(detail=True, methods=["post"], url_path="verify-kyc")
    def verify_kyc(self, request, pk=None):
        member = self.get_object()
        previous = member.kyc_status
        member.kyc_status = KYCStatus.VERIFIED
        member.save(update_fields=["kyc_status", "updated_at"])
        log_action(
            tenant=member.tenant,
            actor=request.user,
            action="verify_kyc",
            model_name="CircleMember",
            object_id=str(member.id),
            changes={"kyc_status": {"before": previous, "after": member.kyc_status}},
            request=request,
        )
        return Response(self.get_serializer(member).data)

    @action(detail=True, methods=["post"], url_path="verify-mandate")
    def verify_mandate(self, request, pk=None):
        """BRD 6.5: a finance checker confirms the member's payment mandate against the bank's confirmation."""
        member = self.get_object()
        if not member.mandate_reference:
            raise ValidationError({"mandate_reference": ["Record the mandate reference on the member first."]})
        if member.mandate_verified_at is not None:
            raise ValidationError("This mandate is already verified.")
        member.mandate_verified_by = request.user
        member.mandate_verified_at = timezone.now()
        member.save(update_fields=["mandate_verified_by", "mandate_verified_at", "updated_at"])
        log_action(
            tenant=member.tenant, actor=request.user, action="verify_mandate", model_name="CircleMember",
            object_id=str(member.id), changes={"mandate_reference": member.mandate_reference}, request=request,
        )
        return Response(self.get_serializer(member).data)

    @action(detail=True, methods=["post"], url_path="flag-arrears")
    def flag_arrears(self, request, pk=None):
        member = self.get_object()

        cycle_number = request.data.get("cycle_number")
        expected_amount = request.data.get("expected_amount")

        errors = {}
        if not cycle_number:
            errors["cycle_number"] = ["This field is required."]
        if not expected_amount:
            errors["expected_amount"] = ["This field is required."]
        if errors:
            raise ValidationError(errors)

        if ArrearsRecord.objects.filter(member=member, cycle_number=cycle_number).exists():
            raise ValidationError(f"Arrears for cycle {cycle_number} are already recorded for this member.")
        if Contribution.objects.filter(member=member, cycle_number=cycle_number, status=ContributionStatus.RECEIVED).exists():
            raise ValidationError("This member has already paid that cycle.")

        arrears = ArrearsRecord.objects.create(
            tenant=member.tenant,
            member=member,
            cycle_number=cycle_number,
            expected_amount=expected_amount,
            status=ArrearsStatus.OVERDUE,
        )

        log_action(
            tenant=member.tenant,
            actor=request.user,
            action="flag_arrears",
            model_name="ArrearsRecord",
            object_id=str(arrears.id),
            changes={
                "member_id": str(member.id),
                "cycle_number": arrears.cycle_number,
                "expected_amount": str(arrears.expected_amount),
                "status": arrears.status,
            },
            request=request,
        )
        events.arrears_flagged(arrears, request.user)
        return Response(ArrearsRecordSerializer(arrears).data, status=201)


class CircleProposalViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = CircleProposalSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = CircleProposal.objects.all()
        pool_id = self.request.query_params.get("pool")
        if pool_id:
            queryset = queryset.filter(pool_id=pool_id)
        return queryset

    def get_permissions(self):
        if self.action == "create":
            return [IsAuthenticated(), IsPoolManager()]
        if self.action == "close":
            return [IsAuthenticated(), IsPoolManager()]
        if self.action == "vote":
            # Members have no logins of their own yet: the organizer or compliance records a member's vote
            # together with the evidence of how it was cast.
            return [IsAuthenticated(), HasAnyRole(["pool_manager", "risk_compliance"])()]
        return [IsAuthenticated(), HasAnyRole(CIRCLE_READ_ROLES)()]

    def perform_create(self, serializer):
        instance = serializer.save(tenant=self.request.user.tenant, created_by=self.request.user)
        log_action(
            tenant=instance.tenant,
            actor=self.request.user,
            action="create",
            model_name="CircleProposal",
            object_id=str(instance.id),
            changes={"title": instance.title, "proposal_type": instance.proposal_type},
            request=self.request,
        )

    @action(detail=True, methods=["post"], url_path="vote")
    def vote(self, request, pk=None):
        proposal = self.get_object()

        if proposal.status != ProposalStatus.OPEN:
            raise ValidationError("This proposal is not open for voting.")

        member_id = request.data.get("member_id")
        decision = request.data.get("decision")

        errors = {}
        if not member_id:
            errors["member_id"] = ["This field is required."]
        if not decision:
            errors["decision"] = ["This field is required."]
        elif decision not in VoteDecision.values:
            errors["decision"] = [f"Must be one of {VoteDecision.values}."]
        if errors:
            raise ValidationError(errors)

        try:
            member = CircleMember.objects.get(pk=member_id, pool=proposal.pool)
        except CircleMember.DoesNotExist:
            raise ValidationError("Member not found on this proposal's pool.")
        method = str(request.data.get("method") or "in_person")
        if method == "portal":
            raise ValidationError({"method": ["Staff record in_person, otp or e_sign votes; members vote in the portal."]})
        from .voting import cast_vote

        vote = cast_vote(
            proposal=proposal, member=member, decision=decision, method=method,
            evidence_reference=str(request.data.get("evidence_reference") or ""), recorder=request.user,
        )

        log_action(
            tenant=proposal.tenant,
            actor=request.user,
            action="vote",
            model_name="CircleVote",
            object_id=str(vote.id),
            changes={"proposal_id": str(proposal.id), "member_id": str(member.id), "decision": vote.decision},
            request=request,
        )
        return Response(CircleVoteSerializer(vote).data, status=201)

    @action(detail=True, methods=["post"], url_path="close")
    def close(self, request, pk=None):
        proposal = self.get_object()

        if proposal.status != ProposalStatus.OPEN:
            raise ValidationError("This proposal is already closed.")

        votes = proposal.votes.all()
        approve_count = votes.filter(decision=VoteDecision.APPROVE).count()
        reject_count = votes.filter(decision=VoteDecision.REJECT).count()
        abstain_count = votes.filter(decision=VoteDecision.ABSTAIN).count()
        active_members = CircleMember.objects.filter(pool=proposal.pool, status=CircleMemberStatus.ACTIVE).count()
        cast = approve_count + reject_count + abstain_count

        if timezone.localdate() <= proposal.voting_deadline and cast < active_members:
            raise ValidationError(
                f"Voting is open until {proposal.voting_deadline} and {active_members - cast} member(s) have not voted yet."
            )
        quorum_met = active_members > 0 and cast * 2 > active_members
        if not quorum_met:
            proposal.status = ProposalStatus.CLOSED  # no decision: fewer than half of the members took part
        else:
            proposal.status = ProposalStatus.APPROVED if approve_count > reject_count else ProposalStatus.REJECTED
        proposal.closed_at = timezone.now()
        proposal.save(update_fields=["status", "closed_at", "updated_at"])

        log_action(
            tenant=proposal.tenant,
            actor=request.user,
            action="close",
            model_name="CircleProposal",
            object_id=str(proposal.id),
            changes={
                "status": proposal.status,
                "approve_count": approve_count,
                "reject_count": reject_count,
                "abstain_count": abstain_count,
                "active_members": active_members,
                "quorum_met": quorum_met,
            },
            request=request,
        )
        return Response(
            {
                **CircleProposalSerializer(proposal).data,
                "vote_counts": {
                    "approve": approve_count,
                    "reject": reject_count,
                    "abstain": abstain_count,
                },
            }
        )


class ArrearsRecordViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """
    Read-only aside from grant_hardship: ArrearsRecords are created only
    via CircleMemberViewSet.flag_arrears().
    """

    serializer_class = ArrearsRecordSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = ArrearsRecord.objects.all()
        pool_id = self.request.query_params.get("pool")
        member_id = self.request.query_params.get("member")
        if pool_id:
            queryset = queryset.filter(member__pool_id=pool_id)
        if member_id:
            queryset = queryset.filter(member_id=member_id)
        return queryset

    def get_permissions(self):
        if self.action == "grant_hardship":
            return [IsAuthenticated(), HasAnyRole(["shariah_secretariat", "shariah_board"])()]
        return [IsAuthenticated()]

    @action(detail=True, methods=["post"], url_path="grant-hardship")
    def grant_hardship(self, request, pk=None):
        arrears = self.get_object()

        hardship_reason = request.data.get("hardship_reason")
        if not hardship_reason:
            raise ValidationError({"hardship_reason": ["This field is required."]})

        arrears.status = ArrearsStatus.HARDSHIP_GRANTED
        arrears.hardship_reason = hardship_reason
        arrears.reviewed_by = request.user
        arrears.reviewed_at = timezone.now()
        arrears.save(update_fields=["status", "hardship_reason", "reviewed_by", "reviewed_at", "updated_at"])

        log_action(
            tenant=arrears.tenant,
            actor=request.user,
            action="grant_hardship",
            model_name="ArrearsRecord",
            object_id=str(arrears.id),
            changes={"status": arrears.status, "hardship_reason": arrears.hardship_reason},
            request=request,
        )
        return Response(ArrearsRecordSerializer(arrears).data)
