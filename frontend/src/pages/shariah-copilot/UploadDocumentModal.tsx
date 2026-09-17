import { useState, type ChangeEvent, type FormEvent } from "react"
import { Modal } from "../../components/Modal"
import { Button } from "../../components/Button"
import { Spinner } from "../../components/Spinner"
import { uploadDocument } from "../../api/shariahCopilot"
import { extractCopilotErrorMessage } from "../../api/errors"
import type { ShariahDocument } from "../../types"

interface UploadDocumentModalProps {
  onClose: () => void
  onUploaded: (document: ShariahDocument) => void
}

const DOCUMENT_TYPES = [
  { value: "policy", label: "Policy" },
  { value: "resolution", label: "Resolution" },
  { value: "guideline", label: "Guideline" },
  { value: "standard", label: "Standard" },
]

const APPROVAL_STATUSES = [
  { value: "draft", label: "Draft" },
  { value: "under_review", label: "Under Review" },
  { value: "approved", label: "Approved" },
  { value: "archived", label: "Archived" },
]

const inputClasses =
  "w-full rounded-md border border-white/10 bg-navy-800 px-3 py-2 text-sm text-ink-primary focus:border-emerald-500 focus:outline-none"
const labelClasses = "mb-1.5 block text-xs font-semibold tracking-wide text-ink-secondary uppercase"

export function UploadDocumentModal({ onClose, onUploaded }: UploadDocumentModalProps) {
  const [file, setFile] = useState<File | null>(null)
  const [documentName, setDocumentName] = useState("")
  const [documentType, setDocumentType] = useState(DOCUMENT_TYPES[0].value)
  const [approvalStatus, setApprovalStatus] = useState(APPROVAL_STATUSES[0].value)
  const [productCategory, setProductCategory] = useState("")
  const [jurisdiction, setJurisdiction] = useState("")
  const [approvedBy, setApprovedBy] = useState("")

  const [error, setError] = useState("")
  const [isSubmitting, setIsSubmitting] = useState(false)

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    setFile(event.target.files?.[0] ?? null)
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    if (!file) {
      setError("Please select a file to upload.")
      return
    }

    setError("")
    setIsSubmitting(true)
    try {
      const document = await uploadDocument({
        file,
        document_name: documentName,
        document_type: documentType,
        approval_status: approvalStatus,
        product_category: productCategory || undefined,
        jurisdiction: jurisdiction || undefined,
        approved_by: approvedBy || undefined,
      })
      onUploaded(document)
    } catch (err) {
      setError(extractCopilotErrorMessage(err, "Unable to upload document."))
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <Modal title="Upload Document" onClose={onClose}>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label htmlFor="document-file" className={labelClasses}>
            File
          </label>
          <input id="document-file" type="file" onChange={handleFileChange} required className={inputClasses} />
        </div>

        <div>
          <label htmlFor="document-name" className={labelClasses}>
            Document Name
          </label>
          <input
            id="document-name"
            type="text"
            value={documentName}
            onChange={(e) => setDocumentName(e.target.value)}
            required
            className={inputClasses}
          />
        </div>

        <div>
          <label htmlFor="document-type" className={labelClasses}>
            Document Type
          </label>
          <select
            id="document-type"
            value={documentType}
            onChange={(e) => setDocumentType(e.target.value)}
            className={inputClasses}
          >
            {DOCUMENT_TYPES.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label htmlFor="approval-status" className={labelClasses}>
            Approval Status
          </label>
          <select
            id="approval-status"
            value={approvalStatus}
            onChange={(e) => setApprovalStatus(e.target.value)}
            className={inputClasses}
          >
            {APPROVAL_STATUSES.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label htmlFor="product-category" className={labelClasses}>
            Product Category (optional)
          </label>
          <input
            id="product-category"
            type="text"
            value={productCategory}
            onChange={(e) => setProductCategory(e.target.value)}
            className={inputClasses}
          />
        </div>

        <div>
          <label htmlFor="jurisdiction" className={labelClasses}>
            Jurisdiction (optional)
          </label>
          <input
            id="jurisdiction"
            type="text"
            value={jurisdiction}
            onChange={(e) => setJurisdiction(e.target.value)}
            className={inputClasses}
          />
        </div>

        <div>
          <label htmlFor="approved-by" className={labelClasses}>
            Approved By (optional)
          </label>
          <input
            id="approved-by"
            type="text"
            value={approvedBy}
            onChange={(e) => setApprovedBy(e.target.value)}
            className={inputClasses}
          />
        </div>

        {isSubmitting && (
          <p className="text-sm text-ink-secondary">
            Uploading and indexing document... this may take up to a minute.
          </p>
        )}

        {error && <p className="text-sm text-red-400">{error}</p>}

        <div className="flex justify-end gap-2 pt-2">
          <Button type="button" variant="secondary" onClick={onClose} disabled={isSubmitting}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" disabled={isSubmitting}>
            {isSubmitting ? <Spinner className="h-4 w-4" /> : "Upload"}
          </Button>
        </div>
      </form>
    </Modal>
  )
}
