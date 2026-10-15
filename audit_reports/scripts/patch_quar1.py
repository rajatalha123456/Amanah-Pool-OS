ROOT = "backend/apps/"


def rd(p):
    return open(ROOT + p, encoding="utf-8").read()


def wr(p, s):
    open(ROOT + p, "w", encoding="utf-8").write(s)


def sub(s, old, new):
    assert old in s, old[:100]
    return s.replace(old, new, 1)


# ---- model ----------------------------------------------------------------------------------------------------
s = rd("governance/models.py")
s = sub(s, '''class ExceptionDetectedBy(models.TextChoices):''', '''class QuarantineStatus(models.TextChoices):
    NONE = "none", "No value held"
    HELD = "held", "Value quarantined, treatment not decided"
    DECIDED = "decided", "Treatment decided"


class QuarantineTreatment(models.TextChoices):
    RELEASE_TO_POOL = "release_to_pool", "Release to the pool (no non-compliance found)"
    PURIFY = "purify", "Purify: route to charity"
    RETURN_TO_SOURCE = "return_to_source", "Return to the source"
    WRITE_OFF = "write_off", "Write off at the bank's cost"


class ExceptionDetectedBy(models.TextChoices):''')
s = sub(s, '''    resolved_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"[{self.severity}] {self.title}"''', '''    resolved_at = models.DateTimeField(null=True, blank=True)

    # BRD 8 exception handling: classify, QUARANTINE value, investigate, decide treatment and DISCLOSE.
    quarantine_status = models.CharField(max_length=10, choices=QuarantineStatus.choices, default=QuarantineStatus.NONE)
    quarantined_amount = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
    quarantine_reason = models.TextField(blank=True, default="")
    quarantined_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    quarantined_at = models.DateTimeField(null=True, blank=True)
    quarantine_treatment = models.CharField(max_length=20, choices=QuarantineTreatment.choices, blank=True, default="")
    treatment_decided_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    treatment_decided_at = models.DateTimeField(null=True, blank=True)
    treatment_note = models.TextField(blank=True, default="")
    disclosure_note = models.TextField(blank=True, default="")
    disclosed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"[{self.severity}] {self.title}"''')
wr("governance/models.py", s)

# ---- serializer -------------------------------------------------------------------------------------------------
s = rd("governance/serializers.py")
s = sub(s, '''            "resolved_by",
            "resolved_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = (''', '''            "resolved_by",
            "resolved_at",
            "quarantine_status",
            "quarantined_amount",
            "quarantine_reason",
            "quarantined_at",
            "quarantine_treatment",
            "treatment_note",
            "treatment_decided_at",
            "disclosure_note",
            "disclosed_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "quarantine_status",
            "quarantined_amount",
            "quarantine_reason",
            "quarantined_at",
            "quarantine_treatment",
            "treatment_note",
            "treatment_decided_at",
            "disclosure_note",
            "disclosed_at",''')
wr("governance/serializers.py", s)

# ---- views --------------------------------------------------------------------------------------------------------
s = rd("governance/views.py")
s = sub(s, '''        if self.action in (
            "update",
            "partial_update",
            "resolve",
            "dismiss",
            "start_investigation",
            "set_treatment",
        ):
            return [IsAuthenticated(), IsRiskCompliance()]
        return [IsAuthenticated()]''', '''        if self.action == "quarantine":
            return [IsAuthenticated(), HasAnyRole(["risk_compliance", "shariah_secretariat", "shariah_board"])()]
        if self.action == "decide_quarantine":
            # A treatment of value is a Shariah decision (BRD 8): the Board decides.
            return [IsAuthenticated(), HasAnyRole(["shariah_board"])()]
        if self.action in (
            "update",
            "partial_update",
            "resolve",
            "dismiss",
            "start_investigation",
            "set_treatment",
        ):
            return [IsAuthenticated(), IsRiskCompliance()]
        return [IsAuthenticated()]''')
