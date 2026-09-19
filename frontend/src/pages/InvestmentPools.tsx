import { useEffect, useState, type FormEvent } from "react"
import { Link } from "react-router-dom"
import { Badge } from "../components/Badge"
import { Button } from "../components/Button"
import { Card } from "../components/Card"
import { Modal } from "../components/Modal"
import { PageHeader } from "../components/PageHeader"
import { Spinner } from "../components/Spinner"
import { Table, type TableColumn } from "../components/Table"
import { useAuth } from "../api/auth"
import {
  createCapitalAccount,
  createNAVSnapshot,
  fetchCapitalAccounts,
  fetchLatestNAV,
  fetchNAVSnapshots,
  publishNAVSnapshot,
  redeem,
  subscribe,
} from "../api/investments"
import { fetchPools } from "../api/pools"
import {
  createInvestorProfile,
  fetchInvestorProfile,
  updateInvestorProfile,
  verifyInvestorKYC,
} from "../api/investorProfile"
import { extractErrorMessage } from "../api/errors"
import type {
  BadgeVariant,
  CapitalAccount,
  CreateCapitalAccountInput,
  InvestorProfile,
  InvestorProfileInput,
  NAVSnapshot,
  Pool,
} from "../types"

type Tab = "accounts" | "nav"
type ModalMode = "account" | "subscribe" | "redeem" | "nav" | null

const inputClasses =
  "w-full rounded-md border border-white/10 bg-navy-800 px-3 py-2 text-sm text-ink-primary focus:border-emerald-500 focus:outline-none"
const labelClasses = "mb-1.5 block text-xs font-semibold tracking-wide text-ink-secondary uppercase"

const NAV_STATUS_BADGE: Record<string, BadgeVariant> = {
  draft: "neutral",
  published: "emerald",
}

function navStatusBadgeVariant(status: string): BadgeVariant {
  return NAV_STATUS_BADGE[status] ?? "neutral"
}

