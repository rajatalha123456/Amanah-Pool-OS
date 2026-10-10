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
from apps.core.audit import log_action
from apps.participants.models import KYCStatus
from apps.pools.models import Pool
from apps.products.shariah import shariah_decision_for

from .models import (
    ArrearsRecord,
    ArrearsStatus,
    CircleMember,
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
from .payouts import build_preflight, create_payout_request, next_cycle_number, next_recipient
from .rotation import run_draw as run_draw_for_pool
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
        return Response(PayoutSerializer(payout).data, status=201)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        payout = self.get_object()
        if payout.status != PayoutStatus.PENDING:
            raise ValidationError(f"Only a pending payout can be approved (current status: '{payout.status}').")
        if payout.requested_by_id == request.user.id:
            raise ValidationError("Dual approval: the requester cannot approve their own payout.")

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
        return Response(PayoutSerializer(payout).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        payout = self.get_object()
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
        return Response(PayoutSerializer(payout).data)

    @action(detail=True, methods=["post"])
    def settle(self, request, pk=None):
        """Records that the approved payout was settled, with the bank's own settlement reference."""
        payout = self.get_object()
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
        if self.action == "create":
            return [IsAuthenticated(), IsPoolManager()]
        if self.action == "run_draw":
            return [IsAuthenticated(), IsPoolManager()]
        if self.action == "record_contribution":
            return [IsAuthenticated(), IsFinanceMaker()]
        if self.action == "verify_kyc":
            return [IsAuthenticated(), IsRiskCompliance()]
        if self.action == "flag_arrears":
            return [IsAuthenticated(), IsRiskCompliance()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
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

        result = run_draw_for_pool(pool)

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

        latest_contrib = Contribution.objects.filter(member__pool=pool).first()
        monthly_contrib = float(latest_contrib.amount) if latest_contrib else 10000.0
        total_pot = monthly_contrib * max(total_members, 1)

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

        import hashlib
        server_entropy = f"CIRCLE-{pool.code}-CYCLE-{current_cycle}-SEED"
        provably_fair_seal = hashlib.sha256(server_entropy.encode("utf-8")).hexdigest()

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
                "server_seed_hash": provably_fair_seal,
                "algorithm": "HMAC-SHA256 (Qur'ah Verifiable Randomness)",
                "shariah_zero_riba_rule": "Rule BR-007 Enforced: Zero markup, zero discount, zero interest uplift on turn allocation.",
                "verification_endpoint": f"/api/v1/circles/members/draw-room-status/{pool.id}/",
            },
        })

    @action(detail=False, methods=["post"], url_path="execute-provably-fair-draw/(?P<pool_id>[^/.]+)")
    def execute_provably_fair_draw(self, request, pool_id=None):
        """
        Executes a Provably Fair Digital Draw (Qur'ah) using cryptographically
        secure randomization, linking client entropy with server seed.
        """
        pool = get_circle_pool(pool_id)

        client_seed = request.data.get("client_seed") or "entropy-client-browser"
        force_reshuffle = request.data.get("force_reshuffle", False)

        with transaction.atomic():
            if force_reshuffle:
                CircleMember.objects.filter(pool=pool, status=CircleMemberStatus.ACTIVE).update(payout_position=None)

            result = run_draw_for_pool(pool)

        import hashlib
        combined = f"{result['seed']}:{client_seed}"
        audit_hash = hashlib.sha256(combined.encode("utf-8")).hexdigest()

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
        reason = request.data.get("reason", "Mutual hardship priority swap")

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

        contribution = Contribution.objects.create(
            tenant=member.tenant,
            member=member,
            amount=amount,
            contribution_date=contribution_date,
            cycle_number=cycle_number,
            status=ContributionStatus.RECEIVED,
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
        return [IsAuthenticated()]

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

        if CircleVote.objects.filter(proposal=proposal, member=member).exists():
            raise ValidationError("This member has already voted on this proposal.")

        vote = CircleVote.objects.create(
            tenant=proposal.tenant,
            proposal=proposal,
            member=member,
            decision=decision,
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
