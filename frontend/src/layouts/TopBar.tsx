import { useEffect, useRef, useState } from "react"
import { useNavigate } from "react-router-dom"
import { useAuth } from "../api/auth"
import { TenantSwitcher } from "../components/TenantSwitcher"
import { LanguageSwitcher } from "../components/LanguageSwitcher"

export function TopBar() {
  const navigate = useNavigate()
  const { user, logout } = useAuth()
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
        <span className="text-sm font-medium text-ink-primary">Amanah Capital</span>
        <TenantSwitcher />
      </div>
      <div className="flex items-center gap-4">
        <LanguageSwitcher />
        <button
          type="button"
          aria-label="Notifications"
          className="rounded-full p-2 text-ink-secondary transition-colors hover:bg-white/5 hover:text-ink-primary"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth={1.8}
            className="h-5 w-5"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M14.857 17.082a23.848 23.848 0 0 0 5.454-1.31A8.967 8.967 0 0 1 18 9.75V9A6 6 0 0 0 6 9v.75a8.967 8.967 0 0 1-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 0 1-5.714 0m5.714 0a3 3 0 1 1-5.714 0"
            />
          </svg>
        </button>

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
              {user?.full_name ?? "User"}
            </span>
          </button>

          {isMenuOpen && (
            <div className="absolute right-0 mt-2 w-44 rounded-md border border-white/8 bg-navy-900 py-1 shadow-lg">
              <button
                type="button"
                onClick={handleLogout}
                className="block w-full px-3 py-2 text-left text-sm text-ink-secondary transition-colors hover:bg-white/5 hover:text-ink-primary"
              >
                Logout
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  )
}
