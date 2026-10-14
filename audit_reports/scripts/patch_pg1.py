ROOT = "backend/apps/"


def rd(p):
    return open(ROOT + p, encoding="utf-8").read()


def wr(p, s):
    open(ROOT + p, "w", encoding="utf-8").write(s)


def sub(s, old, new):
    assert old in s, old[:90]
    return s.replace(old, new, 1)


open(ROOT + "core/pagination.py", "w", encoding="utf-8").write('''"""
Pagination for the lists that grow with the business (BRD 14: P95 under 2 s, million-account scale).

Lists of configuration (products, pools, rule packs, ...) stay small and are returned whole. The lists below grow with
every account, day, event and action, so they are always paged: `?page=N&page_size=M` (default 50, at most 500).
Response: {"count": total rows, "next": url | null, "previous": url | null, "results": [...]}.
"""

from rest_framework.pagination import PageNumberPagination


class StandardPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 500
''')

PAG = "from apps.core.pagination import StandardPagination\n"

# audit log
s = rd("core/views.py")
s = sub(s, '''    serializer_class = AuditLogSerializer
    permission_classes = [IsAuthenticated, HasAnyRole(["auditor", "risk_compliance", "platform_super_admin"])]
''', '''    serializer_class = AuditLogSerializer
    permission_classes = [IsAuthenticated, HasAnyRole(["auditor", "risk_compliance", "platform_super_admin"])]
    pagination_class = StandardPagination
''')
s = sub(s, "from .models import AuditLog\n", PAG + "\nfrom .models import AuditLog\n")
wr("core/views.py", s)

# participants and accounts
s = rd("participants/views.py")
s = sub(s, '''class ParticipantViewSet(viewsets.ModelViewSet):
    serializer_class = ParticipantSerializer
''', '''class ParticipantViewSet(viewsets.ModelViewSet):
    serializer_class = ParticipantSerializer
    pagination_class = StandardPagination
''')
s = sub(s, '''class ParticipantAccountViewSet(viewsets.ModelViewSet):
    serializer_class = ParticipantAccountSerializer
''', '''class ParticipantAccountViewSet(viewsets.ModelViewSet):
    serializer_class = ParticipantAccountSerializer
    pagination_class = StandardPagination
''')
i = s.index("\nfrom ")
s = s[:i] + "\n" + PAG.rstrip("\n") + s[i:]
wr("participants/views.py", s)

# notifications
s = rd("notifications/views.py")
s = sub(s, '''    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
''', '''    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination
''')
i = s.index("\nfrom ")
s = s[:i] + "\n" + PAG.rstrip("\n") + s[i:]
wr("notifications/views.py", s)

# journals and events
s = rd("accounting/views.py")
s = sub(s, '''class JournalBatchViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = JournalBatchSerializer
    permission_classes = [IsAuthenticated]
''', '''class JournalBatchViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = JournalBatchSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination
''')
s = sub(s, '''        queryset = JournalBatch.objects.all()
        pool_id = self.request.query_params.get("pool")''', '''        queryset = JournalBatch.objects.all().order_by("-batch_date", "-created_at")
        pool_id = self.request.query_params.get("pool")''')
s = sub(s, '''class IncomeExpenseEventViewSet(viewsets.ModelViewSet):
    serializer_class = IncomeExpenseEventSerializer
''', '''class IncomeExpenseEventViewSet(viewsets.ModelViewSet):
    serializer_class = IncomeExpenseEventSerializer
    pagination_class = StandardPagination
''')
s = sub(s, '''        queryset = IncomeExpenseEvent.objects.all()
        pool_id = self.request.query_params.get("pool")''', '''        queryset = IncomeExpenseEvent.objects.all().order_by("-event_date", "-created_at")
        pool_id = self.request.query_params.get("pool")''')
i = s.index("\nfrom ")
s = s[:i] + "\n" + PAG.rstrip("\n") + s[i:]
wr("accounting/views.py", s)

# daily balances
s = rd("pools/views.py")
s = sub(s, '''class DailyBalanceViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = DailyBalanceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = DailyBalance.objects.all()''', '''class DailyBalanceViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = DailyBalanceSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination

    def get_queryset(self):
        queryset = DailyBalance.objects.all().order_by("-value_date", "participant_class", "account_id")''')
i = s.index("\nfrom ")
s = s[:i] + "\n" + PAG.rstrip("\n") + s[i:]
wr("pools/views.py", s)
print("ok")
