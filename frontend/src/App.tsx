import type { ReactNode } from "react"
import { Navigate, Route, Routes } from "react-router-dom"
import { AppLayout } from "./layouts/AppLayout"
import { CommandCenter } from "./pages/CommandCenter"
import { ProductCatalogue } from "./pages/ProductCatalogue"
import { ContractTemplateStudio } from "./pages/ContractTemplateStudio"
import { PoolCatalogue } from "./pages/PoolCatalogue"
import { PoolDetail } from "./pages/PoolDetail"
import { NewPoolWizard } from "./pages/NewPoolWizard"
import { AssetRegistry } from "./pages/AssetRegistry"
import { DailyOperationsCockpit } from "./pages/DailyOperationsCockpit"
import { AllocationSimulator } from "./pages/AllocationSimulator"
import { AllocationRunDetail } from "./pages/AllocationRunDetail"
import { FinanceLedger } from "./pages/FinanceLedger"
import { StatementView } from "./pages/StatementView"
import { ShariahCopilot } from "./pages/ShariahCopilot"
import { ShariahGovernance } from "./pages/ShariahGovernance"
import { InvestmentPools } from "./pages/InvestmentPools"
import { CommunityCircles } from "./pages/CommunityCircles"
import { MemberMobileHome } from "./pages/circles/MemberMobileHome"
import { ContributionReceipt } from "./pages/circles/ContributionReceipt"
import { CapitalAccountDetail } from "./pages/investments/CapitalAccountDetail"
import { ExceptionCaseDetail } from "./pages/governance/ExceptionCaseDetail"
import { UserAdministration } from "./pages/UserAdministration"
import { AuditorPortal } from "./pages/AuditorPortal"
import { RestatementWizard } from "./pages/RestatementWizard"
import { MudaribHibaSimulator } from "./pages/MudaribHibaSimulator"
import { ReconciliationCenter } from "./pages/ReconciliationCenter"
import { PeriodCloseManager } from "./pages/PeriodCloseManager"
import { ShariahAuditPlan } from "./pages/governance/ShariahAuditPlan"
import { JurisdictionRulePacks } from "./pages/administration/JurisdictionRulePacks"
import { RiskLimitDashboard } from "./pages/RiskLimitDashboard"
import { PayoutExecutionEngine } from "./pages/PayoutExecutionEngine"
import { IncomeExpenseWorkbench } from "./pages/IncomeExpenseWorkbench"
import { ParticipantRegistry } from "./pages/ParticipantRegistry"
import { SignIn } from "./pages/auth/SignIn"
import { VerifyMfa } from "./pages/auth/VerifyMfa"
import { ProtectedRoute } from "./components/ProtectedRoute"
import { navItems } from "./layouts/navItems"

const CUSTOM_ROUTES: Record<string, ReactNode> = {
  "/products-pools": <ProductCatalogue />,
  "/risk-compliance": <AssetRegistry />,
  "/participants": <ParticipantRegistry />,
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

function App() {
  return (
    <Routes>
      <Route path="/login" element={<SignIn />} />
      <Route path="/verify-mfa" element={<VerifyMfa />} />

      <Route
        element={
          <ProtectedRoute>
            <AppLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<CommandCenter />} />
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
  )
}

export default App
