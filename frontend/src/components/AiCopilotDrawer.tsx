import { useState } from "react"
import { useUIControls } from "../context/UIControlsContext"
import { useAuth } from "../api/auth"
import { askQuestion } from "../api/shariahCopilot"
import { extractErrorMessage } from "../api/errors"
import { Badge } from "./Badge"
import { Button } from "./Button"
import type { EvidencePack } from "../types"

interface Message {
  role: "user" | "assistant" | "error"
  text: string
  pack?: EvidencePack
}

const COPILOT_ROLES = ["shariah_board", "shariah_secretariat", "product_manager", "risk_compliance", "platform_super_admin"]

/**
 * Drawer front-end for the Shariah Policy Copilot service. Answers come from the approved-source library with
 * citations; when the service is unavailable the drawer says so - it never invents an answer.
 */
export function AiCopilotDrawer() {
  const { isCopilotOpen, closeCopilot, copilotContext } = useUIControls()
  const { user } = useAuth()
  const [input, setInput] = useState("")
  const [busy, setBusy] = useState(false)
  const [messages, setMessages] = useState<Message[]>([])

  if (!isCopilotOpen) return null
  const allowed = COPILOT_ROLES.includes(user?.role ?? "")

  async function handleSend() {
    const question = input.trim()
    if (!question || busy) return
    setInput("")
    setMessages((prev) => [...prev, { role: "user", text: question }])
    setBusy(true)
    try {
      const pack = await askQuestion(`${question}\n\n(Screen context: ${copilotContext})`)
      setMessages((prev) => [...prev, { role: "assistant", text: pack.research_summary, pack }])
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: "error", text: extractErrorMessage(err, "The Shariah Copilot service did not answer. Try again later.") },
      ])
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/60 backdrop-blur-xs">
      <div className="flex h-full w-full max-w-md flex-col border-l border-white/10 bg-navy-950 shadow-2xl">
        <div className="flex items-center justify-between border-b border-white/10 px-5 py-4">
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-sm font-semibold text-ink-primary">Shariah Policy Copilot</h2>
              <Badge variant="gold">AI-assisted</Badge>
            </div>
            <p className="text-xs text-ink-muted">Answers cite approved sources and need human review.</p>
          </div>
          <button type="button" onClick={closeCopilot} className="rounded-md p-1.5 text-ink-secondary hover:bg-white/5 hover:text-ink-primary">
            ✕
          </button>
        </div>

        <div className="border-b border-white/5 bg-navy-900/60 px-5 py-2.5">
          <span className="text-[11px] font-medium text-ink-muted uppercase tracking-wider">Screen context:</span>
          <p className="truncate text-xs font-semibold text-emerald-400">{copilotContext}</p>
        </div>

        <div className="flex-1 space-y-4 overflow-y-auto p-5 text-sm">
          {!allowed && (
            <p className="text-xs text-amber-300">The copilot is available to Shariah, product and compliance roles only.</p>
          )}
          {allowed && messages.length === 0 && (
            <p className="text-xs text-ink-secondary">Ask a question about the approved Shariah rulings and standards.</p>
          )}
          {messages.map((m, idx) => (
            <div
              key={idx}
              className={`rounded-xl p-3.5 ${
                m.role === "assistant"
                  ? "border border-white/8 bg-navy-900 text-ink-primary"
                  : m.role === "error"
                    ? "border border-red-500/30 bg-red-950/30 text-red-200"
                    : "ml-6 border border-emerald-500/20 bg-emerald-950/40 text-emerald-100"
              }`}
            >
              <p className="text-xs leading-relaxed whitespace-pre-wrap">{m.text}</p>
              {m.pack && (
                <div className="mt-2.5 space-y-1 border-t border-white/5 pt-1.5 text-[10px] text-gold-400">
                  {m.pack.is_fallback && <p className="text-amber-300">Fallback answer - the AI model was unavailable.</p>}
                  {m.pack.conflict_flagged && <p className="text-amber-300">Sources conflict; a reviewer must decide.</p>}
                  {m.pack.citations.length === 0 ? (
                    <p>No source cited - do not rely on this answer.</p>
                  ) : (
                    m.pack.citations.map((c, i) => (
                      <p key={i}>
                        Source: {c.document_name} v{c.version}
                        {c.section_label ? `, ${c.section_label}` : ""}
                      </p>
                    ))
                  )}
                  <p className="text-ink-muted">{m.pack.disclaimer}</p>
                </div>
              )}
            </div>
          ))}
          {busy && <p className="text-xs text-ink-muted">Asking the copilot...</p>}
        </div>

        <div className="border-t border-white/10 p-4">
          <div className="flex gap-2">
            <input
              type="text"
              value={input}
              disabled={!allowed}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && void handleSend()}
              placeholder="Ask about a ruling or standard..."
              className="flex-1 rounded-lg border border-white/10 bg-navy-900 px-3 py-2 text-xs text-ink-primary placeholder:text-ink-muted focus:border-emerald-500 focus:outline-none disabled:opacity-50"
            />
            <Button variant="primary" onClick={() => void handleSend()} disabled={!allowed || busy} className="px-3 py-2 text-xs">
              Send
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}
