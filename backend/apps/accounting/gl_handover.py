"""
Hand-over of posted journal batches to the enterprise general ledger, and the trial balance (BRD 10 and 12).

A maker generates an export of the batches not yet sent; the file is stored with its hash. A different finance checker
records the GL's answer: confirmed (with the GL's posting reference) or rejected (with a reason, which frees the batches
for a new export). No batch is sent twice while an export holding it is generated or confirmed.
"""

import hashlib
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.core.audit import log_action

from .exports import write_gl_csv
from .models import GLExport, GLExportStatus, JournalBatch, JournalBatchStatus, JournalEntry, JournalEntryType


def pending_batches(pool, date_from=None, date_to=None):
    """Posted batches of the pool, in the range, that are not in a generated or confirmed export."""
    batches = JournalBatch.objects.filter(pool=pool, status=JournalBatchStatus.POSTED).exclude(
        gl_exports__status__in=[GLExportStatus.GENERATED, GLExportStatus.CONFIRMED]
    )
    if date_from:
        batches = batches.filter(batch_date__gte=date_from)
    if date_to:
        batches = batches.filter(batch_date__lte=date_to)
    return batches.order_by("batch_date", "created_at")


def create_export(*, pool, date_from, date_to, user, request=None):
    with transaction.atomic():
        # Lock the candidate batches so that two makers cannot export the same ones at the same moment.
        batches = list(pending_batches(pool, date_from, date_to).select_for_update())
        if not batches:
            raise ValidationError("Nothing to export: every posted batch in this range was already sent to the GL.")
        content, row_count = write_gl_csv(pool, batches)
        total_debit = sum((Decimal(b.total_debit) for b in batches), Decimal("0"))
        total_credit = sum((Decimal(b.total_credit) for b in batches), Decimal("0"))
        export = GLExport.objects.create(
            tenant=pool.tenant, pool=pool, date_from=date_from or None, date_to=date_to or None,
            row_count=row_count, total_debit=total_debit, total_credit=total_credit, content=content,
            content_hash=hashlib.sha256(content.encode("utf-8")).hexdigest(), exported_by=user,
        )
        export.batches.set(batches)
    log_action(
        tenant=pool.tenant, actor=user, action="gl_export_generated", model_name="GLExport", object_id=str(export.id),
        changes={"pool": pool.code, "batches": len(batches), "rows": row_count, "content_hash": export.content_hash},
        request=request,
    )
    return export


def _decide(export, user, status, *, gl_reference="", note="", request=None):
    if export.status != GLExportStatus.GENERATED:
        raise ValidationError(f"This export is already {export.status}.")
    if export.exported_by_id == user.id:
        raise ValidationError("The GL's answer must be recorded by a different person than the one who generated the export.")
    export.status = status
    export.gl_reference = gl_reference
    export.decision_note = note
    export.decided_by = user
    export.decided_at = timezone.now()
    export.save(update_fields=["status", "gl_reference", "decision_note", "decided_by", "decided_at", "updated_at"])
    log_action(
        tenant=export.tenant, actor=user, action=f"gl_export_{status}", model_name="GLExport", object_id=str(export.id),
        changes={"gl_reference": gl_reference}, reason=note or None, request=request,
    )
    return export


def confirm_export(export, user, gl_reference, request=None):
    gl_reference = (gl_reference or "").strip()
    if not gl_reference:
        raise ValidationError({"gl_reference": ["The GL's posting reference is required."]})
    return _decide(export, user, GLExportStatus.CONFIRMED, gl_reference=gl_reference, request=request)


def reject_export(export, user, reason, request=None):
    reason = (reason or "").strip()
    if not reason:
        raise ValidationError({"reason": ["Say why the GL rejected the file."]})
    return _decide(export, user, GLExportStatus.REJECTED, note=reason, request=request)


def trial_balance(pool, as_of=None):
    """Debits and credits per account from every posted journal of the pool up to `as_of`."""
    entries = JournalEntry.objects.filter(batch__pool=pool, batch__status=JournalBatchStatus.POSTED)
    if as_of:
        entries = entries.filter(batch__batch_date__lte=as_of)
    rows = {}
    for row in entries.values("gl_code", "account_name", "entry_type").annotate(total=Sum("amount")):
        key = (row["gl_code"], row["account_name"])
        line = rows.setdefault(
            key, {"gl_code": row["gl_code"], "account_name": row["account_name"], "debit": Decimal("0"), "credit": Decimal("0")}
        )
        line["debit" if row["entry_type"] == JournalEntryType.DEBIT else "credit"] += row["total"]
    lines = sorted(rows.values(), key=lambda r: (r["gl_code"] or "~", r["account_name"]))
    for line in lines:
        line["balance"] = line["debit"] - line["credit"]
    total_debit = sum((line["debit"] for line in lines), Decimal("0"))
    total_credit = sum((line["credit"] for line in lines), Decimal("0"))
    return {
        "pool": pool.code,
        "as_of": str(as_of) if as_of else None,
        "lines": lines,
        "total_debit": total_debit,
        "total_credit": total_credit,
        "balanced": total_debit == total_credit,
    }
