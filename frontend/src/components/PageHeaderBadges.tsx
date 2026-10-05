import { useTranslation } from "react-i18next"
import { useUIControls } from "../context/UIControlsContext"

interface PageHeaderBadgesProps {
  contextName?: string
}

export function PageHeaderBadges({ contextName = "Amanah Shariah Pool Governance" }: PageHeaderBadgesProps) {
  const { openCopilot, openLiveControls } = useUIControls()
  const { i18n } = useTranslation()
  const isUrdu = i18n.language?.startsWith("ur")

  return (
    <div className="flex shrink-0 items-center gap-2.5">
      <button
        type="button"
        onClick={openLiveControls}
        className="group inline-flex items-center gap-2 rounded-full border border-emerald-500/30 bg-emerald-950/40 px-3 py-1.5 text-xs font-semibold text-emerald-400 transition-all hover:border-emerald-500/60 hover:bg-emerald-900/50 hover:text-emerald-300 focus:outline-none"
        title="View live control status"
      >
        <span className="relative flex h-2 w-2">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75"></span>
          <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500"></span>
        </span>
        <span className="tracking-wide uppercase">{isUrdu ? "لائیو کنٹرولز" : "LIVE CONTROLS"}</span>
      </button>

      <button
        type="button"
        onClick={() => openCopilot(contextName)}
        className="inline-flex items-center gap-1.5 rounded-full border border-white/10 bg-navy-900 px-3.5 py-1.5 text-xs font-semibold text-ink-primary transition-all hover:border-emerald-500/40 hover:bg-navy-800 hover:text-white focus:outline-none"
        title="Open AI Shariah Copilot"
      >
        <svg className="h-3.5 w-3.5 text-emerald-400" fill="currentColor" viewBox="0 0 24 24">
          <path d="M12 2L15.09 8.26L22 9.27L17 14.14L18.18 21.02L12 17.77L5.82 21.02L7 14.14L2 9.27L8.91 8.26L12 2Z" />
        </svg>
        <span className="tracking-wide uppercase">{isUrdu ? "اے آئی کو پائلٹ" : "AI COPILOT"}</span>
      </button>
    </div>
  )
}
