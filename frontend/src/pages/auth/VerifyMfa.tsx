import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react"
import { useLocation, useNavigate } from "react-router-dom"
import { AuthLayout } from "../../layouts/AuthLayout"
import { Card } from "../../components/Card"
import { Button } from "../../components/Button"
import { Spinner } from "../../components/Spinner"
import { useAuth } from "../../api/auth"
import { setupMfa, verifyMfa } from "../../api/authApi"
import { extractErrorMessage } from "../../api/errors"

const CODE_LENGTH = 6

interface VerifyMfaState {
  pendingToken?: string
  isFirstTimeSetup?: boolean
}

export function VerifyMfa() {
  const navigate = useNavigate()
  const location = useLocation()
  const { setTokens, loadCurrentUser } = useAuth()

  const state = (location.state ?? {}) as VerifyMfaState
  const pendingToken = state.pendingToken
  const isFirstTimeSetup = Boolean(state.isFirstTimeSetup)

  const [digits, setDigits] = useState<string[]>(Array(CODE_LENGTH).fill(""))
  const [error, setError] = useState("")
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [qrCode, setQrCode] = useState<string | null>(null)
  const [isLoadingSetup, setIsLoadingSetup] = useState(isFirstTimeSetup)
  const inputRefs = useRef<Array<HTMLInputElement | null>>([])

  useEffect(() => {
    if (!pendingToken) {
      navigate("/login", { replace: true })
      return
    }

    if (isFirstTimeSetup) {
      setupMfa(pendingToken)
        .then((response) => {
          setQrCode(response.qr_code_base64)
        })
        .catch((err) => {
          setError(extractErrorMessage(err, "Unable to start MFA setup."))
        })
        .finally(() => {
          setIsLoadingSetup(false)
        })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  function handleChange(index: number, value: string) {
    const digit = value.replace(/\D/g, "").slice(-1)
    const next = [...digits]
    next[index] = digit
    setDigits(next)

    if (digit && index < CODE_LENGTH - 1) {
      inputRefs.current[index + 1]?.focus()
    }
  }

  function handleKeyDown(index: number, event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === "Backspace" && !digits[index] && index > 0) {
      inputRefs.current[index - 1]?.focus()
    }
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    const code = digits.join("")

    if (code.length !== CODE_LENGTH || !/^\d{6}$/.test(code)) {
      setError("Code must be 6 digits")
      return
    }

    if (!pendingToken) {
      navigate("/login", { replace: true })
      return
    }

    setError("")
    setIsSubmitting(true)

    try {
      const response = await verifyMfa(pendingToken, code)
      setTokens(response.access, response.refresh)
      await loadCurrentUser()
      navigate("/", { replace: true })
    } catch (err) {
      setError(extractErrorMessage(err, "Invalid or expired code"))
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <AuthLayout>
      <Card>
        <h1 className="mb-1 text-lg font-semibold text-ink-primary">Verify your identity</h1>
        <p className="mb-5 text-sm text-ink-secondary">
          {isFirstTimeSetup
            ? "Scan this with Google Authenticator, then enter the code"
            : "Enter the 6-digit code sent to your device"}
        </p>

        {isFirstTimeSetup && (
          <div className="mb-5 flex justify-center">
            {isLoadingSetup ? (
              <Spinner className="h-8 w-8 text-emerald-400" />
            ) : qrCode ? (
              <img
                src={qrCode}
                alt="MFA setup QR code"
                className="h-40 w-40 rounded-md border border-white/10 bg-white p-2"
              />
            ) : null}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="flex justify-between gap-2">
            {digits.map((digit, index) => (
              <input
                key={index}
                ref={(el) => {
                  inputRefs.current[index] = el
                }}
                type="text"
                inputMode="numeric"
                maxLength={1}
                value={digit}
                onChange={(e) => handleChange(index, e.target.value)}
                onKeyDown={(e) => handleKeyDown(index, e)}
                disabled={isSubmitting}
                className="h-12 w-12 rounded-md border border-white/10 bg-navy-800 text-center text-lg font-semibold text-ink-primary focus:border-emerald-500 focus:outline-none disabled:opacity-60"
              />
            ))}
          </div>

          {error && <p className="text-sm text-red-400">{error}</p>}

          <Button type="submit" variant="primary" className="w-full" disabled={isSubmitting}>
            {isSubmitting ? <Spinner className="h-4 w-4" /> : "Verify"}
          </Button>

          <p className="text-center text-sm text-ink-secondary">
            Didn't get a code?{" "}
            <button
              type="button"
              className="font-medium text-emerald-400 hover:text-emerald-300"
            >
              Resend code
            </button>
          </p>
        </form>
      </Card>
    </AuthLayout>
  )
}
