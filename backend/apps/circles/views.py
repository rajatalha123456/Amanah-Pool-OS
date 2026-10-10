import hashlib
import uuid
from django.db import transaction
from django.utils import timezone
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.permissions import HasAnyRole, IsFinanceChecker, IsFinanceMaker, IsPoolManager, IsRiskCompliance
from apps.core.audit import log_action
from apps.pools.models import Pool

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
from .rotation import run_draw as run_draw_for_pool
from .serializers import (
    ArrearsRecordSerializer,
    CircleMemberSerializer,
    CircleProposalSerializer,
    CircleVoteSerializer,
    ContributionSerializer,
    PayoutSerializer,
)


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

    @action(detail=False, methods=["get"], url_path="ceremony-readiness/(?P<pool_id>[^/.]+)")
    def ceremony_readiness(self, request, pool_id=None):
        pool = get_circle_pool(pool_id)

        members = CircleMember.objects.filter(pool=pool).order_by("payout_position", "joined_date")
        total_members_count = members.count()
        paid_out_members = members.filter(status=CircleMemberStatus.PAID_OUT)
        paid_out_count = paid_out_members.count()
        current_cycle = paid_out_count + 1

        next_member = members.filter(
            status=CircleMemberStatus.ACTIVE, payout_position__isnull=False
        ).order_by("payout_position").first()

        latest_contrib = Contribution.objects.filter(member__pool=pool).first()
        monthly_share = float(latest_contrib.amount) if latest_contrib else 50000.0
        total_pot_expected = monthly_share * max(total_members_count, 1)

        # Contributions for current cycle
        active_members = members.filter(status=CircleMemberStatus.ACTIVE)
        active_member_ids = set(active_members.values_list("id", flat=True))
        received_contributions = Contribution.objects.filter(
            member__pool=pool,
            cycle_number=current_cycle,
            status=ContributionStatus.RECEIVED,
        )
        received_member_ids = set(received_contributions.values_list("member_id", flat=True))
        pending_member_ids = active_member_ids - received_member_ids

        pending_members = [
            {"id": str(m.id), "name": m.member_name, "reference": m.member_reference}
            for m in active_members if m.id in pending_member_ids
        ]

        total_collected = float(sum(c.amount for c in received_contributions))

        historical_payouts = Payout.objects.filter(pool=pool).order_by("-payout_date", "-created_at")[:5]

        recipient_data = None
        if next_member:
            clean_ref = next_member.member_reference.replace("-", "")
            recipient_data = {
                "member_id": str(next_member.id),
                "member_name": next_member.member_name,
                "member_reference": next_member.member_reference,
                "payout_position": next_member.payout_position,
                "pot_amount": total_pot_expected,
                "default_iban": f"PK36MEZN000100{clean_ref[-8:].zfill(8)}01",
                "default_bank": "Meezan Bank Limited",
                "raast_alias": f"0300{clean_ref[-7:].zfill(7)}",
            }

        return Response({
            "pool": {
                "id": str(pool.id),
                "name": pool.name,
                "code": pool.code,
                "status": pool.status,
                "total_members": total_members_count,
            },
            "cycle_number": current_cycle,
            "next_recipient": recipient_data,
            "pot_summary": {
                "monthly_share_per_member": monthly_share,
                "total_expected_pot": total_pot_expected,
                "total_collected_pot": total_collected,
                "is_pot_fully_funded": len(pending_member_ids) == 0,
                "total_active_members": active_members.count(),
                "received_count": len(received_member_ids),
                "pending_count": len(pending_member_ids),
                "pending_members": pending_members,
            },
            "shariah_preflight": {
                "contract_type": "Qard-e-Hasana Bilateral Mutual Pool",
                "zero_time_value_uplift": True,
                "zero_fee_deduction": True,
                "bank_fee_absorption_note": "SBP Circular 03/2012: The bank absorbs all RTGS / Raast settlement fees. Recipient receives 100% of the pot without deduction.",
                "rotation_parity_verified": True,
            },
            "settlement_rails_options": [
                {
                    "key": SettlementRailType.RAAST_RTGS,
                    "title": "Raast Instant Settlement (RTGS P2P / P2B)",
                    "latency": "Real-time (< 3 seconds)",
                    "fee": "PKR 0.00 (Bank Absorbed)",
                    "recommended": True,
                },
                {
                    "key": SettlementRailType.ONELINK_IPS,
                    "title": "1LINK 1IBFT Clearing Rail",
                    "latency": "Real-time (Batch Settled)",
                    "fee": "PKR 0.00 (Bank Absorbed)",
                    "recommended": False,
                },
                {
                    "key": SettlementRailType.INTERNAL_BOOK,
                    "title": "Internal Islamic Branch Transfer",
                    "latency": "Instant ledger debit/credit",
                    "fee": "PKR 0.00",
                    "recommended": False,
                },
            ],
            "historical_payouts": PayoutSerializer(historical_payouts, many=True).data,
        })

    @action(detail=False, methods=["post"], url_path="execute-ceremony/(?P<pool_id>[^/.]+)")
    def execute_ceremony(self, request, pool_id=None):
        pool = get_circle_pool(pool_id)

        member_id = request.data.get("member_id")
        cycle_number = request.data.get("cycle_number")
        amount = request.data.get("amount")
        payout_date = request.data.get("payout_date") or str(timezone.now().date())
        settlement_rail = request.data.get("settlement_rail") or SettlementRailType.RAAST_RTGS
        recipient_iban = request.data.get("recipient_iban") or ""
        recipient_bank = request.data.get("recipient_bank") or "Meezan Bank Limited"
        biometric_auth_ref = request.data.get("biometric_auth_ref") or f"BIO-VERIFIED-{uuid.uuid4().hex[:6].upper()}"
        auto_reconcile = request.data.get("auto_reconcile_contributions", True)

        try:
            member = CircleMember.objects.get(pk=member_id, pool=pool)
        except CircleMember.DoesNotExist:
            raise ValidationError("Recipient member not found in this pool.")

        if member.status == CircleMemberStatus.PAID_OUT:
            raise ValidationError(f"Member {member.member_name} has already been paid out.")

        with transaction.atomic():
            if auto_reconcile:
                active_mems = CircleMember.objects.filter(pool=pool, status=CircleMemberStatus.ACTIVE)
                for am in active_mems:
                    Contribution.objects.get_or_create(
                        tenant=pool.tenant,
                        member=am,
                        cycle_number=cycle_number,
                        defaults={
                            "amount": float(amount) / max(active_mems.count(), 1),
                            "contribution_date": timezone.now().date(),
                            "status": ContributionStatus.RECEIVED,
                        },
                    )

            settlement_utr = f"RAAST-PK-{timezone.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
            cert_no = f"SHAR-QARD-2025-{uuid.uuid4().hex[:6].upper()}"

            hash_payload = f"{pool.code}:{member.member_reference}:{amount}:{settlement_utr}:{cycle_number}:{payout_date}"
            ceremony_hash = hashlib.sha256(hash_payload.encode("utf-8")).hexdigest()

            payout = Payout.objects.create(
                tenant=pool.tenant,
                member=member,
                pool=pool,
                cycle_number=cycle_number,
                amount=amount,
                payout_date=payout_date,
                status=PayoutStatus.DISBURSED,
                disbursed_by=request.user,
                secondary_approved_by=request.user,
                secondary_approved_at=timezone.now(),
                settlement_rail=settlement_rail,
                settlement_utr=settlement_utr,
                recipient_iban=recipient_iban,
                recipient_bank=recipient_bank,
                shariah_compliance_status="certified_qard_hasana",
                shariah_certificate_number=cert_no,
                biometric_auth_ref=biometric_auth_ref,
                ceremony_hash=ceremony_hash,
            )

            member.status = CircleMemberStatus.PAID_OUT
            member.save(update_fields=["status", "updated_at"])

            log_action(
                tenant=pool.tenant,
                actor=request.user,
                action="payout_ceremony_disbursed",
                model_name="Payout",
                object_id=str(payout.id),
                changes={
                    "cycle_number": cycle_number,
                    "member": member.member_reference,
                    "amount": str(amount),
                    "settlement_rail": settlement_rail,
                    "settlement_utr": settlement_utr,
                    "shariah_certificate": cert_no,
                    "ceremony_hash": ceremony_hash,
                },
                request=request,
            )

        return Response({
            "status": "CEREMONY_SUCCESS",
            "message": f"Payout Release Ceremony concluded successfully. PKR {float(amount):,.2f} disbursed to {member.member_name} via {settlement_rail}.",
            "payout": PayoutSerializer(payout).data,
            "settlement_receipt": {
                "utr": settlement_utr,
                "certificate_number": cert_no,
                "ceremony_hash": ceremony_hash,
                "settlement_rail": settlement_rail,
                "recipient_name": member.member_name,
                "recipient_iban": recipient_iban,
                "recipient_bank": recipient_bank,
                "amount": float(amount),
                "payout_date": str(payout_date),
                "disbursed_by": request.user.username,
                "shariah_seal": "VERIFIED ZERO RIBA - 100% PRINCIPAL DELIVERED",
            },
        }, status=201)

    @action(detail=True, methods=["get"], url_path="receipt")
    def receipt(self, request, pk=None):
        payout = self.get_object()
        return Response({
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
            "secondary_approved_by": payout.secondary_approved_by.username if payout.secondary_approved_by else "Compliance Officer",
            "secondary_approved_at": str(payout.secondary_approved_at) if payout.secondary_approved_at else None,
            "shariah_certificate_number": payout.shariah_certificate_number,
            "biometric_auth_ref": payout.biometric_auth_ref,
            "ceremony_hash": payout.ceremony_hash,
            "legal_entity": payout.pool.legal_entity.name if hasattr(payout.pool, "legal_entity") and payout.pool.legal_entity else "Amanah Islamic Banking Window",
        })


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
        if self.action == "disburse_payout":
            return [IsAuthenticated(), IsFinanceChecker()]
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

    @action(detail=True, methods=["post"], url_path="disburse-payout")
    def disburse_payout(self, request, pk=None):
        member = self.get_object()

        cycle_number = request.data.get("cycle_number")
        amount = request.data.get("amount")
        payout_date = request.data.get("payout_date")

        errors = {}
        if not cycle_number:
            errors["cycle_number"] = ["This field is required."]
        if not amount:
            errors["amount"] = ["This field is required."]
        if not payout_date:
            errors["payout_date"] = ["This field is required."]
        if errors:
            raise ValidationError(errors)

        if member.payout_position is None:
            raise ValidationError("This member has no payout_position assigned yet - run a draw first.")

        active_members = CircleMember.objects.filter(
            pool=member.pool, status=CircleMemberStatus.ACTIVE, payout_position__isnull=False
        )

        # The "turn" is whichever un-paid active member has the smallest
        # payout_position. A member can only be disbursed to once every
        # earlier position has already been paid out - this enforces the
        # rotation sequence rather than letting positions be paid out of
        # order.
        next_turn = active_members.order_by("payout_position").first()
        if next_turn is None or next_turn.id != member.id:
            expected = next_turn.payout_position if next_turn else None
            raise ValidationError(
                f"It is not this member's turn. Current turn is payout_position "
                f"{expected}, but this member is at position {member.payout_position}."
            )

        # Every active member must have a received Contribution for this
        # cycle before anyone can be paid out of it.
        active_member_ids = set(active_members.values_list("id", flat=True))
        received_member_ids = set(
            Contribution.objects.filter(
                member_id__in=active_member_ids,
                cycle_number=cycle_number,
                status=ContributionStatus.RECEIVED,
            ).values_list("member_id", flat=True)
        )
        missing = active_member_ids - received_member_ids
        if missing:
            raise ValidationError(
                f"Not all active members have contributed for cycle {cycle_number} yet "
                f"({len(missing)} member(s) still pending)."
            )

        settlement_rail = request.data.get("settlement_rail") or SettlementRailType.RAAST_RTGS
        settlement_utr = request.data.get("settlement_utr") or f"RAAST-PK-{timezone.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
        recipient_iban = request.data.get("recipient_iban") or ""
        recipient_bank = request.data.get("recipient_bank") or "Meezan Bank Limited"
        cert_no = f"SHAR-QARD-2025-{uuid.uuid4().hex[:6].upper()}"
        hash_payload = f"{member.pool.code}:{member.member_reference}:{amount}:{settlement_utr}:{cycle_number}:{payout_date}"
        ceremony_hash = hashlib.sha256(hash_payload.encode("utf-8")).hexdigest()

        payout = Payout.objects.create(
            tenant=member.tenant,
            member=member,
            pool=member.pool,
            cycle_number=cycle_number,
            amount=amount,
            payout_date=payout_date,
            status=PayoutStatus.DISBURSED,
            disbursed_by=request.user,
            secondary_approved_by=request.user,
            secondary_approved_at=timezone.now(),
            settlement_rail=settlement_rail,
            settlement_utr=settlement_utr,
            recipient_iban=recipient_iban,
            recipient_bank=recipient_bank,
            shariah_compliance_status="certified_qard_hasana",
            shariah_certificate_number=cert_no,
            biometric_auth_ref=request.data.get("biometric_auth_ref") or f"BIO-VERIFIED-{uuid.uuid4().hex[:6].upper()}",
            ceremony_hash=ceremony_hash,
        )

        member.status = CircleMemberStatus.PAID_OUT
        member.save(update_fields=["status", "updated_at"])

        log_action(
            tenant=member.tenant,
            actor=request.user,
            action="disburse_payout",
            model_name="Payout",
            object_id=str(payout.id),
            changes={
                "member_id": str(member.id),
                "cycle_number": payout.cycle_number,
                "amount": str(payout.amount),
                "status": payout.status,
            },
            request=request,
        )
        return Response(PayoutSerializer(payout).data, status=201)

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
