import { useState } from "react"
import { PageHeader } from "../components/PageHeader"
import { JournalBatchReview } from "./JournalBatchReview"
import { IncomeExpenseWorkbench } from "./IncomeExpenseWorkbench"
import { GLHandover } from "../components/finance/GLHandover"

type Tab = "journal-batches" | "income-expense" | "gl-handover"

const TABS: { key: Tab; label: string }[] = [
  { key: "journal-batches", label: "Journal Batches" },
  { key: "income-expense", label: "Income & Expense" },
  { key: "gl-handover", label: "GL Hand-over & Trial Balance" },
]

export function FinanceLedger() {
  const [activeTab, setActiveTab] = useState<Tab>("journal-batches")

  const activeMeta =
    activeTab === "gl-handover"
      ? {
          num: "15",
          title: "GL Hand-over & Trial Balance",
          sub: "Journals sent to the enterprise general ledger, the GL's answer, and the trial balance",
        }
      : activeTab === "income-expense"
      ? {
          num: "10",
          title: "Income & Expense Workbench",
          sub: "Pool-attributable performance events",
        }
      : {
          num: "15",
          title: "Journal Batch Review",
          sub: "Posted journal entries and immutable audit subledger",
        }

  return (
    <div>
      <PageHeader
        screenNumber={activeMeta.num}
        title={activeMeta.title}
        subtitle={activeMeta.sub}
      />

      <div className="mb-6 flex gap-4 border-b border-white/8 text-sm">
        {TABS.map((tab) => (
          <button
            key={tab.key}
            type="button"
            onClick={() => setActiveTab(tab.key)}
            className={`px-1 pb-2 font-medium transition-colors ${
              activeTab === tab.key
                ? "border-b-2 border-emerald-500 text-ink-primary"
                : "text-ink-secondary hover:text-ink-primary"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === "journal-batches" && <JournalBatchReview hideHeader />}
      {activeTab === "income-expense" && <IncomeExpenseWorkbench />}
      {activeTab === "gl-handover" && <GLHandover />}
    </div>
  )
}
