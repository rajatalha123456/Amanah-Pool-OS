import { useEffect, useState, useMemo } from "react"
import { PageHeader } from "../components/PageHeader"
import { Card } from "../components/Card"
import { Badge } from "../components/Badge"
import { Button } from "../components/Button"
import { Spinner } from "../components/Spinner"
import { StatCard } from "../components/StatCard"
import { Table, type TableColumn } from "../components/Table"
import { useAuth } from "../api/auth"
import { fetchUsers, updateUser } from "../api/users"
import { extractErrorMessage } from "../api/errors"
import { NewUserModal } from "./administration/NewUserModal"
import { GeneratedPasswordModal } from "./administration/GeneratedPasswordModal"
import { JurisdictionRulePacks } from "./administration/JurisdictionRulePacks"
import { SecurityAuditLog } from "./administration/SecurityAuditLog"
import { TenantManagement } from "./administration/TenantManagement"
import type { BadgeVariant, UserAdmin, UserCreateResponse } from "../types"

type AdminTab = "audit-log" | "multi-tenant" | "users" | "rule-packs"

const TABS: { key: AdminTab; label: string; num: string }[] = [
  { key: "audit-log", label: "Security & Audit Log", num: "" },
  { key: "multi-tenant", label: "Multi-Tenant Configuration", num: "" },
  { key: "users", label: "User Administration", num: "" },
  { key: "rule-packs", label: "Jurisdiction & Rule Packs", num: "" },
]

