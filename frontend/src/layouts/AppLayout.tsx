import { useEffect } from "react"
import { Outlet } from "react-router-dom"
import { Sidebar } from "./Sidebar"
import { TopBar } from "./TopBar"
import { useAuth } from "../api/auth"

export function AppLayout() {
  const { user, loadCurrentUser } = useAuth()

  useEffect(() => {
    if (!user) {
      loadCurrentUser().catch(() => {
        // Swallow errors here; individual pages handle their own API failures.
      })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return (
    <div className="flex h-screen bg-navy-950">
      <Sidebar />
      <div className="flex flex-1 flex-col overflow-hidden">
        <TopBar />
        <main className="flex-1 overflow-y-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
