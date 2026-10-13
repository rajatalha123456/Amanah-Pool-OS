"""Read-only schema inventory: models, tenant scoping, constraints, indexes, cascades on financial models, money field precision.
Run: cd backend && python manage.py shell -i python -c "exec(open('../audit_reports/scripts/db_inventory.py').read())"
"""
from django.apps import apps
from django.db import models

from apps.core.models import TenantScopedModel

out = []
local = [m for m in apps.get_models() if m.__module__.startswith("apps.")]
scoped = [m for m in local if issubclass(m, TenantScopedModel)]
with_tenant_fk = [m for m in local if any(f.name == "tenant" for f in m._meta.fields)]
out.append(f"models: {len(local)}; TenantScopedModel: {len(scoped)}; with a tenant FK but not scoped: "
           f"{sorted(m.__name__ for m in with_tenant_fk if m not in scoped)}")
out.append(f"unique/check constraints: {sum(len(m._meta.constraints) for m in local)}; "
           f"explicit indexes: {sum(len(m._meta.indexes) for m in local)}")
checks = [f"{m.__name__}.{c.name}" for m in local for c in m._meta.constraints if isinstance(c, models.CheckConstraint)]
out.append(f"check constraints: {checks}")
money = []
for m in local:
    for f in m._meta.fields:
        if isinstance(f, models.FloatField):
            money.append(f"FLOAT {m.__name__}.{f.name}")
        if isinstance(f, models.DecimalField) and f.decimal_places < 2:
            money.append(f"LOW-PRECISION {m.__name__}.{f.name} ({f.max_digits},{f.decimal_places})")
out.append(f"float or low-precision numeric fields: {money}")
financial = {"AllocationRun", "AllocationLine", "JournalBatch", "JournalEntry", "DepositorStatement", "Contribution", "Payout",
             "InvestmentDistributionRun", "UnitMovement", "Subscription", "Redemption", "PurificationEntry", "IncomeExpenseEvent",
             "DailyBalance", "CapitalAccount", "ExceptionCase", "AuditLog"}
for m in local:
    if m.__name__ in financial:
        for f in m._meta.fields:
            if isinstance(f, models.ForeignKey) and f.remote_field.on_delete is models.CASCADE and f.name != "tenant":
                out.append(f"CASCADE {m.__name__}.{f.name} -> {f.related_model.__name__}")
print("\n".join(out))
open("../audit_reports/evidence/db_inventory.txt", "w", encoding="utf-8").write("\n".join(out))
