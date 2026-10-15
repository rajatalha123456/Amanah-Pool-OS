from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.core.pagination import StandardPagination
from apps.accounts.permissions import HasAnyRole
from apps.core.audit import log_action

from .consents import consent_row, data_subject_export, grant_consent, withdraw_consent
from .models import AccountStatus, Consent, KYCStatus, Participant, ParticipantAccount
from .serializers import ParticipantAccountSerializer, ParticipantSerializer

# Roles that may see the participant registry. Investors/members never list it:
# they only ever see their own statements (allocation "my-statements").
READ_ROLES = ["pool_manager", "finance_maker", "finance_checker", "risk_compliance", "auditor"]  # personal data: no Board
WRITE_ROLES = ["pool_manager", "finance_maker"]


class ParticipantViewSet(viewsets.ModelViewSet):
    serializer_class = ParticipantSerializer
    pagination_class = StandardPagination
    http_method_names = ["get", "post", "put", "patch", "head", "options"]

    def get_queryset(self):
        queryset = Participant.objects.all()
        participant_class = self.request.query_params.get("participant_class")
        if participant_class:
            queryset = queryset.filter(participant_class=participant_class)
        return queryset

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update"):
            return [IsAuthenticated(), HasAnyRole(WRITE_ROLES)()]
        if self.action in ("verify_kyc", "reject_kyc"):
            # KYC decisions belong to Risk & Compliance (BRD Section 3).
            return [IsAuthenticated(), HasAnyRole(["risk_compliance"])()]
        if self.action == "link_login":
            return [IsAuthenticated(), HasAnyRole(["pool_manager"])()]
        return [IsAuthenticated(), HasAnyRole(READ_ROLES)()]

    def perform_create(self, serializer):
        instance = serializer.save(tenant=self.request.user.tenant)
        log_action(
            tenant=instance.tenant,
            actor=self.request.user,
            action="create",
            model_name="Participant",
            object_id=str(instance.id),
            changes={"reference": instance.reference, "participant_class": instance.participant_class},
            request=self.request,
        )

    def _set_kyc(self, request, new_status):
        participant = self.get_object()
        previous = participant.kyc_status
        participant.kyc_status = new_status
        participant.save(update_fields=["kyc_status", "updated_at"])
        log_action(
            tenant=participant.tenant,
            actor=request.user,
            action=new_status,
            model_name="Participant",
            object_id=str(participant.id),
            changes={"kyc_status": {"before": previous, "after": new_status}},
            reason=request.data.get("note"),
            request=request,
        )
        return Response(self.get_serializer(participant).data)

    @action(detail=True, methods=["post"], url_path="link-login")
    def link_login(self, request, pk=None):
        """
        The pool manager gives a depositor / investor a sign-in: the participant is linked to an existing investor-role
        user of the same tenant, who then sees only this participant's own accounts and statements.
        """
        from apps.accounts.models import User

        participant = self.get_object()
        email = str(request.data.get("email", "")).strip().lower()
        user = User.objects.filter(tenant=participant.tenant, email__iexact=email, role="investor_member").first()
        if user is None:
            raise ValidationError({"email": ["No investor-role user with this email exists in this tenant (create it in Administration first)."]})
        if Participant.objects.filter(user=user).exclude(pk=participant.pk).exists():
            raise ValidationError({"email": ["This login is already linked to another participant."]})
        participant.user = user
        participant.save(update_fields=["user", "updated_at"])
        log_action(
            tenant=participant.tenant, actor=request.user, action="participant_login_linked", model_name="Participant",
            object_id=str(participant.id), changes={"user": str(user.id)}, request=request,
        )
        return Response(self.get_serializer(participant).data)

    @action(detail=True, methods=["post"], url_path="verify-kyc")
    def verify_kyc(self, request, pk=None):
        return self._set_kyc(request, KYCStatus.VERIFIED)

    @action(detail=True, methods=["post"], url_path="reject-kyc")
    def reject_kyc(self, request, pk=None):
        return self._set_kyc(request, KYCStatus.REJECTED)


