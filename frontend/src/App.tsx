import type { ReactNode } from "react"
import { Route, Routes } from "react-router-dom"
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
import { ReconciliationCenter } from "./pages/ReconciliationCenter"
import { PeriodCloseManager } from "./pages/PeriodCloseManager"
import { ShariahAuditPlan } from "./pages/governance/ShariahAuditPlan"
import { JurisdictionRulePacks } from "./pages/administration/JurisdictionRulePacks"
import { SignIn } from "./pages/auth/SignIn"
import { VerifyMfa } from "./pages/auth/VerifyMfa"
import { ProtectedRoute } from "./components/ProtectedRoute"
import { navItems } from "./layouts/navItems"

const CUSTOM_ROUTES: Record<string, ReactNode> = {
  "/products-pools": <ProductCatalogue />,
  "/risk-compliance": <AssetRegistry />,
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
        <Route path="allocation-simulator" element={<AllocationSimulator />} />
        <Route path="allocation-runs/:id" element={<AllocationRunDetail />} />
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
        {navItems
          .filter((item) => item.path !== "/")
          .map((item) => (
            <Route
              key={item.path}
              path={item.path.slice(1)}
              element={CUSTOM_ROUTES[item.path]}
            />
          ))}
      </Route>
    </Routes>
  )
}

export default App
