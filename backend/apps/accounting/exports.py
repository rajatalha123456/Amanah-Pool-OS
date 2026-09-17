import csv
import io

from .models import JournalBatch, JournalBatchStatus

GL_CSV_COLUMNS = [
    "batch_date",
    "journal_batch_id",
    "allocation_run_id",
    "account_name",
    "entry_type",
    "amount",
    "pool_code",
    "posted_by",
    "posted_at",
]


def generate_gl_csv(pool, date_from=None, date_to=None):
    """
    Flattens JournalBatch + nested JournalEntry records for a pool into a
    standard GL export CSV string. Only "posted" batches are included.
    Rows are sorted by batch_date (oldest first).

    TenantScopedManager on JournalBatch.objects already restricts results
    to the current tenant context, so no explicit tenant filter is needed
    here.
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

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(GL_CSV_COLUMNS)

    for batch in batches:
        posted_by_email = batch.posted_by.email if batch.posted_by else ""
        for entry in batch.entries.all():
            writer.writerow(
                [
                    batch.batch_date,
                    str(batch.id),
                    str(batch.allocation_run_id),
                    entry.account_name,
                    entry.entry_type,
                    entry.amount,
                    pool.code,
                    posted_by_email,
                    batch.created_at,
                ]
            )

    return buffer.getvalue()
