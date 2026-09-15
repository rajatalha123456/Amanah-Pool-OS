import { NavLink } from "react-router-dom"
import { navItems } from "./navItems"

export function Sidebar() {
  return (
    <aside className="flex h-full w-64 shrink-0 flex-col bg-navy-900 border-r border-navy-700">
      <div className="flex h-16 items-center px-6 border-b border-navy-700">
        <span className="text-lg font-semibold text-white">Amanah Pool OS</span>
      </div>
      <nav className="flex-1 overflow-y-auto px-3 py-4">
        <ul className="space-y-1">
          {navItems.map((item) => (
            <li key={item.path}>
              <NavLink
                to={item.path}
                end={item.path === "/"}
                className={({ isActive }) =>
                  `block rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                    isActive
                      ? "bg-emerald-600 text-white"
                      : "text-gray-300 hover:bg-navy-800 hover:text-white"
                  }`
                }
              >
                {item.label}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>
    </aside>
  )
}
