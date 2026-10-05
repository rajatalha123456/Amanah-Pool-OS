import { useState } from "react"
import { useUIControls } from "../context/UIControlsContext"
import { Badge } from "./Badge"
import { Button } from "./Button"

interface Message {
  role: "system" | "user" | "assistant"
  text: string
  reference?: string
}

export function AiCopilotDrawer() {
  const { isCopilotOpen, closeCopilot, copilotContext } = useUIControls()
  const [input, setInput] = useState("")
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      text: `Assalamu Alaikum. I am your Amanah Shariah Copilot. I have context on "${copilotContext}". All calculation rules are deterministic; I can explain formulas, audit trails, and Shariah governance gates.`,
      reference: "AAOIFI Shariah Standard No. 40 / SBP Pool Guidelines",
    },
  ])

  if (!isCopilotOpen) return null

  function handleSend() {
    if (!input.trim()) return
    const userText = input.trim()
    setInput("")

    const newMessages: Message[] = [...messages, { role: "user", text: userText }]
    setMessages(newMessages)

    setTimeout(() => {
      let reply = "Based on SBP Shariah Governance Framework and AAOIFI standards, all allocations require verified daily average funds, explicit Mudarib/Rabb-ul-Mal profit sharing ratios, and non-permissible income exclusion into the purification ledger."
      let ref = "SBP IBD Circular No. 3 / AAOIFI Standard No. 13"

      if (userText.toLowerCase().includes("formula") || userText.toLowerCase().includes("calc")) {
        reply = "Daily Product Formula: Participant Daily Share = (Participant Daily Average Balance × Class Weightage) / Sum(Pool Weighted Balances) × Distributable Pool Profit."
        ref = "Deterministic Rules Engine v2026.1"
      } else if (userText.toLowerCase().includes("exception") || userText.toLowerCase().includes("break")) {
        reply = "Open exceptions are currently isolated from the allocation run. Negligence/misconduct cases route to capital impairment, while non-permissible income routes to charity."
        ref = "Purification & Exception Ledger"
      }

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          text: reply,
          reference: ref,
        },
      ])
    }, 600)
  }

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/60 backdrop-blur-xs transition-opacity animate-in fade-in">
      <div className="flex h-full w-full max-w-md flex-col border-l border-white/10 bg-navy-950 shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-white/10 px-5 py-4">
          <div className="flex items-center gap-2.5">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-500/20 text-emerald-400">
              <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 24 24">
                <path d="M12 2L15.09 8.26L22 9.27L17 14.14L18.18 21.02L12 17.77L5.82 21.02L7 14.14L2 9.27L8.91 8.26L12 2Z" />
              </svg>
            </span>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-sm font-semibold text-ink-primary">AI Shariah Copilot</h2>
                <Badge variant="emerald">Live Engine</Badge>
              </div>
              <p className="text-xs text-ink-muted">Amanah Explainable Intelligence</p>
            </div>
          </div>
          <button
            type="button"
            onClick={closeCopilot}
            className="rounded-md p-1.5 text-ink-secondary hover:bg-white/5 hover:text-ink-primary"
          >
            ✕
          </button>
        </div>

        {/* Context Strip */}
        <div className="border-b border-white/5 bg-navy-900/60 px-5 py-2.5">
          <span className="text-[11px] font-medium text-ink-muted uppercase tracking-wider">Active Context:</span>
          <p className="truncate text-xs font-semibold text-emerald-400">{copilotContext}</p>
        </div>

        {/* Message Stream */}
        <div className="flex-1 space-y-4 overflow-y-auto p-5 text-sm">
          {messages.map((m, idx) => (
            <div
              key={idx}
              className={`rounded-xl p-3.5 ${
                m.role === "assistant"
                  ? "border border-white/8 bg-navy-900 text-ink-primary"
                  : "ml-6 border border-emerald-500/20 bg-emerald-950/40 text-emerald-100"
              }`}
            >
              <div className="mb-1 flex items-center justify-between text-[11px] font-semibold tracking-wider uppercase text-ink-muted">
                <span>{m.role === "assistant" ? "Amanah Intelligence" : "You"}</span>
              </div>
              <p className="text-xs leading-relaxed">{m.text}</p>
              {m.reference && (
                <div className="mt-2.5 border-t border-white/5 pt-1.5 text-[10px] text-gold-400">
                  Ref: {m.reference}
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Input & Quick Prompts */}
        <div className="border-t border-white/10 p-4">
          <div className="mb-3 flex flex-wrap gap-1.5">
            <button
              type="button"
              onClick={() => {
                setInput("Explain the allocation formula for this pool")
              }}
              className="rounded-md border border-white/8 bg-white/5 px-2 py-1 text-[11px] text-ink-secondary hover:bg-white/10 hover:text-ink-primary"
            >
              Calculate Formula
            </button>
            <button
              type="button"
              onClick={() => {
                setInput("What Shariah standards apply here?")
              }}
              className="rounded-md border border-white/8 bg-white/5 px-2 py-1 text-[11px] text-ink-secondary hover:bg-white/10 hover:text-ink-primary"
            >
              Shariah Standards
            </button>
            <button
              type="button"
              onClick={() => {
                setInput("Are there any open reconciliation exceptions?")
              }}
              className="rounded-md border border-white/8 bg-white/5 px-2 py-1 text-[11px] text-ink-secondary hover:bg-white/10 hover:text-ink-primary"
            >
              Check Exceptions
            </button>
          </div>
          <div className="flex gap-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSend()}
              placeholder="Ask Copilot about rules, formulas, or exceptions..."
              className="flex-1 rounded-lg border border-white/10 bg-navy-900 px-3 py-2 text-xs text-ink-primary placeholder:text-ink-muted focus:border-emerald-500 focus:outline-none"
            />
            <Button variant="primary" onClick={handleSend} className="px-3 py-2 text-xs">
              Send
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}
