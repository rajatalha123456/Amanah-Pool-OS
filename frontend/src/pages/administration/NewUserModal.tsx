import { useState, type FormEvent } from "react"
import { Modal } from "../../components/Modal"
import { Button } from "../../components/Button"
import { Spinner } from "../../components/Spinner"
import { createUser } from "../../api/users"
import { extractErrorMessage } from "../../api/errors"
import { USER_ROLES } from "../../types"
import type { UserCreateResponse } from "../../types"

interface NewUserModalProps {
  tenantId: string
  onClose: () => void
  onCreated: (user: UserCreateResponse) => void
}

const inputClasses =
  "w-full rounded-md border border-white/10 bg-navy-800 px-3 py-2 text-sm text-ink-primary focus:border-emerald-500 focus:outline-none"
const labelClasses = "mb-1.5 block text-xs font-semibold tracking-wide text-ink-secondary uppercase"

function formatRoleLabel(role: string): string {
  return role
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ")
}

export function NewUserModal({ tenantId, onClose, onCreated }: NewUserModalProps) {
  const [email, setEmail] = useState("")
  const [fullName, setFullName] = useState("")
  const [role, setRole] = useState<string>(USER_ROLES[2])
  const [error, setError] = useState("")
  const [isSubmitting, setIsSubmitting] = useState(false)

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setError("")
    setIsSubmitting(true)
    try {
      const user = await createUser({
        email,
        full_name: fullName,
        role,
        tenant: tenantId,
      })
      onCreated(user)
    } catch (err) {
      setError(extractErrorMessage(err, "Unable to create user."))
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <Modal title="New User" onClose={onClose}>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label htmlFor="email" className={labelClasses}>
            Email
          </label>
          <input
            id="email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            className={inputClasses}
          />
        </div>

        <div>
          <label htmlFor="full-name" className={labelClasses}>
            Full Name
          </label>
          <input
            id="full-name"
            type="text"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            required
            className={inputClasses}
          />
        </div>

        <div>
          <label htmlFor="role" className={labelClasses}>
            Role
          </label>
          <select
            id="role"
            value={role}
            onChange={(e) => setRole(e.target.value)}
            className={inputClasses}
          >
            {USER_ROLES.map((r) => (
              <option key={r} value={r}>
                {formatRoleLabel(r)}
              </option>
            ))}
          </select>
        </div>

        {error && <p className="text-sm text-red-400">{error}</p>}

        <div className="flex justify-end gap-2 pt-2">
          <Button type="button" variant="secondary" onClick={onClose} disabled={isSubmitting}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" disabled={isSubmitting}>
            {isSubmitting ? <Spinner className="h-4 w-4" /> : "Create"}
          </Button>
        </div>
      </form>
    </Modal>
  )
}
