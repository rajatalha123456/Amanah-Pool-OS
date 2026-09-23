import { useState, type FormEvent } from "react"
import { useNavigate } from "react-router-dom"
import { useTranslation } from "react-i18next"
import { AuthLayout } from "../../layouts/AuthLayout"
import { Card } from "../../components/Card"
import { Button } from "../../components/Button"
import { Spinner } from "../../components/Spinner"
import { useAuth } from "../../api/auth"
import { login } from "../../api/authApi"
import { extractErrorMessage } from "../../api/errors"

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

export function SignIn() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { setTokens, loadCurrentUser } = useAuth()
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState("")
  const [isSubmitting, setIsSubmitting] = useState(false)

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()

    if (!EMAIL_PATTERN.test(email)) {
      setError(t("login.invalidEmail"))
      return
    }

    if (password.trim() === "") {
      setError(t("login.passwordRequired"))
      return
    }

    setError("")
    setIsSubmitting(true)

    try {
      const response = await login(email, password)
      setTokens(response.access, response.refresh)
      await loadCurrentUser()
      navigate("/", { replace: true })
    } catch (err) {
      setError(extractErrorMessage(err, t("login.genericError")))
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <AuthLayout>
      <Card>
        <h1 className="mb-1 text-lg font-semibold text-ink-primary">{t("login.title")}</h1>
        <p className="mb-5 text-sm text-ink-secondary">
          {t("login.subtitle")}
        </p>

        <form onSubmit={handleSubmit} className="space-y-4" noValidate>
          <div>
            <label
              htmlFor="email"
              className="mb-1.5 block text-xs font-semibold tracking-wide text-ink-secondary uppercase"
            >
              {t("login.emailLabel")}
            </label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder={t("login.emailPlaceholder")}
              disabled={isSubmitting}
              className="w-full rounded-md border border-white/10 bg-navy-800 px-3 py-2 text-sm text-ink-primary placeholder:text-ink-muted focus:border-emerald-500 focus:outline-none disabled:opacity-60"
            />
          </div>

          <div>
            <label
              htmlFor="password"
              className="mb-1.5 block text-xs font-semibold tracking-wide text-ink-secondary uppercase"
            >
              {t("login.passwordLabel")}
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              disabled={isSubmitting}
              className="w-full rounded-md border border-white/10 bg-navy-800 px-3 py-2 text-sm text-ink-primary placeholder:text-ink-muted focus:border-emerald-500 focus:outline-none disabled:opacity-60"
            />
          </div>

          {error && <p className="text-sm text-red-400">{error}</p>}

          <Button type="submit" variant="primary" className="w-full" disabled={isSubmitting}>
            {isSubmitting ? <Spinner className="h-4 w-4" /> : t("login.signIn")}
          </Button>
        </form>
      </Card>
    </AuthLayout>
  )
}
