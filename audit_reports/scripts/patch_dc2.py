ROOT = "backend/apps/"


def rd(p):
    return open(ROOT + p, encoding="utf-8").read()


def wr(p, s):
    open(ROOT + p, "w", encoding="utf-8").write(s)


def sub(s, old, new):
    assert old in s, old[:90]
    return s.replace(old, new, 1)


s = rd("participants/seed_ledger.py")
block_start = s.index("    # Daily closes for July and August were signed")
block_end = s.index("    # Allocation runs through the real workflow.")
block = s[block_start:block_end]
s = s[:block_start] + s[block_end:]
# the block goes after the events are posted (a signed day refuses new events), before the runs are submitted
anchor = "    def submit(run_id):"
s = sub(s, anchor, block + anchor)
# the late July accrual arrives after sign-off: the core system records it directly (a real post would be refused)
old = '''    post_event(INCOME, "Financing Profit", "12500.00", date(2026, 7, 31), "Late CBS asset accrual adjustment")'''
new = '''    # (A signed day refuses a normal post, so the demo records it as the core system would: already posted.)
    IncomeExpenseEvent.objects.create(
        tenant=tenant, pool=pool, event_type=INCOME, category="Financing Profit", amount=Decimal("12500.00"),
        event_date=date(2026, 7, 31), description="Late CBS asset accrual adjustment", created_by=maker,
        status="posted", posted_by=checker, posted_at=timezone.now(),
    )'''
s = sub(s, old, new)
wr("participants/seed_ledger.py", s)
print("ok")
