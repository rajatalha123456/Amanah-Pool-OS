ROOT = "backend/apps/"


def rd(p):
    return open(ROOT + p, encoding="utf-8").read()


def wr(p, s):
    open(ROOT + p, "w", encoding="utf-8").write(s)


def sub(s, old, new):
    assert old in s, old[:100]
    return s.replace(old, new, 1)


# ---- models -----------------------------------------------------------------------------------------
s = rd("pools/models.py")
s = sub(s, '''    transfer_reason = models.TextField(blank=True, default="")
    transferred_from = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="transferred_to"
    )
''', '''    transfer_reason = models.TextField(blank=True, default="")
    transferred_from = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="transferred_to"
    )
    # BRD 4: a transfer carries its valuation (the value at which the asset leaves one pool and enters the other).
    transfer_valuation = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
    transfer_valuation_basis = models.CharField(max_length=255, blank=True, default="")
''')
s += '''

class AssetTransferStatus(models.TextChoices):
    PENDING = "pending", "Pending approval"
    APPROVED = "approved", "Approved and transferred"
    REJECTED = "rejected", "Rejected"


class AssetTransferRequest(TenantScopedModel):
    """
    A proposed move of a held asset to another pool (BRD 4: "transfer with effective date, valuation and approval").
    Nothing moves until a different person approves; the valuation and its basis are mandatory and recorded on the
    new assignment. Approval re-checks eligibility, the periods of both pools and the dates, and performs the move.
    """

    assignment = models.ForeignKey(AssetAssignment, on_delete=models.PROTECT, related_name="transfer_requests")
    to_pool = models.ForeignKey(Pool, on_delete=models.PROTECT, related_name="+")
    effective_date = models.DateField()
    reason = models.TextField()
    valuation = models.DecimalField(max_digits=18, decimal_places=2)
    valuation_basis = models.CharField(max_length=255)
    status = models.CharField(max_length=10, choices=AssetTransferStatus.choices, default=AssetTransferStatus.PENDING)
    requested_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, related_name="+")
    decided_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    decided_at = models.DateTimeField(null=True, blank=True)
    decision_note = models.TextField(blank=True, default="")
    new_assignment = models.ForeignKey(AssetAssignment, on_delete=models.PROTECT, null=True, blank=True, related_name="+")

    class Meta:
        ordering = ["-created_at"]
        constraints = [models.CheckConstraint(condition=models.Q(valuation__gt=0), name="asset_transfer_valuation_positive")]

    def delete(self, *args, **kwargs):
        from django.core.exceptions import ValidationError

        raise ValidationError("A transfer request is part of the audit trail and cannot be deleted.")
'''
wr("pools/models.py", s)

