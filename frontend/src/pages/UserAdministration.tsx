import { useEffect, useState } from "react"
import { PageHeader } from "../components/PageHeader"
import { Card } from "../components/Card"
import { Badge } from "../components/Badge"
import { Button } from "../components/Button"
import { Spinner } from "../components/Spinner"
import { Table, type TableColumn } from "../components/Table"
import { useAuth } from "../api/auth"
import { fetchUsers, updateUser } from "../api/users"
import { extractErrorMessage } from "../api/errors"
import { NewUserModal } from "./administration/NewUserModal"
import { GeneratedPasswordModal } from "./administration/GeneratedPasswordModal"
import type { BadgeVariant, UserAdmin, UserCreateResponse } from "../types"

type PageState = "loading" | "loaded" | "error"

export function UserAdministration() {
  const { user } = useAuth()
  const isSuperAdmin = user?.role === "platform_super_admin"

  const [users, setUsers] = useState<UserAdmin[]>([])
  const [pageState, setPageState] = useState<PageState>("loading")
  const [pageError, setPageError] = useState("")
  const [isNewModalOpen, setIsNewModalOpen] = useState(false)
  const [createdUser, setCreatedUser] = useState<UserCreateResponse | null>(null)
  const [actionErrors, setActionErrors] = useState<Record<number, string>>({})
  const [pendingToggleId, setPendingToggleId] = useState<number | null>(null)

  useEffect(() => {
    if (!isSuperAdmin) {
      return
    }
    loadUsers()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isSuperAdmin])

  function loadUsers() {
    setPageState("loading")
    setPageError("")
    fetchUsers()
      .then((data) => {
        setUsers(data)
        setPageState("loaded")
      })
      .catch((err) => {
        setPageError(extractErrorMessage(err, "Failed to load users."))
        setPageState("error")
      })
  }

  function handleCreated(created: UserCreateResponse) {
    setUsers((prev) => [
      {
        id: created.id,
        email: created.email,
        full_name: created.full_name,
        role: created.role,
        tenant_code: created.tenant_code,
        mfa_enabled: created.mfa_enabled,
        is_active: created.is_active,
      },
      ...prev,
    ])
    setIsNewModalOpen(false)
    setCreatedUser(created)
  }

  async function handleToggleActive(target: UserAdmin) {
    setActionErrors((prev) => ({ ...prev, [target.id]: "" }))
    setPendingToggleId(target.id)
    try {
      const updated = await updateUser(target.id, { is_active: !target.is_active })
      setUsers((prev) =>
        prev.map((u) => (u.id === updated.id ? { ...u, is_active: updated.is_active } : u)),
      )
    } catch (err) {
      setActionErrors((prev) => ({
        ...prev,
        [target.id]: extractErrorMessage(err, "Unable to update user."),
      }))
    } finally {
      setPendingToggleId(null)
    }
  }

  if (!isSuperAdmin) {
    return (
      <div>
        <PageHeader title="Administration" subtitle="User account management" />
        <Card>
          <p className="text-sm text-ink-secondary">
            Access restricted — this page is only available to Platform Super Admins.
          </p>
        </Card>
      </div>
    )
  }

  const columns: TableColumn<UserAdmin>[] = [
    { header: "Email", accessor: (u) => u.email },
    { header: "Full Name", accessor: (u) => u.full_name },
    { header: "Role", accessor: (u) => u.role },
    { header: "Tenant", accessor: (u) => u.tenant_code ?? "—" },
    {
      header: "Status",
      accessor: (u) => (
        <Badge variant={(u.is_active ? "emerald" : "navy") as BadgeVariant}>
          {u.is_active ? "active" : "inactive"}
        </Badge>
      ),
    },
    {
      header: "Action",
      accessor: (u) => (
        <div className="flex flex-col gap-1">
          <Button
            variant={u.is_active ? "secondary" : "primary"}
            disabled={pendingToggleId === u.id}
            onClick={() => handleToggleActive(u)}
          >
            {pendingToggleId === u.id ? (
              <Spinner className="h-4 w-4" />
            ) : u.is_active ? (
              "Deactivate"
            ) : (
              "Activate"
            )}
          </Button>
          {actionErrors[u.id] && <p className="text-xs text-red-400">{actionErrors[u.id]}</p>}
        </div>
      ),
    },
  ]

  return (
    <div>
      <PageHeader
        title="Administration"
        subtitle="Create and manage user accounts"
        actions={
          <Button variant="primary" onClick={() => setIsNewModalOpen(true)}>
            + New User
          </Button>
        }
      />

      {pageState === "loading" && (
        <div className="flex items-center gap-2 py-12 text-ink-secondary">
          <Spinner className="h-5 w-5" />
          <span className="text-sm">Loading users...</span>
        </div>
      )}

      {pageState === "error" && (
        <Card>
          <p className="text-sm text-red-400">{pageError}</p>
        </Card>
      )}

      {pageState === "loaded" && (
        <Card>
          {users.length === 0 ? (
            <p className="text-sm text-ink-secondary">No users found.</p>
          ) : (
            <Table columns={columns} data={users} keyField={(u) => u.id} />
          )}
        </Card>
      )}

      {isNewModalOpen && user?.tenant && (
        <NewUserModal
          tenantId={user.tenant}
          onClose={() => setIsNewModalOpen(false)}
          onCreated={handleCreated}
        />
      )}

      {createdUser && (
        <GeneratedPasswordModal
          email={createdUser.email}
          password={createdUser.generated_password}
          onClose={() => setCreatedUser(null)}
        />
      )}
    </div>
  )
}
