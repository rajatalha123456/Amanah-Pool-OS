ROOT = "backend/apps/"


def rd(p):
    return open(ROOT + p, encoding="utf-8").read()


def wr(p, s):
    open(ROOT + p, "w", encoding="utf-8").write(s)


def sub(s, old, new):
    assert old in s, old[:90]
    return s.replace(old, new, 1)


# ---- chart: an optional account (not required for activation) ---------------------------------------
s = rd("accounting/chart.py")
s = sub(s, '''    "recovery_income": "Recovery of Written-off Assets",
}''', '''    "recovery_income": "Recovery of Written-off Assets",
    # Amounts that cannot be placed yet, each one a named item (accounting/suspense.py).
    "suspense": "Suspense - Unidentified Items",
}''')
wr("accounting/chart.py", s)

# ---- model -------------------------------------------------------------------------------------------
s = rd("accounting/models.py")
s += '''

class SuspenseSide(models.TextChoices):
    UNIDENTIFIED_RECEIPT = "unidentified_receipt", "Unidentified receipt (money in, owner not known)"
    UNEXPLAINED_SHORTFALL = "unexplained_shortfall", "Unexplained shortfall (money missing, reason not known)"


class SuspenseStatus(models.TextChoices):
    PROPOSED = "proposed", "Proposed (awaiting a checker)"
    OPEN = "open", "Open in suspense"
    CLEARING_PROPOSED = "clearing_proposed", "Clearing proposed"
    CLEARED = "cleared", "Cleared"
    REJECTED = "rejected", "Rejected"


class SuspenseItem(TenantScopedModel):
    """One amount held in the pool's suspense account, with who, why and where it finally went (accounting/suspense.py)."""

    pool = models.ForeignKey("pools.Pool", on_delete=models.PROTECT, related_name="suspense_items")
    side = models.CharField(max_length=24, choices=SuspenseSide.choices)
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    counter_account_key = models.CharField(max_length=40, default="pool_cash")
    description = models.TextField()
    reference = models.CharField(max_length=100, blank=True, default="")
    opened_on = models.DateField()
    reconciliation_batch = models.ForeignKey(
        ReconciliationBatch, on_delete=models.PROTECT, null=True, blank=True, related_name="suspense_items"
    )
    status = models.CharField(max_length=20, choices=SuspenseStatus.choices, default=SuspenseStatus.PROPOSED)
    proposed_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, related_name="+")
    opened_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    opened_at = models.DateTimeField(null=True, blank=True)
    opening_journal = models.ForeignKey(JournalBatch, on_delete=models.PROTECT, null=True, blank=True, related_name="+")
    clear_account_key = models.CharField(max_length=40, blank=True, default="")
    clear_reason = models.TextField(blank=True, default="")
    clear_proposed_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    cleared_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    cleared_on = models.DateField(null=True, blank=True)
    clearing_journal = models.ForeignKey(JournalBatch, on_delete=models.PROTECT, null=True, blank=True, related_name="+")
    decision_note = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["opened_on", "created_at"]
        constraints = [models.CheckConstraint(condition=models.Q(amount__gt=0), name="suspense_amount_positive")]

    def delete(self, *args, **kwargs):
        raise ValidationError("A suspense item is part of the ledger trail and cannot be deleted; reject or clear it.")
'''
wr("accounting/models.py", s)

