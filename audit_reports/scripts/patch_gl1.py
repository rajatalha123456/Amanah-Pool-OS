ROOT = "backend/apps/accounting/"


def rd(p):
    return open(ROOT + p, encoding="utf-8").read()


def wr(p, s):
    open(ROOT + p, "w", encoding="utf-8").write(s)


def sub(s, old, new):
    assert old in s, old[:90]
    return s.replace(old, new, 1)


# ---- model ----------------------------------------------------------------------------------------
s = rd("models.py")
s += '''

class GLExportStatus(models.TextChoices):
    GENERATED = "generated", "Generated (awaiting the GL's answer)"
    CONFIRMED = "confirmed", "Confirmed posted in the enterprise GL"
    REJECTED = "rejected", "Rejected by the GL (batches free to export again)"


class GLExport(TenantScopedModel):
    """
    One hand-over of journal batches to the enterprise general ledger (BRD 10 / 12: "journal batches, posting status").
    The file is stored with its hash, so what was sent can be downloaded again and proved. A batch belongs to at most one
    export that is generated or confirmed: it cannot be sent twice unless the GL rejected the export it was in.
    """

    pool = models.ForeignKey("pools.Pool", on_delete=models.PROTECT, related_name="gl_exports")
    date_from = models.DateField(null=True, blank=True)
    date_to = models.DateField(null=True, blank=True)
    batches = models.ManyToManyField(JournalBatch, related_name="gl_exports")
    row_count = models.PositiveIntegerField()
    total_debit = models.DecimalField(max_digits=18, decimal_places=2)
    total_credit = models.DecimalField(max_digits=18, decimal_places=2)
    content = models.TextField()
    content_hash = models.CharField(max_length=64)
    status = models.CharField(max_length=10, choices=GLExportStatus.choices, default=GLExportStatus.GENERATED)
    exported_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, related_name="+")
    gl_reference = models.CharField(max_length=100, blank=True, default="")
    decided_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    decided_at = models.DateTimeField(null=True, blank=True)
    decision_note = models.TextField(blank=True, default="")

    _DECISION_FIELDS = frozenset({"status", "gl_reference", "decided_by", "decided_at", "decision_note", "updated_at"})

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        # The file and its figures never change once generated; only the GL's answer is recorded afterwards.
        if not self._state.adding:
            fields = kwargs.get("update_fields")
            if fields is None or not set(fields) <= self._DECISION_FIELDS:
                raise ValidationError("A GL export file is immutable; only the GL's answer can be recorded.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("A GL export is a record of what was sent and cannot be deleted.")
'''
wr("models.py", s)

# ---- CSV writer shared by the preview and the hand-over ---------------------------------------------
s = rd("exports.py")
start = s.index("def generate_gl_csv(")
s = s[:start] + '''def write_gl_csv(pool, batches):
    """CSV text and the number of data rows for the given batches (in the order given)."""
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(GL_CSV_COLUMNS)
    rows = 0
    for batch in batches:
        posted_by_email = batch.posted_by.email if batch.posted_by else ""
        for entry in batch.entries.all():
            writer.writerow(
                [
                    batch.batch_date,
                    str(batch.id),
                    str(batch.allocation_run_id),
                    entry.gl_code,
                    entry.account_name,
                    entry.entry_type,
                    entry.amount,
                    pool.code,
                    posted_by_email,
                    batch.created_at,
                ]
            )
            rows += 1
    return buffer.getvalue(), rows


def generate_gl_csv(pool, date_from=None, date_to=None):
    """
    Preview of the GL file for a pool: every "posted" batch in the range, oldest first. It records nothing; the
    controlled hand-over (stored file, no batch sent twice, the GL's answer) is apps/accounting/gl_handover.py.

    TenantScopedManager on JournalBatch.objects already restricts results to the current tenant context.
    """

    batches = (
        JournalBatch.objects.filter(pool=pool, status=JournalBatchStatus.POSTED)
        .select_related("posted_by")
        .prefetch_related("entries")
        .order_by("batch_date")
    )

    if date_from:
        batches = batches.filter(batch_date__gte=date_from)
    if date_to:
        batches = batches.filter(batch_date__lte=date_to)

    return write_gl_csv(pool, batches)[0]
'''
wr("exports.py", s)

