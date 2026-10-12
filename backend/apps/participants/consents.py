"""Consent register and the data-subject export (BRD privacy requirements)."""

from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .models import Consent, ConsentPurpose, ConsentStatus

METHODS = ("in_person", "e_sign", "otp", "portal")


def grant_consent(*, participant, purpose, method, evidence_reference, user):
    if purpose not in ConsentPurpose.values:
        raise ValidationError({"purpose": [f"Must be one of: {', '.join(ConsentPurpose.values)}."]})
    if method not in METHODS:
        raise ValidationError({"method": [f"Must be one of: {', '.join(METHODS)}."]})
    if method != "in_person" and not str(evidence_reference).strip():
        raise ValidationError({"evidence_reference": ["An e-signature / OTP / portal reference is required."]})
    if Consent.objects.filter(participant=participant, purpose=purpose, status=ConsentStatus.GRANTED).exists():
        raise ValidationError("A live consent for this purpose already exists; withdraw it first to record a new one.")
    return Consent.objects.create(
        tenant=participant.tenant, participant=participant, purpose=purpose, method=method,
        evidence_reference=str(evidence_reference).strip(), granted_at=timezone.now(), recorded_by=user,
    )


def withdraw_consent(consent, reason):
    if consent.status == ConsentStatus.WITHDRAWN:
        raise ValidationError("This consent has already been withdrawn.")
    consent.status = ConsentStatus.WITHDRAWN
    consent.withdrawn_at = timezone.now()
    consent.withdrawal_reason = str(reason or "").strip()[:255]
    consent.save(update_fields=["status", "withdrawn_at", "withdrawal_reason", "updated_at"])
    return consent


def has_consent(participant, purpose):
    return Consent.objects.filter(participant=participant, purpose=purpose, status=ConsentStatus.GRANTED).exists()


def consent_row(c):
    return {
        "id": str(c.id), "purpose": c.purpose, "purpose_label": c.get_purpose_display(), "status": c.status,
        "granted_at": c.granted_at.isoformat(), "method": c.method, "evidence_reference": c.evidence_reference,
        "withdrawn_at": c.withdrawn_at.isoformat() if c.withdrawn_at else None, "withdrawal_reason": c.withdrawal_reason,
    }


def data_subject_export(participant):
    """Everything held about one participant, for the data-subject access request."""
    from apps.allocation.models import DepositorStatement

    accounts = participant.accounts.all()
    statements = DepositorStatement.objects.filter(account__participant=participant).select_related("account")
    return {
        "generated_at": timezone.now().isoformat(),
        "participant": {
            "reference": participant.reference, "full_name": participant.full_name, "class": participant.participant_class,
            "kyc_status": participant.kyc_status, "cnic_ntn": participant.cnic_ntn, "iban": participant.iban,
            "bank_name": participant.bank_name, "tax_status": participant.tax_status, "zakat_exempt": participant.zakat_exempt,
            "email": participant.email, "nominee_name": participant.nominee_name,
        },
        "accounts": [
            {"account_number": a.account_number, "pool": a.pool.code, "opened_date": str(a.opened_date), "status": a.status}
            for a in accounts
        ],
        "statement_count": statements.count(),
        "consents": [consent_row(c) for c in participant.consents.all()],
    }