class ParticipantAccountViewSet(viewsets.ModelViewSet):
    serializer_class = ParticipantAccountSerializer
    pagination_class = StandardPagination
    http_method_names = ["get", "post", "put", "patch", "head", "options"]

    def get_queryset(self):
        queryset = ParticipantAccount.objects.select_related("participant").all()
        pool_id = self.request.query_params.get("pool")
        if pool_id:
            queryset = queryset.filter(pool_id=pool_id)
        participant_id = self.request.query_params.get("participant")
        if participant_id:
            queryset = queryset.filter(participant_id=participant_id)
        # ?participants=id1,id2: the accounts of the participants shown on one page of the registry
        participant_ids = [p for p in (self.request.query_params.get("participants") or "").split(",") if p]
        if participant_ids:
            queryset = queryset.filter(participant_id__in=participant_ids)
        return queryset

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "close"):
            return [IsAuthenticated(), HasAnyRole(WRITE_ROLES)()]
        return [IsAuthenticated(), HasAnyRole(READ_ROLES)()]

    def perform_create(self, serializer):
        instance = serializer.save(tenant=self.request.user.tenant)
        log_action(
            tenant=instance.tenant,
            actor=self.request.user,
            action="create",
            model_name="ParticipantAccount",
            object_id=str(instance.id),
            changes={"account_number": instance.account_number, "pool": str(instance.pool_id)},
            request=self.request,
        )

    @action(detail=True, methods=["post"])
    def close(self, request, pk=None):
        account = self.get_object()
        if account.status == AccountStatus.CLOSED:
            raise ValidationError("This account is already closed.")
        account.status = AccountStatus.CLOSED
        account.closed_date = timezone.localdate()
        account.save(update_fields=["status", "closed_date", "updated_at"])
        log_action(
            tenant=account.tenant,
            actor=request.user,
            action="close",
            model_name="ParticipantAccount",
            object_id=str(account.id),
            request=request,
        )
        return Response(self.get_serializer(account).data)


class ConsentViewSet(viewsets.ViewSet):
    """
    Consent register. Staff record and withdraw consents on a participant's behalf (with evidence); a member
    reads and withdraws only their own consents and can download everything held about them.
    """

    CONSENT_ROLES = ["pool_manager", "finance_maker", "risk_compliance"]

    def get_permissions(self):
        if self.action in ("mine", "my_data"):
            return [IsAuthenticated(), HasAnyRole(["investor_member"])()]
        if self.action == "create":
            return [IsAuthenticated(), HasAnyRole(self.CONSENT_ROLES)()]
        if self.action == "withdraw":
            return [IsAuthenticated(), HasAnyRole(self.CONSENT_ROLES + ["investor_member"])()]
        return [IsAuthenticated(), HasAnyRole(READ_ROLES)()]

    def list(self, request):
        queryset = Consent.objects.select_related("participant")
        participant = request.query_params.get("participant")
        if participant:
            queryset = queryset.filter(participant_id=participant)
        return Response([{**consent_row(c), "participant": str(c.participant_id), "participant_name": c.participant.full_name} for c in queryset])

    def create(self, request):
        try:
            participant = Participant.objects.get(pk=request.data.get("participant"))
        except (Participant.DoesNotExist, ValueError, TypeError, DjangoValidationError):
            raise ValidationError({"participant": ["Unknown participant."]})
        consent = grant_consent(
            participant=participant, purpose=request.data.get("purpose"), method=request.data.get("method", "in_person"),
            evidence_reference=request.data.get("evidence_reference", ""), user=request.user,
        )
        log_action(
            tenant=consent.tenant, actor=request.user, action="consent_granted", model_name="Consent",
            object_id=str(consent.id), changes={"purpose": consent.purpose, "participant": participant.reference}, request=request,
        )
        return Response(consent_row(consent), status=201)

    @action(detail=True, methods=["post"])
    def withdraw(self, request, pk=None):
        consent = Consent.objects.filter(pk=pk).first()
        if consent is None:
            raise ValidationError("Unknown consent.")
        if request.user.role == "investor_member" and consent.participant.user_id != request.user.id:
            raise ValidationError("Unknown consent.")  # never reveal other people's records
        withdraw_consent(consent, request.data.get("reason"))
        log_action(
            tenant=consent.tenant, actor=request.user, action="consent_withdrawn", model_name="Consent",
            object_id=str(consent.id), changes={"purpose": consent.purpose}, reason=consent.withdrawal_reason, request=request,
        )
        return Response(consent_row(consent))

    @action(detail=False, methods=["get"])
    def mine(self, request):
        participant = Participant.objects.filter(user=request.user).first()
        rows = Consent.objects.filter(participant=participant) if participant else []
        return Response([consent_row(c) for c in rows])

    @action(detail=False, methods=["get"], url_path="my-data")
    def my_data(self, request):
        participant = Participant.objects.filter(user=request.user).first()
        if participant is None:
            raise ValidationError("No participant record is linked to your login.")
        log_action(
            tenant=participant.tenant, actor=request.user, action="data_subject_export", model_name="Participant",
            object_id=str(participant.id), request=request,
        )
        return Response(data_subject_export(participant))


@api_view(["GET"])
@permission_classes([IsAuthenticated, HasAnyRole(["investor_member"])])
def my_tax_support(request):
    """The caller's own tax and Zakat support statement."""
    from .tax_support import tax_support_for

    data = tax_support_for(request.user)
    if data is None:
        raise ValidationError("No participant record is linked to your login.")
    return Response(data)
