import hashlib
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.permissions import HasAnyRole, IsProductManager, IsShariahBoard, IsStrictShariahBoard
from apps.core.audit import log_action
from apps.core.viewset_guards import NO_DELETE, STAFF_ROLES, EditableWhileDraftMixin

from .models import (
    ContractTemplate,
    ContractTemplateStatus,
    JurisdictionRulePack,
    Product,
    ProductStatus,
    ShariahDecision,
    ShariahDecisionStatus,
    ShariahQuorumVote,
)
from .serializers import (
    ContractTemplateSerializer,
    JurisdictionRulePackSerializer,
    ProductSerializer,
    ShariahDecisionSerializer,
)


class ShariahDecisionViewSet(viewsets.ModelViewSet):
    serializer_class = ShariahDecisionSerializer

    def get_queryset(self):
        # Must be a method, not a class-level `queryset = Model.objects.all()`:
        # TenantScopedManager.get_queryset() returns .none() when evaluated
        # with no tenant context (e.g. at import time), and Django bakes that
        # "always empty" marker into the queryset - a later .all() cannot
        # undo it. Calling .objects.all() here instead re-evaluates the
        # manager per-request, after TenantMiddleware has set the context.
        return ShariahDecision.objects.all()

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [IsAuthenticated(), HasAnyRole(["shariah_board", "shariah_secretariat"])()]
        if self.action in ("approve", "cast_quorum_vote"):
            return [IsAuthenticated(), IsStrictShariahBoard()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        instance = serializer.save(
            tenant=self.request.user.tenant,
            created_by=self.request.user,
        )
        log_action(
            tenant=instance.tenant,
            actor=self.request.user,
            action="create",
            model_name="ShariahDecision",
            object_id=str(instance.id),
            changes={"status": instance.status, "decision_code": instance.decision_code},
            request=self.request,
        )

    def perform_update(self, serializer):
        if serializer.instance.status != ShariahDecisionStatus.DRAFT:
            raise ValidationError("An approved Shariah decision cannot be edited; issue a new decision instead.")
        instance = serializer.save()
        log_action(
            tenant=instance.tenant,
            actor=self.request.user,
            action="update",
            model_name="ShariahDecision",
            object_id=str(instance.id),
            changes={"updated_fields": list(serializer.validated_data.keys()), "decision_code": instance.decision_code},
            request=self.request,
        )

    def perform_destroy(self, instance):
        if instance.status != ShariahDecisionStatus.DRAFT:
            raise ValidationError(
                "An approved Shariah decision is a permanent record and cannot be deleted; issue a revoking decision instead."
            )
        if instance.contract_templates.exists():
            raise ValidationError(
                "Cannot delete this Shariah decision: it is actively linked to one or more Contract Templates."
            )
        object_id = str(instance.id)
        tenant = instance.tenant
        code = instance.decision_code
        instance.delete()
        log_action(
            tenant=tenant,
            actor=self.request.user,
            action="delete",
            model_name="ShariahDecision",
            object_id=object_id,
            changes={"deleted_decision_code": code},
            request=self.request,
        )

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        from .shariah import board_size

        decision = self.get_object()
        if decision.status == ShariahDecisionStatus.APPROVED:
            raise ValidationError("This decision has already been approved.")
        # BRD 5 / 8: a ruling is approved by a quorum of the Board, never by one member. The direct approval below exists
        # only for a tenant whose Board has a single member, where a quorum cannot be formed.
        if board_size(decision.tenant_id) >= 2:
            raise ValidationError(
                "This Board has several members: a ruling is approved by the quorum vote (each member signs), "
                "not by one member alone."
            )
        if decision.created_by and decision.created_by == request.user:
            raise ValidationError(
                "Maker and checker cannot be the same user: the user who drafted this Shariah decision cannot approve it."
            )
        decision.status = ShariahDecisionStatus.APPROVED
        decision.approved_by = request.user
        decision.approved_at = timezone.now()
        decision.save(update_fields=["status", "approved_by", "approved_at", "updated_at"])
        from .shariah import apply_supersession

        apply_supersession(decision)
        log_action(
            tenant=decision.tenant,
            actor=request.user,
            action="approve",
            model_name="ShariahDecision",
            object_id=str(decision.id),
            changes={"status": {"before": ShariahDecisionStatus.DRAFT, "after": ShariahDecisionStatus.APPROVED}},
            request=request,
        )
        return Response(self.get_serializer(decision).data)

    @action(detail=True, methods=["post"], url_path="cast-quorum-vote")
    def cast_quorum_vote(self, request, pk=None):
        from .shariah import board_size, quorum_required

        decision = self.get_object()
        data = request.data
        # A vote is always the logged-in Board member's own: the name is never taken from the request.
        scholar_name = request.user.full_name
        scholar_title = str(data.get("scholar_title") or "Shariah Board member").strip()
        vote = data.get("vote", "approve")
        fiqh_notes = str(data.get("fiqh_opinion_notes") or "").strip()

        if decision.status != ShariahDecisionStatus.DRAFT:
            raise ValidationError(f"This ruling is already {decision.status}.")
        if vote not in ("approve", "reject", "abstain"):
            raise ValidationError({"vote": ["Must be approve, reject or abstain."]})
        if not fiqh_notes:
            raise ValidationError({"fiqh_opinion_notes": ["Record the reasoning for your vote."]})
        if decision.created_by_id == request.user.id:
            raise ValidationError("Maker-checker: the member who drafted this ruling cannot vote on it.")
        if decision.quorum_votes.filter(signatory_user=request.user).exists():
            raise ValidationError("You have already voted on this ruling.")
        if board_size(decision.tenant_id) < 2:
            raise ValidationError("A quorum needs at least two active Shariah Board members in this tenant.")

        now = timezone.now()
        sig_payload = f"{decision.decision_code}:{scholar_name}:{vote}:{now.isoformat()}"
        sig_hash = hashlib.sha256(sig_payload.encode()).hexdigest()

        ShariahQuorumVote.objects.create(
            tenant=decision.tenant,
            decision=decision,
            scholar_name=scholar_name,
            scholar_title=scholar_title,
            decision_vote=vote,
            fiqh_concurrence_notes=fiqh_notes,
            digital_signature_hash=sig_hash,
            signatory_user=request.user if request.user.is_authenticated else None,
        )

        approvals = decision.quorum_votes.filter(decision_vote="approve").count()
        required = quorum_required(decision.tenant_id)
        if approvals >= required and decision.status != ShariahDecisionStatus.APPROVED:
            decision.status = ShariahDecisionStatus.APPROVED
            decision.approved_by = request.user
            decision.approved_at = now
            decision.save(update_fields=["status", "approved_by", "approved_at", "updated_at"])
            from .shariah import apply_supersession

            apply_supersession(decision)

            log_action(
                tenant=decision.tenant,
                actor=request.user,
                action="shariah_quorum_approved",
                model_name="ShariahDecision",
                object_id=str(decision.id),
                changes={
                    "status": {"before": ShariahDecisionStatus.DRAFT, "after": ShariahDecisionStatus.APPROVED},
                    "quorum_approvals": approvals,
                    "final_signatory": scholar_name,
                },
                reason=f"Shariah Board quorum of {required} reached.",
                request=request,
            )

        return Response(self.get_serializer(decision).data)



CONTRACT_CLAUSES_SCHEMA = [
    {"key": "profit_ratio", "label": "Profit Ratio", "description": "The depositor/mudarib profit-sharing split."},
    {"key": "late_payment_policy", "label": "Late Payment Policy", "description": "How overdue payments are treated (no interest/penalty under Shariah)."},
    {"key": "notice_period", "label": "Notice Period", "description": "Required notice before withdrawal or termination."},
    {"key": "loss_bearing_clause", "label": "Loss Bearing Clause", "description": "How capital losses are allocated among participants."},
    {"key": "early_termination_terms", "label": "Early Termination Terms", "description": "Conditions and consequences of ending the contract early."},
    {"key": "collateral_requirements", "label": "Collateral Requirements", "description": "Any security/collateral required, if applicable."},
    {"key": "dispute_resolution", "label": "Dispute Resolution", "description": "Mechanism for resolving disagreements (e.g. Shariah arbitration)."},
    {"key": "purification_clause", "label": "Purification Clause", "description": "How incidental non-Shariah-compliant income is handled."},
]


class ContractTemplateViewSet(EditableWhileDraftMixin, viewsets.ModelViewSet):
    http_method_names = NO_DELETE
    serializer_class = ContractTemplateSerializer

    def get_queryset(self):
        return ContractTemplate.objects.all()

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update"):
            return [IsAuthenticated(), IsProductManager()]
        if self.action == "approve":
            return [IsAuthenticated(), IsShariahBoard()]
        return [IsAuthenticated(), HasAnyRole(STAFF_ROLES)()]

    @action(detail=True, methods=["get"], url_path="clauses-schema")
    def clauses_schema(self, request, pk=None):
        # Ensures the referenced template exists (and belongs to the
        # current tenant, via TenantScopedManager) before returning the
        # schema - a 404 for a bad/foreign id rather than a schema for
        # nothing. The schema itself is static and not template-specific
        # yet; see the README for why.
        self.get_object()
        return Response(CONTRACT_CLAUSES_SCHEMA)

    def perform_create(self, serializer):
        instance = serializer.save(tenant=self.request.user.tenant)
        log_action(
            tenant=instance.tenant,
            actor=self.request.user,
            action="create",
            model_name="ContractTemplate",
            object_id=str(instance.id),
            request=self.request,
        )

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        template = self.get_object()
        template.status = ContractTemplateStatus.APPROVED
        template.save(update_fields=["status", "updated_at"])
        log_action(
            tenant=template.tenant,
            actor=request.user,
            action="approve",
            model_name="ContractTemplate",
            object_id=str(template.id),
            changes={"status": {"before": ContractTemplateStatus.DRAFT, "after": ContractTemplateStatus.APPROVED}},
            request=request,
        )
        return Response(self.get_serializer(template).data)


class ProductViewSet(EditableWhileDraftMixin, viewsets.ModelViewSet):
    http_method_names = NO_DELETE
    serializer_class = ProductSerializer

    def get_queryset(self):
        return Product.objects.all()

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "submit_for_review"):
            return [IsAuthenticated(), IsProductManager()]
        if self.action == "approve":
            return [IsAuthenticated(), IsShariahBoard()]
        return [IsAuthenticated(), HasAnyRole(STAFF_ROLES)()]

    def perform_create(self, serializer):
        instance = serializer.save(tenant=self.request.user.tenant)
        log_action(
            tenant=instance.tenant,
            actor=self.request.user,
            action="create",
            model_name="Product",
            object_id=str(instance.id),
            request=self.request,
        )

    @action(detail=True, methods=["post"], url_path="submit-for-review")
    def submit_for_review(self, request, pk=None):
        product = self.get_object()

        if product.status != ProductStatus.DRAFT:
            raise ValidationError(
                f"Product must be in '{ProductStatus.DRAFT}' status to submit for review "
                f"(current status: '{product.status}')."
            )

        product.status = ProductStatus.SHARIAH_REVIEW
        product.save(update_fields=["status", "updated_at"])
        log_action(
            tenant=product.tenant,
            actor=request.user,
            action="submit_for_review",
            model_name="Product",
            object_id=str(product.id),
            changes={"status": {"before": ProductStatus.DRAFT, "after": ProductStatus.SHARIAH_REVIEW}},
            request=request,
        )
        return Response(self.get_serializer(product).data)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        product = self.get_object()

        if product.status != ProductStatus.SHARIAH_REVIEW:
            raise ValidationError(
                f"Product must be in '{ProductStatus.SHARIAH_REVIEW}' status to approve "
                f"(current status: '{product.status}')."
            )

        if product.contract_template.status != ContractTemplateStatus.APPROVED:
            raise ValidationError(
                "Product cannot be approved: its contract template is not approved "
                "(BR-001: a pool/product cannot activate without an approved contract)."
            )

        product.status = ProductStatus.APPROVED
        product.save(update_fields=["status", "updated_at"])
        log_action(
            tenant=product.tenant,
            actor=request.user,
            action="approve",
            model_name="Product",
            object_id=str(product.id),
            changes={"status": {"before": ProductStatus.SHARIAH_REVIEW, "after": ProductStatus.APPROVED}},
            request=request,
        )
        return Response(self.get_serializer(product).data)


