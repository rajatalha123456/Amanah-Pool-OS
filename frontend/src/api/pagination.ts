/** Server-paged list response (see backend apps/core/pagination.py: default 50 rows, at most 500). */
export interface Page<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

export const DEFAULT_PAGE_SIZE = 50

export function pageParams(page = 1, pageSize = DEFAULT_PAGE_SIZE) {
  return { page, page_size: pageSize }
}
