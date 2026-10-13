ROOT = "backend/apps/"


def rd(p):
    return open(ROOT + p, encoding="utf-8").read()


def wr(p, s):
    open(ROOT + p, "w", encoding="utf-8").write(s)


def sub(s, old, new):
    assert old in s, old[:90]
    return s.replace(old, new, 1)


# ---- model: immutable revision history ---------------------------------------------------------
s = rd("products/models.py")
s = sub(s, '''    def __str__(self):
        return f"{self.name} v{self.version} ({self.code})"


class QuorumVoteDecision''', '''    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        RulePackRevision.record(self)

    def __str__(self):
        return f"{self.name} v{self.version} ({self.code})"


class RulePackRevision(TenantScopedModel):
    """
    One immutable row for every distinct content a rule pack has had (BRD 11: a signed run references immutable
    rule-pack versions). A run seals the hash of the pack it used; this history lets anyone read what that content was.
    """

    pack = models.ForeignKey(JurisdictionRulePack, on_delete=models.PROTECT, related_name="revisions")
    revision = models.PositiveIntegerField()
    content_hash = models.CharField(max_length=64)
    content = models.JSONField()

    class Meta:
        ordering = ["-revision"]
        constraints = [models.UniqueConstraint(fields=["pack", "revision"], name="unique_rulepack_revision")]

    @staticmethod
    def content_of(pack):
        effective = pack.effective_date
        return {
            "version": pack.version,
            "effective_date": effective.isoformat() if hasattr(effective, "isoformat") else str(effective),
            "is_active": bool(pack.is_active),
            "is_default": bool(pack.is_default),
            "rules_config": pack.rules_config or {},
        }

    @staticmethod
    def hash_of(content):
        import hashlib
        import json

        return hashlib.sha256(json.dumps(content, sort_keys=True, default=str).encode("utf-8")).hexdigest()

    @classmethod
    def record(cls, pack):
        content = cls.content_of(pack)
        digest = cls.hash_of(content)
        last = cls._base_manager.filter(pack=pack).order_by("-revision").first()
        if last is not None and last.content_hash == digest:
            return last
        return cls._base_manager.create(
            tenant_id=pack.tenant_id, pack=pack, revision=(last.revision + 1) if last else 1,
            content_hash=digest, content=content,
        )

    def save(self, *args, **kwargs):
        if not self._state.adding:
            from django.core.exceptions import ValidationError

            raise ValidationError("A rule pack revision is a historical record and cannot be changed.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        from django.core.exceptions import ValidationError

        raise ValidationError("A rule pack revision is a historical record and cannot be deleted.")


class QuorumVoteDecision''')
wr("products/models.py", s)

# ---- snapshot helpers -----------------------------------------------------------------------------
s = rd("pools/config_snapshot.py")
s = sub(s, "def build_pool_snapshot(pool,", '''def rule_pack_snapshot(pool):
    """What a run seals about the rule pack that governed it: identity, revision, content hash and the rules themselves."""
    from apps.products.models import RulePackRevision

    pack = bound_rule_pack(pool)
    if pack is None:
        return None
    revision = RulePackRevision.record(pack)
    return {
        "id": str(pack.id),
        "code": pack.code,
        "version": pack.version,
        "revision": revision.revision,
        "content_hash": revision.content_hash,
        "rules_config": pack.rules_config or {},
    }


def assert_rule_pack_unchanged(run, pool):
    """
    A run was calculated under a specific rule pack content. If the pack changed since (an approved change in between),
    the figures no longer reflect the rules in force: the run is refused and must be re-run. Runs created before the
    snapshot existed carry none and are not checked.
    """
    from rest_framework.exceptions import ValidationError

    from apps.products.models import RulePackRevision

    sealed = (run.config_snapshot or {}).get("rule_pack")
    if not sealed:
        return
    pack = bound_rule_pack(pool)
    current = RulePackRevision.hash_of(RulePackRevision.content_of(pack)) if pack else None
    if current != sealed.get("content_hash"):
        raise ValidationError(
            f"The jurisdiction rule pack changed after this run was calculated (it used revision {sealed.get('revision')} "
            f"of {sealed.get('code')}). Reject the run and calculate it again under the rules now in force."
        )


def build_pool_snapshot(pool,''')
wr("pools/config_snapshot.py", s)

