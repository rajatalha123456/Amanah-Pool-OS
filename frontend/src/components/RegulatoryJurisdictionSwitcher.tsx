import { useEffect, useRef, useState } from "react"
import { useAuth } from "../api/auth"
import { TENANT_CODE_KEY } from "../api/axios"
import { Badge } from "./Badge"

export interface JurisdictionProfile {
  id: string
  code: string
  country: string
  flag: string
  authority: string
  authorityShort: string
  tenantCode: string
  legalEntity: string
  currency: string
  currencySymbol: string
  benchmark: string
  benchmarkRate: string
  clearingRail: string
  rulePackCode: string
  regulatoryCircular: string
  guardrails: {
    mudaribCapPct: number
    perCeilingPct: number
    irrCeilingPct: number
    noticePeriodDays: number
    purificationInterval: string
  }
}

export const JURISDICTIONS: JurisdictionProfile[] = [
  {
    id: "pk-sbp",
    code: "PK",
    country: "Pakistan",
    flag: "🇵🇰",
    authority: "State Bank of Pakistan (IBD / BPRD)",
    authorityShort: "SBP",
    tenantCode: "NOVU-DEMO",
    legalEntity: "Novu Labs Demo Bank Ltd (Islamic Banking Division)",
    currency: "PKR",
    currencySymbol: "₨",
    benchmark: "KIBOR",
    benchmarkRate: "18.50%",
    clearingRail: "Raast RTGS / 1LINK Payouts",
    rulePackCode: "PK-SBP-2025",
    regulatoryCircular: "IBD Circular 03/2012 & BPRD 02/2018",
    guardrails: {
      mudaribCapPct: 20.0,
      perCeilingPct: 2.0,
      irrCeilingPct: 5.0,
      noticePeriodDays: 30,
      purificationInterval: "Monthly",
    },
  },
  {
    id: "uae-cbuae",
    code: "UAE",
    country: "United Arab Emirates",
    flag: "🇦🇪",
    authority: "Central Bank of the UAE & Higher Shari'ah Authority",
    authorityShort: "CBUAE / HSA",
    tenantCode: "DUBAI-DEMO",
    legalEntity: "Amanah Islamic Bank PJSC - Dubai DIFC",
    currency: "AED",
    currencySymbol: "د.إ",
    benchmark: "EIBOR",
    benchmarkRate: "5.25%",
    clearingRail: "UAEFTS / IPI Instant Clearing",
    rulePackCode: "UAE-CBUAE-2025",
    regulatoryCircular: "HSA Deen Standard 2021 & Notice 4465/2021",
    guardrails: {
      mudaribCapPct: 25.0,
      perCeilingPct: 3.5,
      irrCeilingPct: 8.0,
      noticePeriodDays: 14,
      purificationInterval: "Monthly",
    },
  },
  {
    id: "ksa-sama",
    code: "KSA",
    country: "Saudi Arabia",
    flag: "🇸🇦",
    authority: "Saudi Central Bank (SAMA) Shariah Governance",
    authorityShort: "SAMA",
    tenantCode: "RIYADH-DEMO",
    legalEntity: "Al-Amanah Financial Services Ltd - Riyadh",
    currency: "SAR",
    currencySymbol: "﷼",
    benchmark: "SAIBOR",
    benchmarkRate: "6.10%",
    clearingRail: "SARIE RTGS / IPS Instant Rails",
    rulePackCode: "KSA-SAMA-2025",
    regulatoryCircular: "SAMA Shariah Governance Framework for Islamic Banking",
    guardrails: {
      mudaribCapPct: 20.0,
      perCeilingPct: 3.0,
      irrCeilingPct: 6.0,
      noticePeriodDays: 21,
      purificationInterval: "Quarterly",
    },
  },
  {
    id: "global-aaoifi",
    code: "AAOIFI",
    country: "International",
    flag: "🌐",
    authority: "AAOIFI / IFSB Global Standards Board",
    authorityShort: "AAOIFI",
    tenantCode: "NOVU-DEMO",
    legalEntity: "Global Islamic Capital Facilities",
    currency: "USD",
    currencySymbol: "$",
    benchmark: "SOFR",
    benchmarkRate: "4.85%",
    clearingRail: "Cross-Border ISO 20022 Swift / RTGS",
    rulePackCode: "AAOIFI-GS1",
    regulatoryCircular: "AAOIFI Governance Standard GS-1 to GS-7 & FAS 27",
    guardrails: {
      mudaribCapPct: 30.0,
      perCeilingPct: 5.0,
      irrCeilingPct: 10.0,
      noticePeriodDays: 15,
      purificationInterval: "Quarterly",
    },
  },
]

export const ACTIVE_JURISDICTION_KEY = "amanah_active_jurisdiction"

export function getActiveJurisdiction(): JurisdictionProfile {
  const savedId = localStorage.getItem(ACTIVE_JURISDICTION_KEY)
  const currentTenant = localStorage.getItem(TENANT_CODE_KEY)

  if (savedId) {
    const found = JURISDICTIONS.find((j) => j.id === savedId)
    if (found) return found
  }

  if (currentTenant) {
    const foundByTenant = JURISDICTIONS.find((j) => j.tenantCode === currentTenant)
    if (foundByTenant) return foundByTenant
  }

  return JURISDICTIONS[0] // Default Pakistan (SBP)
}

