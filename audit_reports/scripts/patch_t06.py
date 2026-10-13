import re

ROOT = "backend/apps/"


def rd(p):
    return open(ROOT + p, encoding="utf-8").read()


def wr(p, s):
    open(ROOT + p, "w", encoding="utf-8").write(s)


def sub(s, old, new, count=1):
    assert old in s, old[:80]
    return s.replace(old, new, count)


# ---- models -----------------------------------------------------------------------------------
p = "investments/models.py"
s = rd(p)
s = sub(s, '''    PENDING_APPROVAL = "pending_approval", "Pending Approval"
    SIGNED = "signed", "Signed"
    REJECTED = "rejected", "Rejected"
    REVERSED = "reversed", "Reversed"


class InvestmentDistributionRun''', '''    PENDING_APPROVAL = "pending_approval", "Pending Approval"
    # Same ceremony as a bank-pool run (BRD 6.3): independent check -> Shariah review -> release by the signatory.
    CHECKED = "checked", "Independent Check Complete"
    SHARIAH_REVIEW = "shariah_review", "Shariah Review Complete"
    SIGNED = "signed", "Signed"
    REJECTED = "rejected", "Rejected"
    REVERSED = "reversed", "Reversed"


class InvestmentDistributionRun''')
s = sub(s, '''    checked_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(null=True, blank=True)

    _SIGNED_MUTABLE_FIELDS''', '''    checked_at = models.DateTimeField(null=True, blank=True)
    shariah_signed_off_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    shariah_signed_off_at = models.DateTimeField(null=True, blank=True)
    shariah_review_note = models.TextField(null=True, blank=True)
    released_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    released_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(null=True, blank=True)

    _SIGNED_MUTABLE_FIELDS''')
wr(p, s)

# ---- serializer -------------------------------------------------------------------------------
p = "investments/serializers.py"
s = rd(p)
s = sub(s, '''            "checked_at",
            "rejection_reason",
            "lines",''', '''            "checked_at",
            "shariah_signed_off_by",
            "shariah_signed_off_at",
            "shariah_review_note",
            "released_by",
            "released_at",
            "rejection_reason",
            "lines",''')
wr(p, s)

# ---- notifications ----------------------------------------------------------------------------
p = "notifications/events.py"
s = rd(p)
s = sub(s, "def distribution_decided(run, actor, approved, reason=\"\"):", '''def distribution_checked(run, actor):
    notify_roles(
        run.tenant, ["shariah_secretariat", "shariah_board"], category=C.APPROVAL_REQUIRED, exclude=actor,
        title=f"Profit distribution awaiting Shariah review: {run.pool.code} {run.period_start} to {run.period_end}",
        body="The independent check is complete.", link="/investments", related=("InvestmentDistributionRun", run.id),
    )


def distribution_shariah_reviewed(run, actor):
    notify_roles(
        run.tenant, ["authorized_signatory"], category=C.APPROVAL_REQUIRED, exclude=actor,
        title=f"Profit distribution awaiting final release: {run.pool.code} {run.period_start} to {run.period_end}",
        body="Independent check and Shariah review are complete.", link="/investments",
        related=("InvestmentDistributionRun", run.id),
    )


def distribution_decided(run, actor, approved, reason=""):''')
wr(p, s)

# ---- views ------------------------------------------------------------------------------------
p = "investments/distribution_views.py"
s = rd(p)
s = sub(s, "from apps.accounts.permissions import HasAnyRole, IsFinanceChecker, IsFinanceMaker",
        "from apps.accounts.permissions import HasAnyRole, IsAuthorizedSignatory, IsFinanceChecker, IsFinanceMaker")
s = sub(s, '''        if self.action in ("approve", "reject"):
            return [IsAuthenticated(), IsFinanceChecker()]
        return [IsAuthenticated()]

    def _calculate''', '''        if self.action == "check":
            return [IsAuthenticated(), IsFinanceChecker()]
        if self.action == "shariah_sign_off":
            # A review, not a ruling (BRD 3): the Secretariat or the Board. Final authority is the signatory's.
            return [IsAuthenticated(), HasAnyRole(["shariah_secretariat", "shariah_board"])()]
        if self.action == "approve":
            return [IsAuthenticated(), IsAuthorizedSignatory()]
        if self.action == "reject":
            return [IsAuthenticated(), HasAnyRole(
                ["finance_checker", "shariah_secretariat", "shariah_board", "authorized_signatory"]
            )()]
        return [IsAuthenticated()]

    def _calculate''')

