import { Modal } from "../../components/Modal"
import { Button } from "../../components/Button"

interface GeneratedPasswordModalProps {
  email: string
  password: string
  onClose: () => void
}

export function GeneratedPasswordModal({ email, password, onClose }: GeneratedPasswordModalProps) {
  return (
    <Modal title="User Created" onClose={onClose}>
      <div className="space-y-4">
        <p className="text-sm text-ink-secondary">
          Account created for <span className="font-medium text-ink-primary">{email}</span>.
        </p>

        <div>
          <p className="mb-1.5 text-xs font-semibold tracking-wide text-ink-secondary uppercase">
            Generated Password
          </p>
          <code className="block w-full rounded-md border border-gold-500/30 bg-navy-800 px-3 py-2 text-sm text-gold-400">
            {password}
          </code>
        </div>

        <p className="text-sm font-medium text-red-400">
          Save this password now — it will not be shown again.
        </p>

        <div className="flex justify-end pt-2">
          <Button type="button" variant="primary" onClick={onClose}>
            Done
          </Button>
        </div>
      </div>
    </Modal>
  )
}
