import { NavLink } from "react-router-dom"
import { useTranslation } from "react-i18next"
import { navItems } from "./navItems"

export function Sidebar() {
  const { t } = useTranslation()

  return (
    <aside className="flex h-full w-64 shrink-0 flex-col bg-navy-950 border-r border-white/5">
      <div className="px-6 pt-6 pb-5">
        <p className="text-[11px] font-semibold tracking-widest text-gold-500 uppercase">
          Novu Labs
        </p>
        <p className="mt-0.5 text-sm font-semibold text-ink-primary">
          Amanah Pool OS
        </p>
      </div>
      <nav className="flex-1 overflow-y-auto px-3">
        <ul className="space-y-0.5">
          {navItems.map((item) => (
            <li key={item.path}>
              <NavLink
                to={item.path}
                end={item.path === "/"}
                className={({ isActive }) =>
                  `block rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                    isActive
                      ? "bg-emerald-600/15 text-emerald-400"
                      : "text-ink-secondary hover:bg-white/5 hover:text-ink-primary"
                  }`
                }
              >
                {t(item.labelKey)}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>
      <div className="border-t border-white/5 px-6 py-4">
        <p className="text-xs text-ink-muted">Moneeb A. Jaffari • Chairman</p>
      </div>
    </aside>
  )
}
