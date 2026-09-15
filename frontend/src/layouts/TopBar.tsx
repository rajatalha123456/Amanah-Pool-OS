import { Badge } from "../components/Badge"

export function TopBar() {
  return (
    <header className="flex h-16 items-center justify-between border-b border-navy-700 bg-navy-950 px-6">
      <div className="flex items-center gap-3">
        <span className="text-sm font-semibold text-white">Amanah Capital</span>
        <Badge variant="gold">Tenant</Badge>
      </div>
      <div className="flex items-center gap-4">
        <button
          type="button"
          aria-label="Notifications"
          className="rounded-full p-2 text-gray-300 hover:bg-navy-800 hover:text-white"
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
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-emerald-600 text-sm font-medium text-white">
            U
          </div>
          <span className="text-sm text-gray-300">User Placeholder</span>
        </div>
      </div>
    </header>
  )
}