export function InvestmentPools() {
  const { user } = useAuth()
  const isFinanceMaker = user?.role === "finance_maker"
  const isFinanceChecker = user?.role === "finance_checker"

  const [pools, setPools] = useState<Pool[]>([])
  const [selectedPoolId, setSelectedPoolId] = useState("")
  const [accounts, setAccounts] = useState<CapitalAccount[]>([])
  const [snapshots, setSnapshots] = useState<NAVSnapshot[]>([])
  const [latestNAV, setLatestNAV] = useState<NAVSnapshot | null>(null)
  const [activeTab, setActiveTab] = useState<Tab>("accounts")
  const [expandedAccountId, setExpandedAccountId] = useState<string | null>(null)
  const [modalMode, setModalMode] = useState<ModalMode>(null)
  const [selectedAccount, setSelectedAccount] = useState<CapitalAccount | null>(null)
  const [pageError, setPageError] = useState("")
  const [actionError, setActionError] = useState("")
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [profiles, setProfiles] = useState<Record<string, InvestorProfile | null>>({})
  const [profileLoading, setProfileLoading] = useState<Record<string, boolean>>({})

  useEffect(() => {
    fetchPools()
      .then((data) => {
        const investmentPools = data.filter(
          (pool) => pool.product_detail?.operating_model === "investment_pool",
        )
        setPools(investmentPools)
        setSelectedPoolId(investmentPools[0]?.id ?? "")
      })
      .catch((error) => setPageError(extractErrorMessage(error, "Unable to load investment pools.")))
      .finally(() => setIsLoading(false))
  }, [])

  useEffect(() => {
    if (!selectedPoolId) {
      setAccounts([])
      setSnapshots([])
      setLatestNAV(null)
      return
    }

    setIsLoading(true)
    setPageError("")
    Promise.all([
      fetchCapitalAccounts(selectedPoolId),
      fetchNAVSnapshots(selectedPoolId),
      fetchLatestNAV(selectedPoolId),
    ])
      .then(([accountData, snapshotData, latestData]) => {
        setAccounts(accountData)
        setSnapshots(snapshotData)
        setLatestNAV(latestData)
      })
      .catch((error) => setPageError(extractErrorMessage(error, "Unable to load investment data.")))
      .finally(() => setIsLoading(false))
  }, [selectedPoolId])

  function closeModal() {
    setModalMode(null)
    setSelectedAccount(null)
    setActionError("")
  }

  function openAccountAction(mode: "subscribe" | "redeem", account: CapitalAccount) {
    setSelectedAccount(account)
    setActionError("")
    setModalMode(mode)
  }

  async function expandAccount(account: CapitalAccount) {
    setExpandedAccountId((current) => current === account.id ? null : account.id)
    if (profiles[account.id] !== undefined || profileLoading[account.id]) return
    setProfileLoading((current) => ({ ...current, [account.id]: true }))
    try {
      const profile = await fetchInvestorProfile(account.id)
      setProfiles((current) => ({ ...current, [account.id]: profile }))
    } catch (error) {
      setActionError(extractErrorMessage(error, "Unable to load investor KYC profile."))
    } finally {
      setProfileLoading((current) => ({ ...current, [account.id]: false }))
    }
  }

  function handleProfileSaved(profile: InvestorProfile) {
    setProfiles((current) => ({ ...current, [profile.capital_account]: profile }))
  }

  async function refreshInvestmentData() {
    if (!selectedPoolId) return
    const [accountData, snapshotData, latestData] = await Promise.all([
      fetchCapitalAccounts(selectedPoolId),
      fetchNAVSnapshots(selectedPoolId),
      fetchLatestNAV(selectedPoolId),
    ])
    setAccounts(accountData)
    setSnapshots(snapshotData)
    setLatestNAV(latestData)
  }

  async function handleCreateAccount(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    setActionError("")
    setIsSaving(true)
    try {
      const data: CreateCapitalAccountInput = {
        pool: selectedPoolId,
        investor_name: String(form.get("investor_name")),
        investor_reference: String(form.get("investor_reference")),
      }
      await createCapitalAccount(data)
      await refreshInvestmentData()
      closeModal()
    } catch (error) {
      setActionError(extractErrorMessage(error, "Unable to create capital account."))
    } finally {
      setIsSaving(false)
    }
  }

  async function handleSubscribe(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!selectedAccount) return
    const form = new FormData(event.currentTarget)
    setActionError("")
    setIsSaving(true)
    try {
      await subscribe(selectedAccount.id, {
        amount: String(form.get("amount")),
        transaction_date: String(form.get("transaction_date")),
      })
      await refreshInvestmentData()
      closeModal()
    } catch (error) {
      setActionError(extractErrorMessage(error, "Unable to process subscription."))
    } finally {
      setIsSaving(false)
    }
  }

  async function handleRedeem(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!selectedAccount) return
    const form = new FormData(event.currentTarget)
    setActionError("")
    setIsSaving(true)
    try {
      await redeem(selectedAccount.id, {
        units_redeemed: String(form.get("units_redeemed")),
        transaction_date: String(form.get("transaction_date")),
      })
      await refreshInvestmentData()
      closeModal()
    } catch (error) {
      setActionError(extractErrorMessage(error, "Unable to process redemption."))
    } finally {
      setIsSaving(false)
    }
  }

  async function handleCreateNAV(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    setActionError("")
    setIsSaving(true)
    try {
      await createNAVSnapshot({
        pool: selectedPoolId,
        valuation_date: String(form.get("valuation_date")),
        total_pool_value: String(form.get("total_pool_value")),
      })
      await refreshInvestmentData()
      closeModal()
    } catch (error) {
      setActionError(extractErrorMessage(error, "Unable to create NAV snapshot."))
    } finally {
      setIsSaving(false)
    }
  }

  async function handlePublish(snapshot: NAVSnapshot) {
    setActionError("")
    setIsSaving(true)
    try {
      await publishNAVSnapshot(snapshot.id)
      await refreshInvestmentData()
    } catch (error) {
      setActionError(extractErrorMessage(error, "Unable to publish NAV snapshot."))
    } finally {
      setIsSaving(false)
    }
  }

  const hasPublishedNAV = latestNAV !== null
  const accountColumns: TableColumn<CapitalAccount>[] = [
    { header: "Investor Reference", accessor: (account) => account.investor_reference },
    { header: "Investor Name", accessor: (account) => account.investor_name },
    { header: "Units Held", accessor: (account) => account.units_held },
    { header: "Status", accessor: (account) => <Badge variant="emerald">{account.status}</Badge> },
  ]
  const navColumns: TableColumn<NAVSnapshot>[] = [
    { header: "Valuation Date", accessor: (snapshot) => snapshot.valuation_date },
    { header: "Total Pool Value", accessor: (snapshot) => snapshot.total_pool_value },
    { header: "NAV Per Unit", accessor: (snapshot) => snapshot.nav_per_unit },
    {
      header: "Status",
      accessor: (snapshot) => (
        <Badge variant={navStatusBadgeVariant(snapshot.status)}>{snapshot.status}</Badge>
      ),
    },
    {
      header: "Action",
      accessor: (snapshot) =>
        snapshot.status === "draft" && isFinanceChecker ? (
          <Button
            variant="outline"
            onClick={(event) => {
              event.stopPropagation()
              void handlePublish(snapshot)
            }}
            disabled={isSaving}
          >
            Publish
          </Button>
        ) : null,
    },
  ]

  return (
    <div>
      <PageHeader
        title="Investment Pools"
        subtitle="Manage capital accounts and published unit valuations"
        actions={
          <div className="flex items-center gap-3">
            <select
              value={selectedPoolId}
              onChange={(event) => setSelectedPoolId(event.target.value)}
              className="rounded-md border border-white/10 bg-navy-800 px-3 py-2 text-sm text-ink-primary focus:border-emerald-500 focus:outline-none"
              disabled={pools.length === 0}
            >
              {pools.length === 0 ? <option value="">No investment pools</option> : null}
              {pools.map((pool) => (
                <option key={pool.id} value={pool.id}>
                  {pool.name} ({pool.code})
                </option>
              ))}
            </select>
          </div>
        }
      />

      {pageError && <p className="mb-4 text-sm text-red-400">{pageError}</p>}
      {actionError && <p className="mb-4 text-sm text-red-400">{actionError}</p>}

      {isLoading ? (
        <div className="flex items-center gap-2 py-12 text-ink-secondary">
          <Spinner className="h-5 w-5" />
          Loading investment data...
        </div>
      ) : pools.length === 0 ? (
        <Card>
          <p className="text-sm text-ink-secondary">No investment pools available.</p>
        </Card>
      ) : (
        <>
          <Card className="mb-6">
            <p className="mb-1 text-xs font-semibold tracking-wide text-ink-secondary uppercase">Current NAV</p>
            {latestNAV ? (
              <div className="flex flex-wrap items-baseline gap-3">
                <span className="text-3xl font-semibold text-ink-primary">{latestNAV.nav_per_unit}</span>
                <span className="text-sm text-ink-secondary">as of {latestNAV.valuation_date}</span>
              </div>
            ) : (
              <p className="text-sm text-gold-400">No NAV published yet for this pool</p>
            )}
          </Card>

          <div className="mb-4 flex gap-4 border-b border-white/8 text-sm">
            <button
              type="button"
              onClick={() => setActiveTab("accounts")}
              className={`border-b-2 px-1 pb-2 ${activeTab === "accounts" ? "border-emerald-500 text-ink-primary" : "border-transparent text-ink-secondary"}`}
            >
              Capital Accounts
            </button>
            <button
              type="button"
              onClick={() => setActiveTab("nav")}
              className={`border-b-2 px-1 pb-2 ${activeTab === "nav" ? "border-emerald-500 text-ink-primary" : "border-transparent text-ink-secondary"}`}
            >
              NAV History
            </button>
          </div>

          {activeTab === "accounts" ? (
            <Card
              title="Capital Accounts"
              className="relative"
            >
              <div className="mb-4 flex justify-end">
                <Button variant="primary" onClick={() => setModalMode("account")}>+ New Account</Button>
              </div>
              {accounts.length === 0 ? (
                <p className="text-sm text-ink-secondary">No capital accounts for this pool yet.</p>
              ) : (
                <>
                  <Table
                    columns={accountColumns}
                    data={accounts}
                    keyField={(account) => account.id}
                    onRowClick={(account) => void expandAccount(account)}
                  />
                  {expandedAccountId && (
                    <div className="mt-3 rounded-md border border-white/8 bg-navy-800 p-4 text-sm">
                      {accounts.filter((account) => account.id === expandedAccountId).map((account) => (
                        <div key={account.id} className="space-y-4">
                          {profileLoading[account.id] ? (
                            <div className="flex items-center gap-2 text-sm text-ink-secondary"><Spinner className="h-4 w-4" /> Loading KYC profile...</div>
                          ) : (
                            <InvestorKYCSection
                              account={account}
                              profile={profiles[account.id] ?? null}
                              isFinanceMaker={isFinanceMaker}
                              isRiskCompliance={user?.role === "risk_compliance"}
                              onSaved={handleProfileSaved}
                            />
                          )}
                          <div className="flex flex-wrap items-center justify-between gap-3 border-t border-white/8 pt-4">
                            <span className="text-ink-secondary">Select an action for {account.investor_name}</span>
                            <div className="flex gap-2">
                              <Link
                                to={`/investments/capital-accounts/${account.id}`}
                                className="rounded-md border border-white/10 px-3 py-2 text-sm text-ink-secondary hover:text-ink-primary"
                                onClick={(event) => event.stopPropagation()}
                              >
                                View Portfolio Summary
                              </Link>
                              {isFinanceMaker && (() => {
                                const kycVerified = profiles[account.id]?.kyc_status === "verified"
                                const disabledReason = !kycVerified ? "KYC verification required" : !hasPublishedNAV ? "Publish a NAV snapshot first" : undefined
                                return (
                                  <Button
                                    variant="outline"
                                    disabled={Boolean(disabledReason)}
                                    title={disabledReason}
                                    onClick={() => openAccountAction("subscribe", account)}
                                  >
                                    Subscribe
                                  </Button>
                                )
                              })()}
                              {isFinanceChecker && (
                                <Button
                                  variant="gold"
                                  disabled={!hasPublishedNAV}
                                  title={!hasPublishedNAV ? "Publish a NAV snapshot first" : undefined}
                                  onClick={() => openAccountAction("redeem", account)}
                                >
                                  Redeem
                                </Button>
                              )}
                            </div>
                            {!profiles[account.id] && <p className="basis-full text-xs text-gold-400">KYC verification required</p>}
                            {profiles[account.id] && profiles[account.id]?.kyc_status !== "verified" && <p className="basis-full text-xs text-gold-400">KYC verification required</p>}
                            {!profiles[account.id] && hasPublishedNAV === false ? <p className="basis-full text-xs text-gold-400">Publish a NAV snapshot first</p> : null}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </>
              )}
            </Card>
          ) : (
            <Card title="NAV History">
              <div className="mb-4 flex justify-end">
                {isFinanceMaker && <Button variant="primary" onClick={() => setModalMode("nav")}>+ New NAV Snapshot</Button>}
              </div>
              {snapshots.length === 0 ? (
                <p className="text-sm text-ink-secondary">No NAV snapshots for this pool yet.</p>
              ) : (
                <Table columns={navColumns} data={snapshots} keyField={(snapshot) => snapshot.id} />
              )}
            </Card>
          )}
        </>
      )}

      {modalMode === "account" && (
        <Modal title="New Capital Account" onClose={closeModal}>
          <form onSubmit={handleCreateAccount} className="space-y-4">
            <label className={labelClasses}>Investor Reference<input name="investor_reference" required className={inputClasses} /></label>
            <label className={labelClasses}>Investor Name<input name="investor_name" required className={inputClasses} /></label>
            {actionError && <p className="text-sm text-red-400">{actionError}</p>}
            <Button type="submit" disabled={isSaving}>{isSaving ? <Spinner className="h-4 w-4" /> : "Create Account"}</Button>
          </form>
        </Modal>
      )}

      {(modalMode === "subscribe" || modalMode === "redeem") && selectedAccount && latestNAV && (
        <Modal title={modalMode === "subscribe" ? "Subscribe" : "Redeem"} onClose={closeModal}>
          <form onSubmit={modalMode === "subscribe" ? handleSubscribe : handleRedeem} className="space-y-4">
            <p className="rounded-md border border-emerald-500/20 bg-emerald-500/5 p-3 text-sm text-emerald-300">
              Uses latest published NAV: {latestNAV.nav_per_unit}
            </p>
            <label className={labelClasses}>
              {modalMode === "subscribe" ? "Amount" : "Units Redeemed"}
              <input name={modalMode === "subscribe" ? "amount" : "units_redeemed"} type="number" step="0.000001" min="0" required className={inputClasses} />
            </label>
            <label className={labelClasses}>Transaction Date<input name="transaction_date" type="date" required className={inputClasses} /></label>
            {actionError && <p className="text-sm text-red-400">{actionError}</p>}
            <Button type="submit" disabled={isSaving}>{isSaving ? <Spinner className="h-4 w-4" /> : modalMode === "subscribe" ? "Process Subscription" : "Process Redemption"}</Button>
          </form>
        </Modal>
      )}

      {modalMode === "nav" && (
        <Modal title="New NAV Snapshot" onClose={closeModal}>
          <form onSubmit={handleCreateNAV} className="space-y-4">
            <label className={labelClasses}>Valuation Date<input name="valuation_date" type="date" required className={inputClasses} /></label>
            <label className={labelClasses}>Total Pool Value<input name="total_pool_value" type="number" step="0.01" min="0" required className={inputClasses} /></label>
            {actionError && <p className="text-sm text-red-400">{actionError}</p>}
            <Button type="submit" disabled={isSaving}>{isSaving ? <Spinner className="h-4 w-4" /> : "Create Snapshot"}</Button>
          </form>
        </Modal>
      )}
    </div>
  )
}

function InvestorKYCSection({
  account,
  profile,
  isFinanceMaker,
  isRiskCompliance,
  onSaved,
}: {
  account: CapitalAccount
  profile: InvestorProfile | null
  isFinanceMaker: boolean
  isRiskCompliance: boolean
  onSaved: (profile: InvestorProfile) => void
}) {
  const [form, setForm] = useState<InvestorProfileInput>({
    capital_account: account.id,
    id_document_type: profile?.id_document_type ?? "passport",
    id_document_number: profile?.id_document_number ?? "",
    date_of_birth: profile?.date_of_birth ?? "",
    address: profile?.address ?? "",
    risk_tolerance: profile?.risk_tolerance ?? "moderate",
    suitability_assessment_notes: profile?.suitability_assessment_notes ?? "",
  })
  const [verificationNotes, setVerificationNotes] = useState("")
  const [error, setError] = useState("")
  const [isSaving, setIsSaving] = useState(false)

  useEffect(() => {
    setForm({
      capital_account: account.id,
      id_document_type: profile?.id_document_type ?? "passport",
      id_document_number: profile?.id_document_number ?? "",
      date_of_birth: profile?.date_of_birth ?? "",
      address: profile?.address ?? "",
      risk_tolerance: profile?.risk_tolerance ?? "moderate",
      suitability_assessment_notes: profile?.suitability_assessment_notes ?? "",
    })
  }, [account.id, profile])

  async function saveProfile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setIsSaving(true)
    setError("")
    try {
      const saved = profile
        ? await updateInvestorProfile(profile.id, form)
        : await createInvestorProfile(form)
      onSaved(saved)
    } catch (saveError) {
      setError(extractErrorMessage(saveError, "Unable to save investor KYC profile."))
    } finally {
      setIsSaving(false)
    }
  }

  async function verify(status: "verified" | "rejected") {
    if (!profile) return
    setIsSaving(true)
    setError("")
    try {
      const saved = await verifyInvestorKYC(profile.id, {
        kyc_status: status,
        notes: verificationNotes,
      })
      onSaved(saved)
      setVerificationNotes("")
    } catch (verifyError) {
      setError(extractErrorMessage(verifyError, "Unable to verify KYC profile."))
    } finally {
      setIsSaving(false)
    }
  }

  function updateField(field: keyof InvestorProfileInput, value: string) {
    setForm((current) => ({ ...current, [field]: value }))
  }

  return (
    <div className="rounded-md border border-white/8 bg-navy-900 p-4">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-xs font-semibold tracking-wide text-ink-secondary uppercase">KYC</h3>
        <Badge variant={profile?.kyc_status === "verified" ? "emerald" : profile?.kyc_status === "rejected" ? "navy" : "gold"}>
          {profile?.kyc_status ?? "not_started"}
        </Badge>
      </div>

      {isFinanceMaker ? (
        <form onSubmit={saveProfile} className="grid gap-3 md:grid-cols-2">
          <label className={labelClasses}>Document Type<select value={form.id_document_type} onChange={(event) => updateField("id_document_type", event.target.value)} className={inputClasses}><option value="passport">Passport</option><option value="national_id">National ID</option><option value="driving_license">Driving License</option></select></label>
          <label className={labelClasses}>Document Number<input required value={form.id_document_number} onChange={(event) => updateField("id_document_number", event.target.value)} className={inputClasses} /></label>
          <label className={labelClasses}>Date of Birth<input required type="date" value={form.date_of_birth} onChange={(event) => updateField("date_of_birth", event.target.value)} className={inputClasses} /></label>
          <label className={labelClasses}>Risk Tolerance<select value={form.risk_tolerance} onChange={(event) => updateField("risk_tolerance", event.target.value as InvestorProfileInput["risk_tolerance"])} className={inputClasses}><option value="conservative">Conservative</option><option value="moderate">Moderate</option><option value="aggressive">Aggressive</option></select></label>
          <label className={`${labelClasses} md:col-span-2`}>Address<textarea required rows={2} value={form.address} onChange={(event) => updateField("address", event.target.value)} className={inputClasses} /></label>
          <label className={`${labelClasses} md:col-span-2`}>Suitability Notes<textarea rows={2} value={form.suitability_assessment_notes ?? ""} onChange={(event) => updateField("suitability_assessment_notes", event.target.value)} className={inputClasses} /></label>
          <div className="md:col-span-2"><Button type="submit" disabled={isSaving}>{isSaving ? <Spinner className="h-4 w-4" /> : profile ? "Save KYC Profile" : "Create KYC Profile"}</Button></div>
        </form>
      ) : !profile ? (
        <p className="text-sm text-ink-secondary">No KYC profile has been created.</p>
      ) : null}

      {isRiskCompliance && profile && (
        <div className="mt-4 space-y-3 border-t border-white/8 pt-4">
          <textarea rows={2} placeholder="Verification notes" value={verificationNotes} onChange={(event) => setVerificationNotes(event.target.value)} className={inputClasses} />
          <div className="flex flex-wrap gap-2">
            <Button variant="primary" disabled={isSaving} onClick={() => void verify("verified")}>Verify KYC</Button>
            <Button variant="outline" disabled={isSaving} onClick={() => void verify("rejected")}>Reject KYC</Button>
          </div>
        </div>
      )}
      {error && <p className="mt-3 text-sm text-red-400">{error}</p>}
    </div>
  )
}
