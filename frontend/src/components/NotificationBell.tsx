import { useCallback, useEffect, useRef, useState } from "react"
import { useNavigate } from "react-router-dom"
import {
  fetchNotifications,
  fetchUnreadCount,
  markAllNotificationsRead,
  markNotificationRead,
  type AppNotification,
} from "../api/notifications"

const POLL_MS = 60_000

/** Top-bar bell: live unread count (polled), latest unread items, click to open the related screen. */
export function NotificationBell() {
  const navigate = useNavigate()
  const [count, setCount] = useState(0)
  const [items, setItems] = useState<AppNotification[]>([])
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement | null>(null)

  const refreshCount = useCallback(async () => {
    try {
      setCount(await fetchUnreadCount())
    } catch {
      /* the bell is a convenience; a failed poll must never disturb the page */
    }
  }, [])

  useEffect(() => {
    void refreshCount()
    const timer = window.setInterval(() => void refreshCount(), POLL_MS)
    return () => window.clearInterval(timer)
  }, [refreshCount])

  useEffect(() => {
    function onClickOutside(event: MouseEvent) {
      if (ref.current && !ref.current.contains(event.target as Node)) setOpen(false)
    }
    document.addEventListener("mousedown", onClickOutside)
    return () => document.removeEventListener("mousedown", onClickOutside)
  }, [])

  async function toggle() {
    const next = !open
    setOpen(next)
    if (next) {
      try {
        setItems((await fetchNotifications({ unread: true })).slice(0, 8))
      } catch {
        setItems([])
      }
    }
  }

  async function openItem(item: AppNotification) {
    try {
      await markNotificationRead(item.id)
    } catch {
      /* navigate anyway */
    }
    setOpen(false)
    void refreshCount()
    if (item.link) navigate(item.link)
  }

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        aria-label={`Notifications${count ? `, ${count} unread` : ""}`}
        onClick={() => void toggle()}
        className="relative rounded-full p-2 text-ink-secondary transition-colors hover:bg-white/5 hover:text-ink-primary"
      >
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} className="h-5 w-5">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M14.857 17.082a23.848 23.848 0 0 0 5.454-1.31A8.967 8.967 0 0 1 18 9.75V9A6 6 0 0 0 6 9v.75a8.967 8.967 0 0 1-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 0 1-5.714 0m5.714 0a3 3 0 1 1-5.714 0"
          />
        </svg>
        {count > 0 && (
          <span className="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-red-500 px-1 text-[10px] font-semibold text-white">
            {count > 99 ? "99+" : count}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 z-50 mt-2 w-80 rounded-md border border-white/8 bg-navy-900 py-1 shadow-lg rtl:left-0 rtl:right-auto">
          <div className="flex items-center justify-between border-b border-white/8 px-3 py-2 text-xs">
            <span className="font-semibold text-ink-primary">Notifications</span>
            <button
              type="button"
              className="text-emerald-400 hover:text-emerald-300"
              onClick={async () => {
                await markAllNotificationsRead()
                setItems([])
                void refreshCount()
              }}
            >
              Mark all read
            </button>
          </div>
          {items.length === 0 ? (
            <p className="px-3 py-4 text-xs text-ink-secondary">You are all caught up.</p>
          ) : (
            items.map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => void openItem(item)}
                className="block w-full border-b border-white/5 px-3 py-2 text-left text-xs hover:bg-white/5"
              >
                <span className="block font-medium text-ink-primary">{item.title}</span>
                {item.body && <span className="mt-0.5 block line-clamp-2 text-ink-secondary">{item.body}</span>}
                <span className="mt-0.5 block text-[10px] text-ink-muted">{new Date(item.created_at).toLocaleString()}</span>
              </button>
            ))
          )}
          <button
            type="button"
            className="block w-full px-3 py-2 text-center text-xs text-emerald-400 hover:bg-white/5"
            onClick={() => {
              setOpen(false)
              navigate("/notifications")
            }}
          >
            View all
          </button>
        </div>
      )}
    </div>
  )
}
