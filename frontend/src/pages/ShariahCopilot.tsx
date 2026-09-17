import { useEffect, useState, type FormEvent } from "react"
import { PageHeader } from "../components/PageHeader"
import { Card } from "../components/Card"
import { Badge } from "../components/Badge"
import { Button } from "../components/Button"
import { Spinner } from "../components/Spinner"
import { Table, type TableColumn } from "../components/Table"
import { useAuth } from "../api/auth"
import { askQuestion, fetchDocuments, submitReview } from "../api/shariahCopilot"
import { extractCopilotErrorMessage } from "../api/errors"
import { UploadDocumentModal } from "./shariah-copilot/UploadDocumentModal"
import type { BadgeVariant, EvidencePack, ShariahDocument } from "../types"

type CopilotTab = "ask" | "documents"

const TABS: { key: CopilotTab; label: string }[] = [
  { key: "ask", label: "Ask" },
  { key: "documents", label: "Documents" },
]

const DOCUMENT_STATUS_BADGE: Record<string, BadgeVariant> = {
  draft: "neutral",
  under_review: "gold",
  approved: "emerald",
  archived: "navy",
}

function documentStatusBadgeVariant(status: string): BadgeVariant {
  return DOCUMENT_STATUS_BADGE[status] ?? "neutral"
}

const REVIEW_STATUS_BADGE: Record<string, BadgeVariant> = {
  human_review_required: "gold",
  approved: "emerald",
  rejected: "navy",
}

function reviewStatusBadgeVariant(status: string): BadgeVariant {
  return REVIEW_STATUS_BADGE[status] ?? "neutral"
}

export function ShariahCopilot() {
  const { user } = useAuth()
  const [activeTab, setActiveTab] = useState<CopilotTab>("ask")

  const canUpload = user?.role === "shariah_board" || user?.role === "shariah_secretariat"
  const canReview = user?.role === "shariah_board"

  return (
    <div>
      <PageHeader
        title="Shariah Policy Copilot"
        subtitle="Research assistant for approved Shariah rulings — never issues a fatwa"
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

      {activeTab === "ask" && <AskTab canReview={canReview} />}
      {activeTab === "documents" && <DocumentsTab canUpload={canUpload} />}
    </div>
  )
}

function AskTab({ canReview }: { canReview: boolean }) {
  const [question, setQuestion] = useState("")
  const [isAsking, setIsAsking] = useState(false)
  const [askError, setAskError] = useState("")
  const [pack, setPack] = useState<EvidencePack | null>(null)
  const [isReviewing, setIsReviewing] = useState(false)
  const [reviewError, setReviewError] = useState("")

  async function handleAsk(event: FormEvent) {
    event.preventDefault()
    if (!question.trim()) return

    setIsAsking(true)
    setAskError("")
    setReviewError("")
    try {
      const result = await askQuestion(question)
      setPack(result)
    } catch (err) {
      setAskError(extractCopilotErrorMessage(err, "Unable to get an answer. Please try again."))
      setPack(null)
    } finally {
      setIsAsking(false)
    }
  }

  async function handleReview(approve: boolean) {
    if (!pack) return
    setIsReviewing(true)
    setReviewError("")
    try {
      // submitReview() only returns {id, review_status, reviewer_id, reviewed_at},
      // not a full EvidencePack — merge just the status in, don't replace the pack.
      const result = await submitReview(pack.id, approve)
      setPack((prev) => (prev ? { ...prev, review_status: result.review_status } : prev))
    } catch (err) {
      setReviewError(extractCopilotErrorMessage(err, "Unable to submit review. Please try again."))
    } finally {
      setIsReviewing(false)
    }
  }

  return (
    <div className="space-y-6">
      <Card>
        <form onSubmit={handleAsk} className="flex gap-2">
          <input
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="e.g. What is the policy on late payment charges?"
            className="flex-1 rounded-md border border-white/10 bg-navy-800 px-3 py-2 text-sm text-ink-primary focus:border-emerald-500 focus:outline-none"
          />
          <Button type="submit" variant="primary" disabled={isAsking || !question.trim()}>
            {isAsking ? <Spinner className="h-4 w-4" /> : "Ask"}
          </Button>
        </form>
      </Card>

      {isAsking && (
        <Card>
          <div className="flex items-center gap-3 py-4 text-ink-secondary">
            <Spinner className="h-5 w-5" />
            <span className="text-sm">Researching... this may take up to 30 seconds</span>
          </div>
        </Card>
      )}

      {!isAsking && askError && (
        <Card>
          <p className="text-sm text-red-400">{askError}</p>
        </Card>
      )}

      {!isAsking && pack && (
        <Card>
          <div className="mb-4 flex flex-wrap items-center gap-2">
            <Badge variant={reviewStatusBadgeVariant(pack.review_status)}>{pack.review_status}</Badge>
            {pack.conflict_flagged && <Badge variant="gold">Conflict Detected</Badge>}
          </div>

          {pack.is_fallback && (
            <div className="mb-4 rounded-lg border border-gold-500/30 bg-gold-500/10 px-4 py-3 text-sm text-gold-400">
              No approved ruling found for this question.
            </div>
          )}

          <p className="text-base font-medium text-ink-primary">{pack.research_summary}</p>

          {(pack.key_evidence_excerpts ?? []).length > 0 && (
            <div className="mt-5 space-y-3">
              <h3 className="text-xs font-semibold tracking-wide text-ink-secondary uppercase">Evidence</h3>
              {(pack.key_evidence_excerpts ?? []).map((excerpt, index) => (
                <div
                  key={`${excerpt.document_id}-${index}`}
                  className="rounded-lg border border-white/8 bg-navy-800 px-4 py-3"
                >
                  <p className="text-sm text-ink-primary">{excerpt.excerpt}</p>
                  <p className="mt-2 text-xs text-ink-secondary">
                    {excerpt.document_name}
                    {excerpt.citation.section_label ? ` · ${excerpt.citation.section_label}` : ""}
                  </p>
                </div>
              ))}
            </div>
          )}

          {(pack.open_issues ?? []).length > 0 && (
            <div className="mt-5">
              <h3 className="mb-2 text-xs font-semibold tracking-wide text-ink-secondary uppercase">Open Issues</h3>
              <ul className="list-disc space-y-1 pl-5 text-sm text-ink-secondary">
                {(pack.open_issues ?? []).map((issue, index) => (
                  <li key={index}>{issue}</li>
                ))}
              </ul>
            </div>
          )}

          <p className="mt-5 text-xs italic text-ink-secondary">{pack.disclaimer}</p>

          {canReview && pack.review_status === "human_review_required" && (
            <div className="mt-5 flex gap-2 border-t border-white/8 pt-4">
              <Button variant="primary" disabled={isReviewing} onClick={() => handleReview(true)}>
                {isReviewing ? <Spinner className="h-4 w-4" /> : "Approve"}
              </Button>
              <Button variant="secondary" disabled={isReviewing} onClick={() => handleReview(false)}>
                Reject
              </Button>
            </div>
          )}

          {reviewError && <p className="mt-3 text-sm text-red-400">{reviewError}</p>}
        </Card>
      )}
    </div>
  )
}