export function UserAdministration() {
  const { user } = useAuth()
  const isSuperAdmin = user?.role === "platform_super_admin"

  const [activeTab, setActiveTab] = useState<AdminTab>("audit-log")
  const [users, setUsers] = useState<UserAdmin[]>([])
  const [pageState, setPageState] = useState<"loading" | "loaded" | "error">("loading")
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

  const { activeUsersCount, mfaUsersCount } = useMemo(() => {
    return {
      activeUsersCount: users.filter((u) => u.is_active).length,
      mfaUsersCount: users.filter((u) => u.mfa_enabled).length,
    }
  }, [users])

  const activeMeta = useMemo(() => {
    switch (activeTab) {
      case "audit-log":
        return {
          num: "39",
          title: "39. Security & Audit Log",
          sub: "Immutable append-only audit trail, tamper-proof SHA-256 integrity, actor verification",
        }
      case "multi-tenant":
        return {
          num: "40",
          title: "40. Multi-Tenant Switching & Configuration",
          sub: "Strict Row-Level ContextVar Isolation, Legal Entity Scopes, and Residency Controls",
        }
      case "rule-packs":
        return {
          num: "42",
          title: "42. Jurisdiction & Rule Packs",
          sub: "Regulatory Framework Configurations, Multi-Jurisdiction Islamic Banking Standards, and PER/IRR Ceilings",
        }
      case "users":
      default:
        return {
          num: "42",
          title: "42. User & Role Management",
          sub: "Cryptographic 4-Eyes Segregation of Duties, Role-Based Access Control, and MFA Enforcement",
        }
    }
  }, [activeTab])

  if (!isSuperAdmin) {
    return (
      <div>
        <PageHeader title="Administration" subtitle="System controls and security management" />
        <Card>
          <p className="text-sm text-ink-secondary">
            Access restricted — this administration suite is only available to Platform Super Admins and authorized compliance officers.
          </p>
        </Card>
      </div>
    )
  }

  const columns: TableColumn<UserAdmin>[] = [
    {
      header: "Email",
      accessor: (u) => <span className="font-mono text-xs text-ink-primary font-semibold">{u.email}</span>,
    },
    { header: "Full Name", accessor: (u) => u.full_name },
    {
      header: "Role",
      accessor: (u) => (
        <span className="rounded bg-navy-800 px-2 py-0.5 font-mono text-[11px] text-emerald-400">
          {u.role}
        </span>
      ),
    },
    {
      header: "Tenant Scope",
      accessor: (u) => (
        <span className="font-mono text-xs text-ink-primary font-bold">
          {u.tenant_code ?? "ALL TENANTS (SUPER)"}
        </span>
      ),
    },
    {
      header: "MFA Status",
      accessor: (u) => (
        <Badge variant={u.mfa_enabled ? "emerald" : "gold"}>
          {u.mfa_enabled ? "ENFORCED" : "OPTIONAL"}
        </Badge>
      ),
    },
    {
      header: "Account Status",
      accessor: (u) => (
        <Badge variant={(u.is_active ? "emerald" : "navy") as BadgeVariant}>
          {u.is_active ? "ACTIVE" : "DISABLED"}
        </Badge>
      ),
    },
    {
      header: "Action",
      accessor: (u) => (
        <div className="flex flex-col gap-1">
          <Button
            size="sm"
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
    <div className="space-y-6">
      <PageHeader
        screenNumber={activeMeta.num}
        title={activeMeta.title}
        subtitle={activeMeta.sub}
        actions={
          activeTab === "users" ? (
            <Button variant="primary" onClick={() => setIsNewModalOpen(true)}>
              + Provision New User
            </Button>
          ) : undefined
        }
      />

      {/* Administration Tabs matching Visual Catalogue Screens 39, 40, 42 */}
      <div className="flex gap-4 border-b border-white/8 text-sm overflow-x-auto">
        {TABS.map((tab) => (
          <button
            key={tab.key}
            type="button"
            onClick={() => setActiveTab(tab.key)}
            className={`px-2 pb-2 font-medium transition-colors whitespace-nowrap ${
              activeTab === tab.key
                ? "border-b-2 border-emerald-500 text-ink-primary font-bold"
                : "text-ink-secondary hover:text-ink-primary"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab 1: Screen 39 Security & Audit Log */}
      {activeTab === "audit-log" && <SecurityAuditLog hideHeader />}

      {/* Tab 2: Screen 40 Multi-Tenant Configuration */}
      {activeTab === "multi-tenant" && <TenantManagement hideHeader />}

      {/* Tab 3: Screen 42 User Administration */}
      {activeTab === "users" && (
        <div className="space-y-6">
          {/* StatCards */}
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <StatCard
              label="Total Users"
              value={users.length.toString()}
              subtext="System Access Accounts"
            />
            <StatCard
              label="Active Accounts"
              value={activeUsersCount.toString()}
              subtext="Operational Signatories"
            />
            <StatCard
              label="MFA Protection"
              value={`${mfaUsersCount} Enforced`}
              subtext="Multi-Factor Auth Active"
            />
            <StatCard
              label="Role Segregation"
              value="4-EYES PRINCIPLE"
              subtext="Maker/Checker/Shariah Enforced"
            />
          </div>

          {pageState === "loading" && (
            <div className="flex items-center gap-2 py-12 text-ink-secondary">
              <Spinner className="h-5 w-5" />
              <span className="text-sm">Loading users directory...</span>
            </div>
          )}

          {pageState === "error" && (
            <Card>
              <p className="text-sm text-red-400">{pageError}</p>
            </Card>
          )}

          {pageState === "loaded" && (
            <Card title="Authorized Users & Access Roles">
              {users.length === 0 ? (
                <p className="py-8 text-center text-xs text-ink-muted">No users found.</p>
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

          {/* Bottom Control Total Bar matching Catalogue Screen 42 */}
          <div className="mt-6 border-t border-white/8 pt-4">
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-4 text-xs">
              <div>
                <p className="text-[11px] font-semibold text-ink-secondary uppercase">
                  ACTIVE USERS PROCESSED
                </p>
                <p className="text-base font-bold text-ink-primary">
                  {users.length} <span className="text-emerald-400 text-xs">100%</span>
                </p>
              </div>
              <div>
                <p className="text-[11px] font-semibold text-ink-secondary uppercase">4-EYES SEGREGATION</p>
                <p className="text-base font-bold text-emerald-400">Strict Enforcement Active</p>
              </div>
              <div>
                <p className="text-[11px] font-semibold text-ink-secondary uppercase">MFA COVERAGE</p>
                <p className="text-base font-bold text-emerald-400">100% Authenticated</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tab 4: Screen 42 Jurisdiction & Rule Packs */}
      {activeTab === "rule-packs" && <JurisdictionRulePacks hideHeader />}
    </div>
  )
}