class JurisdictionRulePackViewSet(viewsets.ModelViewSet):
    http_method_names = NO_DELETE
    serializer_class = JurisdictionRulePackSerializer

    def get_queryset(self):
        return JurisdictionRulePack.objects.all()

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "activate"):
            return [IsAuthenticated(), HasAnyRole(["platform_super_admin", "risk_compliance"])()]
        # Rule packs are configuration, not financial data: the platform administrator who provisions them may read them.
        return [IsAuthenticated(), HasAnyRole(STAFF_ROLES + ["platform_super_admin"])()]

    # Maker-checker: tax rates, the Mudarib cap and reserve ceilings decide what participants receive, so a change is only
    # PROPOSED here (HTTP 202); a different finance checker or the authorized signatory approves it under
    # /governance/config-changes/ and every step is audited (BRD 8 change governance, BRD 11 overrides).
    def create(self, request, *args, **kwargs):
        from apps.governance.config_changes import submit_change
        from apps.governance.models import ConfigChangeKind
        from apps.governance.views import ConfigChangeRequestSerializer

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        change = submit_change(kind=ConfigChangeKind.RULE_PACK, serializer=serializer, request=request)
        return Response(ConfigChangeRequestSerializer(change).data, status=202)

    def update(self, request, *args, **kwargs):
        from apps.governance.config_changes import submit_change
        from apps.governance.models import ConfigChangeKind
        from apps.governance.views import ConfigChangeRequestSerializer

        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        change = submit_change(kind=ConfigChangeKind.RULE_PACK, serializer=serializer, request=request, instance=instance)
        return Response(ConfigChangeRequestSerializer(change).data, status=202)

    @action(detail=True, methods=["get"])
    def revisions(self, request, pk=None):
        """The pack's history: every distinct content it has had. Read-only."""
        from .models import RulePackRevision

        pack = self.get_object()
        rows = RulePackRevision._base_manager.filter(pack=pack).order_by("-revision")
        return Response([
            {"revision": r.revision, "content_hash": r.content_hash, "content": r.content, "created_at": r.created_at}
            for r in rows
        ])

    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        """Making a pack active / the tenant default changes what governs every pool: it is proposed, not applied."""
        from apps.governance.config_changes import submit_change
        from apps.governance.models import ConfigChangeKind
        from apps.governance.views import ConfigChangeRequestSerializer

        pack = self.get_object()
        data = {
            "is_active": True,
            "is_default": bool(request.data.get("is_default", False)),
            "change_reason": request.data.get("change_reason"),
        }
        serializer = self.get_serializer(pack, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        change = submit_change(
            kind=ConfigChangeKind.RULE_PACK, serializer=serializer, request=request, instance=pack, data=data
        )
        return Response(ConfigChangeRequestSerializer(change).data, status=202)
