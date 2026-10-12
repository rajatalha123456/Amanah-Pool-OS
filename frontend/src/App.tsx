import { lazy, Suspense, type ReactNode } from "react"
import { Navigate, Route, Routes } from "react-router-dom"
import { AppLayout } from "./layouts/AppLayout"
const CommandCenter = lazy(() => import("./pages/CommandCenter").then((m) => ({ default: m.CommandCenter })))
const ProductCatalogue = lazy(() => import("./pages/ProductCatalogue").then((m) => ({ default: m.ProductCatalogue })))
const ContractTemplateStudio = lazy(() => import("./pages/ContractTemplateStudio").then((m) => ({ default: m.ContractTemplateStudio })))
const PoolCatalogue = lazy(() => import("./pages/PoolCatalogue").then((m) => ({ default: m.PoolCatalogue })))
const PoolDetail = lazy(() => import("./pages/PoolDetail").then((m) => ({ default: m.PoolDetail })))
const NewPoolWizard = lazy(() => import("./pages/NewPoolWizard").then((m) => ({ default: m.NewPoolWizard })))
const AssetRegistry = lazy(() => import("./pages/AssetRegistry").then((m) => ({ default: m.AssetRegistry })))
const DailyOperationsCockpit = lazy(() => import("./pages/DailyOperationsCockpit").then((m) => ({ default: m.DailyOperationsCockpit })))
const AllocationSimulator = lazy(() => import("./pages/AllocationSimulator").then((m) => ({ default: m.AllocationSimulator })))
const AllocationRunDetail = lazy(() => import("./pages/AllocationRunDetail").then((m) => ({ default: m.AllocationRunDetail })))
const FinanceLedger = lazy(() => import("./pages/FinanceLedger").then((m) => ({ default: m.FinanceLedger })))
const StatementView = lazy(() => import("./pages/StatementView").then((m) => ({ default: m.StatementView })))
const ShariahCopilot = lazy(() => import("./pages/ShariahCopilot").then((m) => ({ default: m.ShariahCopilot })))
const ShariahGovernance = lazy(() => import("./pages/ShariahGovernance").then((m) => ({ default: m.ShariahGovernance })))
const InvestmentPools = lazy(() => import("./pages/InvestmentPools").then((m) => ({ default: m.InvestmentPools })))
const CommunityCircles = lazy(() => import("./pages/CommunityCircles").then((m) => ({ default: m.CommunityCircles })))
const MemberMobileHome = lazy(() => import("./pages/circles/MemberMobileHome").then((m) => ({ default: m.MemberMobileHome })))
const ContributionReceipt = lazy(() => import("./pages/circles/ContributionReceipt").then((m) => ({ default: m.ContributionReceipt })))
const CapitalAccountDetail = lazy(() => import("./pages/investments/CapitalAccountDetail").then((m) => ({ default: m.CapitalAccountDetail })))
const ExceptionCaseDetail = lazy(() => import("./pages/governance/ExceptionCaseDetail").then((m) => ({ default: m.ExceptionCaseDetail })))
const UserAdministration = lazy(() => import("./pages/UserAdministration").then((m) => ({ default: m.UserAdministration })))
const AuditorPortal = lazy(() => import("./pages/AuditorPortal").then((m) => ({ default: m.AuditorPortal })))
const RestatementWizard = lazy(() => import("./pages/RestatementWizard").then((m) => ({ default: m.RestatementWizard })))
const MudaribHibaSimulator = lazy(() => import("./pages/MudaribHibaSimulator").then((m) => ({ default: m.MudaribHibaSimulator })))
const ReconciliationCenter = lazy(() => import("./pages/ReconciliationCenter").then((m) => ({ default: m.ReconciliationCenter })))
const PeriodCloseManager = lazy(() => import("./pages/PeriodCloseManager").then((m) => ({ default: m.PeriodCloseManager })))
const ShariahAuditPlan = lazy(() => import("./pages/governance/ShariahAuditPlan").then((m) => ({ default: m.ShariahAuditPlan })))
const JurisdictionRulePacks = lazy(() => import("./pages/administration/JurisdictionRulePacks").then((m) => ({ default: m.JurisdictionRulePacks })))
const RiskLimitDashboard = lazy(() => import("./pages/RiskLimitDashboard").then((m) => ({ default: m.RiskLimitDashboard })))
const PayoutExecutionEngine = lazy(() => import("./pages/PayoutExecutionEngine").then((m) => ({ default: m.PayoutExecutionEngine })))
const IncomeExpenseWorkbench = lazy(() => import("./pages/IncomeExpenseWorkbench").then((m) => ({ default: m.IncomeExpenseWorkbench })))
const GovernanceConfig = lazy(() => import("./pages/GovernanceConfig").then((m) => ({ default: m.GovernanceConfig })))
const Notifications = lazy(() => import("./pages/Notifications").then((m) => ({ default: m.Notifications })))
const ParticipantRegistry = lazy(() => import("./pages/ParticipantRegistry").then((m) => ({ default: m.ParticipantRegistry })))
import { SignIn } from "./pages/auth/SignIn"
import { VerifyMfa } from "./pages/auth/VerifyMfa"
import { ProtectedRoute } from "./components/ProtectedRoute"
import { useAuth } from "./api/auth"
const InvestorPortal = lazy(() => import("./pages/InvestorPortal").then((m) => ({ default: m.InvestorPortal })))
const SitePage = lazy(() => import("./pages/site/SitePage").then((m) => ({ default: m.SitePage })))
import { navItems } from "./layouts/navItems"

