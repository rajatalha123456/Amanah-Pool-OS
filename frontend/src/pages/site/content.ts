/**
 * Copy for the public website. Everything here describes something the platform actually does; there are no customer
 * names, quotations, performance figures or certifications, because none exist to quote.
 */

export const NAV_LINKS = [
  { label: "Operating models", href: "#models" },
  { label: "Platform", href: "#platform" },
  { label: "Release ceremony", href: "#ceremony" },
  { label: "Governance", href: "#governance" },
  { label: "AI guardrails", href: "#ai" },
  { label: "Roles", href: "#roles" },
]

export const FACTS = [
  { value: "3", label: "operating models on one ledger" },
  { value: "4", label: "separate people to release a profit run" },
  { value: "11", label: "role-based workspaces" },
  { value: "SHA-256", label: "seal on runs, reports and the audit chain" },
]

export const MODELS = [
  {
    key: "bank",
    tag: "Islamic bank pools",
    title: "Mudarabah and Wakalah pools for banks",
    body: "Daily balances weighted by approved bands, shared by the approved profit-sharing ratio, with the Mudarib share or Wakalah fee, PER / IRR reserves, a loss waterfall and purification built in.",
    points: ["Account-level balance import with control totals", "Signed runs that are never edited, only reversed and re-run", "Statements and journals produced from the signed run"],
  },
  {
    key: "investment",
    tag: "Investment pools",
    title: "Mudarabah and Musharakah for investors",
    body: "Capital in units priced at a published NAV, with subscriptions and redemptions that respect notice periods and gates, and profit or loss shared by contract.",
    points: ["Investor disclosures approved before anyone can subscribe", "Negligence cases that change how a loss is borne", "Capital accounts and statements in the investor's own portal"],
  },
  {
    key: "circle",
    tag: "Community savings",
    title: "Qard-based savings circles",
    body: "Rotating savings with sealed rules every member accepts, a draw anyone can verify afterwards, contribution tracking and payouts that need two people. No interest, no uplift, no penalty.",
    points: ["Commit-and-reveal draw with a recomputable result", "Gentle reminders; hardship goes to Shariah oversight", "Closure with a final reconciliation"],
  },
]

export const CAPABILITIES = [
  {
    icon: "calc",
    title: "Deterministic allocation",
    body: "Inputs, rule versions and results are hashed into every run. The same inputs always give the same answer, and a signed run is never edited.",
  },
  {
    icon: "people",
    title: "Maker-checker by design",
    body: "Preparer, independent checker, Shariah reviewer and authorized signatory are different people. The system refuses a second role for the same person.",
  },
  {
    icon: "scale",
    title: "Shariah governance",
    body: "A decision register, Board quorum voting, exceptions, purification and audit plans. No product or pool activates without an approved, in-force decision.",
  },
  {
    icon: "lock",
    title: "Daily and period close",
    body: "Gates are computed by the server from recorded data, then signed by role. A closed day or period stops accepting changes.",
  },
  {
    icon: "chain",
    title: "Tamper-evident audit",
    body: "A hash-chained audit log you can verify, sealed periodic reports and an evidence bundle an examiner can check independently.",
  },
  {
    icon: "spark",
    title: "AI that advises",
    body: "Every AI output is recorded with its sources, confidence and a human decision. A kill switch turns a model off. AI never posts, rules or waives.",
  },
  {
    icon: "user",
    title: "Investor and member portals",
    body: "Statements, disclosures, consents, circle membership and a download of their own data. Members see only what is theirs.",
  },
  {
    icon: "layers",
    title: "Multi-tenant, rule-pack driven",
    body: "Every record is scoped to its tenant and tested for isolation. Jurisdiction rule packs set the caps, ceilings and tax rates, not the code.",
  },
]

export const CEREMONY = [
  { role: "Finance Maker", title: "Prepare", body: "Builds the run from posted income and expenses. Nothing is typed in by hand." },
  { role: "Finance Checker", title: "Independent check", body: "Re-derives the figures and the seal. The maker cannot check their own run." },
  { role: "Shariah Board / Secretariat", title: "Shariah review", body: "Reviews the conformity of the run and its parameters." },
  { role: "Authorized Signatory", title: "Final release", body: "Releases within the approval-matrix limit. Neither maker nor checker." },
  { role: "System", title: "Journals and statements", body: "Balanced journals are posted and statements are generated from the signed run." },
]

export const GOVERNANCE = [
  { title: "Deny by default", body: "Investors and the platform administrator can call only an explicit list of endpoints. Everything else is refused before it runs." },
  { title: "Role separation", body: "The platform administrator cannot read tenant financial data. The auditor reads and never posts. Maker and checker never coincide." },
  { title: "Immutable approvals", body: "Approved ratios, weightages, rulings and signed runs cannot be edited, and nothing is hard-deleted." },
  { title: "Strong sign-in", body: "MFA, throttled sign-in, rotating refresh tokens and a blacklist on logout." },
  { title: "Privacy built in", body: "Consent records, a data download for each member, masked AI logs and a retention policy that two people approve." },
  { title: "Honest integrations", body: "Payment rails that are simulated are clearly marked and switched off in production. Nothing pretends to be a bank." },
]

export const AI_CAN = [
  "Explain a return in plain language, with sources",
  "Flag unusual yield, drift or suspicious patterns",
  "Propose reconciliation matches for a person to confirm",
  "Draft a comparison or an evidence pack for review",
]

export const AI_CANNOT = [
  "Issue a Shariah ruling",
  "Change an approved profit-sharing ratio",
  "Waive a loss or an obligation",
  "Post a financial journal",
  "Approve a related-party allocation",
]

export const ROLES = [
  { name: "Platform Super Admin", does: "Provisions tenants, users and configuration. Cannot view tenant financial data." },
  { name: "Product Manager", does: "Drafts products, rules and disclosures. Cannot approve their own configuration." },
  { name: "Pool Manager", does: "Creates pools, assigns assets, proposes allocations. Cannot approve a run." },
  { name: "Finance Maker / Checker", does: "Imports, journals and independent approval. Cannot change signed Shariah parameters." },
  { name: "Shariah Secretariat", does: "Research, document control and exception triage. No final ruling." },
  { name: "Shariah Board", does: "Approves contracts, rules, exceptions and purification." },
  { name: "Risk & Compliance", does: "Limits, KYC alerts and reporting. No profit manipulation." },
  { name: "Authorized Signatory", does: "Final release and period lock within approval limits." },
  { name: "Auditor", does: "Read-only evidence, sampling and reperformance. No operational posting." },
  { name: "Investor / Member", does: "Statements, consent, disclosures and circle membership. Own data only." },
]

export const FAQ = [
  {
    q: "Does the platform give a Shariah ruling?",
    a: "No. It enforces the rulings your Shariah Board approves and records the evidence. AI can explain and flag, but a ruling always comes from qualified people.",
  },
  {
    q: "Which regulations does it follow?",
    a: "It is designed to support SBP pool-management instructions, AAOIFI governance standards and IFSB principles through jurisdiction rule packs. Every implementation still needs its own legal and Shariah review.",
  },
  {
    q: "Does it move money?",
    a: "Staff record settlements with the bank's own reference. Live payment-rail integrations are not part of this release, and the simulated rails are disabled in production.",
  },
  {
    q: "Can one deployment serve several institutions?",
    a: "Yes. It is multi-tenant: each institution's data is isolated and covered by automated isolation tests.",
  },
]
