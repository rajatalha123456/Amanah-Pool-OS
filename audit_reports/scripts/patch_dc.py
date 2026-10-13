ROOT = "backend/apps/"

def rd(p): return open(ROOT + p, encoding="utf-8").read()
def wr(p, s): open(ROOT + p, "w", encoding="utf-8").write(s)
def sub(s, old, new):
    assert old in s, old[:90]
    return s.replace(old, new, 1)

s = rd("allocation/views.py")
# independent check: days must be signed (not for restatements, which re-derive a closed period under approval)
s = sub(s, '''        assert_rule_pack_unchanged(run, run.pool)
        # The checker verifies exactly what the maker sealed.''', '''        assert_rule_pack_unchanged(run, run.pool)
        if not run.is_restatement:
            assert_days_signed(run.pool, run.effective_period_start, run.value_date)
        # The checker verifies exactly what the maker sealed.''')
s = sub(s, '''        previous_status = run.status
        assert_rule_pack_unchanged(run, run.pool)
''', '''        previous_status = run.status
        assert_rule_pack_unchanged(run, run.pool)
        if not run.is_restatement:
            assert_days_signed(run.pool, run.effective_period_start, run.value_date)
''')
s = sub(s, "from apps.pools.config_snapshot import assert_rule_pack_unchanged\n", "from apps.pools.config_snapshot import assert_rule_pack_unchanged\nfrom apps.pools.daily_close import assert_days_signed, unsigned_balance_days\n")
# simulate: warn
s = sub(s, '''                "warnings": (
                    [f"{totals['pending_count']} pending income/expense event(s) in this period are not included."]
                    if totals["pending_count"]
                    else []
                ),''', '''                "warnings": (
                    [f"{totals['pending_count']} pending income/expense event(s) in this period are not included."]
                    if totals["pending_count"]
                    else []
                )
                + (
                    [f"{len(unsigned)} day(s) with balances have no signed daily close yet; the run cannot be checked until they are signed."]
                    if (unsigned := unsigned_balance_days(data["pool"], data.get("period_start") or data["value_date"], data["value_date"]))
                    else []
                ),''')
wr("allocation/views.py", s)

# seed: the daily closes of July and August were signed (demo data), September is still waiting
s = rd("participants/seed_ledger.py")
s = sub(s, '''    # Allocation runs through the real workflow.
    call = make_api_caller(tenant)
''', '''    # Daily closes for July and August were signed by an independent checker (demo data); September is still in progress.
    from apps.pools.models import DailyClose, DailyCloseStatus

    for signed_day in sorted({r.value_date for r in rows if r.value_date < date(2026, 9, 1)}):
        DailyClose.objects.create(
            tenant=tenant, pool=pool, value_date=signed_day, status=DailyCloseStatus.SIGNED,
            gates=[], notes="Demo data: signed by the seed.", prepared_by=maker, signed_by=checker,
            prepared_at=timezone.now(), signed_at=timezone.now(),
        )

    # Allocation runs through the real workflow.
    call = make_api_caller(tenant)
''')
wr("participants/seed_ledger.py", s)
print("ok")
