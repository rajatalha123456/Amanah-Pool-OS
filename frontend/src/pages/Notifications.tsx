import { useCallback, useEffect, useState } from "react"
import { useNavigate } from "react-router-dom"
import { Badge } from "../components/Badge"
import { Button } from "../components/Button"
import { Card } from "../components/Card"
import { PageHeader } from "../components/PageHeader"
import { Spinner } from "../components/Spinner"
import { extractErrorMessage } from "../api/errors"
import {
  fetchNotifications,
  markAllNotificationsRead,
  markNotificationRead,
  type AppNotification,
} from "../api/notifications"
import type { BadgeVariant } from "../types"

const CATEGORY: Record<AppNotification["category"], { label: string; variant: BadgeVariant }> = {
  approval_required: { label: "Approval required", variant: "gold" },
  approval_outcome: { label: "Approval outcome", variant: "emerald" },
  arrears_reminder: { label: "Arrears", variant: "navy" },
  economics_change: { label: "Economics change", variant: "gold" },
  system: { label: "System", variant: "neutral" },
}

/** BRD Foundation screen 4: Notifications. */
export function Notifications() {
  const navigate = useNavigate()
  const [items, setItems] = useState<AppNotification[]>([])
  const [onlyUnread, setOnlyUnread] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")

  const load = useCallback(async () => {
    try {
      setItems(await fetchNotifications({ unread: onlyUnread }))
      setError("")
    } catch (err) {
      setError(extractErrorMessage(err, "Unable to load notifications."))
    } finally {
      setLoading(false)
    }
  }, [onlyUnread])

  useEffect(() => {
    void load()
  }, [load])

  async function open(item: AppNotification) {
    if (!item.is_read) await markNotificationRead(item.id)
    if (item.link) navigate(item.link)
    else void load()
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Notifications"
        subtitle="Approvals waiting for you, outcomes of your submissions, arrears and economics-change notices"
        actions={
          <div className="flex items-center gap-3">
            <label className="flex items-center gap-2 text-xs text-ink-secondary">
              <input type="checkbox" checked={onlyUnread} onChange={(e) => setOnlyUnread(e.target.checked)} />
              Unread only
            </label>
            <Button
              variant="secondary"
              onClick={async () => {
                await markAllNotificationsRead()
                void load()
              }}
            >
              Mark all read
            </Button>
          </div>
        }
      />
      {error && <p className="text-sm text-red-400">{error}</p>}
      <Card title={`Inbox (${items.length})`}>
        {loading ? (
          <div className="flex items-center gap-2 py-6 text-ink-secondary">
            <Spinner /> <span className="text-sm">Loading...</span>
          </div>
        ) : items.length === 0 ? (
          <p className="text-sm text-ink-secondary">Nothing here.</p>
        ) : (
          <ul className="divide-y divide-white/5">
            {items.map((item) => (
              <li key={item.id}>
                <button
                  type="button"
                  onClick={() => void open(item)}
                  className="flex w-full items-start gap-3 py-3 text-left hover:bg-white/5"
                >
                  <span className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${item.is_read ? "bg-transparent" : "bg-emerald-400"}`} />
                  <span className="flex-1">
                    <span className="flex flex-wrap items-center gap-2">
                      <span className={`text-sm ${item.is_read ? "text-ink-secondary" : "font-semibold text-ink-primary"}`}>
                        {item.title}
                      </span>
                      <Badge variant={CATEGORY[item.category].variant}>{CATEGORY[item.category].label}</Badge>
                    </span>
                    {item.body && <span className="mt-0.5 block whitespace-pre-line text-xs text-ink-secondary">{item.body}</span>}
                    <span className="mt-0.5 block text-[10px] text-ink-muted">{new Date(item.created_at).toLocaleString()}</span>
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  )
}