s = sub(s, '''    @action(detail=True, methods=["post"])
    def resolve(self, request, pk=None):
        case = self.get_object()

        resolution_notes = request.data.get("resolution_notes")
        if not resolution_notes:
            raise ValidationError({"resolution_notes": ["This field is required."]})
''', '''    @action(detail=True, methods=["post"])
    def quarantine(self, request, pk=None):
        """Holds a stated amount of value while the case is investigated; nothing is distributed from it meanwhile."""
        from decimal import Decimal, InvalidOperation

        from .models import QuarantineStatus

        case = self.get_object()
        if case.status in (ExceptionStatus.RESOLVED, ExceptionStatus.DISMISSED):
            raise ValidationError("A closed case cannot hold value.")
        if case.quarantine_status != QuarantineStatus.NONE:
            raise ValidationError("Value is already quarantined for this case.")
        try:
            amount = Decimal(str(request.data.get("amount")))
        except InvalidOperation:
            amount = Decimal("0")
        if amount <= 0:
            raise ValidationError({"amount": ["The amount held must be greater than zero."]})
        reason = str(request.data.get("reason") or "").strip()
        if not reason:
            raise ValidationError({"reason": ["Say what is held and why."]})
        case.quarantine_status, case.quarantined_amount, case.quarantine_reason = QuarantineStatus.HELD, amount, reason
        case.quarantined_by, case.quarantined_at = request.user, timezone.now()
        if case.status == ExceptionStatus.OPEN:
            case.status = ExceptionStatus.INVESTIGATING
        case.save(update_fields=[
            "quarantine_status", "quarantined_amount", "quarantine_reason", "quarantined_by", "quarantined_at", "status",
            "updated_at",
        ])
        log_action(
            tenant=case.tenant, actor=request.user, action="quarantine", model_name="ExceptionCase", object_id=str(case.id),
            changes={"amount": str(amount)}, reason=reason, request=request,
        )
        return Response(self.get_serializer(case).data)

    @action(detail=True, methods=["post"], url_path="decide-quarantine")
    def decide_quarantine(self, request, pk=None):
        """The Shariah Board decides what happens to the held value; the case cannot close before this."""
        from .models import QuarantineStatus, QuarantineTreatment

        case = self.get_object()
        if case.quarantine_status != QuarantineStatus.HELD:
            raise ValidationError("There is no quarantined value awaiting a decision.")
        treatment = request.data.get("treatment")
        if treatment not in QuarantineTreatment.values:
            raise ValidationError({"treatment": [f"One of {', '.join(QuarantineTreatment.values)}."]})
        note = str(request.data.get("note") or "").strip()
        if not note:
            raise ValidationError({"note": ["Record the reasoning for the treatment."]})
        case.quarantine_status, case.quarantine_treatment, case.treatment_note = QuarantineStatus.DECIDED, treatment, note
        case.treatment_decided_by, case.treatment_decided_at = request.user, timezone.now()
        case.save(update_fields=[
            "quarantine_status", "quarantine_treatment", "treatment_note", "treatment_decided_by", "treatment_decided_at",
            "updated_at",
        ])
        log_action(
            tenant=case.tenant, actor=request.user, action="quarantine_treatment_decided", model_name="ExceptionCase",
            object_id=str(case.id), changes={"treatment": treatment, "amount": str(case.quarantined_amount)}, reason=note,
            request=request,
        )
        return Response(self.get_serializer(case).data)

    @staticmethod
    def _assert_value_settled(case, request):
        """A case with quarantined value closes only after the Board decided its treatment and a disclosure was written."""
        from .models import QuarantineStatus

        if case.quarantine_status == QuarantineStatus.HELD:
            raise ValidationError("Value is quarantined for this case: the Shariah Board must decide its treatment first.")
        if case.quarantine_status == QuarantineStatus.DECIDED:
            disclosure = str(request.data.get("disclosure_note") or "").strip()
            if not disclosure:
                raise ValidationError({"disclosure_note": ["Write how the treatment of the held value is disclosed."]})
            case.disclosure_note, case.disclosed_at = disclosure, timezone.now()

    @action(detail=True, methods=["post"])
    def resolve(self, request, pk=None):
        case = self.get_object()

        resolution_notes = request.data.get("resolution_notes")
        if not resolution_notes:
            raise ValidationError({"resolution_notes": ["This field is required."]})
        self._assert_value_settled(case, request)
''')
s = sub(s, '''        previous_status = case.status
        case.status = ExceptionStatus.RESOLVED
        case.resolution_notes = resolution_notes
        case.resolved_by = request.user
        case.resolved_at = timezone.now()
        case.save(update_fields=["status", "resolution_notes", "resolved_by", "resolved_at", "updated_at"])''', '''        previous_status = case.status
        case.status = ExceptionStatus.RESOLVED
        case.resolution_notes = resolution_notes
        case.resolved_by = request.user
        case.resolved_at = timezone.now()
        case.save(update_fields=["status", "resolution_notes", "resolved_by", "resolved_at", "disclosure_note", "disclosed_at", "updated_at"])''')
s = sub(s, '''        resolution_notes = request.data.get("resolution_notes")
        if not resolution_notes:
            raise ValidationError({"resolution_notes": ["This field is required."]})

        previous_status = case.status
        case.status = ExceptionStatus.DISMISSED''', '''        resolution_notes = request.data.get("resolution_notes")
        if not resolution_notes:
            raise ValidationError({"resolution_notes": ["This field is required."]})
        self._assert_value_settled(case, request)

        previous_status = case.status
        case.status = ExceptionStatus.DISMISSED''')
s = sub(s, '''        case.status = ExceptionStatus.DISMISSED
        case.resolution_notes = resolution_notes
        case.resolved_by = request.user
        case.resolved_at = timezone.now()
        case.save(update_fields=["status", "resolution_notes", "resolved_by", "resolved_at", "updated_at"])''', '''        case.status = ExceptionStatus.DISMISSED
        case.resolution_notes = resolution_notes
        case.resolved_by = request.user
        case.resolved_at = timezone.now()
        case.save(update_fields=["status", "resolution_notes", "resolved_by", "resolved_at", "disclosure_note", "disclosed_at", "updated_at"])''')
wr("governance/views.py", s)
print("ok")
