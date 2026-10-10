from rest_framework import serializers

from .models import Participant, ParticipantAccount


class ParticipantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Participant
        fields = (
            "id",
            "tenant",
            "reference",
            "full_name",
            "participant_class",
            "kyc_status",
            "cnic_ntn",
            "iban",
            "bank_name",
            "bic",
            "tax_status",
            "zakat_exempt",
            "default_channel",
            "nominee_name",
            "user",
            "created_at",
            "updated_at",
        )
        # KYC status only changes through the dedicated verify/reject actions.
        read_only_fields = ("id", "tenant", "kyc_status", "created_at", "updated_at")

    def validate_reference(self, value):
        # The tenant-scoped manager already limits this to the current tenant.
        qs = Participant.objects.filter(reference=value)
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("A participant with this reference already exists.")
        return value


class ParticipantAccountSerializer(serializers.ModelSerializer):
    participant_name = serializers.CharField(source="participant.full_name", read_only=True)
    participant_reference = serializers.CharField(source="participant.reference", read_only=True)
    participant_class = serializers.CharField(source="participant.participant_class", read_only=True)

    class Meta:
        model = ParticipantAccount
        fields = (
            "id",
            "tenant",
            "participant",
            "participant_name",
            "participant_reference",
            "participant_class",
            "pool",
            "account_number",
            "opened_date",
            "closed_date",
            "status",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "tenant", "status", "created_at", "updated_at")

    def __init__(self, *args, **kwargs):
        # Related querysets must be built per instance, after TenantMiddleware
        # has set the tenant (see BulkBalanceImportSerializer for the reason).
        super().__init__(*args, **kwargs)
        from apps.pools.models import Pool

        self.fields["participant"] = serializers.PrimaryKeyRelatedField(queryset=Participant.objects.all())
        self.fields["pool"] = serializers.PrimaryKeyRelatedField(queryset=Pool.objects.all())

    def validate(self, attrs):
        opened = attrs.get("opened_date", getattr(self.instance, "opened_date", None))
        closed = attrs.get("closed_date", getattr(self.instance, "closed_date", None))
        if opened and closed and closed < opened:
            raise serializers.ValidationError({"closed_date": "closed_date cannot be before opened_date."})
        return attrs

    def validate_account_number(self, value):
        qs = ParticipantAccount.objects.filter(account_number=value)
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("An account with this number already exists.")
        return value
