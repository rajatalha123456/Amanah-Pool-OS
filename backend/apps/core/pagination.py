"""
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
