"""
Benchmark of the allocation engine at a given size (BRD section 14 performance: "million-account horizontal scaling").

It builds a throw-away tenant with N participant accounts and D days of balances, times `calculate_allocation`, records the
peak Python memory, and deletes the tenant again. Nothing outside the throw-away tenant is touched.

    python manage.py benchmark_allocation --accounts 10000 --days 30
"""

import time
import tracemalloc
import uuid
from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError

from apps.allocation.engine import calculate_allocation
from apps.allocation.models import PSRStatus, ProfitSharingRatio, WeightageBand, WeightageBandStatus
from apps.core.context import set_current_tenant
from apps.participants.models import Participant, ParticipantAccount
from apps.pools.models import DailyBalance, DailyBalanceStatus, Pool
from apps.products.models import ContractTemplate, Product
from apps.tenants.models import Tenant


class Command(BaseCommand):
    help = "Times the allocation engine on synthetic data in a throw-away tenant (removed afterwards)."

    def add_arguments(self, parser):
        parser.add_argument("--accounts", type=int, default=5000)
        parser.add_argument("--days", type=int, default=30)
        parser.add_argument("--keep", action="store_true", help="Keep the throw-away tenant (default: delete it).")
        parser.add_argument("--profile", action="store_true", help="Print the 15 most expensive calls.")

    def handle(self, *args, **options):
        accounts, days = options["accounts"], options["days"]
        if accounts < 1 or not 1 <= days <= 366:
            raise CommandError("Use at least one account and between 1 and 366 days.")
        code = f"BENCH-{uuid.uuid4().hex[:8]}"
        tenant = Tenant.objects.create(name="Benchmark (temporary)", code=code, data_residency="PK")
        set_current_tenant(tenant)
        try:
            start = date(2026, 1, 1)
            end = start + timedelta(days=days - 1)
            contract = ContractTemplate.objects.create(
                tenant=tenant, name="C", contract_type="mudarabah_unrestricted", version="1", clauses={}
            )
            product = Product.objects.create(tenant=tenant, name="P", code="P", operating_model="bank_pool", contract_template=contract)
            pool = Pool.objects.create(tenant=tenant, name="Bench pool", code="BENCH", product=product, effective_date=start)
            WeightageBand.objects.create(
                tenant=tenant, pool=pool, participant_class="retail", weightage=Decimal("1.00"), effective_from=start,
                status=WeightageBandStatus.APPROVED,
            )
            ProfitSharingRatio.objects.create(
                tenant=tenant, pool=pool, depositor_share=Decimal("70.00"), mudarib_share=Decimal("30.00"), effective_from=start,
                status=PSRStatus.APPROVED,
            )
            self.stdout.write(f"Creating {accounts} accounts and {accounts * days} balance rows...")
            t0 = time.perf_counter()
            participants = Participant.objects.bulk_create(
                [Participant(tenant=tenant, reference=f"B-{i}", full_name=f"Bench {i}", participant_class="retail") for i in range(accounts)],
                batch_size=5000,
            )
            account_rows = ParticipantAccount.objects.bulk_create(
                [ParticipantAccount(tenant=tenant, participant=p, pool=pool, account_number=f"BA-{i}", opened_date=start)
                 for i, p in enumerate(participants)],
                batch_size=5000,
            )
            day_list = [start + timedelta(days=d) for d in range(days)]
            batch = []
            for i, account in enumerate(account_rows):
                base = Decimal(1000 + (i % 97) * 10)
                for d in day_list:
                    batch.append(DailyBalance(
                        tenant=tenant, pool=pool, account=account, participant_class="retail", value_date=d,
                        balance_amount=base, status=DailyBalanceStatus.VALIDATED,
                    ))
                if len(batch) >= 20000:
                    DailyBalance.objects.bulk_create(batch)
                    batch = []
            if batch:
                DailyBalance.objects.bulk_create(batch)
            self.stdout.write(f"  data ready in {time.perf_counter() - t0:.1f}s")

            tracemalloc.start()
            t1 = time.perf_counter()
            if options["profile"]:
                import cProfile
                import io
                import pstats

                profiler = cProfile.Profile()
                profiler.enable()
                result = calculate_allocation(pool, end, Decimal("1000000.00"), Decimal("50000.00"), period_start=start)
                profiler.disable()
                out = io.StringIO()
                pstats.Stats(profiler, stream=out).sort_stats("cumulative").print_stats(15)
                self.stdout.write(out.getvalue())
            else:
                result = calculate_allocation(pool, end, Decimal("1000000.00"), Decimal("50000.00"), period_start=start)
            elapsed = time.perf_counter() - t1
            _, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            self.stdout.write(self.style.SUCCESS(
                f"calculate_allocation: {accounts} accounts x {days} days = {accounts * days} balance rows, "
                f"{len(result['lines'])} lines in {elapsed:.2f}s, peak Python memory {peak / 1_048_576:.0f} MB"
            ))
            self.stdout.write(f"  throughput {accounts * days / elapsed:,.0f} balance rows/s")
        finally:
            if not options["keep"]:
                remove_tenant_data(tenant)
                self.stdout.write(f"Throw-away tenant {code} removed.")
            set_current_tenant(None)


def remove_tenant_data(tenant):
    """Deletes a throw-away tenant: the protected relations must go child first."""
    for model in (DailyBalance, ParticipantAccount, Participant, WeightageBand, ProfitSharingRatio, Pool, Product, ContractTemplate):
        model._base_manager.filter(tenant=tenant).delete()
    tenant.delete()