# ---- views ------------------------------------------------------------------------------------------
s = rd("views.py")
s += '''

GL_READ_ROLES = ["finance_maker", "finance_checker", "authorized_signatory", "risk_compliance", "auditor", "pool_manager"]


class GLExportSerializer(serializers.ModelSerializer):
    pool_code = serializers.CharField(source="pool.code", read_only=True)
    exported_by_name = serializers.CharField(source="exported_by.full_name", read_only=True, default=None)
    decided_by_name = serializers.CharField(source="decided_by.full_name", read_only=True, default=None)
    batch_count = serializers.SerializerMethodField()

    class Meta:
        model = GLExport
        fields = (
            "id", "pool", "pool_code", "date_from", "date_to", "row_count", "total_debit", "total_credit",
            "content_hash", "status", "exported_by", "exported_by_name", "gl_reference", "decided_by",
            "decided_by_name", "decided_at", "decision_note", "batch_count", "created_at",
        )
        read_only_fields = fields

    def get_batch_count(self, obj):
        return obj.batches.count()


class GLExportViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """
    Controlled hand-over to the enterprise GL. A finance maker generates an export of the batches not yet sent; a
    different finance checker records the GL's answer (confirmed with its reference, or rejected with a reason).
    """

    serializer_class = GLExportSerializer
    pagination_class = StandardPagination

    def get_queryset(self):
        queryset = GLExport.objects.select_related("pool", "exported_by", "decided_by")
        pool_id = self.request.query_params.get("pool")
        if pool_id:
            queryset = queryset.filter(pool_id=pool_id)
        return queryset

    def get_permissions(self):
        if self.action == "create":
            return [IsAuthenticated(), IsFinanceMaker()]
        if self.action in ("confirm", "reject"):
            return [IsAuthenticated(), IsFinanceChecker()]
        return [IsAuthenticated(), HasAnyRole(GL_READ_ROLES)()]

    def create(self, request, *args, **kwargs):
        from .gl_handover import create_export

        pool = get_object_or_404(Pool, id=request.data.get("pool"))
        export = create_export(
            pool=pool, date_from=request.data.get("date_from") or None, date_to=request.data.get("date_to") or None,
            user=request.user, request=request,
        )
        return Response(self.get_serializer(export).data, status=201)

    @action(detail=True, methods=["get"])
    def download(self, request, pk=None):
        export = self.get_object()
        log_action(
            tenant=export.tenant, actor=request.user, action="gl_export_downloaded", model_name="GLExport",
            object_id=str(export.id), request=request,
        )
        response = HttpResponse(export.content, content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="gl_export_{export.pool.code}_{export.id}.csv"'
        response["X-Content-SHA256"] = export.content_hash
        return response

    @action(detail=True, methods=["post"])
    def confirm(self, request, pk=None):
        from .gl_handover import confirm_export

        return Response(self.get_serializer(confirm_export(self.get_object(), request.user, request.data.get("gl_reference"), request)).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        from .gl_handover import reject_export

        return Response(self.get_serializer(reject_export(self.get_object(), request.user, request.data.get("reason"), request)).data)

    @action(detail=False, methods=["get"], url_path="pending-batches")
    def pending(self, request):
        """How many posted batches of the pool have not been sent to the GL yet."""
        from .gl_handover import pending_batches

        pool = get_object_or_404(Pool, id=request.query_params.get("pool"))
        return Response({"pool": pool.code, "pending_batches": pending_batches(pool).count()})


@api_view(["GET"])
@permission_classes([IsAuthenticated, HasAnyRole(GL_READ_ROLES)])
def trial_balance_view(request):
    """Trial balance of a pool's posted journals up to `as_of` (default: everything)."""
    from .gl_handover import trial_balance

    pool = get_object_or_404(Pool, id=request.query_params.get("pool"))
    return Response(trial_balance(pool, request.query_params.get("as_of") or None))
'''
wr("views.py", s)

s = rd("urls.py")
s = sub(s, "    gl_export,\n)", "    GLExportViewSet,\n    gl_export,\n    trial_balance_view,\n)")
s = sub(s, 'router.register("reconciliations", ReconciliationBatchViewSet, basename="reconciliation")\n',
        'router.register("reconciliations", ReconciliationBatchViewSet, basename="reconciliation")\nrouter.register("gl-exports", GLExportViewSet, basename="gl-export")\n')
s = sub(s, '    path("journal-batches/gl-export/", gl_export, name="journal-batch-gl-export"),\n',
        '    path("journal-batches/gl-export/", gl_export, name="journal-batch-gl-export"),\n    path("trial-balance/", trial_balance_view, name="trial-balance"),\n')
wr("urls.py", s)
print("ok")
