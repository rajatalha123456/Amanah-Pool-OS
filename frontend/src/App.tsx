import { Route, Routes } from "react-router-dom"
import { AppLayout } from "./layouts/AppLayout"
import { CommandCenter } from "./pages/CommandCenter"
import { PlaceholderPage } from "./pages/PlaceholderPage"
import { SignIn } from "./pages/auth/SignIn"
import { VerifyMfa } from "./pages/auth/VerifyMfa"
import { ProtectedRoute } from "./components/ProtectedRoute"
import { navItems } from "./layouts/navItems"

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
        {navItems
          .filter((item) => item.path !== "/")
          .map((item) => (
            <Route
              key={item.path}
              path={item.path.slice(1)}
              element={<PlaceholderPage title={item.label} />}
            />
          ))}
      </Route>
    </Routes>
  )
}

export default App