# ---- rules: request, approve, reject -----------------------------------------------------------------
s = rd("pools/asset_rules.py")
s = sub(s, '''def transfer_asset(assignment, to_pool, effective_date, reason, user):''', '''def request_transfer(assignment, to_pool, effective_date, reason, valuation, valuation_basis, user):
    """A proposed transfer, fully validated now (and again on approval); nothing moves yet."""
    from decimal import Decimal, InvalidOperation

    from .models import AssetTransferRequest, AssetTransferStatus

    try:
        valuation = Decimal(str(valuation))
    except (InvalidOperation, TypeError):
        valuation = Decimal("0")
    if valuation <= 0:
        raise ValidationError({"valuation": ["The value of the asset at the transfer date is required (greater than zero)."]})
    if not (valuation_basis or "").strip():
        raise ValidationError({"valuation_basis": ["Say how the value was established (valuer, report or market source)."]})
    if assignment.unassigned_date is not None:
        raise ValidationError("Only a current assignment can be transferred.")
    if not (reason or "").strip():
        raise ValidationError({"reason": ["A transfer reason is required."]})
    if to_pool.id == assignment.pool_id:
        raise ValidationError({"to_pool": ["The asset is already in this pool."]})
    if effective_date <= assignment.assigned_date:
        raise ValidationError({"effective_date": ["The transfer must take effect after the current assignment began."]})
    assert_asset_eligible(assignment.asset, to_pool, effective_date)
    assert_period_open(assignment.pool, effective_date)
    if AssetTransferRequest.objects.filter(assignment=assignment, status=AssetTransferStatus.PENDING).exists():
        raise ValidationError("A transfer of this asset is already awaiting approval.")
    return AssetTransferRequest.objects.create(
        tenant=assignment.tenant, assignment=assignment, to_pool=to_pool, effective_date=effective_date,
        reason=reason.strip(), valuation=valuation, valuation_basis=valuation_basis.strip(), requested_by=user,
    )


def approve_transfer(request_obj, user):
    """A different person approves; the transfer is performed and the valuation recorded on the new assignment."""
    from django.db import transaction
    from django.utils import timezone

    from .models import AssetTransferRequest, AssetTransferStatus

    with transaction.atomic():
        req = AssetTransferRequest.objects.select_for_update().get(pk=request_obj.pk)
        if req.status != AssetTransferStatus.PENDING:
            raise ValidationError(f"This transfer is already {req.status}.")
        if req.requested_by_id == user.id:
            raise ValidationError("Four-eyes rule: the person who requested a transfer cannot approve it.")
        new = transfer_asset(req.assignment, req.to_pool, req.effective_date, req.reason, req.requested_by)
        new.transfer_valuation, new.transfer_valuation_basis = req.valuation, req.valuation_basis
        new.save(update_fields=["transfer_valuation", "transfer_valuation_basis", "updated_at"])
        req.status, req.decided_by, req.decided_at, req.new_assignment = AssetTransferStatus.APPROVED, user, timezone.now(), new
        req.save(update_fields=["status", "decided_by", "decided_at", "new_assignment", "updated_at"])
    return req


def reject_transfer(request_obj, user, reason):
    from django.utils import timezone

    from .models import AssetTransferStatus

    if request_obj.status != AssetTransferStatus.PENDING:
        raise ValidationError(f"This transfer is already {request_obj.status}.")
    if not (reason or "").strip():
        raise ValidationError({"reason": ["Say why the transfer is refused."]})
    if request_obj.requested_by_id == user.id:
        raise ValidationError("Four-eyes rule: the person who requested a transfer cannot decide it.")
    request_obj.status, request_obj.decided_by = AssetTransferStatus.REJECTED, user
    request_obj.decided_at, request_obj.decision_note = timezone.now(), reason.strip()
    request_obj.save(update_fields=["status", "decided_by", "decided_at", "decision_note", "updated_at"])
    return request_obj


def transfer_asset(assignment, to_pool, effective_date, reason, user):''')
wr("pools/asset_rules.py", s)

# ---- serializer: expose the valuation on the assignment -----------------------------------------------
s = rd("pools/serializers.py")
s = sub(s, '''            "transfer_reason",
            "transferred_from",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id", "tenant", "unassigned_date", "assigned_by", "transfer_reason", "transferred_from",
            "created_at", "updated_at",
        )''', '''            "transfer_reason",
            "transferred_from",
            "transfer_valuation",
            "transfer_valuation_basis",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id", "tenant", "unassigned_date", "assigned_by", "transfer_reason", "transferred_from",
            "transfer_valuation", "transfer_valuation_basis", "created_at", "updated_at",
        )''')