# ---- views -------------------------------------------------------------------------------------------
s = rd("accounting/views.py")
s += '''

class SuspenseItemSerializer(serializers.ModelSerializer):
    pool_code = serializers.CharField(source="pool.code", read_only=True)
    proposed_by_name = serializers.CharField(source="proposed_by.full_name", read_only=True, default=None)
    opened_by_name = serializers.CharField(source="opened_by.full_name", read_only=True, default=None)
    cleared_by_name = serializers.CharField(source="cleared_by.full_name", read_only=True, default=None)

    class Meta:
        model = SuspenseItem
        fields = (
            "id", "pool", "pool_code", "side", "amount", "counter_account_key", "description", "reference", "opened_on",
            "reconciliation_batch", "status", "proposed_by", "proposed_by_name", "opened_by_name", "opened_at",
            "opening_journal", "clear_account_key", "clear_reason", "clear_proposed_by", "cleared_by_name", "cleared_on",
            "clearing_journal", "decision_note", "created_at",
        )
        read_only_fields = fields


class SuspenseItemViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """
    Suspense items of a pool. A finance maker proposes to park an amount (or to clear one); a different finance checker
    approves, and only then is the journal posted.
    """

    serializer_class = SuspenseItemSerializer
    pagination_class = StandardPagination

    def get_queryset(self):
        queryset = SuspenseItem.objects.select_related("pool", "proposed_by", "opened_by", "cleared_by")
        for param in ("pool", "status"):
            value = self.request.query_params.get(param)
            if value:
                queryset = queryset.filter(**{f"{param}_id" if param == "pool" else param: value})
        return queryset

    def get_permissions(self):
        if self.action in ("create", "propose_clear"):
            return [IsAuthenticated(), IsFinanceMaker()]
        if self.action in ("approve", "reject", "approve_clear", "reject_clear"):
            return [IsAuthenticated(), IsFinanceChecker()]
        return [IsAuthenticated(), HasAnyRole(GL_READ_ROLES)()]

    def create(self, request, *args, **kwargs):
        from .suspense import propose_open

        pool = get_object_or_404(Pool, id=request.data.get("pool"))
        recon = None
        if request.data.get("reconciliation_batch"):
            recon = get_object_or_404(ReconciliationBatch, id=request.data["reconciliation_batch"], pool=pool)
        item = propose_open(
            pool=pool, side=request.data.get("side"), amount=request.data.get("amount"),
            description=request.data.get("description", ""), reference=request.data.get("reference", ""),
            counter_account_key=request.data.get("counter_account_key") or "pool_cash",
            opened_on=request.data.get("opened_on") or None, reconciliation_batch=recon, user=request.user, request=request,
        )
        return Response(self.get_serializer(item).data, status=201)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        from .suspense import approve_open

        return Response(self.get_serializer(approve_open(self.get_object(), request.user, request)).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        from .suspense import reject_open

        return Response(self.get_serializer(reject_open(self.get_object(), request.user, request.data.get("reason"), request)).data)

    @action(detail=True, methods=["post"], url_path="propose-clear")
    def propose_clear(self, request, pk=None):
        from .suspense import propose_clear

        item = propose_clear(self.get_object(), request.user, request.data.get("target_account_key"), request.data.get("reason"), request)
        return Response(self.get_serializer(item).data)

    @action(detail=True, methods=["post"], url_path="approve-clear")
    def approve_clear(self, request, pk=None):
        from .suspense import approve_clear

        return Response(self.get_serializer(approve_clear(self.get_object(), request.user, request)).data)

    @action(detail=True, methods=["post"], url_path="reject-clear")
    def reject_clear(self, request, pk=None):
        from .suspense import reject_clear

        return Response(self.get_serializer(reject_clear(self.get_object(), request.user, request.data.get("reason"), request)).data)

    @action(detail=False, methods=["get"])
    def ageing(self, request):
        from .suspense import ageing

        pool = get_object_or_404(Pool, id=request.query_params.get("pool"))
        return Response(ageing(pool, request.query_params.get("as_of") or None))

    @action(detail=False, methods=["get"])
    def accounts(self, request):
        """The pool accounts an amount can be cleared to."""
        from .chart import ACCOUNTS

        return Response([{"key": k, "name": v} for k, v in ACCOUNTS.items() if k != "suspense"])
'''
s = sub(s, "from .models import (\n    GLExport,\n", "from .models import (\n    GLExport,\n    SuspenseItem,\n")
wr("accounting/views.py", s)

s = rd("accounting/urls.py")
s = sub(s, "    GLExportViewSet,\n", "    GLExportViewSet,\n    SuspenseItemViewSet,\n")
s = sub(s, 'router.register("gl-exports", GLExportViewSet, basename="gl-export")\n',
        'router.register("gl-exports", GLExportViewSet, basename="gl-export")\nrouter.register("suspense-items", SuspenseItemViewSet, basename="suspense-item")\n')
wr("accounting/urls.py", s)

# ---- period close gate 6 -------------------------------------------------------------------------------
s = rd("pools/period_close_engine.py")
s = sub(s, '''   - Gate 5  that run's journal batch is posted and balanced.
''', '''   - Gate 5  that run's journal batch is posted and balanced;
   - Gate 6  suspense: every amount in suspense is a named item, and none is older than the allowed age at period end
             (rule pack `suspense_max_age_days`, default 30).
''')
s = sub(s, '''        applicable=not is_circle,
    )
    return gates, run
''', '''        applicable=not is_circle,
    )

    # Gate 6 - suspense
    from apps.accounting.suspense import ageing

    sus = ageing(pool, end)
    gates["suspense_cleared"] = _gate(
        sus["itemized"] and sus["overdue_items"] == 0,
        "Gate 6: Suspense explained",
        (
            "Nothing in suspense." if sus["open_items"] == 0 else
            f"{sus['open_items']} open item(s), none older than {sus['max_age_days']} days."
        ) if sus["itemized"] and sus["overdue_items"] == 0 else (
            f"The suspense ledger ({sus['ledger_balance']}) does not equal its open items ({sus['items_net']})."
            if not sus["itemized"] else
            f"{sus['overdue_items']} suspense item(s) older than {sus['max_age_days']} days must be cleared first."
        ),
    )
    return gates, run
''')
wr("pools/period_close_engine.py", s)
print("ok")
