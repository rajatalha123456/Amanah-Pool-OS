import { useEffect, useState } from "react"
import { Outlet } from "react-router-dom"
import { Sidebar } from "./Sidebar"
import { TopBar } from "./TopBar"
import { Spinner } from "../components/Spinner"
import { useAuth } from "../api/auth"
import { UIControlsProvider } from "../context/UIControlsContext"
import { AiCopilotDrawer } from "../components/AiCopilotDrawer"
import { LiveControlsModal } from "../components/LiveControlsModal"

import { ErrorBoundary } from "../components/ErrorBoundary"

export function AppLayout() {
  const { user, loadCurrentUser } = useAuth()
  const [isLoadingUser, setIsLoadingUser] = useState(!user)

  useEffect(() => {
    if (!user) {
      loadCurrentUser()
        .catch(() => {
          // Swallow errors here; individual pages handle their own API failures.
        })
        .finally(() => setIsLoadingUser(false))
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return (
    <UIControlsProvider>
      <div className="flex h-screen bg-navy-950 font-sans text-ink-primary antialiased">
        <Sidebar />
        <div className="flex flex-1 flex-col overflow-hidden">
          <TopBar />
          <main className="flex-1 overflow-y-auto p-6">
            {isLoadingUser ? (
              <div className="flex items-center gap-2 py-12 text-ink-secondary">
                <Spinner className="h-5 w-5" />
                <span className="text-sm">Loading workspace...</span>
              </div>
            ) : (
              <ErrorBoundary fallbackTitle="Module Render Exception">
                <Outlet />
              </ErrorBoundary>
            )}
          </main>
        </div>
        <AiCopilotDrawer />
        <LiveControlsModal />
      </div>
    </UIControlsProvider>
  )
}

