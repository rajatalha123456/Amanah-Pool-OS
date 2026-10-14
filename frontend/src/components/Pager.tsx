import { Button } from "./Button"

interface PagerProps {
  page: number
  pageSize: number
  count: number
  onChange: (page: number) => void
  disabled?: boolean
}

/** Previous / next controls for the server-paged lists (rows X-Y of N). Renders nothing when everything fits on one page. */
export function Pager({ page, pageSize, count, onChange, disabled }: PagerProps) {
  const pages = Math.max(1, Math.ceil(count / pageSize))
  if (count <= pageSize) return null
  const first = (page - 1) * pageSize + 1
  const last = Math.min(page * pageSize, count)
  return (
    <div className="mt-3 flex items-center justify-between gap-3 text-xs text-ink-secondary">
      <span>
        Rows {first.toLocaleString()}-{last.toLocaleString()} of {count.toLocaleString()} · page {page} of {pages}
      </span>
      <div className="flex gap-2">
        <Button size="sm" variant="secondary" disabled={disabled || page <= 1} onClick={() => onChange(page - 1)}>
          Previous
        </Button>
        <Button size="sm" variant="secondary" disabled={disabled || page >= pages} onClick={() => onChange(page + 1)}>
          Next
        </Button>
      </div>
    </div>
  )
}
