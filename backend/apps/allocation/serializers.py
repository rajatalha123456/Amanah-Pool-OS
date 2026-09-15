from decimal import Decimal

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import ProfitSharingRatio, WeightageBand
from .validators import check_no_overlap


class WeightageBandSerializer(serializers.ModelSerializer):
    class Meta:
        model = WeightageBand
        fields = (
            "id",
            "tenant",
            "pool",
            "participant_class",
            "weightage",
            "effective_from",
            "effective_to",
            "status",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "tenant", "status", "created_at", "updated_at")

    def validate(self, attrs):
        pool = attrs.get("pool", getattr(self.instance, "pool", None))
        participant_class = attrs.get(
            "participant_class", getattr(self.instance, "participant_class", None)
        )
        effective_from = attrs.get(
            "effective_from", getattr(self.instance, "effective_from", None)
        )
        effective_to = attrs.get("effective_to", getattr(self.instance, "effective_to", None))

        try:
            check_no_overlap(
                WeightageBand,
                pool=pool,
                effective_from=effective_from,
                effective_to=effective_to,
                exclude_id=self.instance.id if self.instance else None,
                extra_filter={"participant_class": participant_class},
            )
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message) from exc

        return attrs


class PSRSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProfitSharingRatio
        fields = (
            "id",
            "tenant",
            "pool",
            "depositor_share",
            "mudarib_share",
            "effective_from",
            "effective_to",
            "status",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "tenant", "status", "created_at", "updated_at")

    def validate(self, attrs):
        depositor_share = attrs.get(
            "depositor_share", getattr(self.instance, "depositor_share", None)
        )
        mudarib_share = attrs.get(
            "mudarib_share", getattr(self.instance, "mudarib_share", None)
        )

        if depositor_share is not None and mudarib_share is not None:
            if depositor_share + mudarib_share != Decimal("100.00"):
                raise serializers.ValidationError(
                    "depositor_share and mudarib_share must add up to 100.00."
                )

        pool = attrs.get("pool", getattr(self.instance, "pool", None))
        effective_from = attrs.get(
            "effective_from", getattr(self.instance, "effective_from", None)
        )
        effective_to = attrs.get("effective_to", getattr(self.instance, "effective_to", None))

        try:
            check_no_overlap(
                ProfitSharingRatio,
                pool=pool,
                effective_from=effective_from,
                effective_to=effective_to,
                exclude_id=self.instance.id if self.instance else None,
            )
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message) from exc

        return attrs
