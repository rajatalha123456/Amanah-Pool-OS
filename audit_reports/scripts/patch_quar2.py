ROOT = "frontend/src/"


def edit(path, pairs):
    s = open(ROOT + path, encoding="utf-8").read()
    for old, new in pairs:
        assert old in s, (path, old[:90])
        s = s.replace(old, new, 1)
    open(ROOT + path, "w", encoding="utf-8").write(s)


edit("types/index.ts", [
    ('''  resolved_by: number | null
  resolved_at: string | null
  created_at: string
  updated_at: string
}

export interface UpdateExceptionAssigneeInput {''', '''  resolved_by: number | null
  resolved_at: string | null
  quarantine_status: "none" | "held" | "decided"
  quarantined_amount: string | null
  quarantine_reason: string
  quarantined_at: string | null
  quarantine_treatment: string
  treatment_note: string
  disclosure_note: string
  created_at: string
  updated_at: string
}

export interface UpdateExceptionAssigneeInput {'''),
])

edit("api/governance.ts", [
    ('''export async function resolveException(id: string, resolutionNotes: string): Promise<ExceptionCase> {
  const response = await apiClient.post<ExceptionCase>(`governance/exceptions/${id}/resolve/`, {
    resolution_notes: resolutionNotes,
  })
  return response.data
}

export async function dismissException(id: string, resolutionNotes: string): Promise<ExceptionCase> {
  const response = await apiClient.post<ExceptionCase>(`governance/exceptions/${id}/dismiss/`, {
    resolution_notes: resolutionNotes,
  })
  return response.data
}''', '''export async function resolveException(id: string, resolutionNotes: string, disclosureNote?: string): Promise<ExceptionCase> {
  const response = await apiClient.post<ExceptionCase>(`governance/exceptions/${id}/resolve/`, {
    resolution_notes: resolutionNotes,
    disclosure_note: disclosureNote,
  })
  return response.data
}

export async function dismissException(id: string, resolutionNotes: string, disclosureNote?: string): Promise<ExceptionCase> {
  const response = await apiClient.post<ExceptionCase>(`governance/exceptions/${id}/dismiss/`, {
    resolution_notes: resolutionNotes,
    disclosure_note: disclosureNote,
  })
  return response.data
}

/** Holds an amount of value while the case is investigated (BRD 8). */
export async function quarantineValue(id: string, amount: string, reason: string): Promise<ExceptionCase> {
  return (await apiClient.post<ExceptionCase>(`governance/exceptions/${id}/quarantine/`, { amount, reason })).data
}

/** The Shariah Board decides what happens to the held value. */
export async function decideQuarantine(id: string, treatment: string, note: string): Promise<ExceptionCase> {
  return (await apiClient.post<ExceptionCase>(`governance/exceptions/${id}/decide-quarantine/`, { treatment, note })).data
}'''),
])

edit("pages/governance/ExceptionCaseDetail.tsx", [
    ("  dismissException,\n  fetchExceptionCase,", "  decideQuarantine,\n  dismissException,\n  fetchExceptionCase,\n  quarantineValue,"),
    ('''  const canAct = user?.role === "risk_compliance"
''', '''  const canAct = user?.role === "risk_compliance"
  const canQuarantine = user?.role === "risk_compliance" || user?.role === "shariah_secretariat" || user?.role === "shariah_board"
  const isBoard = user?.role === "shariah_board"
'''),
    ('''      {canAct && exceptionCase.status === "open" && (
        <Card title="Start Investigation" className="mb-6">''', '''      {(exceptionCase.quarantine_status !== "none" || (canQuarantine && !(exceptionCase.status === "resolved" || exceptionCase.status === "dismissed"))) && (
        <QuarantineCard
          exceptionCase={exceptionCase}
          canQuarantine={canQuarantine}
          isBoard={isBoard}
          onUpdated={handleUpdated}
          onError={setActionError}
        />
      )}

      {canAct && exceptionCase.status === "open" && (
        <Card title="Start Investigation" className="mb-6">'''),
    ('''  const [notes, setNotes] = useState("")
  const [error, setError] = useState("")
  const [isSubmitting, setIsSubmitting] = useState(false)

  async function handleSubmit(mode: "resolve" | "dismiss") {
    if (!notes.trim()) {
      setError("Notes are required.")
      return
    }
    setError("")
    setIsSubmitting(true)
    try {
      const updated =
        mode === "resolve"
          ? await resolveException(exceptionCase.id, notes)
          : await dismissException(exceptionCase.id, notes)''', '''  const [notes, setNotes] = useState("")
  const [disclosure, setDisclosure] = useState("")
  const [error, setError] = useState("")
  const [isSubmitting, setIsSubmitting] = useState(false)

  async function handleSubmit(mode: "resolve" | "dismiss") {
    if (!notes.trim()) {
      setError("Notes are required.")
      return
    }
    setError("")
    setIsSubmitting(true)
    try {
      const updated =
        mode === "resolve"
          ? await resolveException(exceptionCase.id, notes, disclosure)
          : await dismissException(exceptionCase.id, notes, disclosure)'''),
    ('''      {error && <p className="text-sm text-red-400">{error}</p>}
      <div className="flex gap-2">
        <Button type="button" variant="primary" disabled={isSubmitting} onClick={() => handleSubmit("resolve")}>''', '''      {exceptionCase.quarantine_status === "decided" && (
        <div>
          <label htmlFor="disclosure-note" className={labelClasses}>
            Disclosure of the treatment of the held value
          </label>
          <textarea
            id="disclosure-note"
            value={disclosure}
            onChange={(e) => setDisclosure(e.target.value)}
            rows={2}
            className={inputClasses}
            placeholder="Where and how the treatment is disclosed (report, note or notice)"
          />
        </div>
      )}
      {error && <p className="text-sm text-red-400">{error}</p>}
      <div className="flex gap-2">
        <Button type="button" variant="primary" disabled={isSubmitting} onClick={() => handleSubmit("resolve")}>'''),
])

