import csv
import io

from .models import JournalBatch, JournalBatchStatus

GL_CSV_COLUMNS = [
    "batch_date",
    "journal_batch_id",
    "allocation_run_id",
    "gl_code",
    "account_name",
    "entry_type",
    "amount",
    "pool_code",
    "posted_by",
    "posted_at",
]


def write_gl_csv(pool, batches):
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