start = s.index('    @action(detail=True, methods=["post"])\n    def approve(self, request, pk=None):')
end = s.index("        case_ids = _verify_negligence_state(run)")
new_head = '''    @action(detail=True, methods=["post"])
    def check(self, request, pk=None):
        """Independent check by a finance checker who did not prepare the run."""
        run = self.get_object()
        if run.status != DistributionRunStatus.PENDING_APPROVAL:
            raise ValidationError(f"Only a pending run can be checked (current status: '{run.status}').")
        try:
            validate_maker_checker(maker_user=run.created_by, checker_user=request.user)
        except DjangoValidationError as exc:
            raise ValidationError(exc.message) from exc
        if not run.calculation_hash or compute_run_hash(run) != run.calculation_hash:
            raise ValidationError(
                "Calculation hash mismatch: the run no longer matches the figures it was sealed with. "
                "Reject it and re-run the distribution."
            )
        run.status = DistributionRunStatus.CHECKED
        run.checked_by = request.user
        run.checked_at = timezone.now()
        run.save(update_fields=["status", "checked_by", "checked_at", "updated_at"])
        log_action(
            tenant=run.tenant, actor=request.user, action="independent_check", model_name="InvestmentDistributionRun",
            object_id=str(run.id), reason=request.data.get("note"), request=request,
        )
        events.distribution_checked(run, request.user)
        return Response(self.get_serializer(run).data)

    @action(detail=True, methods=["post"], url_path="shariah-sign-off")
    def shariah_sign_off(self, request, pk=None):
        run = self.get_object()
        if run.status != DistributionRunStatus.CHECKED:
            raise ValidationError(
                f"The run must have its independent check before the Shariah review (current status: '{run.status}')."
            )
        run.status = DistributionRunStatus.SHARIAH_REVIEW
        run.shariah_signed_off_by = request.user
        run.shariah_signed_off_at = timezone.now()
        run.shariah_review_note = request.data.get("note")
        run.save(update_fields=[
            "status", "shariah_signed_off_by", "shariah_signed_off_at", "shariah_review_note", "updated_at",
        ])
        log_action(
            tenant=run.tenant, actor=request.user, action="shariah_sign_off", model_name="InvestmentDistributionRun",
            object_id=str(run.id), reason=run.shariah_review_note, request=request,
        )
        events.distribution_shariah_reviewed(run, request.user)
        return Response(self.get_serializer(run).data)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        """Final release by the authorized signatory, who is neither the maker nor the independent checker."""
        run = self.get_object()
        if run.status != DistributionRunStatus.SHARIAH_REVIEW:
            raise ValidationError(
                f"Final release needs the independent check and the Shariah review first (current status: '{run.status}')."
            )
        assert_may_approve(request.user, run.tenant_id, "distribution_approve", run.distributable_amount)
        try:
            validate_maker_checker(maker_user=run.created_by, checker_user=request.user)
        except DjangoValidationError as exc:
            raise ValidationError(exc.message) from exc
        if run.checked_by_id == request.user.id:
            raise ValidationError("The final release cannot be given by the user who did the independent check.")

        if not run.calculation_hash or compute_run_hash(run) != run.calculation_hash:
            raise ValidationError(
                "Calculation hash mismatch: the run no longer matches the figures it was sealed with. "
                "Reject it and re-run the distribution."
            )
        if not run.is_restatement:
            assert_period_open(run.pool, run.period_end, what="a profit distribution", start=run.period_start)
'''
s = s[:start] + new_head + s[end:]
s = sub(s, '''            with transaction.atomic():
                reversal = None
                if run.is_restatement:''', '''            with transaction.atomic():
                # Re-read under a row lock: a concurrent second release must not pass the status check as well.
                locked = InvestmentDistributionRun.objects.select_for_update().get(pk=run.pk)
                if locked.status != DistributionRunStatus.SHARIAH_REVIEW:
                    raise ValidationError("This run was already released or changed by another request.")
                reversal = None
                if run.is_restatement:''')
s = sub(s, '''                run.checked_by = request.user
                run.checked_at = timezone.now()
                run.save(update_fields=["status", "checked_by", "checked_at", "updated_at"])
                batch = create_journal_from_distribution''', '''                run.released_by = request.user
                run.released_at = timezone.now()
                run.save(update_fields=["status", "released_by", "released_at", "updated_at"])
                batch = create_journal_from_distribution''')
s = sub(s, '''        if run.status != DistributionRunStatus.PENDING_APPROVAL:
            raise ValidationError(f"Only a pending run can be rejected (current status: '{run.status}').")''', '''        if run.status not in (
            DistributionRunStatus.PENDING_APPROVAL, DistributionRunStatus.CHECKED, DistributionRunStatus.SHARIAH_REVIEW
        ):
            raise ValidationError(f"Only a run in the approval ceremony can be rejected (current status: '{run.status}').")''')
s = sub(s, '''            status__in=[DistributionRunStatus.SIMULATED, DistributionRunStatus.PENDING_APPROVAL],''', '''            status__in=[
                DistributionRunStatus.SIMULATED, DistributionRunStatus.PENDING_APPROVAL,
                DistributionRunStatus.CHECKED, DistributionRunStatus.SHARIAH_REVIEW,
            ],''')
wr(p, s)
print("ok")