s = open(ROOT + "pages/governance/ExceptionCaseDetail.tsx", encoding="utf-8").read()
marker = "export function ExceptionCaseDetail() {"
card = '''const TREATMENTS: Record<string, string> = {
  release_to_pool: "Release to the pool (no non-compliance found)",
  purify: "Purify: route to charity",
  return_to_source: "Return to the source",
  write_off: "Write off at the bank's cost",
}

/** Value held while a case is investigated (BRD 8: classify, quarantine value, investigate, decide treatment, disclose). */
function QuarantineCard({
  exceptionCase,
  canQuarantine,
  isBoard,
  onUpdated,
  onError,
}: {
  exceptionCase: ExceptionCase
  canQuarantine: boolean
  isBoard: boolean
  onUpdated: (updated: ExceptionCase) => void
  onError: (error: string) => void
}) {
  const [amount, setAmount] = useState("")
  const [reason, setReason] = useState("")
  const [treatment, setTreatment] = useState("")
  const [note, setNote] = useState("")
  const [busy, setBusy] = useState(false)

  async function run(action: () => Promise<ExceptionCase>) {
    setBusy(true)
    try {
      onUpdated(await action())
    } catch (err) {
      onError(extractErrorMessage(err, "The action was refused."))
    } finally {
      setBusy(false)
    }
  }

  const status = exceptionCase.quarantine_status
  return (
    <Card title="Quarantined value" className="mb-6">
      {status === "none" && canQuarantine && (
        <form
          className="grid grid-cols-1 gap-3 sm:grid-cols-3"
          onSubmit={(e: FormEvent) => {
            e.preventDefault()
            void run(() => quarantineValue(exceptionCase.id, amount, reason))
          }}
        >
          <label className={labelClasses}>
            Amount to hold (PKR)
            <input required type="number" min="0.01" step="0.01" value={amount} onChange={(e) => setAmount(e.target.value)} className={inputClasses} />
          </label>
          <label className={`${labelClasses} sm:col-span-2`}>
            What is held and why
            <input required value={reason} onChange={(e) => setReason(e.target.value)} className={inputClasses} />
          </label>
          <div className="sm:col-span-3">
            <Button type="submit" disabled={busy}>
              Quarantine this value
            </Button>
            <span className="ml-3 text-xs text-ink-secondary">The case cannot close until the Shariah Board decides what happens to it.</span>
          </div>
        </form>
      )}

      {status !== "none" && (
        <div className="space-y-2 text-sm text-ink-primary">
          <p>
            <span className="font-semibold">PKR {Number(exceptionCase.quarantined_amount ?? 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}</span> held: {exceptionCase.quarantine_reason}
          </p>
          {status === "held" && <Badge variant="gold">Treatment not decided yet</Badge>}
          {status === "decided" && (
            <>
              <p>
                <Badge variant="emerald">Decided</Badge> {TREATMENTS[exceptionCase.quarantine_treatment] ?? exceptionCase.quarantine_treatment}
              </p>
              <p className="text-ink-secondary">Board reasoning: {exceptionCase.treatment_note}</p>
            </>
          )}
          {exceptionCase.disclosure_note && <p className="text-ink-secondary">Disclosure: {exceptionCase.disclosure_note}</p>}
        </div>
      )}

      {status === "held" && isBoard && (
        <form
          className="mt-4 grid grid-cols-1 gap-3 border-t border-white/8 pt-4 sm:grid-cols-3"
          onSubmit={(e: FormEvent) => {
            e.preventDefault()
            void run(() => decideQuarantine(exceptionCase.id, treatment, note))
          }}
        >
          <label className={labelClasses}>
            Treatment
            <select required value={treatment} onChange={(e) => setTreatment(e.target.value)} className={inputClasses}>
              <option value="">Choose a treatment</option>
              {Object.entries(TREATMENTS).map(([key, label]) => (
                <option key={key} value={key}>
                  {label}
                </option>
              ))}
            </select>
          </label>
          <label className={`${labelClasses} sm:col-span-2`}>
            Reasoning
            <input required value={note} onChange={(e) => setNote(e.target.value)} className={inputClasses} />
          </label>
          <div className="sm:col-span-3">
            <Button type="submit" disabled={busy}>
              Record the Board&apos;s decision
            </Button>
          </div>
        </form>
      )}
    </Card>
  )
}

'''
s = s.replace(marker, card + marker, 1)
open(ROOT + "pages/governance/ExceptionCaseDetail.tsx", "w", encoding="utf-8").write(s)
print("ok")
