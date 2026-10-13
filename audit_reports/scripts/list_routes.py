"""Lists every URL pattern with the view and its permission classes. Read-only.
Run: cd backend && python manage.py shell < ../audit_reports/scripts/list_routes.py
"""
from django.urls import get_resolver

rows = []


def walk(resolver, prefix=""):
    for entry in resolver.url_patterns:
        if hasattr(entry, "url_patterns"):
            walk(entry, prefix + str(entry.pattern))
            continue
        route = (prefix + str(entry.pattern)).replace("^", "").replace("$", "")
        if not route.startswith("api") or "format" in route:
            continue
        cb = entry.callback
        cls = getattr(cb, "cls", None) or getattr(cb, "view_class", None)
        actions = getattr(cb, "actions", None) or {}
        name = cls.__name__ if cls else cb.__name__
        perms = ",".join(p.__name__ for p in getattr(cls, "permission_classes", []) or []) if cls else ""
        methods = ",".join(m.upper() for m in actions) if actions else ""
        rows.append(f"{route}\t{methods}\t{name}\t{perms}")


walk(get_resolver())
with open("../audit_reports/evidence/api_routes.tsv", "w", encoding="utf-8") as fh:
    fh.write("route\tmethods\tview\tpermission_classes\n" + "\n".join(sorted(set(rows))))
print(len(set(rows)))
