import { createContext, useContext, useState, type ReactNode } from "react"

interface UIControlsContextType {
  isCopilotOpen: boolean
  isLiveControlsOpen: boolean
  copilotContext: string
  openCopilot: (contextText?: string) => void
  closeCopilot: () => void
  openLiveControls: () => void
  closeLiveControls: () => void
}

const UIControlsContext = createContext<UIControlsContextType | undefined>(undefined)

export function UIControlsProvider({ children }: { children: ReactNode }) {
  const [isCopilotOpen, setIsCopilotOpen] = useState(false)
  const [isLiveControlsOpen, setIsLiveControlsOpen] = useState(false)
  const [copilotContext, setCopilotContext] = useState("General Shariah Pool Governance")

  function openCopilot(contextText?: string) {
    if (contextText) setCopilotContext(contextText)
    setIsCopilotOpen(true)
  }

  function closeCopilot() {
    setIsCopilotOpen(false)
  }

  function openLiveControls() {
    setIsLiveControlsOpen(true)
  }

  function closeLiveControls() {
    setIsLiveControlsOpen(false)
  }

  return (
    <UIControlsContext.Provider
      value={{
        isCopilotOpen,
        isLiveControlsOpen,
        copilotContext,
        openCopilot,
        closeCopilot,
        openLiveControls,
        closeLiveControls,
      }}
    >
      {children}
    </UIControlsContext.Provider>
  )
}

export function useUIControls() {
  const context = useContext(UIControlsContext)
  if (!context) {
    throw new Error("useUIControls must be used within a UIControlsProvider")
  }
  return context
}
