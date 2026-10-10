from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.permissions import HasAnyRole
from apps.core.audit import log_action

from .models import AccountStatus, KYCStatus, Participant, ParticipantAccount
from .serializers import ParticipantAccountSerializer, ParticipantSerializer

# Roles that may see the participant registry. Investors/members never list it:
# they only ever see their own statements (allocation "my-statements").
READ_ROLES = ["pool_manager", "finance_maker", "finance_checker", "risk_compliance", "auditor", "shariah_board"]
WRITE_ROLES = ["pool_manager", "finance_maker"]


class ParticipantViewSet(viewsets.ModelViewSet):
    serializer_class = ParticipantSerializer
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

    @action(detail=True, methods=["post"], url_path="verify-kyc")
    def verify_kyc(self, request, pk=None):
        return self._set_kyc(request, KYCStatus.VERIFIED)

    @action(detail=True, methods=["post"], url_path="reject-kyc")
    def reject_kyc(self, request, pk=None):
        return self._set_kyc(request, KYCStatus.REJECTED)


class ParticipantAccountViewSet(viewsets.ModelViewSet):
    serializer_class = ParticipantAccountSerializer
    http_method_names = ["get", "post", "put", "patch", "head", "options"]

    def get_queryset(self):
        queryset = ParticipantAccount.objects.select_related("participant").all()
        pool_id = self.request.query_params.get("pool")
        if pool_id:
            queryset = queryset.filter(pool_id=pool_id)
        participant_id = self.request.query_params.get("participant")
        if participant_id:
            queryset = queryset.filter(participant_id=participant_id)
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
