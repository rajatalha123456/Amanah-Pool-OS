import type { ReactNode } from "react"
import { Route, Routes } from "react-router-dom"
import { AppLayout } from "./layouts/AppLayout"
import { CommandCenter } from "./pages/CommandCenter"
import { ProductCatalogue } from "./pages/ProductCatalogue"
import { PoolCatalogue } from "./pages/PoolCatalogue"
import { PoolDetail } from "./pages/PoolDetail"
import { NewPoolWizard } from "./pages/NewPoolWizard"
import { AssetRegistry } from "./pages/AssetRegistry"
import { BalanceImport } from "./pages/BalanceImport"
import { AllocationSimulator } from "./pages/AllocationSimulator"
import { AllocationRunDetail } from "./pages/AllocationRunDetail"
import { JournalBatchReview } from "./pages/JournalBatchReview"
import { StatementView } from "./pages/StatementView"
import { ShariahCopilot } from "./pages/ShariahCopilot"
import { PurificationLedger } from "./pages/PurificationLedger"
import { InvestmentPools } from "./pages/InvestmentPools"
import { UserAdministration } from "./pages/UserAdministration"
import { PlaceholderPage } from "./pages/PlaceholderPage"
import { SignIn } from "./pages/auth/SignIn"
import { VerifyMfa } from "./pages/auth/VerifyMfa"
import { ProtectedRoute } from "./components/ProtectedRoute"
import { navItems } from "./layouts/navItems"

const CUSTOM_ROUTES: Record<string, ReactNode> = {
  "/products-pools": <ProductCatalogue />,
  "/risk-compliance": <AssetRegistry />,
  "/daily-operations": <BalanceImport />,
  "/allocation-engine": <AllocationSimulator />,
  "/finance-ledger": <JournalBatchReview />,
  "/ai-analytics": <ShariahCopilot />,
  "/shariah-governance": <PurificationLedger />,
  "/investments": <InvestmentPools />,
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
        {navItems
          .filter((item) => item.path !== "/")
          .map((item) => (
            <Route
              key={item.path}
              path={item.path.slice(1)}
              element={CUSTOM_ROUTES[item.path] ?? <PlaceholderPage title={item.label} />}
            />
          ))}
      </Route>
    </Routes>
  )
}

export default App