# ---- engine and distribution seal the pack -----------------------------------------------------------
s = rd("allocation/engine.py")
s = sub(s, '''        "total_daily_funds": str(_round(total_daily_funds)),''', '''        "rule_pack": rule_pack_snapshot(pool),
        "total_daily_funds": str(_round(total_daily_funds)),''')
s = sub(s, "from apps.participants.models import ParticipantAccount\n",
        "from apps.participants.models import ParticipantAccount\nfrom apps.pools.config_snapshot import rule_pack_snapshot\n")
wr("allocation/engine.py", s)

s = rd("investments/distribution.py")
s = sub(s, '''        "config_snapshot": {
            "contract_type": contract_type,''', '''        "config_snapshot": {
            "rule_pack": rule_pack_snapshot(pool),
            "contract_type": contract_type,''')
i = s.index("\nfrom ")
s = s[:i] + "\nfrom apps.pools.config_snapshot import rule_pack_snapshot" + s[i:]
wr("investments/distribution.py", s)

# ---- views: refuse a stale run at check and release ---------------------------------------------------
s = rd("allocation/views.py")
s = sub(s, '''        # The checker verifies exactly what the maker sealed.
        if not run.calculation_hash or compute_run_hash(run) != run.calculation_hash:''', '''        assert_rule_pack_unchanged(run, run.pool)
        # The checker verifies exactly what the maker sealed.
        if not run.calculation_hash or compute_run_hash(run) != run.calculation_hash:''')
s = sub(s, '''        previous_status = run.status

        # The checker signs exactly''', '''        previous_status = run.status
        assert_rule_pack_unchanged(run, run.pool)

        # The checker signs exactly''')
s = sub(s, "from apps.pools.exception_gate import assert_no_open_serious_exception\n",
        "from apps.pools.config_snapshot import assert_rule_pack_unchanged\nfrom apps.pools.exception_gate import assert_no_open_serious_exception\n")
wr("allocation/views.py", s)

s = rd("investments/distribution_views.py")
s = sub(s, '''        try:
            validate_maker_checker(maker_user=run.created_by, checker_user=request.user)
        except DjangoValidationError as exc:
            raise ValidationError(exc.message) from exc
        if not run.calculation_hash or compute_run_hash(run) != run.calculation_hash:
            raise ValidationError(
                "Calculation hash mismatch: the run no longer matches the figures it was sealed with. "
                "Reject it and re-run the distribution."
            )
        run.status = DistributionRunStatus.CHECKED''', '''        try:
            validate_maker_checker(maker_user=run.created_by, checker_user=request.user)
        except DjangoValidationError as exc:
            raise ValidationError(exc.message) from exc
        assert_rule_pack_unchanged(run, run.pool)
        if not run.calculation_hash or compute_run_hash(run) != run.calculation_hash:
            raise ValidationError(
                "Calculation hash mismatch: the run no longer matches the figures it was sealed with. "
                "Reject it and re-run the distribution."
            )
        run.status = DistributionRunStatus.CHECKED''')
s = sub(s, '''        if not run.is_restatement:
            assert_period_open(run.pool, run.period_end, what="a profit distribution", start=run.period_start)
        case_ids''', '''        assert_rule_pack_unchanged(run, run.pool)
        if not run.is_restatement:
            assert_period_open(run.pool, run.period_end, what="a profit distribution", start=run.period_start)
        case_ids''')
s = sub(s, "from apps.pools.exception_gate import assert_no_open_serious_exception\n",
        "from apps.pools.config_snapshot import assert_rule_pack_unchanged\nfrom apps.pools.exception_gate import assert_no_open_serious_exception\n")
wr("investments/distribution_views.py", s)

# ---- endpoint to read the history -----------------------------------------------------------------------
s = rd("products/views.py")
s = sub(s, '''    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):''', '''    @action(detail=True, methods=["get"])
    def revisions(self, request, pk=None):
        """The pack's history: every distinct content it has had. Read-only."""
        from .models import RulePackRevision

        pack = self.get_object()
        rows = RulePackRevision._base_manager.filter(pack=pack).order_by("-revision")
        return Response([
            {"revision": r.revision, "content_hash": r.content_hash, "content": r.content, "created_at": r.created_at}
            for r in rows
        ])

    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):''')
wr("products/views.py", s)
print("ok")
