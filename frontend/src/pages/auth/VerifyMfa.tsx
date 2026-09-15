import { useRef, useState, type FormEvent, type KeyboardEvent } from "react"
import { useNavigate } from "react-router-dom"
import { AuthLayout } from "../../layouts/AuthLayout"
import { Card } from "../../components/Card"
import { Button } from "../../components/Button"
import { useAuth } from "../../api/auth"

const CODE_LENGTH = 6

export function VerifyMfa() {
  const navigate = useNavigate()
  const { login } = useAuth()
  const [digits, setDigits] = useState<string[]>(Array(CODE_LENGTH).fill(""))
  const [error, setError] = useState("")
  const inputRefs = useRef<Array<HTMLInputElement | null>>([])

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

  function handleSubmit(event: FormEvent) {
    event.preventDefault()
    const code = digits.join("")

    if (code.length !== CODE_LENGTH || !/^\d{6}$/.test(code)) {
      setError("Code must be 6 digits")
      return
    }

    setError("")
    login()
    navigate("/")
  }

  return (
    <AuthLayout>
      <Card>
        <h1 className="mb-1 text-lg font-semibold text-ink-primary">Verify your identity</h1>
        <p className="mb-5 text-sm text-ink-secondary">
          Enter the 6-digit code sent to your device
        </p>

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
                className="h-12 w-12 rounded-md border border-white/10 bg-navy-800 text-center text-lg font-semibold text-ink-primary focus:border-emerald-500 focus:outline-none"
              />
            ))}
          </div>

          {error && <p className="text-sm text-red-400">{error}</p>}

          <Button type="submit" variant="primary" className="w-full">
            Verify
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
