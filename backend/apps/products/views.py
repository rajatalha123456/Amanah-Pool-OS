from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.permissions import HasAnyRole, IsProductManager, IsShariahBoard
from apps.core.audit import log_action

from .models import (
    ContractTemplate,
    ContractTemplateStatus,
    JurisdictionRulePack,
    Product,
    ProductStatus,
    ShariahDecision,
    ShariahDecisionStatus,
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
            return [IsAuthenticated(), HasAnyRole(["shariah_board", "shariah_secretariat", "platform_super_admin"])()]
        if self.action == "approve":
            return [IsAuthenticated(), IsShariahBoard()]
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
        if instance.status == ShariahDecisionStatus.APPROVED:
            if getattr(self.request.user, "role", None) not in ("shariah_board", "platform_super_admin"):
                raise PermissionDenied(
                    "Shariah Secretariat cannot delete an approved Shariah decision. Only the Shariah Supervisory Board can delete or revoke approved rulings."
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
        decision = self.get_object()
        if decision.status == ShariahDecisionStatus.APPROVED:
            raise ValidationError("This decision has already been approved.")
        if decision.created_by and decision.created_by == request.user:
            raise ValidationError(
                "Maker and checker cannot be the same user: the user who drafted this Shariah decision cannot approve it."
            )
        decision.status = ShariahDecisionStatus.APPROVED
        decision.approved_by = request.user
        decision.approved_at = timezone.now()
        decision.save(update_fields=["status", "approved_by", "approved_at", "updated_at"])
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


class ContractTemplateViewSet(viewsets.ModelViewSet):
    serializer_class = ContractTemplateSerializer

    def get_queryset(self):
        return ContractTemplate.objects.all()

    def get_permissions(self):
        if self.action == "create":
            return [IsAuthenticated(), IsProductManager()]
        if self.action == "approve":
            return [IsAuthenticated(), IsShariahBoard()]
        return [IsAuthenticated()]

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


class ProductViewSet(viewsets.ModelViewSet):
    serializer_class = ProductSerializer

    def get_queryset(self):
        return Product.objects.all()

    def get_permissions(self):
        if self.action in ("create", "submit_for_review"):
            return [IsAuthenticated(), IsProductManager()]
        if self.action == "approve":
            return [IsAuthenticated(), IsShariahBoard()]
        return [IsAuthenticated()]

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
    serializer_class = JurisdictionRulePackSerializer

    def get_queryset(self):
        return JurisdictionRulePack.objects.all()

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy", "activate"):
            return [IsAuthenticated(), HasAnyRole(["platform_super_admin", "risk_manager", "compliance_officer"])()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.tenant)

    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        pack = self.get_object()
        is_default = request.data.get("is_default", False)
        if is_default:
            JurisdictionRulePack.objects.filter(tenant=pack.tenant).update(is_default=False)
            pack.is_default = True
        pack.is_active = True
        pack.save()
        log_action(
            tenant=pack.tenant,
            actor=request.user,
            action="activate_rule_pack",
            model_name="JurisdictionRulePack",
            object_id=str(pack.id),
            changes={"is_active": True, "is_default": pack.is_default},
            request=request,
        )
        return Response(self.get_serializer(pack).data)
