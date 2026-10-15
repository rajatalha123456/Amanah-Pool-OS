ROOT = "backend/apps/accounting/"


def edit(path, pairs):
    s = open(ROOT + path, encoding="utf-8").read()
    for old, new in pairs:
        assert old in s, (path, old[:100])
        s = s.replace(old, new, 1)
    open(ROOT + path, "w", encoding="utf-8").write(s)


edit("gl_handover.py", [
    ('''    with transaction.atomic():
        # Lock the candidate batches so that two makers cannot export the same ones at the same moment.
        batches = list(pending_batches(pool, date_from, date_to).select_for_update())''',
     '''    with transaction.atomic():
        # One export of a pool at a time. Locking the batches alone is not enough: whether a batch was already sent is
        # decided by another table, which the database does not re-check after waiting for a row lock. Locking the pool
        # serialises exports, and the "not sent yet" query below then runs after the first export has committed.
        Pool._base_manager.select_for_update().get(pk=pool.pk)
        batches = list(pending_batches(pool, date_from, date_to).select_for_update())'''),
    ("from apps.core.audit import log_action\n", "from apps.core.audit import log_action\nfrom apps.pools.models import Pool\n"),
    ('''def _decide(export, user, status, *, gl_reference="", note="", request=None):
    if export.status != GLExportStatus.GENERATED:''', '''def _decide(export, user, status, *, gl_reference="", note="", request=None):
    # Re-read under a row lock: two checkers answering the same export at once must not both succeed.
    export = GLExport.objects.select_for_update().get(pk=export.pk) if transaction.get_connection().in_atomic_block else export
    if export.status != GLExportStatus.GENERATED:'''),
])
print("gl ok")

s = open(ROOT + "suspense.py", encoding="utf-8").read()
# lock the item at the start of every decision, inside one transaction
for name in ("approve_open", "reject_open", "propose_clear", "approve_clear", "reject_clear"):
    marker = f"def {name}("
    i = s.index(marker)
    j = s.index("\n", i) + 1
    s = s[:j] + '    item = _locked(item)\n' + s[j:]
helper = '''def _locked(item):
    """The item as it is now, row-locked, so that two people deciding it at once cannot both succeed."""
    return SuspenseItem.objects.select_for_update().get(pk=item.pk)


'''
s = s.replace("def _different(", helper + "def _different(", 1)
# the decisions are atomic units: wrap the public functions
for name in ("approve_open", "reject_open", "propose_clear", "approve_clear", "reject_clear"):
    s = s.replace(f"def {name}(", f"@transaction.atomic\ndef {name}(", 1)
open(ROOT + "suspense.py", "w", encoding="utf-8").write(s)
print("suspense ok")