const CUSTOM_ROUTES: Record<string, ReactNode> = {
  "/products-pools": <ProductCatalogue />,
  "/risk-compliance": <AssetRegistry />,
  "/participants": <ParticipantRegistry />,
  "/governance-config": <GovernanceConfig />,
  "/daily-operations": <DailyOperationsCockpit />,
  "/allocation-engine": <AllocationSimulator />,
  "/finance-ledger": <FinanceLedger />,
  "/ai-analytics": <ShariahCopilot />,
  "/shariah-governance": <ShariahGovernance />,
  "/investments": <InvestmentPools />,
  "/community-circles": <CommunityCircles />,
  "/reports": <AuditorPortal />,
  "/administration": <UserAdministration />,
}

function HomeRoute() {
  const { user } = useAuth()
  return user?.role === "investor_member" ? <InvestorPortal /> : <CommandCenter />
}

function App() {
  return (
    <Suspense fallback={<div className="p-8 text-sm text-ink-secondary">Loading...</div>}>
    <Routes>
      <Route path="/welcome" element={<SitePage />} />
      <Route path="/login" element={<SignIn />} />
      <Route path="/verify-mfa" element={<VerifyMfa />} />

      <Route
        element={
          <ProtectedRoute>
            <AppLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<HomeRoute />} />
        <Route path="notifications" element={<Notifications />} />
        <Route path="pools" element={<PoolCatalogue />} />
        <Route path="pools/new" element={<NewPoolWizard />} />
        <Route path="pools/:id" element={<PoolDetail />} />
        <Route path="pools/:id/versions" element={<PoolDetail initialTab="versions" />} />
        <Route path="pool-versions/:id" element={<PoolDetail initialTab="versions" />} />
        <Route path="allocation-simulator" element={<AllocationSimulator />} />
        <Route path="allocation-runs/:id" element={<AllocationRunDetail />} />
        <Route path="allocation-runs/:id/restate" element={<RestatementWizard />} />
        <Route path="statements/:id" element={<StatementView />} />
        <Route path="restatement-wizard/:runId" element={<RestatementWizard />} />
        <Route path="reconciliation" element={<ReconciliationCenter />} />
        <Route path="period-close" element={<PeriodCloseManager />} />
        <Route path="period-close/:poolId" element={<PeriodCloseManager />} />
        <Route path="shariah-audit-plan" element={<ShariahAuditPlan />} />
        <Route path="jurisdiction-rule-packs" element={<JurisdictionRulePacks />} />
        <Route path="investments/capital-accounts/:id" element={<CapitalAccountDetail />} />
        <Route path="circles/members/:id" element={<MemberMobileHome />} />
        <Route path="circles/contributions/:id/receipt" element={<ContributionReceipt />} />
        <Route path="exceptions/:id" element={<ExceptionCaseDetail />} />
        <Route path="contract-templates" element={<ContractTemplateStudio />} />

        {/* Shorthand URL Aliases */}
        <Route path="operations" element={<DailyOperationsCockpit />} />
        <Route path="balance-import" element={<DailyOperationsCockpit />} />
        <Route path="circles" element={<CommunityCircles />} />
        <Route path="governance" element={<ShariahGovernance />} />
        <Route path="copilot" element={<ShariahCopilot />} />
        <Route path="allocation" element={<AllocationSimulator />} />
        <Route path="audit" element={<AuditorPortal />} />
        <Route path="users" element={<UserAdministration />} />
        <Route path="mudarib-fee-optimization" element={<MudaribHibaSimulator />} />
        <Route path="hiba-simulator" element={<MudaribHibaSimulator />} />
        <Route path="allocation-runs/:id/hiba" element={<MudaribHibaSimulator />} />
        <Route path="risk-dashboard" element={<RiskLimitDashboard />} />
        <Route path="risk-limits" element={<RiskLimitDashboard />} />
        <Route path="concentration-risk" element={<RiskLimitDashboard />} />
        <Route path="shariah-quorum" element={<ShariahGovernance initialTab="quorum-ceremony" />} />
        <Route path="quorum-ceremony" element={<ShariahGovernance initialTab="quorum-ceremony" />} />
        <Route path="fatwa-seal" element={<ShariahGovernance initialTab="quorum-ceremony" />} />
        <Route path="payouts" element={<PayoutExecutionEngine />} />
        <Route path="payout-clearing" element={<PayoutExecutionEngine />} />
        <Route path="clearing-rails" element={<PayoutExecutionEngine />} />
        <Route path="clearing-engine" element={<PayoutExecutionEngine />} />
        <Route path="audit-trail" element={<AuditorPortal initialTab="merkle-trail" />} />
        <Route path="forensic-audit" element={<AuditorPortal initialTab="merkle-trail" />} />
        <Route path="merkle-audit" element={<AuditorPortal initialTab="merkle-trail" />} />
        <Route path="evidence-bundle" element={<AuditorPortal initialTab="evidence-bundle" />} />
        <Route path="evidence-builder" element={<AuditorPortal initialTab="evidence-bundle" />} />
        <Route path="audit-dossier" element={<AuditorPortal initialTab="evidence-bundle" />} />
        <Route path="income-expense" element={<IncomeExpenseWorkbench />} />
        <Route path="income-expense-workbench" element={<IncomeExpenseWorkbench />} />
        <Route path="cost-segregation" element={<IncomeExpenseWorkbench />} />
        <Route path="expense-workbench" element={<IncomeExpenseWorkbench />} />
        <Route path="draw-room" element={<CommunityCircles initialTab="draw" />} />
        <Route path="circle-draw" element={<CommunityCircles initialTab="draw" />} />
        <Route path="rotation-room" element={<CommunityCircles initialTab="draw" />} />
        <Route path="payout-ceremony" element={<CommunityCircles initialTab="payout" />} />
        <Route path="payout-release" element={<CommunityCircles initialTab="payout" />} />
        <Route path="ceremony" element={<CommunityCircles initialTab="payout" />} />
        <Route path="circle-payout" element={<CommunityCircles initialTab="payout" />} />



        {navItems
          .filter((item) => item.path !== "/")
          .map((item) => (
            <Route
              key={item.path}
              path={item.path.slice(1)}
              element={CUSTOM_ROUTES[item.path]}
            />
          ))}

        {/* Graceful Fallback for unmatched routes */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
    </Suspense>
  )
}

export default App