export function RegulatoryJurisdictionSwitcher() {
  const { user } = useAuth()
  const [isOpen, setIsOpen] = useState(false)
  const [activeTab, setActiveTab] = useState<"switch" | "entities" | "guardrails">("switch")
  const [currentJurisdiction, setCurrentJurisdiction] = useState<JurisdictionProfile>(
    getActiveJurisdiction(),
  )
  const containerRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }
    document.addEventListener("mousedown", handleClickOutside)
    return () => document.removeEventListener("mousedown", handleClickOutside)
  }, [])

  function handleSelectJurisdiction(target: JurisdictionProfile) {
    localStorage.setItem(ACTIVE_JURISDICTION_KEY, target.id)
    localStorage.setItem(TENANT_CODE_KEY, target.tenantCode)
    localStorage.setItem("amanah_active_rule_pack", target.rulePackCode)
    setCurrentJurisdiction(target)
    setIsOpen(false)

    // Broadcast change and trigger page refresh so all queries & API calls re-scope
    window.dispatchEvent(
      new CustomEvent("amanah_jurisdiction_changed", { detail: target }),
    )
    window.location.reload()
  }

  return (
    <div className="relative" ref={containerRef}>
      {/* TopBar Interactive Pill */}
      <button
        type="button"
        onClick={() => setIsOpen((prev) => !prev)}
        className="flex items-center gap-2 rounded-full border border-white/10 bg-navy-900/90 px-3 py-1.5 text-xs text-ink-primary shadow-sm transition-all hover:border-gold-500/50 hover:bg-navy-800"
      >
        <span className="text-base leading-none">{currentJurisdiction.flag}</span>
        <div className="flex items-center gap-1.5">
          <span className="font-semibold text-gold-400">
            {currentJurisdiction.authorityShort}
          </span>
          <span className="text-ink-muted">|</span>
          <span className="text-ink-secondary">{currentJurisdiction.tenantCode}</span>
          <span className="text-ink-muted">|</span>
          <span className="font-mono text-emerald-400">
            {currentJurisdiction.benchmark}
          </span>
        </div>
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth={2}
          className={`h-3 w-3 text-ink-muted transition-transform ${
            isOpen ? "rotate-180" : ""
          }`}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {/* Dropdown Modal */}
      {isOpen && (
        <div className="absolute left-0 mt-2 w-[480px] rounded-xl border border-white/10 bg-navy-900 p-4 shadow-2xl z-50">
          <div className="flex items-center justify-between border-b border-white/8 pb-3">
            <div>
              <div className="flex items-center gap-1.5">
                <span className="rounded bg-gold-500/20 px-2 py-0.5 text-[10px] font-bold text-gold-400">
                  BRD SCREEN 02 & 06
                </span>
                <span className="text-xs text-ink-muted">Regulatory Engine</span>
              </div>
              <h3 className="mt-1 text-sm font-semibold text-ink-primary">
                Cross-Jurisdiction & Regulatory Framework Switcher
              </h3>
            </div>
            <button
              onClick={() => setIsOpen(false)}
              className="text-xs text-ink-muted hover:text-ink-primary"
            >
              ✕
            </button>
          </div>

          {/* Tab Selector */}
          <div className="mt-3 flex gap-2 border-b border-white/5 pb-2 text-xs">
            <button
              onClick={() => setActiveTab("switch")}
              className={`rounded px-2.5 py-1 font-medium transition-colors ${
                activeTab === "switch"
                  ? "bg-emerald-600 text-white"
                  : "text-ink-secondary hover:text-ink-primary"
              }`}
            >
              Active Jurisdiction
            </button>
            <button
              onClick={() => setActiveTab("entities")}
              className={`rounded px-2.5 py-1 font-medium transition-colors ${
                activeTab === "entities"
                  ? "bg-emerald-600 text-white"
                  : "text-ink-secondary hover:text-ink-primary"
              }`}
            >
              Legal Entities (Screen 02)
            </button>
            <button
              onClick={() => setActiveTab("guardrails")}
              className={`rounded px-2.5 py-1 font-medium transition-colors ${
                activeTab === "guardrails"
                  ? "bg-emerald-600 text-white"
                  : "text-ink-secondary hover:text-ink-primary"
              }`}
            >
              Rule Guardrails (Screen 06)
            </button>
          </div>

          {/* Tab 1: Quick Switcher */}
          {activeTab === "switch" && (
            <div className="mt-3 space-y-2.5 max-h-[380px] overflow-y-auto pr-1">
              {JURISDICTIONS.map((item) => {
                const isActive = item.id === currentJurisdiction.id
                return (
                  <div
                    key={item.id}
                    onClick={() => handleSelectJurisdiction(item)}
                    className={`cursor-pointer rounded-lg border p-3 transition-all ${
                      isActive
                        ? "border-emerald-500/50 bg-emerald-500/10 shadow-sm"
                        : "border-white/5 bg-navy-950/60 hover:border-white/15 hover:bg-navy-950"
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex items-center gap-2">
                        <span className="text-xl leading-none">{item.flag}</span>
                        <div>
                          <div className="flex items-center gap-1.5">
                            <h4 className="text-xs font-semibold text-ink-primary">
                              {item.country} ({item.authorityShort})
                            </h4>
                            {isActive && (
                              <Badge variant="emerald" className="text-[10px]">
                                Active Context
                              </Badge>
                            )}
                          </div>
                          <p className="text-[11px] text-ink-muted">
                            {item.authority}
                          </p>
                        </div>
                      </div>

                      <div className="text-right">
                        <span className="font-mono text-xs font-bold text-gold-400">
                          {item.benchmark} {item.benchmarkRate}
                        </span>
                        <span className="block text-[10px] text-ink-muted">
                          {item.currency} ({item.currencySymbol})
                        </span>
                      </div>
                    </div>

                    <div className="mt-2.5 grid grid-cols-3 gap-2 border-t border-white/5 pt-2 text-[10px]">
                      <div>
                        <span className="text-ink-muted">Clearing Rail:</span>
                        <p className="font-medium text-ink-secondary truncate">
                          {item.clearingRail}
                        </p>
                      </div>
                      <div>
                        <span className="text-ink-muted">Tenant Scope:</span>
                        <p className="font-mono font-medium text-ink-secondary">
                          {item.tenantCode}
                        </p>
                      </div>
                      <div>
                        <span className="text-ink-muted">Rule Pack:</span>
                        <p className="font-mono font-medium text-emerald-400">
                          {item.rulePackCode}
                        </p>
                      </div>
                    </div>

                    <div className="mt-1.5 text-[10px] text-ink-muted italic">
                      Circular: {item.regulatoryCircular}
                    </div>
                  </div>
                )
              })}
            </div>
          )}

          {/* Tab 2: Legal Entity Directory (Screen 02) */}
          {activeTab === "entities" && (
            <div className="mt-3 space-y-2 max-h-[380px] overflow-y-auto">
              <p className="text-xs text-ink-secondary">
                Registered banking institutions and operating entities configured for the
                selected enterprise:
              </p>
              {JURISDICTIONS.map((item) => (
                <div
                  key={item.id}
                  className="rounded-lg border border-white/5 bg-navy-950 p-2.5 text-xs"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-ink-primary">
                      {item.flag} {item.legalEntity}
                    </span>
                    <Badge variant={item.id === currentJurisdiction.id ? "emerald" : "neutral"}>
                      {item.currency}
                    </Badge>
                  </div>
                  <div className="mt-1 flex items-center justify-between text-[11px] text-ink-muted">
                    <span>Jurisdiction: {item.country}</span>
                    <span>Tenant ID: {item.tenantCode}</span>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Tab 3: Regulatory Guardrails (Screen 06) */}
          {activeTab === "guardrails" && (
            <div className="mt-3 space-y-3 max-h-[380px] overflow-y-auto text-xs">
              <p className="text-xs text-ink-secondary">
                Prudential reserve caps and Mudarib ceiling limits enforced by the active
                rules engine:
              </p>
              <table className="w-full text-left text-[11px]">
                <thead>
                  <tr className="border-b border-white/10 text-ink-muted">
                    <th className="py-1">Jurisdiction</th>
                    <th className="py-1">Mudarib Cap</th>
                    <th className="py-1">PER Cap</th>
                    <th className="py-1">IRR Cap</th>
                    <th className="py-1">Notice</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {JURISDICTIONS.map((j) => (
                    <tr
                      key={j.id}
                      className={j.id === currentJurisdiction.id ? "text-emerald-400 font-semibold" : "text-ink-secondary"}
                    >
                      <td className="py-1.5">{j.flag} {j.authorityShort}</td>
                      <td className="py-1.5 font-mono">{j.guardrails.mudaribCapPct}%</td>
                      <td className="py-1.5 font-mono">{j.guardrails.perCeilingPct}%</td>
                      <td className="py-1.5 font-mono">{j.guardrails.irrCeilingPct}%</td>
                      <td className="py-1.5 font-mono">{j.guardrails.noticePeriodDays}d</td>
                    </tr>
                  ))}
                </tbody>
              </table>

              <div className="rounded border border-gold-500/20 bg-gold-500/5 p-2 text-[11px] text-gold-300">
                Active Rule Pack: <strong>{currentJurisdiction.rulePackCode}</strong>.
                All calculations in Daily Operations and Pool Simulator strictly enforce these caps.
              </div>
            </div>
          )}

          <div className="mt-3 flex items-center justify-between border-t border-white/8 pt-2.5 text-[11px] text-ink-muted">
            <span>
              Session: <strong className="text-ink-secondary">{user?.email}</strong>
            </span>
            <span className="text-emerald-400">✓ Multi-Tenant Isolation Active</span>
          </div>
        </div>
      )}
    </div>
  )
}
