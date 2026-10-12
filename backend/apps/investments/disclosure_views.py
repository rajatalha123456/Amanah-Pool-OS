from rest_framework import mixins, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.permissions import HasAnyRole
from apps.core.audit import log_action
from apps.pools.models import Pool

from . import disclosures
from .models import CapitalAccount, PoolDisclosure

PUBLISH_ROLES = ["pool_manager", "product_manager"]  # prepare
APPROVE_ROLES = ["shariah_board", "risk_compliance"]  # validate (a different person)
STAFF_READ = ["pool_manager", "product_manager", "finance_maker", "finance_checker", "risk_compliance", "auditor",
              "shariah_board", "shariah_secretariat", "authorized_signatory"]


class PoolDisclosureSerializer(serializers.ModelSerializer):
    class Meta:
        model = PoolDisclosure
        fields = ("id", "pool", "version", "summary", "terms", "terms_hash", "risk_warnings", "fee_statement",
                  "published_by", "status", "approved_by", "approved_at", "created_at")
        read_only_fields = fields


def _pool_or_400(value):
    pool = Pool.objects.filter(id=value).select_related("product").first() if value else None
    if pool is None:
        raise ValidationError({"pool": ["A valid pool is required."]})
    return pool


class PoolDisclosureViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = PoolDisclosureSerializer

    def get_queryset(self):
        queryset = PoolDisclosure.objects.all()
        if self.request.user.role == "investor_member":
            queryset = queryset.filter(status="published")
        pool_id = self.request.query_params.get("pool")
        return queryset.filter(pool_id=pool_id) if pool_id else queryset

    def get_permissions(self):
        if self.action == "publish":
            return [IsAuthenticated(), HasAnyRole(PUBLISH_ROLES)()]
        if self.action == "approve":
            return [IsAuthenticated(), HasAnyRole(APPROVE_ROLES)()]
        if self.action == "acknowledge":
            return [IsAuthenticated(), HasAnyRole(["investor_member", "finance_maker", "pool_manager"])()]
        return [IsAuthenticated(), HasAnyRole(STAFF_READ + ["investor_member"])()]

    @action(detail=False, methods=["get"])
    def preview(self, request):
        """The terms a disclosure published now would state (taken from the pool's real configuration)."""
        return Response(disclosures.current_terms(_pool_or_400(request.query_params.get("pool"))))

    @action(detail=False, methods=["post"])
    def publish(self, request):
        pool = _pool_or_400(request.data.get("pool"))
        disclosure = disclosures.publish_disclosure(
            pool=pool, user=request.user, risk_warnings=str(request.data.get("risk_warnings") or ""),
            fee_statement=str(request.data.get("fee_statement") or ""), summary=str(request.data.get("summary") or ""),
        )
        log_action(
            tenant=pool.tenant, actor=request.user, action="disclosure_prepared", model_name="PoolDisclosure",
            object_id=str(disclosure.id), changes={"version": disclosure.version, "terms_hash": disclosure.terms_hash},
            request=request,
        )
        return Response(self.get_serializer(disclosure).data, status=201)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        """A different person validates the prepared disclosure; only then can investors acknowledge it."""
        disclosure = disclosures.approve_disclosure(self.get_object(), request.user)
        log_action(
            tenant=disclosure.tenant, actor=request.user, action="disclosure_approved", model_name="PoolDisclosure",
            object_id=str(disclosure.id), changes={"version": disclosure.version, "terms_hash": disclosure.terms_hash},
            request=request,
        )
        return Response(self.get_serializer(disclosure).data)

    @action(detail=True, methods=["post"])
    def acknowledge(self, request, pk=None):
        """The investor acknowledges in the portal; staff record other methods with evidence."""
        disclosure = self.get_object()
        account_qs = CapitalAccount.objects.filter(id=request.data.get("capital_account"), pool=disclosure.pool)
        is_investor = request.user.role == "investor_member"
        if is_investor:
            account_qs = account_qs.filter(participant__user=request.user)
        account = account_qs.first()
        if account is None:
            raise ValidationError({"capital_account": ["A valid capital account of your own is required."]})
        method = str(request.data.get("method") or ("portal" if is_investor else ""))
        if is_investor and method != "portal":
            raise ValidationError({"method": ["Investors acknowledge through the portal."]})
        if not is_investor and method == "portal":
            raise ValidationError({"method": ["Staff record in_person, otp or e_sign acknowledgements."]})
        ack = disclosures.acknowledge(
            account=account, disclosure=disclosure, method=method, user=request.user,
            evidence_reference=str(request.data.get("evidence_reference") or ""),
            risk_acknowledged=request.data.get("risk_acknowledged") is True,
        )
        log_action(
            tenant=account.tenant, actor=request.user, action="disclosure_acknowledged",
            model_name="DisclosureAcknowledgement", object_id=str(ack.id),
            changes={"account": account.investor_reference, "version": disclosure.version, "method": method},
            request=request,
        )
        return Response({"capital_account": str(account.id), "version": disclosure.version, "method": method}, status=201)

    @action(detail=False, methods=["get"], url_path="subscription-status")
    def subscription_status(self, request):
        """Whether an account may subscribe now, and why not."""
        account = CapitalAccount.objects.filter(id=request.query_params.get("capital_account")).first()
        if account is None or (
            request.user.role == "investor_member"
            and (account.participant is None or account.participant.user_id != request.user.id)
        ):
            raise ValidationError({"capital_account": ["A valid capital account is required."]})
        try:
            disclosures.assert_subscription_allowed(account)
            return Response({"may_subscribe": True, "reason": ""})
        except ValidationError as exc:
            detail = exc.detail if isinstance(exc.detail, list) else [exc.detail]
            return Response({"may_subscribe": False, "reason": " ".join(str(d) for d in detail)})
