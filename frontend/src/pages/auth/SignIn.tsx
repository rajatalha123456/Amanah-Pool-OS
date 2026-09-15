import { useState, type FormEvent } from "react"
import { useNavigate } from "react-router-dom"
import { AuthLayout } from "../../layouts/AuthLayout"
import { Card } from "../../components/Card"
import { Button } from "../../components/Button"

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

export function SignIn() {
  const navigate = useNavigate()
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState("")

  function handleSubmit(event: FormEvent) {
    event.preventDefault()

    if (!EMAIL_PATTERN.test(email)) {
      setError("Invalid email format")
      return
    }

    if (password.trim() === "") {
      setError("Password is required")
      return
    }

    setError("")
    navigate("/verify-mfa")
  }

  return (
    <AuthLayout>
      <Card>
        <h1 className="mb-1 text-lg font-semibold text-ink-primary">Sign in</h1>
        <p className="mb-5 text-sm text-ink-secondary">
          Access your Amanah Pool OS workspace
        </p>

        <form onSubmit={handleSubmit} className="space-y-4" noValidate>
          <div>
            <label
              htmlFor="email"
              className="mb-1.5 block text-xs font-semibold tracking-wide text-ink-secondary uppercase"
            >
              Email
            </label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@amanahcapital.com"
              className="w-full rounded-md border border-white/10 bg-navy-800 px-3 py-2 text-sm text-ink-primary placeholder:text-ink-muted focus:border-emerald-500 focus:outline-none"
            />
          </div>

          <div>
            <label
              htmlFor="password"
              className="mb-1.5 block text-xs font-semibold tracking-wide text-ink-secondary uppercase"
            >
              Password
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              className="w-full rounded-md border border-white/10 bg-navy-800 px-3 py-2 text-sm text-ink-primary placeholder:text-ink-muted focus:border-emerald-500 focus:outline-none"
            />
          </div>

          {error && <p className="text-sm text-red-400">{error}</p>}

          <Button type="submit" variant="primary" className="w-full">
            Sign In
          </Button>
        </form>
      </Card>
    </AuthLayout>
  )
}
