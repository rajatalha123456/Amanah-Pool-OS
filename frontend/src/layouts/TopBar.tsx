import { translatePhrase } from "../i18n/translate"
import { useEffect, useRef, useState } from "react"
import { useNavigate } from "react-router-dom"
import { useTranslation } from "react-i18next"
import { useAuth } from "../api/auth"
import { TenantSwitcher } from "../components/TenantSwitcher"
import { LanguageSwitcher } from "../components/LanguageSwitcher"
import { NotificationBell } from "../components/NotificationBell"

export function TopBar() {
  const navigate = useNavigate()
  const { user, logout } = useAuth()
  const { i18n } = useTranslation()
  const [isMenuOpen, setIsMenuOpen] = useState(false)
  const menuRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setIsMenuOpen(false)
      }
    }
    document.addEventListener("mousedown", handleClickOutside)
    return () => document.removeEventListener("mousedown", handleClickOutside)
  }, [])

  function handleLogout() {
    logout()
    navigate("/login", { replace: true })
  }

  const initial = user?.full_name?.[0]?.toUpperCase() ?? "U"

  return (
    <header className="flex h-16 items-center justify-between border-b border-white/5 bg-navy-950 px-6">
      <div className="flex items-center gap-3">
        <span className="text-sm font-medium text-ink-primary">
          {translatePhrase(i18n.language, "Amanah Capital")}
        </span>
        <TenantSwitcher />
      </div>
      <div className="flex items-center gap-4">
        <LanguageSwitcher />
        <NotificationBell />

        <div className="relative" ref={menuRef}>
          <button
            type="button"
            onClick={() => setIsMenuOpen((open) => !open)}
            className="flex items-center gap-2 rounded-md px-2 py-1 transition-colors hover:bg-white/5"
          >
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-emerald-600 text-sm font-medium text-white">
              {initial}
            </div>
            <span className="text-sm text-ink-secondary">
              {user?.full_name ?? (translatePhrase(i18n.language, "User"))}
            </span>
          </button>

          {isMenuOpen && (
            <div className="absolute right-0 rtl:right-auto rtl:left-0 mt-2 w-44 rounded-md border border-white/8 bg-navy-900 py-1 shadow-lg z-50">
              <button
                type="button"
                onClick={handleLogout}
                className="block w-full px-3 py-2 text-left rtl:text-right text-sm text-ink-secondary transition-colors hover:bg-white/5 hover:text-ink-primary"
              >
                {translatePhrase(i18n.language, "Logout")}
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  )
}