s += '''

class AssetTransferRequestSerializer(serializers.ModelSerializer):
    asset_reference = serializers.CharField(source="assignment.asset.reference_code", read_only=True)
    from_pool_code = serializers.CharField(source="assignment.pool.code", read_only=True)
    to_pool_code = serializers.CharField(source="to_pool.code", read_only=True)
    requested_by_name = serializers.CharField(source="requested_by.full_name", read_only=True, default=None)
    decided_by_name = serializers.CharField(source="decided_by.full_name", read_only=True, default=None)

    class Meta:
        model = AssetTransferRequest
        fields = (
            "id", "assignment", "asset_reference", "from_pool_code", "to_pool", "to_pool_code", "effective_date", "reason",
            "valuation", "valuation_basis", "status", "requested_by", "requested_by_name", "decided_by_name", "decided_at",
            "decision_note", "new_assignment", "created_at",
        )
        read_only_fields = fields
'''
wr("pools/serializers.py", s)

# ---- views --------------------------------------------------------------------------------------------
s = rd("pools/views.py")
a = s.index('    @action(detail=True, methods=["post"])\n    def transfer(self, request, pk=None):')
b = s.index("class DailyBalanceViewSet")
new = '''    @action(detail=True, methods=["post"])
    def transfer(self, request, pk=None):
        """
        Proposes an effective-dated move of the asset to another pool (BRD 4). Valuation and its basis are required and
        a different person approves (`pools/asset-transfers/{id}/approve/`); the old assignment ends the day before.
        """
        from .asset_rules import request_transfer

        assignment = self.get_object()
        to_pool = Pool.objects.filter(id=request.data.get("to_pool")).first()
        if to_pool is None:
            raise ValidationError({"to_pool": ["A valid destination pool is required."]})
        try:
            effective_date = date.fromisoformat(str(request.data.get("effective_date")))
        except ValueError:
            raise ValidationError({"effective_date": ["A valid date (YYYY-MM-DD) is required."]})

        proposal = request_transfer(
            assignment, to_pool, effective_date, str(request.data.get("reason") or ""),
            request.data.get("valuation"), str(request.data.get("valuation_basis") or ""), request.user,
        )
        log_action(
            tenant=assignment.tenant, actor=request.user, action="asset_transfer_requested", model_name="AssetTransferRequest",
            object_id=str(proposal.id),
            changes={"from_pool": str(assignment.pool_id), "to_pool": str(to_pool.id), "effective_date": str(effective_date),
                     "valuation": str(proposal.valuation), "basis": proposal.valuation_basis},
            reason=proposal.reason, request=request,
        )
        return Response(AssetTransferRequestSerializer(proposal).data, status=202)


class AssetTransferViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """Proposed asset transfers: the requester is a pool manager; a different finance checker or risk officer decides."""

    serializer_class = AssetTransferRequestSerializer

    def get_queryset(self):
        queryset = AssetTransferRequest.objects.select_related("assignment__asset", "assignment__pool", "to_pool", "requested_by", "decided_by")
        pool_id = self.request.query_params.get("pool")
        if pool_id:
            queryset = queryset.filter(Q(assignment__pool_id=pool_id) | Q(to_pool_id=pool_id))
        return queryset

    def get_permissions(self):
        if self.action in ("approve", "reject"):
            return [IsAuthenticated(), HasAnyRole(["finance_checker", "risk_compliance"])()]
        return [IsAuthenticated(), HasAnyRole(STAFF_ROLES)()]

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        from .asset_rules import approve_transfer

        req = approve_transfer(self.get_object(), request.user)
        log_action(
            tenant=req.tenant, actor=request.user, action="asset_transfer_approved", model_name="AssetTransferRequest",
            object_id=str(req.id), changes={"new_assignment": str(req.new_assignment_id), "valuation": str(req.valuation)},
            request=request,
        )
        return Response(self.get_serializer(req).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        from .asset_rules import reject_transfer

        req = reject_transfer(self.get_object(), request.user, request.data.get("reason"))
        log_action(
            tenant=req.tenant, actor=request.user, action="asset_transfer_rejected", model_name="AssetTransferRequest",
            object_id=str(req.id), reason=req.decision_note, request=request,
        )
        return Response(self.get_serializer(req).data)


'''
s = s[:a] + new + s[b:]
wr("pools/views.py", s)
print("ok")
