import { useEffect, useState, type FormEvent } from "react"
import { useAuth } from "../api/auth"
import { fetchPools } from "../api/pools"
import {
  createRelatedPartyTransaction,
  fetchRelatedPartyTransactions,
  reviewRelatedPartyTransaction,
} from "../api/relatedParty"
import { extractErrorMessage } from "../api/errors"
import { Badge } from "../components/Badge"
import { Button } from "../components/Button"
import { Card } from "../components/Card"
import { Modal } from "../components/Modal"
import { Spinner } from "../components/Spinner"
import { Table, type TableColumn } from "../components/Table"
import type { BadgeVariant, Pool, RelatedPartyTransaction } from "../types"

const RELATIONSHIP_TYPES = ["director", "shareholder", "family_member", "affiliate_company", "other"]
const STATUS_BADGE: Record<string, BadgeVariant> = {
  disclosed: "neutral",
  pending_review: "gold",
  approved: "emerald",
  flagged: "navy",
}

const inputClasses =
  "w-full rounded-md border border-white/10 bg-navy-800 px-3 py-2 text-sm text-ink-primary focus:border-emerald-500 focus:outline-none"

export function RelatedPartyReview() {
  const { user } = useAuth()
  const canCreate = user?.role === "finance_maker" || user?.role === "pool_manager"
  const canReview = user?.role === "risk_compliance" || user?.role === "shariah_board"
  const [pools, setPools] = useState<Pool[]>([])
  const [poolId, setPoolId] = useState("")
  const [transactions, setTransactions] = useState<RelatedPartyTransaction[]>([])
  const [pageState, setPageState] = useState<"loading" | "loaded" | "error">("loading")
  const [error, setError] = useState("")
  const [isNewOpen, setIsNewOpen] = useState(false)
  const [reviewing, setReviewing] = useState<RelatedPartyTransaction | null>(null)
  const [reviewNotes, setReviewNotes] = useState("")
  const [isSubmitting, setIsSubmitting] = useState(false)

  useEffect(() => {
    fetchPools().then(setPools).catch(() => setError("Failed to load pools."))
  }, [])

  useEffect(() => {
    setPageState("loading")
    fetchRelatedPartyTransactions(poolId || undefined)
      .then((data) => {
        setTransactions(data)
        setPageState("loaded")
      })
      .catch((err) => {
        setError(extractErrorMessage(err, "Failed to load related-party transactions."))
        setPageState("error")
      })
  }, [poolId])

  async function handleCreated(transaction: RelatedPartyTransaction) {
    setTransactions((current) => [transaction, ...current])
    setIsNewOpen(false)
  }

  async function handleReview(event: FormEvent, decision: "approved" | "flagged") {
    event.preventDefault()
    if (!reviewing) return
    setIsSubmitting(true)
    setError("")
    try {
      const updated = await reviewRelatedPartyTransaction(reviewing.id, { decision, notes: reviewNotes })
      setTransactions((current) => current.map((item) => (item.id === updated.id ? updated : item)))
      setReviewing(null)
      setReviewNotes("")
    } catch (err) {
      setError(extractErrorMessage(err, "Unable to submit review."))
    } finally {
      setIsSubmitting(false)
    }
  }

  const columns: TableColumn<RelatedPartyTransaction>[] = [
    { header: "Related Party", accessor: (item) => item.related_party_name },
    { header: "Relationship", accessor: (item) => item.relationship_type },
    { header: "Amount", accessor: (item) => item.amount },
    {
      header: "Status",
      accessor: (item) => <Badge variant={STATUS_BADGE[item.disclosure_status] ?? "neutral"}>{item.disclosure_status}</Badge>,
    },
    {
      header: "Action",
      accessor: (item) =>
        canReview && item.disclosure_status === "pending_review" ? (
          <Button variant="outline" onClick={() => setReviewing(item)}>
            Review
          </Button>
        ) : null,
    },
  ]

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <select value={poolId} onChange={(event) => setPoolId(event.target.value)} className={inputClasses + " max-w-xs"}>
          <option value="">All pools</option>
          {pools.map((pool) => (
            <option key={pool.id} value={pool.id}>
              {pool.name} ({pool.code})
            </option>
          ))}
        </select>
        {canCreate && <Button onClick={() => setIsNewOpen(true)}>+ New Transaction</Button>}
      </div>

      {error && <p className="text-sm text-red-400">{error}</p>}
      {pageState === "loading" && <Spinner className="h-5 w-5" />}
      {pageState === "error" && <Card><p className="text-sm text-ink-secondary">Unable to load transactions.</p></Card>}
      {pageState === "loaded" && (
        <Card>
          {transactions.length === 0 ? (
            <p className="text-sm text-ink-secondary">No related-party transactions yet.</p>
          ) : (
            <Table columns={columns} data={transactions} keyField={(item) => item.id} />
          )}
        </Card>
      )}

      {isNewOpen && <NewTransactionModal pools={pools} onClose={() => setIsNewOpen(false)} onCreated={handleCreated} />}
      {reviewing && (
        <Modal title="Review Related-Party Transaction" onClose={() => setReviewing(null)}>
          <form onSubmit={(event) => handleReview(event, "approved")} className="space-y-4">
            <p className="text-sm text-ink-secondary">{reviewing.related_party_name} · {reviewing.amount}</p>
            <textarea value={reviewNotes} onChange={(event) => setReviewNotes(event.target.value)} placeholder="Review notes" className={inputClasses} rows={3} />
            <div className="flex justify-end gap-2">
              <Button type="button" variant="outline" disabled={isSubmitting} onClick={(event) => handleReview(event, "flagged")}>Flag</Button>
              <Button type="submit" disabled={isSubmitting}>{isSubmitting ? <Spinner className="h-4 w-4" /> : "Approve"}</Button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  )
}

function NewTransactionModal({
  pools,
  onClose,
  onCreated,
}: {
  pools: Pool[]
  onClose: () => void
  onCreated: (transaction: RelatedPartyTransaction) => void
}) {
  const [form, setForm] = useState({ pool: pools[0]?.id ?? "", related_party_name: "", relationship_type: RELATIONSHIP_TYPES[0], transaction_type: "", amount: "", transaction_date: "" })
  const [error, setError] = useState("")
  const [isSubmitting, setIsSubmitting] = useState(false)

  async function submit(event: FormEvent) {
    event.preventDefault()
    setIsSubmitting(true)
    try {
      onCreated(await createRelatedPartyTransaction(form))
    } catch (err) {
      setError(extractErrorMessage(err, "Unable to create transaction."))
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <Modal title="New Related-Party Transaction" onClose={onClose}>
      <form onSubmit={submit} className="space-y-3">
        <select required value={form.pool} onChange={(event) => setForm({ ...form, pool: event.target.value })} className={inputClasses}>
          <option value="">Select pool</option>
          {pools.map((pool) => <option key={pool.id} value={pool.id}>{pool.name}</option>)}
        </select>
        <input required placeholder="Related party name" value={form.related_party_name} onChange={(event) => setForm({ ...form, related_party_name: event.target.value })} className={inputClasses} />
        <select value={form.relationship_type} onChange={(event) => setForm({ ...form, relationship_type: event.target.value })} className={inputClasses}>
          {RELATIONSHIP_TYPES.map((type) => <option key={type} value={type}>{type}</option>)}
        </select>
        <input required placeholder="Transaction type" value={form.transaction_type} onChange={(event) => setForm({ ...form, transaction_type: event.target.value })} className={inputClasses} />
        <input required type="number" min="0" step="0.01" placeholder="Amount" value={form.amount} onChange={(event) => setForm({ ...form, amount: event.target.value })} className={inputClasses} />
        <input required type="date" value={form.transaction_date} onChange={(event) => setForm({ ...form, transaction_date: event.target.value })} className={inputClasses} />
        {error && <p className="text-sm text-red-400">{error}</p>}
        <div className="flex justify-end gap-2 pt-2"><Button type="button" variant="secondary" onClick={onClose}>Cancel</Button><Button type="submit" disabled={isSubmitting}>{isSubmitting ? <Spinner className="h-4 w-4" /> : "Create"}</Button></div>
      </form>
    </Modal>
  )
}