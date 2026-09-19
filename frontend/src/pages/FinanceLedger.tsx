import { useState } from "react"
import { PageHeader } from "../components/PageHeader"
import { JournalBatchReview } from "./JournalBatchReview"
import { IncomeExpenseWorkbench } from "./IncomeExpenseWorkbench"

type Tab = "journal-batches" | "income-expense"

const TABS: { key: Tab; label: string }[] = [
  { key: "journal-batches", label: "Journal Batches" },
  { key: "income-expense", label: "Income & Expense" },
]

export function FinanceLedger() {
  const [activeTab, setActiveTab] = useState<Tab>("journal-batches")

  return (
    <div>
      <PageHeader
        title="Finance & Ledger"
        subtitle="Posted journal entries, audit trail, and manual income/expense events"
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

      {activeTab === "journal-batches" && <JournalBatchReview />}
      {activeTab === "income-expense" && <IncomeExpenseWorkbench />}
    </div>
  )
}