function DocumentsTab({ canUpload }: { canUpload: boolean }) {
  const [documents, setDocuments] = useState<ShariahDocument[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [loadError, setLoadError] = useState("")
  const [isModalOpen, setIsModalOpen] = useState(false)

  function loadDocuments() {
    setIsLoading(true)
    setLoadError("")
    fetchDocuments(true)
      .then(setDocuments)
      .catch((err) => setLoadError(extractCopilotErrorMessage(err, "Unable to load documents.")))
      .finally(() => setIsLoading(false))
  }

  useEffect(() => {
    loadDocuments()
  }, [])

  const columns: TableColumn<ShariahDocument>[] = [
    { header: "Name", accessor: (doc) => doc.document_name },
    { header: "Type", accessor: (doc) => doc.document_type },
    { header: "Version", accessor: (doc) => doc.version },
    {
      header: "Status",
      accessor: (doc) => (
        <Badge variant={documentStatusBadgeVariant(doc.approval_status)}>{doc.approval_status}</Badge>
      ),
    },
    { header: "Product Category", accessor: (doc) => doc.product_category ?? "—" },
  ]

  return (
    <div>
      {canUpload && (
        <div className="mb-4 flex justify-end">
          <Button variant="primary" onClick={() => setIsModalOpen(true)}>
            + Upload Document
          </Button>
        </div>
      )}

      {isLoading && (
        <div className="flex items-center gap-2 py-12 text-ink-secondary">
          <Spinner className="h-5 w-5" />
          <span className="text-sm">Loading documents...</span>
        </div>
      )}

      {!isLoading && loadError && (
        <Card>
          <p className="text-sm text-red-400">{loadError}</p>
        </Card>
      )}

      {!isLoading && !loadError && (
        <Card>
          {documents.length === 0 ? (
            <p className="text-sm text-ink-secondary">No documents uploaded yet.</p>
          ) : (
            <Table columns={columns} data={documents} keyField={(doc) => doc.id} />
          )}
        </Card>
      )}

      {isModalOpen && (
        <UploadDocumentModal
          onClose={() => setIsModalOpen(false)}
          onUploaded={() => {
            setIsModalOpen(false)
            loadDocuments()
          }}
        />
      )}
    </div>
  )
}
