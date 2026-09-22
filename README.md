# Amanah Pool OS

Amanah Pool Management System — backend built with Django + Django REST Framework, frontend built with React (Vite) + TypeScript.

## Project Structure

```
pool management system/
├── backend/                   # Django backend (this is the current focus)
│   ├── config/                 # Django project package
│   │   ├── settings/
│   │   │   ├── base.py         # Shared settings
│   │   │   ├── development.py  # Local dev settings (DEBUG=True)
│   │   │   └── production.py   # Production settings (env-var driven)
│   │   ├── urls.py
│   │   ├── wsgi.py
│   │   └── asgi.py
│   ├── apps/                   # All Django apps live here
│   │   ├── core/                # Shared utilities, base models, middleware, health-check
│   │   ├── tenants/              # Tenant, LegalEntity
│   │   ├── accounts/              # User, Role, ApprovalMatrix
│   │   ├── products/              # Product, ContractTemplate, ShariahDecision
│   │   ├── pools/                  # Pool, PoolVersion
│   │   ├── allocation/             # AllocationRun, AllocationLine
│   │   ├── accounting/              # JournalBatch, ledger entries
│   │   ├── governance/               # ShariahDecision register, ExceptionCase
│   │   ├── investments/               # CapitalAccount, Subscription
│   │   ├── circles/                    # CommunityCircle, Member, Contribution
│   │   └── ai_agents/                   # AI agent integration layer
│   ├── manage.py
│   ├── requirements.txt
│   ├── .env                    # Local secrets (not committed)
│   └── .env.example            # Template for required env vars
└── frontend/                   # React (Vite) + TypeScript frontend
    ├── src/
    │   ├── api/                 # Axios instance + API call functions
    │   ├── components/          # Reusable UI components (Button, Card, Table, Badge)
    │   ├── layouts/              # Sidebar + TopBar shell layout, nav items
    │   ├── pages/                # Screen-level components (one per sidebar item)
    │   ├── types/                 # Shared TypeScript interfaces
    │   ├── App.tsx
    │   ├── main.tsx
    │   └── index.css              # Tailwind import + design tokens
    ├── .env                     # Local env vars (not committed)
    ├── .env.example             # Template for required env vars
    └── package.json
```

## Prerequisites

- Python 3.11+
- PostgreSQL (running locally, or a Supabase project)
- Node.js 18+ and npm

## Backend Setup

1. **Clone the repository and go to the backend folder**

   ```bash
   cd backend
   ```

2. **Create and activate a virtual environment**

   ```bash
   python -m venv venv

   # Windows
   venv\Scripts\activate

   # macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Create your `.env` file**

   Copy `.env.example` to `.env` and fill in your own values:

   ```bash
   cp .env.example .env
   ```

   Required variables:

   | Variable | Description |
   |---|---|
   | `SECRET_KEY` | Django secret key (generate one, never reuse the example) |
   | `DEBUG` | `True` for local dev, `False` in production |
   | `ALLOWED_HOSTS` | Comma-separated list of allowed hosts |
   | `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` | PostgreSQL connection details |
   | `CORS_ALLOWED_ORIGINS` | Comma-separated list of allowed frontend origins |

   To generate a secret key:

   ```bash
   python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
   ```

5. **Create the database** (if it doesn't already exist)

   ```sql
   CREATE DATABASE amanah_pool_os;
   ```

6. **Run migrations**

   ```bash
   python manage.py migrate
   ```

7. **Run the development server**

   By default `manage.py` uses `config.settings.development`.

   ```bash
   python manage.py runserver
   ```

8. **Verify it's working**

   Open [http://127.0.0.1:8000/api/v1/health/](http://127.0.0.1:8000/api/v1/health/) — it should return:

   ```json
   {"status": "ok"}
   ```

## Settings Environments

- `config.settings.development` — used by `manage.py` locally (`DEBUG=True`, relaxed CORS).
- `config.settings.production` — used by `wsgi.py`/`asgi.py` for deployment (`DEBUG=False`, all secrets/hosts from environment variables, HTTPS/security hardening enabled).

To run management commands against production settings:

```bash
DJANGO_SETTINGS_MODULE=config.settings.production python manage.py <command>
```

## Adding a New App

All apps live under `backend/apps/`. After creating a new app:

1. Add it to `LOCAL_APPS` in `config/settings/base.py` as `"apps.<app_name>"`.
2. Make sure its `apps.py` `name` attribute is set to `"apps.<app_name>"`.

## Frontend Setup

1. **Go to the frontend folder**

   ```bash
   cd frontend
   ```

2. **Install dependencies**

   ```bash
   npm install
   ```

3. **Create your `.env` file**

   Copy `.env.example` to `.env`:

   ```bash
   cp .env.example .env
   ```

   | Variable | Description |
   |---|---|
   | `VITE_API_BASE_URL` | Base URL of the backend API (defaults to `http://localhost:8000/api/v1/`) |

4. **Run the development server**

   ```bash
   npm run dev
   ```

   The app runs at [http://localhost:5173](http://localhost:5173).

5. **Verify frontend-backend connection**

   With the Django backend also running (see Backend Setup above), open the app — the **Command Center** page (the default route) calls `GET /api/v1/health/` and shows a "Connected" badge with the response status once it succeeds.

### Frontend Stack

- **Vite + React + TypeScript**
- **React Router** for client-side routing — one placeholder route per sidebar navigation item (Command Center, Products & Pools, Daily Operations, Allocation Engine, Investments, Community Circles, Shariah Governance, Risk & Compliance, Finance & Ledger, AI & Analytics, Reports, Administration).
- **Axios** for API calls, configured via `src/api/axios.ts` using `VITE_API_BASE_URL`.
- **Tailwind CSS v4** (CSS-first config via `@theme` in `src/index.css`) with custom design tokens:
  - `navy` — primary background / header color
  - `emerald` — interactive controls, buttons, active states
  - `gold` — governance/approval signals, highlights, badges
  - Font: **Inter** (institutional, clean sans-serif)

### Authentication (connected)

`/login` (SignIn) and `/verify-mfa` (VerifyMfa) are connected to the real backend auth flow described in [Authentication](#authentication) below:

- `SignIn.tsx` calls `POST /auth/login/`. Depending on the response it navigates to `/verify-mfa` with route state `{ pendingToken, isFirstTimeSetup }`.
- `VerifyMfa.tsx` calls `POST /auth/mfa/setup/` first when `isFirstTimeSetup` is true (showing the returned QR code), then always calls `POST /auth/mfa/verify/` with the entered code. On success it stores the returned `access`/`refresh` tokens and fetches `GET /auth/me/`.
- `src/api/auth.tsx` (`AuthProvider`/`useAuth`) holds `accessToken` and `user` in state, persisting `access`/`refresh` tokens and the user's `tenant_code` to `localStorage`.
- `src/api/axios.ts` attaches `Authorization: Bearer <access_token>` and `X-Tenant-Code: <tenant_code>` to every request automatically via a request interceptor, when those values are present in `localStorage`.
- `ProtectedRoute` checks for a real access token (via `useAuth().isAuthenticated`, derived from `localStorage`) and redirects to `/login` when absent.
- Logout (TopBar → user menu → Logout) clears all stored tokens/tenant code and redirects to `/login`.

Note: `access` tokens expire after 20 minutes (see [Authentication](#authentication)) and this frontend does not yet call `POST /auth/refresh/` automatically — a future task should add refresh-on-401 handling.

### Tenant Switcher (single-tenant display for now)

`TopBar.tsx` shows a `TenantSwitcher` (`src/components/TenantSwitcher.tsx`) — a small pill in the top bar with the current tenant's code and a dropdown arrow. Clicking it opens a list showing the current tenant with a checkmark.

This is a **display-only** component for now: the backend's `apps.accounts.User` model supports only one `tenant` per user (see [Data Model](#data-model)), so there is nothing to actually switch between yet. The dropdown UI is built ahead of that backend capability, sourcing its single item from `useAuth().user.tenant_code`.

Once the backend supports multiple tenants per user, `TenantSwitcher.tsx` (see the `TODO(multi-tenant)` comment in the file) should: fetch the real list of tenants available to the current user from an API instead of using `user.tenant_code` directly; on selecting a different tenant, write the new code to `localStorage` under `TENANT_CODE_KEY` (`src/api/axios.ts`) so it's sent as `X-Tenant-Code` on subsequent requests; and trigger a reload/refetch of tenant-scoped data, since nearly everything in the app is tenant-scoped.

### Command Center (connected to real data)

`src/pages/CommandCenter.tsx` (the default route, `/`) is connected to the real backend — it is **not mock data**. On mount it calls `fetchPools()` (`src/api/pools.ts`, `GET /api/v1/pools/pools/`) and `fetchProducts()` (`src/api/products.ts`, `GET /api/v1/products/products/`) and renders:

- A small "Backend Connection" card (kept from earlier work) showing live `/health/` status.
- A stat row (`StatCard`): Total Pools, Active Pools (`status === "open"`), Draft Pools (`status === "draft"`), Total Products.
- A `Table` of all pools — Name, Code, Status (`Badge`, colored via a status→variant map: `draft`→gray/`neutral`, `approved`→gold, `open`/`allocation`→emerald, `closed`→navy, `archived`→gray/`neutral`), Product name (from the nested `product_detail`), Effective Date.
- A loading spinner while the requests are in flight, an error message ("Failed to load data") if either call fails, and a "No pools yet" empty state when the pool list is empty.

`Pool` and `Product` TypeScript interfaces (`src/types/index.ts`) mirror the backend serializers exactly, including nested `product_detail`/`contract_template_detail`.

**Manually verified the data contract** by replaying the exact requests the page makes (same endpoints, same `Authorization`/`X-Tenant-Code` headers) against the running backend seeded via `seed_demo_pool`/`seed_demo_product`: the response shapes match the `Pool`/`Product` TypeScript interfaces field-for-field, confirmed `tsc --noEmit` and `npm run build` are clean, and confirmed the page and its new modules serve without compile errors from the Vite dev server. Full in-browser visual verification (spinner timing, table rendering, badge colors) was not done in this pass since it requires a real browser session.

### Product Catalogue (connected — list, create, submit-for-review)

`src/pages/ProductCatalogue.tsx` (routed at `/products-pools`, replacing its earlier placeholder) is fully functional, not mock:

- On mount, calls `fetchProducts()` (`GET /api/v1/products/products/`) and renders a `Table` — Name, Code, Operating Model, Contract Template (from the nested `contract_template_detail.name`), Status (`Badge`, mapped `draft`→gray/neutral, `shariah_review`→gold, `approved`/`active`→emerald, `retired`→navy), Updated At.
- **"+ New Product"** (top-right, next to the page title) opens `NewProductModal` (built on a new generic `Modal` component, `src/components/Modal.tsx` — dark overlay, centered card, close button). The form calls `fetchContractTemplates()` (`GET /api/v1/products/contract-templates/`) to populate the Contract Template dropdown; if none exist, it shows "No contract templates available. Create one first." and disables the Create button. On submit, `createProduct()` (`POST /api/v1/products/products/`) either closes the modal and prepends the new row, or shows the backend's validation error inline.
- Each **`draft`**-status row shows a **"Submit for Review"** action calling `submitProductForReview()` (`POST /api/v1/products/products/{id}/submit-for-review/`); the row updates in place on success. The button isn't itself role-gated in the UI — the backend enforces `IsProductManager`, and a `403` from a disallowed role is shown as an inline error message above the table.
- Standard loading/error states matching Command Center's pattern, plus a "No products yet. Create your first product to get started." empty state.

`extractErrorMessage()` (`src/api/errors.ts`) was extended to also parse the backend's standard `{"error": {"code", "message", "details"}}` shape (used by raised DRF exceptions like `permission_denied` and `validation_error`) — it previously only recognized the older `{"detail": "..."}` shape used by a few pre-existing endpoints (login, MFA). Both are now handled, so a `403` or a field validation error from any endpoint surfaces a real message instead of falling through to the generic fallback text.

**Manually verified the data contract via real HTTP requests** against the running backend: `fetchContractTemplates()`'s endpoint returned the shape expected by the `ContractTemplate` interface; `createProduct()`'s endpoint created a real `Product` (`status: "draft"`) matching the `Product` interface exactly; `submitProductForReview()`'s endpoint flipped `status` to `shariah_review` as expected; and a `403` from a disallowed role (`shariah_board` attempting to create a product) came back in the `{"error": {"message": ...}}` shape, confirming `extractErrorMessage()`'s new branch actually fires on real backend errors rather than only in theory. `tsc --noEmit`, `npm run build`, and Vite module serving are all clean. As with Command Center, full in-browser visual/interaction verification (modal open/close, form submission UX) was not done in this pass.

### Contract Template Studio (connected — list + create, third Products & Pools tab)

**Backend**: one new read-only endpoint, `GET /api/v1/products/contract-templates/{id}/clauses-schema/` (`ContractTemplateViewSet.clauses_schema`, any authenticated user). It 404s for an unknown/foreign-tenant id (via `self.get_object()`, so tenant isolation is enforced the same as every other action on this viewset) and otherwise returns a static list of standard Islamic-finance contract clause fields — `profit_ratio`, `late_payment_policy`, `notice_period`, `loss_bearing_clause`, `early_termination_terms`, `collateral_requirements`, `dispute_resolution`, `purification_clause` — each with a `key`, `label`, and `description`. It's intentionally static/not template-specific for now (no per-`contract_type` variation yet); making it vary by contract type is future scope if the clause set actually needs to differ between Mudarabah/Musharakah/Wakalah/Qard.

**Frontend**: `src/pages/ContractTemplateStudio.tsx`, routed at `/contract-templates` and added as the third tab ("Contract Templates") alongside Products and Pools on both `ProductCatalogue.tsx` and `PoolCatalogue.tsx`'s existing tab bars.

- Lists existing templates in a table (name, contract_type, version, status badge, linked `shariah_decision_code`) via the pre-existing `fetchContractTemplates()`.
- **"+ New Template"** expands an inline single-page form (not a multi-step wizard — deliberately kept simple per this task's scope) with name, contract type, version, an optional approved-Shariah-decision dropdown (fetched via `fetchShariahDecisions()`, filtered to `status === "approved"`), and a dynamic clauses editor: add/remove key-value rows freely, plus quick-add buttons sourced from the new `clauses-schema/` endpoint (falling back to a matching static list when the catalogue has no existing template yet to fetch the schema from — the schema is currently identical either way, since it isn't template-specific). Submits via a new `createContractTemplate()` (`POST /api/v1/products/contract-templates/`), building the `clauses` JSON object from the non-empty rows client-side.
- New template rows are `IsProductManager`-gated server-side, same as the rest of this viewset; a disallowed role's `403` surfaces inline via `extractErrorMessage()`.

**Verified via real HTTP requests** in `apps/products/tests.py::ContractTemplateClausesSchemaApiTests`: fetched the clauses schema and confirmed it contains the standard fields; confirmed a `404` for an unknown template id; created a template with a dynamic `clauses` object (`{"profit_ratio": "70/30", "notice_period": "30 days"}`), confirmed the response echoes it back exactly and starts in `draft` status, and confirmed it appears in the list endpoint. `npm run build` is clean.

### Related-Party Transactions (connected — create and review)

Risk & Compliance includes a **Related-Party** tab alongside the Asset Registry and Exception Queue. It calls the live governance API at `/api/v1/governance/related-party-transactions/` and supports pool filtering, transaction creation, and review decisions.

- Finance Makers and Pool Managers can create transactions; new records start as `pending_review`.
- Risk & Compliance and Shariah Board users can approve or flag a transaction with review notes through `POST /api/v1/governance/related-party-transactions/{id}/review/` using `{ "decision": "approved" | "flagged", "notes": "..." }`.
- The backend applies tenant isolation and writes audit entries for create and review actions. The governance API test suite covers create, approve, flag, and forbidden-role responses.

### Exception Case Investigation Lifecycle (quarantine, investigation, treatment)

`ExceptionCase` now tracks two additional stages beyond open/resolved/dismissed — `investigation_notes` and `treatment_plan` — so a Risk & Compliance case can show its full quarantine → investigation → treatment → resolution history, not just a final outcome:

- **`POST /api/v1/governance/exceptions/{id}/start-investigation/`** — `IsRiskCompliance` only. Requires `status == "open"` and a required `investigation_notes` body field (`400` if missing or if the case isn't `open`, e.g. calling it twice). Transitions `open` → `investigating`.
- **`POST /api/v1/governance/exceptions/{id}/set-treatment/`** — `IsRiskCompliance` only. Requires `status == "investigating"` (so a treatment plan can't be set before an investigation has started) and a required `treatment_plan` body field. Status stays `investigating` — setting a treatment plan is a sub-step within investigation, not a status transition of its own.
- `resolve/`/`dismiss/` (pre-existing) remain the final step, unchanged.
- Every transition writes an `AuditLog` entry (`start_investigation`, `set_treatment`), the same as the rest of this model's actions.

**Frontend**: `src/pages/governance/ExceptionCaseDetail.tsx`, routed at `/exceptions/{id}`. `ExceptionQueue`'s table rows now navigate here on click instead of the old inline-expand card (which has been removed, along with the now-fully-superseded `ResolutionModal.tsx`). The page shows the case's title/severity/description, then a 4-stage timeline card (**Quarantine** → **Investigation** → **Treatment Plan** → **Resolve/Dismiss**) with a decision badge (Completed / In Review / Pending / Blocked) and the stage's notes per card, followed by whichever action form applies to the case's current status (Start Investigation / Set Treatment Plan / Resolve or Dismiss), gated to `risk_compliance` the same as before.

**Verified via real HTTP requests** in `apps/governance/tests.py::ExceptionCaseInvestigationLifecycleApiTests`: ran the full lifecycle (start-investigation → set-treatment → resolve) end-to-end confirming each response's status and stored notes; confirmed `start-investigation` rejects a missing `investigation_notes` and rejects being called a second time once already `investigating`; confirmed `set-treatment` rejects being called before an investigation has started; confirmed a non-`risk_compliance` role gets `403` on both new actions. `npm run build` is clean.

### Shariah Governance page (connected — Workspace, Fatwa Register, Purification Ledger)

The **Shariah Governance** nav item now routes to `src/pages/ShariahGovernance.tsx`, a three-tab page rather than the single Purification Ledger it previously pointed straight to:

- **Workspace** — calls `fetchShariahDashboard()` against the existing `GET /api/v1/governance/shariah-dashboard/` aggregation endpoint and renders it as `StatCard`s (total pending items, critical exceptions, pending decisions, pending purification entries) plus a list per pending category (Shariah decisions, contract templates, weightage bands, PSR schedules, open exception cases, purification entries, pool approvals). Nothing new on the backend — this is a read-only view over an endpoint that already existed.
- **Fatwa Register** — a new `ShariahDecisionViewSet` frontend: a table of `ShariahDecision` rows (`decision_code`, `title`, status badge, `effective_date`) backed by `src/api/shariahGovernance.ts`'s `fetchShariahDecisions()` / `createShariahDecision()` / `approveShariahDecision()`, calling the pre-existing `apps.products` endpoints (`GET/POST /api/v1/products/shariah-decisions/`, `POST /api/v1/products/shariah-decisions/{id}/approve/`). A **"+ New Decision"** modal creates a `draft` decision; an **Approve** action (visible to Shariah Board / Shariah Secretariat, matching the endpoint's existing permission) flips it to `approved`.
- **Purification Ledger** — the existing `PurificationLedger` component, unchanged in behavior, now rendered as the third tab instead of owning its own page/route. Its own `PageHeader` was removed (replaced with a plain subtitle line) since it's nested under the parent page's header now.

Backend test coverage added in `apps/products/tests.py` (`ShariahDecisionApiTests`) — create/list/approve a decision, a non-Shariah role forbidden from creating one, and the dashboard correctly reflecting a newly-created pending decision — run via real `APIClient` HTTP requests against `reverse()`d URLs, all passing.

`npm run build` is clean.

### New Pool Wizard (connected — Model selection + basic Pool creation only)

`src/pages/NewPoolWizard.tsx` (routed at `/pools/new`, linked from a **"+ New Pool"** button next to Product Catalogue's "+ New Product") follows the catalogue's 6-station visual design — a `Stepper` shows "1 Model" / "2 Contract" / "3 Economics" / "4 Assets" / "5 Governance" / "6 Review", the current step highlighted in emerald, the rest muted — but **only two of those stations are functional right now**:

- **Step 1 "Model"** — calls `fetchApprovedProducts()` (`src/api/pools.ts`; since `ProductViewSet.get_queryset()` doesn't support a `?status=` filter, this fetches all products via `fetchProducts()` and filters to `status === "approved"` client-side) and shows them in a dropdown. If none are approved, shows "No approved products available. Create and approve a product first." and disables **Next**.
- **Steps 2–5 ("Contract", "Economics", "Assets", "Governance")** are **informational placeholders only** — each shows: *"This will be configurable after the pool is created (Weightage & PSR Setup, Asset Assignment screens)."* **Next** advances immediately with no input collected, and **Back** returns to the previous step. These are intentionally not functional yet — they exist so the wizard's shape matches the catalogue design ahead of their dedicated screens (Weightage & PSR Setup and Asset Assignment already exist as backend APIs — see [Weightage & PSR Setup](#weightage--psr-setup) and [Asset Assignment](#asset-assignment) — but have no frontend UI yet) being wired in as their own steps later.
- **Step 6 "Review"** — shows the selected product's summary, then collects **Pool Name**, **Pool Code**, and **Effective Date** (not collected earlier in the wizard) and calls `createPool()` (`POST /api/v1/pools/pools/`) on submit. On success, navigates to the Pool Catalogue (below) with a success message; on failure, shows the backend's error via `extractErrorMessage()`.

**Backend bug found and fixed while testing this task** (pre-existing, from the BE-008 Pool model work — not introduced by this frontend task, but discovered because this wizard was the first place duplicate-code creation was actually exercised through the API): `Pool.code` (and, it turns out, `Product.code` — same pattern, same bug) is only enforced unique via a composite `UniqueConstraint(tenant, code)` at the database level. DRF only auto-validates a plain `unique=True` field, not a composite `UniqueConstraint`, so creating a pool or product with a duplicate code raised a raw `IntegrityError` that surfaced as an unhandled `500 internal_server_error` instead of a clean `400`. Fixed by adding `validate_code()` to both `PoolSerializer` and `ProductSerializer`, checking uniqueness within `self.context["request"].user.tenant` before save.

**Manually verified end-to-end via real HTTP requests:** `fetchApprovedProducts()`'s underlying endpoint returned 2 total products with exactly 1 correctly identified as `approved`; `createPool()`'s endpoint created a real `Pool` matching the `Pool` TypeScript interface exactly; a duplicate pool code initially reproduced the `500` bug above, which was then fixed and reverified — the same request now returns a clean `400` with `{"code": ["A pool with this code already exists."]}`; confirmed the identical fix for `Product.code` with a real duplicate-product request; confirmed a fresh, unique code still creates successfully (no regression). `tsc --noEmit`, `npm run build`, and Vite module serving are all clean.

### Pool 360° Overview (connected — full lifecycle from the UI)

`src/pages/PoolCatalogue.tsx` (`/pools`) and `src/pages/PoolDetail.tsx` (`/pools/:id`) are now functional — **the entire Pool lifecycle (submit-for-approval → open → close) can be triggered from the UI**, not just the API.

- **Pool Catalogue** lists all pools (`fetchPools()`) in a `Table` — Name, Code, Status (`Badge`, same draft/approved/open-allocation/closed-archived → neutral/gold/emerald/navy map used elsewhere), Product, Effective Date. Rows are clickable (`Table`'s new optional `onRowClick` prop) and navigate to `/pools/{id}`. A **"+ New Pool"** button links to the wizard.
- Product Catalogue and Pool Catalogue now cross-link via a small "Products / Pools" tab row under each page's header, since both live under the sidebar's single "Products & Pools" nav item.
- **Pool Detail** calls `fetchPoolDetail()` and `fetchPoolVersions()` on mount. Shows: a Product card (`product_detail.name`, and — reaching one level deeper than Pool Catalogue's table — `product_detail.contract_template.name`/`contract_type`); a Pool Info card (`effective_date`, `closed_date` when set, `status`); a **Version History** table (`version_number`, `created_at`, and a one-line snapshot summary built from `snapshot.product.name`/`status` and `snapshot.contract_template.name`/`version` — not the raw JSON); and status-conditional action buttons:

  | Status | Action shown |
  |---|---|
  | `draft` | Submit for Approval → `submitPoolForApproval()` |
  | `approved` | Open Pool → `openPool()` |
  | `open` / `allocation` | Close Pool → `closePool()` |
  | `closed` / `archived` | "Pool is closed" (no action) |

  Each action re-fetches the pool and its versions on success (so, for example, opening a pool immediately shows the newly-created version in the history table below) and shows the backend's error via `extractErrorMessage()` on failure — including a clear "You do not have permission to perform this action" for a `403` from the wrong role, now that `extractErrorMessage()` parses that shape correctly (fixed in the previous task).

  `approvePool()` also exists in `src/api/pools.ts` but is intentionally not wired to a button here: per the backend's actual lifecycle (see [Pool Lifecycle](#pool-lifecycle)), `submit-for-approval` already moves a pool to `approved`, and `approve` is a formal Shariah-Board audit sign-off that doesn't change `status` — there's no UI need for it in this pass.

**Manually verified the entire lifecycle end-to-end via real HTTP requests** (the same endpoints, same headers `PoolDetail.tsx` calls): created a draft pool, confirmed `fetchPoolVersions()` returns `[]` before it's opened; `submitPoolForApproval()` → `status: "approved"`; `openPool()` → `status: "open"`, and `fetchPoolVersions()` then returned exactly one version whose `snapshot.product.name`/`status` and `snapshot.contract_template.name`/`version` match what `PoolDetail.tsx`'s version-summary accessor reads; a `pool_manager` attempting `closePool()` correctly got `403` in the `{"error": {"message": ...}}` shape; a `finance_checker` then closed it successfully, with `closed_date` set. `tsc --noEmit`, `npm run build`, and Vite module serving are all clean.

### Weightage & PSR (connected — manageable from Pool Detail)

`PoolDetail.tsx`'s **"Weightage & PSR"** tab lets Pool Managers add draft `WeightageBand`/`ProfitSharingRatio` records and Shariah Board users approve them, without leaving the pool's page:

- `src/pages/pool-detail/WeightageBandsSection.tsx` — lists bands (`fetchWeightageBands(poolId)`) in a `Table` (participant class, weightage, effective from/to, status `Badge`: draft→gray, approved→emerald), a compact inline "+ Add Band" form beneath it (`createWeightageBand()`), and an "Approve" link on each `draft` row (`approveWeightageBand()`).
- `src/pages/pool-detail/PSRSection.tsx` — identical pattern for `ProfitSharingRatio` (`fetchPSRSchedules()`, `createPSR()`, `approvePSR()`).

**Backend UX gap found and fixed while testing this task:** `extractErrorMessage()` previously only read the generic top-level `message` field from `{"error": {...}}` responses — for a `validation_error`, that's almost always the unhelpful literal `"Validation failed."`, while the actually useful text (e.g. a BR-002 overlap message, or "depositor_share and mudarib_share must add up to 100.00.") lives one level deeper in `details.non_field_errors` or a named field. Fixed by having `extractErrorMessage()` prefer the first string found in `details` (checking `non_field_errors` first, then any other field) whenever `code === "validation_error"`, falling back to the generic `message` otherwise. Verified against three real captured error payloads (a BR-002 overlap, a duplicate pool code, and a `permission_denied` with no `details`) that each now surfaces the right text.

**Manually verified via real HTTP requests:** `fetchWeightageBands()`/`fetchPSRSchedules()` return data matching their TypeScript interfaces exactly; `createWeightageBand()` creates a `draft` record; a `pool_manager` attempting `approveWeightageBand()` correctly `403`s (`IsShariahBoard` only) and a `shariah_board` user then approves it successfully; creating an overlapping band for the same `participant_class` reproduces the real BR-002 error, now shown in full via the `extractErrorMessage()` fix above; an invalid PSR (shares not summing to 100) shows its specific message the same way.

### Asset Registry (new page, connected)

`src/pages/AssetRegistry.tsx` (routed at `/risk-compliance` — the closest existing sidebar nav item, per this task's own suggestion) lists all `Asset`s (`fetchAssets()`) in a `Table` (reference code, asset type, face value, status `Badge`: available→emerald, assigned→gold, matured/written_off→navy) with a **"+ New Asset"** modal (`createAsset()`).

`PoolDetail.tsx`'s **"Assets"** tab (`src/pages/pool-detail/AssignedAssetsSection.tsx`) shows the current pool's active assignments (`fetchAssetAssignments(poolId)`, filtered client-side to `unassigned_date === null`), joining each assignment's `asset` UUID against a full `fetchAssets()` call to show the readable reference code/type. **"+ Assign Asset"** opens a modal (`src/pages/pool-detail/AssignAssetModal.tsx`) whose dropdown is filtered to `status === "available"` assets only (via `fetchAssets()`, client-side filter — same pattern as `fetchApprovedProducts()` in the New Pool Wizard, since neither endpoint supports a `?status=` query param). Each row has an "Unassign" action (`unassignAsset()`).

**Manually verified via real HTTP requests:** `fetchAssets()` and `createAsset()` match the `Asset` interface exactly (`status: "available"` on creation); `assignAsset()` creates an assignment with `unassigned_date: null`, matching the "active assignment" filter; `fetchAssetAssignments()` returns assignments keyed by asset UUID, confirming the join logic in `AssignedAssetsSection.tsx` works; `unassignAsset()` sets `unassigned_date` to today.

### Balance Import & Validation (connected)

`src/pages/BalanceImport.tsx` is a standalone component (not part of `PoolDetail.tsx`, since it needs its own pool selector and a wide multi-row form) with:

- A **Pool** dropdown (`fetchPools()`), **Value Date**, optional **Control Total Expected**, and dynamic **participant_class / balance_amount** rows (**"+ Add Row"**, minimum 1 row, each row removable except the last).
- **Import** calls `importBalances()` and renders an **Import Summary** card: total/matched/exception counts, a status `Badge` (`balanced`→emerald, `exception`→gold), and — when present — the backend's `errors` array rendered as a red bulleted list (not folded into a single string), so multiple duplicate-skip messages are all visible at once.
- An **Import History** table below (`fetchImportHistory(poolId)`), re-fetched after every import.

**Manually verified via real HTTP requests:** a 3-record import with a matching control total returns `status: "balanced"` with an empty `errors` array; re-importing the same `value_date` + `participant_class` returns `status: "exception"` with the exact duplicate-skip message in `errors`, confirming the list-rendering path is exercised by a real backend response rather than just a hardcoded example; `fetchImportHistory()` returns entries matching the `BalanceImportBatch` interface exactly, in the shape the history table's columns read.

**Now nested, not a standalone route** — see [Daily Operations Cockpit](#daily-operations-cockpit-aggregation-dashboard-no-new-backend) below: `/daily-operations` renders a new parent page with this as its "Balance Import" tab, so its own `PageHeader` was removed (it now inherits the parent's).

### Daily Operations Cockpit (aggregation dashboard, no new backend)

`src/pages/DailyOperationsCockpit.tsx`, now routed at `/daily-operations` (replacing the old direct route to `BalanceImport.tsx`), is a two-tab page: **Cockpit** (new) and **Balance Import** (the pre-existing page above, unchanged, just relocated here as a tab).

The Cockpit tab is a pure aggregation view — **no new backend endpoints**, everything is computed client-side from three existing endpoints:

- **Total Managed Funds** and **Close Readiness** are both derived from `GET /api/v1/pools/balance-imports/?pool={id}`, called once per pool currently "in cycle" (`status` is `open` or `allocation` — `draft`/`approved`/`closed`/`archived` pools are excluded, since they aren't mid-operating-cycle). For each in-cycle pool: if it has at least one balance-import batch, it counts toward "close-ready" and its most recent batch's `control_total_actual` is added to the funds total. Close Readiness is shown as both a percentage and the raw `{ready}/{total}` count. There's no bulk "all pools' funds" or "all pools' import status" endpoint, so this fans out one request per in-cycle pool — acceptable given the small number of pools actually open at once, but not something to scale to hundreds of pools without a real aggregation endpoint.
- **Open Exceptions** is a single `GET /api/v1/governance/exceptions/?status=open` call, count of the results.
- The **"Pools In Progress"** table lists pools with `status === "allocation"` (i.e. mid-cycle, past `open` but not yet `closed`), reusing the same `Pool` rows/columns pattern as Command Center.

**Verified via a real end-to-end HTTP test** in `apps/pools/tests.py::DailyOperationsCockpitAggregationApiTests`, which reproduces the exact sequence of calls the frontend makes: created 3 pools (one `allocation` with a balance import posted, one `open` with none, one `draft` excluded entirely), posted one balance import, then re-fetched pools/exceptions/balance-imports through the real API exactly as the cockpit does and confirmed the resulting aggregation — 2 in-cycle pools, 1 close-ready, `50%` readiness, `1000.00` total managed funds, 1 open exception. `npm run build` is clean.

### Risk Dashboard (aggregation tab, no new backend)

`src/pages/RiskLimitDashboard.tsx`, added as the fourth tab ("Risk Dashboard") on `AssetRegistry.tsx` alongside Asset Registry, Exception Queue, and Related-Party — same tabbed-page pattern, no new route. Like the Daily Operations Cockpit above, this is a pure client-side aggregation with **no new backend endpoints**:

- **Total Open Exceptions** and the **by-severity breakdown** (Critical/High/Medium/Low StatCards) both come from a single `GET /api/v1/governance/exceptions/?status=open` call, bucketed by `severity` client-side.
- **Related-Party Pending Review** is `GET /api/v1/governance/related-party-transactions/` (full list, no server-side status filter available on this endpoint), filtered client-side to `disclosure_status === "pending_review"`.
- **Purification Pending** is `GET /api/v1/governance/purification-entries/` (same reasoning), filtered client-side to `status === "identified"` (the ledger's initial, not-yet-approved state).

**Verified via a real end-to-end HTTP test** in `apps/governance/tests.py::RiskDashboardAggregationApiTests`: created 3 exceptions (critical, medium, and one already-`resolved` to confirm it's correctly excluded), 2 related-party transactions (one `pending_review`, one `approved`), and 2 purification entries (one `identified`, one `distributed`); then reproduced the dashboard's exact call sequence and confirmed the resulting counts — 2 open exceptions (1 critical, 1 medium), 1 pending related-party transaction, 1 pending purification entry. `npm run build` is clean.

### Allocation Simulator (new page, connected — BRD Screen #12)

`src/pages/AllocationSimulator.tsx` is the backend-connected version of the catalogue's **Allocation Simulator** (Screen #12). It's reachable two ways: the sidebar's existing **"Allocation Engine"** nav item (`/allocation-engine`), and directly at `/allocation-simulator` (both routes render the same page).

**Formula summary** (full detail in [Allocation Engine](#allocation-engine)): `distributable = gross_income - direct_expenses`; each participant class's `daily_funds × weightage = weighted_funds`; `total_weighted_funds` = their sum; the pool's active PSR splits `distributable` into `depositor_pool_share`/`mudarib_share`; each class's `allocated_amount = depositor_pool_share × (weighted_funds / total_weighted_funds)` — the depositor's share, not the full distributable, is what's split across classes.

- A **Pool** dropdown, **Value Date**, **Gross Income**, and optional **Direct Expenses** (defaults to `0`).
- **Simulate** calls `simulateAllocation()` (`POST .../simulate/`) and renders the result below a small **"Preview only — not saved"** pill: `StatCard`s for Distributable / Total Weighted Funds / Depositor Share / Mudarib Share, and a `Table` of the per-participant-class breakdown (daily funds, weightage, weighted funds, allocated amount). Nothing is written to the database by this call.
- **"Save as Allocation Run"** (only enabled once a simulation has succeeded) re-sends the same form data to `createAllocationRun()` (`POST .../allocation-runs/`, no `/simulate/` suffix), which persists it as a real `AllocationRun` + `AllocationLine`s (`status: "simulated"`) and navigates to the new `AllocationRunDetail` page (`/allocation-runs/{id}`).
- A missing-data failure (no `DailyBalance` for the date, no matching `WeightageBand`, no approved `PSR`, or `total_weighted_funds == 0`) shows the backend's specific message via `extractErrorMessage()`, so the user knows exactly what's missing (e.g. "No DailyBalance records found for pool=... on ...") rather than a generic failure.

**Backend UX gap found and fixed while testing this task:** `extractErrorMessage()`'s `details`-parsing (added in the previous task for BR-002/PSR errors) only handled the common case where `details` is an object of `field → [messages]`. The allocation engine's plain `ValueError`s (e.g. the missing-`DailyBalance` case above) instead produce a `details` that is itself a bare array of strings (`{"details": ["No DailyBalance records found..."]}`) — a shape `extractErrorMessage()` didn't explicitly handle. It happened to still show the right text by coincidence (the top-level `message` field already equals the same string in this case), but confirmed and fixed it properly rather than leaving it working by luck: `firstStringFromDetails()` now checks for a bare array first before assuming an object of fields.

**Manually verified via real HTTP requests** against the seeded demo pool: `simulateAllocation()` returned the same worked-example numbers documented under [Allocation Engine](#allocation-engine) (distributable 11M, total_weighted_funds 100M, depositor/mudarib split 7.7M/3.3M, three correct per-class lines) and confirmed nothing was persisted by that call; `createAllocationRun()` with the identical input then created a real `AllocationRun` (`status: "simulated"`) with 3 `AllocationLine`s; simulating against a date with no `DailyBalance` returned the specific missing-data message, now verified to route through the fixed array-shaped `details` path rather than by coincidence; `fetchAllocationRuns()`/`fetchAllocationRunDetail()` both returned data matching the `AllocationRun` TypeScript interface exactly (including a null `journal_batch` on an unsigned run). `tsc --noEmit`, `npm run build`, and Vite module serving are all clean.

### Allocation Run Detail & Maker-Checker Workflow (FE-014, connected—status-driven UI)

`src/pages/AllocationRunDetail.tsx` is the detail page for a saved `AllocationRun`, reachable directly at `/allocation-runs/{id}` (linked from the Simulator's "Recent Runs" list after saving a run). Displays the same stat cards + lines table as the Simulator, plus status-conditional actions to drive the maker-checker approval workflow:

- **`simulated`** status: "Submit for Checking" button → `POST .../allocation-runs/{id}/submit-for-checking/` (no body), transitions to `pending_approval` (requires `finance_maker` role).
- **`pending_approval`** status: "Approve" button (requires `finance_checker` role, different user than maker via `validate_maker_checker()` backend check) → `POST .../allocation-runs/{id}/approve/` → transitions to `signed`, creates a `JournalBatch` with double-entry rows (e.g. debit "Profit Expense — savings_tier_a" / credit "Depositor Payable — savings_tier_a"), then renders the Journal Batch card showing batch_date, total_debit, total_credit, and a table of entries. Also "Reject" button → opens a small modal (required `rejection_reason` text field) → `POST .../allocation-runs/{id}/reject/` with body `{rejection_reason}` → transitions to `rejected`. **Updated by a later task** for `bank_pool` runs — see [Allocation Run approval timeline (frontend)](#allocation-run-approval-timeline-frontend) below: a `shariah_review` stage now sits between `pending_approval` and `signed`, so the Approve button here only appears directly when `shariah_review_required` is `False`.
- **`signed`** status: read-only display of the Journal Batch card (batch_date, totals, entries table with account_name/entry_type/amount).
- **`rejected`** status: displays the rejection_reason in a read-only box.

The Simulator page also gained a "Recent Runs" table (keyed to the selected pool), listed below the simulation/save area, pulling from `fetchAllocationRuns(poolId)` — clicking a row navigates to its detail page.

**Manually verified via real HTTP requests:** Created an `AllocationRun` as `pool_manager` (role-allowed), submitted it for checking as `finance_maker` (same user, status updated to `pending_approval`), then as `finance_checker` (a different user per `validate_maker_checker` backend constraint) clicked Approve — status transitioned to `signed` and the Journal Batch card appeared with debit/credit rows. Tried rejecting without a reason (blocked by required field validation, error surfaced by `extractErrorMessage()`). Created a second run and rejected it as `finance_checker` with a reason — status transitioned to `rejected` and reason displayed. Recent Runs table loads and row-click navigation works. `tsc --noEmit`, `npm run build` are clean.

## Authentication

Login uses a two-step flow: password, then TOTP-based MFA (via [pyotp](https://pypi.org/project/pyotp/), compatible with Google Authenticator / Authy — no external SMS/email service required). Real access/refresh tokens (JWT, via `djangorestframework-simplejwt`) are only issued after MFA is verified.

**Flow:**

1. **`POST /api/v1/auth/login/`** — body: `{"email": "...", "password": "..."}`.
   - Wrong credentials → `401`.
   - Correct credentials, MFA not yet set up (`user.mfa_enabled == False`) → `{"mfa_setup_required": true, "pending_token": "..."}`.
   - Correct credentials, MFA already set up → `{"mfa_required": true, "pending_token": "..."}`.
   - `pending_token` is a short-lived (5 min) JWT carrying only `user_id` and `pending_mfa: true` — it cannot be used to access any protected endpoint other than the two below.

2. **`POST /api/v1/auth/mfa/setup/`** — body: `{"pending_token": "..."}`. First-time only: generates a TOTP secret for the user (stored on `user.totp_secret`), returns `{"secret": "...", "qr_code_base64": "data:image/png;base64,..."}`. Scan the QR with an authenticator app, or use the raw `secret` (also printed server-side to the console) to generate codes manually for testing:
   ```bash
   python -c "import pyotp; print(pyotp.TOTP('<secret>').now())"
   ```

3. **`POST /api/v1/auth/mfa/verify/`** — body: `{"pending_token": "...", "code": "123456"}`. Verifies the 6-digit TOTP code. On success: sets `user.mfa_enabled = True` (if this was first-time setup) and returns real tokens: `{"access": "...", "refresh": "..."}`.

4. **`POST /api/v1/auth/refresh/`** — body: `{"refresh": "..."}` → returns a new `{"access": "..."}` (`djangorestframework-simplejwt`'s built-in `TokenRefreshView`).

5. **`GET /api/v1/auth/me/`** — requires `Authorization: Bearer <access>` → returns the logged-in user's profile (`id`, `email`, `full_name`, `role`, `tenant`, `tenant_code`, `mfa_enabled`). `tenant_code` is included specifically so the frontend can send it back as the `X-Tenant-Code` header (see [Multi-Tenancy](#multi-tenancy)).

**Token lifetimes** (`SIMPLE_JWT` in `config/settings/base.py`): access tokens 20 minutes, refresh tokens 7 days.

**Manual testing:** run `python manage.py create_test_user --role pool_manager` (or any other role — see [Permissions](#permissions-rbacabac)) to create a test user under the `NOVU-DEMO` tenant and print its email/password, then walk through the flow above with curl.

**Frontend integration:** the frontend (`frontend/src/pages/auth/`, `frontend/src/api/auth.tsx`, `frontend/src/api/axios.ts`) is now connected to this flow — see [Authentication (connected)](#authentication-connected) above.

## Permissions (RBAC/ABAC)

Role checks (RBAC) and tenant-ownership checks (ABAC) are implemented as DRF permission classes in `apps/accounts/permissions.py`.

**Role-based permission classes** — one per BRD role, each allows only an authenticated user whose `user.role` matches:

- `IsPlatformSuperAdmin`, `IsProductManager`, `IsPoolManager`, `IsFinanceMaker`, `IsFinanceChecker`, `IsShariahSecretariat`, `IsShariahBoard`, `IsRiskCompliance`, `IsAuditor`, `IsInvestorOrMember`

Use them like any DRF permission class:

```python
class SomeView(APIView):
    permission_classes = [IsAuthenticated, IsPoolManager]
```

**`HasAnyRole(roles)`** — a factory for endpoints that should allow more than one role, without writing a new class per combination:

```python
from apps.accounts.permissions import HasAnyRole

class SomeView(APIView):
    permission_classes = [IsAuthenticated, HasAnyRole(["pool_manager", "finance_checker"])]
```

**`IsSameTenant`** — an object-level (ABAC) permission for tenant-scoped models. `has_permission` only requires the user to be authenticated; `has_object_permission` checks `obj.tenant_id == request.user.tenant_id`. There's no real tenant-scoped business model yet (see `apps.core.TenantScopedModel`, [Multi-Tenancy](#multi-tenancy)) — this is ready for BE-007+ endpoints that use DRF's object-level permission checks (e.g. `get_object()` on a `RetrieveAPIView`/`ModelViewSet`), combined with a role permission:

```python
permission_classes = [IsAuthenticated, IsPoolManager, IsSameTenant]
```

**`validate_maker_checker(maker_user, checker_user)`** (`apps/accounts/workflow.py`) — raises `ValidationError` if the same user is passed as both maker and checker. No approval workflow model exists yet; this helper is ready for BE-013 (approval workflows — journal batch review, allocation run approval, etc.) to import and call before persisting a checker decision.

**Test endpoints** (temporary, `apps/accounts/views.py` — to be removed once real business endpoints exist):

- `GET /api/v1/auth/test-permissions/pool-manager-only/` — `IsPoolManager` only.
- `GET /api/v1/auth/test-permissions/finance-only/` — `HasAnyRole(["finance_maker", "finance_checker"])`.

**Manually verified:** a `pool_manager` test user gets `200` from the pool-manager-only endpoint and `403` from the finance-only endpoint; a `finance_maker` test user gets `200` from the finance-only endpoint and `403` from the pool-manager-only endpoint; no token at all gets `401`.

## Error Handling, Logging & Audit Trail

### Standard error format

All exceptions raised through DRF (`ValidationError`, `NotAuthenticated`, `PermissionDenied`, `NotFound`, unhandled exceptions, etc.) are converted by `apps/core/exceptions.py` (`custom_exception_handler`, wired via `REST_FRAMEWORK["EXCEPTION_HANDLER"]`) into one consistent shape:

```json
{
  "error": {
    "code": "validation_error",
    "message": "Validation failed.",
    "details": { "password": ["This field is required."] }
  }
}
```

- `code` — a stable, machine-readable string (`validation_error`, `not_authenticated`, `permission_denied`, `not_found`, `internal_server_error`, etc.).
- `message` — a single human-readable summary.
- `details` — the original DRF error payload (e.g. field → list of errors) when available, otherwise `null`.
- Unhandled exceptions (bugs, DB errors) are logged with a full traceback and returned as a generic `500 internal_server_error` rather than leaking a stack trace.

Note: a few endpoints written before this handler existed (`/auth/login/`, `/auth/mfa/setup/`, `/auth/mfa/verify/`, `TenantMiddleware`'s 403s) return manually-constructed `{"detail": "..."}` responses rather than raising a DRF exception, so they are **not yet** converted to this shape — the exception handler only intercepts raised exceptions, not directly returned `Response` objects. New endpoints should raise the appropriate DRF exception (or `serializer.is_valid(raise_exception=True)`) to get the standard format for free.

(Fixed while building the Products API: `custom_exception_handler` originally crashed with `AttributeError: 'Http404' object has no attribute 'detail'` on any genuine 404/`PermissionDenied`, because DRF's default handler normalizes those internally only for the *response* it builds, not for the `exc` object passed back to custom handlers. It now normalizes `Http404`/Django's `PermissionDenied` into their DRF equivalents itself before reading `.detail`.)

### Logging

Configured in `config/settings/base.py` (`LOGGING`): a console handler for local development plus a rotating file handler writing to `backend/logs/app.log` (5 MB per file, 5 backups kept). Format: `{timestamp} {level} {module} {message}`. Two loggers are configured — `django` (framework logs, e.g. request/response lines) and `apps` (for application code — use `logging.getLogger("apps")` in any `apps.*` module). `logs/` is gitignored.

### Audit Trail

`apps.core.AuditLog` is an **append-only** record of significant actions — it deliberately does not inherit `BaseModel` (no `is_active`/soft-delete concept) and overrides `save()`/`delete()` to raise `ValueError` if called on an existing row: entries can only ever be created, never updated or deleted, including from the Django admin (`AuditLogAdmin` disables add/change/delete entirely — it's view-only).

Fields: `tenant` (nullable, for system-level actions), `actor` (nullable, for automated actions), `action` (e.g. `"create"`, `"approve"`, `"reject"`), `model_name`, `object_id`, `changes` (JSON, e.g. before/after values), `reason` (free text — required context for approvals), `ip_address`, `created_at`.

Use the `log_action()` helper (`apps/core/audit.py`) from any business module (BE-007+) whenever an action worth auditing happens:

```python
from apps.core.audit import log_action

log_action(
    tenant=pool.tenant,
    actor=request.user,
    action="approve",
    model_name="AllocationRun",
    object_id=str(allocation_run.id),
    changes={"status": {"before": "pending", "after": "approved"}},
    reason="Variance within tolerance",
    request=request,  # optional - IP address is extracted from it if provided
)
```

**Manual testing:** run `python manage.py test_audit_log` — it creates a few entries via `log_action()`, then attempts to update and delete one of them, confirming both are rejected.

## Data Model

Backend models are documented here as they are added.

- **`apps.core.BaseModel`** (abstract) — shared base for all models: UUID primary key, `created_at`, `updated_at`, and `is_active` (soft state only — no physical deletes, per BRD).
- **`apps.tenants.Tenant`** — a customer organization (`name`, unique `code`, unique `domain`, `data_residency`, `is_suspended`).
- **`apps.tenants.LegalEntity`** — a legal entity under a `Tenant` (`tenant` FK, `name`, `registration_number`, `jurisdiction`, `base_currency`, `timezone`).
- **`apps.core.TenantScopedModel`** (abstract, inherits `BaseModel`) — adds a required `tenant` FK and swaps in `TenantScopedManager` as the default manager. All future business models (Product, Pool, etc.) should inherit from this instead of `BaseModel` directly.
- **`apps.accounts.User`** (`AUTH_USER_MODEL`, extends `AbstractUser`) — email-based login (`USERNAME_FIELD = "email"`), `full_name`, `role` (one of the BRD roles: platform super admin, product manager, pool manager, finance maker/checker, Shariah secretariat/board, risk & compliance, auditor, investor/member), `tenant` FK (nullable, for platform super admins), `totp_secret`, `mfa_enabled`.
- **`apps.core.AuditLog`** — append-only audit trail, not derived from `BaseModel`; see [Error Handling, Logging & Audit Trail](#error-handling-logging--audit-trail).
- **`apps.products.ShariahDecision`** (`TenantScopedModel`) — a Shariah ruling (`decision_code` unique, `title`, `description`, `status`: draft/approved/superseded, `effective_date`, `approved_by` FK to `User`).
- **`apps.products.ContractTemplate`** (`TenantScopedModel`) — `name`, `contract_type` (mudarabah unrestricted/restricted, musharakah, wakalah, qard), `version`, `clauses` (JSON), `shariah_decision` FK (nullable), `status` (draft/approved/retired).
- **`apps.products.Product`** (`TenantScopedModel`) — `name`, `code` (unique per tenant), `operating_model` (bank pool/investment pool/community circle), `contract_template` FK, `status` (draft/shariah_review/approved/active/retired), `base_currency`.
- **`apps.pools.Pool`** (`TenantScopedModel`) — `name`, `code` (unique per tenant), `product` FK, `status` (draft/approved/open/allocation/closed/archived), `effective_date`, `closed_date`; see [Pool Lifecycle](#pool-lifecycle).
- **`apps.pools.PoolVersion`** (`TenantScopedModel`) — `pool` FK (`related_name="versions"`), `version_number`, `snapshot` (JSON), `created_by`, `is_current`.
- **`apps.allocation.WeightageBand`** (`TenantScopedModel`) — `pool` FK (`related_name="weightage_bands"`), `participant_class`, `weightage`, `effective_from`, `effective_to`, `status` (draft/approved); see [Weightage & PSR Setup](#weightage--psr-setup).
- **`apps.allocation.ProfitSharingRatio`** (`TenantScopedModel`) — `pool` FK (`related_name="psr_schedules"`), `depositor_share`, `mudarib_share`, `effective_from`, `effective_to`, `status` (draft/approved).
- **`apps.allocation.AllocationRun`** (`TenantScopedModel`) — `pool` FK (`related_name="allocation_runs"`), `value_date`, `gross_income`, `direct_expenses`, `distributable_amount`, `total_weighted_funds`, `depositor_pool_share`, `mudarib_share`, `status` (simulated/pending_approval/signed/rejected), `calculation_hash`, `created_by`, `checked_by`, `checked_at`, `rejection_reason`. Populated exclusively from `apps.allocation.engine.calculate_allocation()`; see [Allocation Engine](#allocation-engine) and [Maker-Checker Approval & Journal Posting](#maker-checker-approval--journal-posting).
- **`apps.allocation.AllocationLine`** (`TenantScopedModel`) — `allocation_run` FK (`related_name="lines"`), `participant_class`, `daily_funds`, `weightage`, `weighted_funds`, `allocated_amount`.
- **`apps.accounting.JournalBatch`** (`TenantScopedModel`) — `allocation_run` (`OneToOneField`, `related_name="journal_batch"`), `pool` FK, `batch_date`, `total_debit`, `total_credit`, `status` (posted), `posted_by`. `clean()`/`save()` reject an unbalanced batch (`total_debit != total_credit`); see [Maker-Checker Approval & Journal Posting](#maker-checker-approval--journal-posting).
- **`apps.accounting.JournalEntry`** (`TenantScopedModel`) — `batch` FK (`related_name="entries"`), `account_name`, `entry_type` (debit/credit), `amount`.
- **`apps.allocation.DepositorStatement`** (`TenantScopedModel`) — `allocation_run` FK (`related_name="statements"`), `participant_class`, `period_start`, `period_end`, `opening_balance`, `net_deposits`, `profit_allocated`, `closing_balance`, `narrative`, `generated_at`; see [Depositor Statements](#depositor-statements).
- **`apps.pools.Asset`** (`TenantScopedModel`) — `reference_code` (unique per tenant), `asset_type` (murabahah/ijarah/diminishing_musharakah/other), `description`, `face_value`, `status` (available/assigned/matured/written_off); see [Asset Assignment](#asset-assignment).
- **`apps.pools.AssetAssignment`** (`TenantScopedModel`) — `asset` FK (`related_name="assignments"`), `pool` FK (`related_name="asset_assignments"`), `assigned_date`, `unassigned_date`, `assigned_by`.
- **`apps.pools.DailyBalance`** (`TenantScopedModel`) — `pool` FK (`related_name="daily_balances"`), `participant_class`, `value_date`, `balance_amount`, `source` (manual/file_import/api), `status` (pending/validated/rejected); see [Balance Import & Validation](#balance-import--validation).
- **`apps.pools.BalanceImportBatch`** (`TenantScopedModel`) — `pool` FK (`related_name="import_batches"`), `value_date`, `total_records`, `matched_records`, `exception_count`, `control_total_expected`, `control_total_actual`, `status` (processing/balanced/exception), `imported_by`.

## Products API

CRUD endpoints for the models above, all tenant-scoped (require `X-Tenant-Code`, see [Multi-Tenancy](#multi-tenancy)) and role-gated (see [Permissions](#permissions-rbacabac)):

| Endpoint | Create | Notes |
|---|---|---|
| `/api/v1/products/shariah-decisions/` | `IsShariahBoard` or `IsShariahSecretariat` | Standard CRUD + `POST {id}/approve/` (same roles) |
| `/api/v1/products/contract-templates/` | `IsProductManager` | Standard CRUD + `POST {id}/approve/` (`IsShariahBoard` only) |
| `/api/v1/products/products/` | `IsProductManager` | Standard CRUD + two custom actions below |

**Custom Product actions:**

- **`POST /api/v1/products/products/{id}/submit-for-review/`** — `IsProductManager` only. Moves `draft` → `shariah_review`. Fails with a `400 validation_error` if the product isn't currently `draft`.
- **`POST /api/v1/products/products/{id}/approve/`** — `IsShariahBoard` only. Moves `shariah_review` → `approved`. Enforces **BR-001**: fails with `400 validation_error` unless the product's `contract_template.status == "approved"` — a pool/product cannot be approved without an approved contract.

All create/approve/submit-for-review actions write an `AuditLog` entry via `log_action()`.

**Manually verified end-to-end** with `pool_manager`, `product_manager`, `shariah_board`, and `shariah_secretariat` test users (`create_test_user --role ...`): every cross-role action correctly returns `403`; the full lifecycle (create `ShariahDecision` → approve it → create `ContractTemplate` referencing it → create `Product` → `submit-for-review` → attempt `approve` while the contract template is still `draft`, which correctly fails BR-001 → approve the `ContractTemplate` → retry `approve` on the product, which then succeeds) works as designed; a second tenant's `X-Tenant-Code` correctly sees an empty product list, confirming tenant isolation holds for real business data (not just the `TenantIsolationTestRecord` used to validate `TenantScopedManager` in isolation).

**Implementation note:** DRF `ModelViewSet`s in this app use `get_queryset()` (a method) rather than a class-level `queryset = Model.objects.all()` attribute. With `TenantScopedManager`, a class-level queryset gets evaluated once at import time — before any request (and its tenant context) exists — and Django bakes that "no tenant → empty" result permanently into the queryset object; a later `.all()` at request time does not undo it. Any new tenant-scoped ViewSet should follow the same `get_queryset()` pattern.

## Pool Lifecycle

`apps.pools` adds `Pool` and `PoolVersion` (both `TenantScopedModel`) on top of an approved `Product`.

- **`Pool`** — `name`, `code` (unique per tenant, same `UniqueConstraint` pattern as `Product.code`), `product` FK, `status` (draft/approved/open/allocation/closed/archived), `effective_date`, `closed_date`.
- **`PoolVersion`** (`related_name="versions"` on `Pool`) — `version_number`, `snapshot` (JSON — currently just the product/contract-template config at the time of versioning, since weightage/PSR don't exist yet), `created_by`, `is_current`.

**Important:** once a Pool reaches `open` or later, its configuration must never be edited directly — any config change should produce a new `PoolVersion` instead. Only the structure and the very first version (created automatically on `open`) exist so far; the actual change-request/versioning workflow for an already-open pool is a future task.

**Endpoints** (`/api/v1/pools/pools/`, tenant-scoped, role-gated):

| Action | Endpoint | Role | Transition | Guard |
|---|---|---|---|---|
| Create | `POST /` | `IsPoolManager` | — creates in `draft` | — |
| List versions | `GET /{id}/versions/` | any authenticated | — (read-only) | — |
| Submit for approval | `POST /{id}/submit-for-approval/` | `IsPoolManager` | `draft` → `approved` | Pool must be `draft`; `Pool.product.status` must be `approved` ("Product must be approved first.") |
| Approve | `POST /{id}/approve/` | `IsShariahBoard` | none (formal sign-off only) | Pool must already be `approved`. The substantive Shariah approval happened at the Product level (BR-001); this only records a Pool-specific `AuditLog` sign-off entry. |
| Open | `POST /{id}/open/` | `IsPoolManager` | `approved` → `open` | Pool must be `approved`. Automatically creates `PoolVersion` #1 with a snapshot of the product/contract template. |
| Close | `POST /{id}/close/` | `IsFinanceChecker` | `open` or `allocation` → `closed` | Sets `closed_date` to today. |

Every transition (and `create`) writes an `AuditLog` entry via `log_action()`.

**Seeding for manual testing:** `python manage.py seed_demo_product` creates a fully-approved demo `ShariahDecision` → `ContractTemplate` → `Product` chain under `NOVU-DEMO`; `python manage.py seed_demo_pool` then creates a `draft` `Pool` from that product.

**Manually verified end-to-end** with `pool_manager`, `shariah_board`, and `finance_checker` test users: attempting `open` directly on a `draft` pool correctly fails with a `400 validation_error` (state machine enforced); every cross-role action on every action correctly returns `403`; the full happy path (`submit-for-approval` → `approve` → `open`, which auto-creates `PoolVersion` #1 with the expected product/contract snapshot, confirmed via `GET /versions/` → `close`, which sets `closed_date`) works exactly as designed; confirmed an `AuditLog` entry exists for every one of these steps with the correct actor.

## Weightage & PSR Setup

`apps.allocation` adds effective-dated economics to a `Pool`: `WeightageBand` (per participant class) and `ProfitSharingRatio`/PSR (depositor vs. mudarib split), both `TenantScopedModel`.

- **`WeightageBand`** — `pool` FK (`related_name="weightage_bands"`), `participant_class` (free text, e.g. `"savings_tier_a"` — not a choices field, so new classes don't need a migration), `weightage`, `effective_from`, `effective_to` (nullable = open-ended), `status` (draft/approved).
- **`ProfitSharingRatio`** — `pool` FK (`related_name="psr_schedules"`), `depositor_share`, `mudarib_share`, `effective_from`, `effective_to`, `status` (draft/approved). `clean()` (called from `save()`) enforces `depositor_share + mudarib_share == 100.00`, raising `ValidationError` otherwise.

### BR-002: no overlapping effective-dated records

`apps/allocation/validators.py` (`check_no_overlap`) is a reusable check called from both serializers' `validate()`: for a given `pool` (and, for `WeightageBand`, the same `participant_class` via `extra_filter`), a new record's `[effective_from, effective_to]` range must not overlap any existing record's range for that same pool/class. `effective_to = null` means open-ended (overlaps everything from `effective_from` onward). Overlap is:

```
(new_from <= existing_to OR existing_to is null)
AND
(new_to >= existing_from OR new_to is null)
```

Violating this raises a `400 validation_error` naming the conflicting record. Different `participant_class` values never conflict with each other — only overlap *within the same class* (or, for PSR, within the same pool) is rejected.

**Endpoints** (tenant-scoped, role-gated, filterable by `?pool={pool_id}`):

| Endpoint | Create/Update | Approve |
|---|---|---|
| `/api/v1/allocation/weightage-bands/` | `IsPoolManager` | `POST /{id}/approve/` — `IsShariahBoard`, `draft` → `approved` |
| `/api/v1/allocation/psr-schedules/` | `IsPoolManager` | `POST /{id}/approve/` — `IsShariahBoard`, `draft` → `approved` |

Every create/approve writes an `AuditLog` entry via `log_action()`.

**Seeding for manual testing:** `python manage.py seed_demo_weightage_psr` (after `seed_demo_pool`) creates the BRD example values against the demo pool — `WeightageBand`s for `savings_tier_a` (1.00), `term_tier_b` (1.20), `institutional` (1.25), all pre-approved, plus an approved 70/30 `ProfitSharingRatio`, all effective from the pool's `effective_date`.

**Manually verified end-to-end**: created a `draft` `WeightageBand` and approved it; creating a second band for the *same* `participant_class` with an overlapping (open-ended) date range correctly failed with `400` and named the conflicting record (BR-002); creating a band for a *different* `participant_class` with the exact same dates correctly succeeded (`201`); a PSR with `depositor_share + mudarib_share != 100` correctly failed validation; a valid 70/30 PSR on a pool with no existing PSR succeeded and was approved; a `pool_manager` attempting `approve` (Shariah-Board-only) correctly got `403`. Also caught and fixed a real bug while testing: `ProfitSharingRatio.clean()` compared `depositor_share`/`mudarib_share` without coercing to `Decimal` first — when values arrive as plain strings (e.g. from a management command's `defaults={...}` dict, before Django's field-level casting runs), `"70.00" + "30.00"` is Python string concatenation (`"70.0030.00"`), not addition, so the check always failed. Fixed by explicitly wrapping both values in `Decimal(...)` inside `clean()`.

## Allocation Engine

`apps.allocation.engine` computes a profit allocation for one pool on one `value_date`, given `gross_income` and `direct_expenses`. `AllocationRun` (the persisted result of a calculation) and `AllocationLine` (the per-participant-class breakdown) are described in [Data Model](#data-model).

### Formula

1. `distributable = gross_income - direct_expenses`
2. For each `participant_class` with a `DailyBalance` on `value_date`: find its approved `WeightageBand` covering that date (`effective_from <= value_date <= effective_to`-or-open-ended) and compute `weighted_funds = daily_funds * weightage`.
3. `total_weighted_funds` = sum of all `weighted_funds`.
4. Find the pool's approved `ProfitSharingRatio` covering `value_date`, and split `distributable` into `depositor_pool_share = distributable * depositor_share / 100` and `mudarib_share = distributable * mudarib_share / 100`.
5. Each class's `allocated_amount = depositor_pool_share * (weighted_funds / total_weighted_funds)` — **the depositor's share, not the full distributable, is what gets split across participant classes** (the mudarib's share is the pool operator's own return, never allocated to depositors).
6. All monetary values use `Decimal` with `ROUND_HALF_UP` to 2 decimal places — never `float`.
7. Raises `ValueError` for: no `DailyBalance` found for the date, a participant class with a balance but no matching approved `WeightageBand`, no approved `PSR` covering the date, or `total_weighted_funds == 0` (division-by-zero guard).

### Worked example (BRD Allocation Simulator)

With the seeded demo pool's data — `savings_tier_a` 60M (weightage 1.00), `term_tier_b` 25M (1.20), `institutional` 8M (1.25) — and `gross_income = 12,000,000`, `direct_expenses = 1,000,000`:

| | |
|---|---|
| `distributable` | 11,000,000.00 |
| `total_weighted_funds` | 100,000,000.00 (60M + 30M + 10M) |
| PSR | 70 / 30 |
| `depositor_pool_share` | 7,700,000.00 |
| `mudarib_share` | 3,300,000.00 |

| participant_class | daily_funds | weightage | weighted_funds | allocated_amount |
|---|---|---|---|---|
| savings_tier_a | 60,000,000.00 | 1.00 | 60,000,000.00 | 4,620,000.00 |
| term_tier_b | 25,000,000.00 | 1.20 | 30,000,000.00 | 2,310,000.00 |
| institutional | 8,000,000.00 | 1.25 | 10,000,000.00 | 770,000.00 |

The three `allocated_amount`s sum exactly to `depositor_pool_share` (7,700,000.00), confirmed with no rounding drift.

### `calculate_hash(run_data)`

Returns the SHA-256 hex digest of `run_data` serialized as a sort-keyed JSON string (`Decimal`s stringified first, since they aren't natively JSON-serializable). Used to stamp `AllocationRun.calculation_hash` at save time, so a persisted run's inputs/outputs can later be checked for tampering.

### Endpoints

- **`POST /api/v1/allocation/allocation-runs/simulate/`** — runs `calculate_allocation()` and returns the result **directly in the response**; nothing is written to the database. Body: `{"pool": "<id>", "value_date": "2026-09-01", "gross_income": "12000000.00", "direct_expenses": "1000000.00"}`. Permission: `IsPoolManager` or `IsFinanceMaker` (via `HasAnyRole`).
- **`POST /api/v1/allocation/allocation-runs/`** — same input, but persists the result as one `AllocationRun` (`status="simulated"`, `calculation_hash` set) plus its `AllocationLine`s, and returns the saved record (nested `lines`). Same permission as `simulate/`.
- **`GET /api/v1/allocation/allocation-runs/?pool={pool_id}`** — list, with nested `lines`, filterable by pool. Any authenticated user.
- **`GET /api/v1/allocation/allocation-runs/{id}/`** — detail, with nested `lines`.

Every persisted run writes an `AuditLog` entry via `log_action()` with the run's summary (`distributable_amount`, `total_weighted_funds`, `depositor_pool_share`, `mudarib_share`, line count, `calculation_hash`).

**Implementation note:** the input serializer (`AllocationRunInputSerializer`) builds its `pool` field in `__init__` rather than as a class-level `PrimaryKeyRelatedField(queryset=Pool.objects.all())`, for the same reason documented under [Balance Import & Validation](#balance-import--validation) — a `TenantScopedManager` queryset frozen at import time (no tenant context yet) stays empty forever no matter how many times `.all()` is called on it afterward.

**Manually verified end-to-end via real HTTP requests** (not Django shell): `simulate/` returned the exact worked-example numbers above and confirmed **zero** `AllocationRun`/`AllocationLine` rows existed afterward; `POST /allocation-runs/` then created exactly 1 `AllocationRun` (`status="simulated"`, a populated `calculation_hash`) and 3 `AllocationLine`s with the same numbers; a `value_date` with no `DailyBalance` returned a clear `400 validation_error` via the API; a request missing a required field (`gross_income`) returned DRF's own field-level `400`; a `shariah_board` user (neither `pool_manager` nor `finance_maker`) got `403` on both `simulate/` and the save endpoint; the list and detail `GET` endpoints returned the run with its nested lines, and `?pool=` filtering worked; confirmed the `AuditLog` entry for the persisted run.

## Maker-Checker Approval & Journal Posting

Once an `AllocationRun` is persisted (`status="simulated"`), it goes through a maker-checker approval flow before its numbers are posted to the ledger.

### AllocationRun status lifecycle

`simulated` → (Finance Maker submits) → `pending_approval` → **[bank_pool only] (Shariah Secretariat signs off) →** `shariah_review` → (Finance Checker decides) → `signed` **or** `rejected`

A Finance Checker can reject from either `pending_approval` or `shariah_review` (whichever stage the run is currently sitting in); `approve/` (→ `signed`) is only reachable from the single stage the pool's `shariah_review_required` flag currently requires.

- **`POST /api/v1/allocation/allocation-runs/{id}/submit-for-checking/`** — `IsFinanceMaker` only. Requires `status == "simulated"`.
- **`AllocationRun.shariah_review_required`** (read-only computed property, exposed on the serializer) is `True` when the run's pool's `Product.operating_model == "bank_pool"` **and** the `ALLOCATION_SHARIAH_REVIEW_REQUIRED_FOR_BANK_POOL` setting (env-configurable, default `True`) is on. It is evaluated live from the pool + setting each time it's read, not stored on the row — flipping the setting doesn't retroactively change the flow already in progress for a run's UI state, since the flag is derived fresh on every request.
- **`POST /api/v1/allocation/allocation-runs/{id}/shariah-sign-off/`** — `IsShariahSecretariat` only. Requires `shariah_review_required == True` and `status == "pending_approval"` (`400` with *"This AllocationRun's pool does not require Shariah review."* if the pool doesn't need it at all). Body: `{"note": "..."}` (optional, stored as `shariah_review_note`). Sets `shariah_signed_off_by`, `shariah_signed_off_at`, `status = "shariah_review"`.
- **`POST /api/v1/allocation/allocation-runs/{id}/approve/`** — `IsFinanceChecker` only. Requires `status == "pending_approval"` when `shariah_review_required == False`, or `status == "shariah_review"` when it's `True` — so for a `bank_pool` run, a Finance Checker cannot skip straight from `pending_approval` to `signed`; the Shariah sign-off step is enforced server-side, not just hidden in the UI. Calls `apps.accounts.workflow.validate_maker_checker(maker_user=run.created_by, checker_user=request.user)` — if the same user created and is now approving the run, the request fails with `400`: *"Maker and checker cannot be the same user"*. On success: sets `checked_by`, `checked_at`, `status = "signed"`, and immediately calls `create_journal_from_allocation()` to post the ledger entries (below). The response includes the nested `journal_batch`.
- **`POST /api/v1/allocation/allocation-runs/{id}/reject/`** — `IsFinanceChecker` only. Requires `status == "pending_approval"` **or** `status == "shariah_review"` — unlike `approve/`, which can only fire from whichever single stage is currently required (`shariah_review` when the pool needs Shariah review, `pending_approval` otherwise), `reject/` is allowed from either stage, so a Finance Checker can still stop a `bank_pool` run after it has cleared Shariah sign-off. Also requires a `rejection_reason` in the body (`400` if missing). Sets `checked_by`, `checked_at`, `rejection_reason`, `status = "rejected"`; the `AuditLog` entry's `changes.status.before` records whichever of the two stages the run was rejected from. No journal is posted.

Every transition writes an `AuditLog` entry; for `reject`, the `rejection_reason` is also stored in the `AuditLog.reason` field, not just on the run; for `shariah-sign-off`, `shariah_review_note` is stored the same way.

### Allocation Run approval timeline (frontend)

`src/pages/AllocationRunDetail.tsx` renders a 4-stage timeline (Prepared → Independent Check → Shariah Review → Final Release) as a row of cards above the run's figures, each showing an owner, a decision badge (Completed / Approved / In Review / Blocked / Pending), and a timestamp:

- **Prepared** — always `Completed`, showing `created_by` and `created_at`.
- **Independent Check** — `Pending` while `simulated`, `In Review` once submitted (`pending_approval`) with no owner yet (nobody has actually checked it), `Approved` once past that stage, `Blocked` if `rejected`.
- **Shariah Review** — only meaningful when `shariah_review_required` is `True`; otherwise stays `Pending`/greyed with no owner. Shows `In Review` while waiting in `pending_approval`, `Approved` with the signing-off Secretariat user and `shariah_signed_off_at` once signed off.
- **Final Release** — `Completed` with `checked_by`/`checked_at` only once `status == "signed"`; `Blocked` if rejected, `Pending` otherwise.

The Actions card adapts to the same flag: a `bank_pool` run sitting in `pending_approval` shows a "Waiting for Shariah Secretariat sign-off" notice and a **Shariah Sign-Off** button (calls the new `shariahSignOffRun()` in `src/api/allocationRuns.ts`) instead of the Approve/Reject buttons, which only appear once the run reaches `shariah_review`; a non-`bank_pool` run keeps the original direct `pending_approval` → Approve/Reject behavior unchanged.

User references (`created_by`, `checked_by`, `shariah_signed_off_by`) are shown as `User #{id}` — there's no user-lookup-by-id endpoint yet to resolve a display name, consistent with how user references are shown everywhere else in the frontend today.

**Verified via real HTTP requests** in `apps/allocation/tests.py::AllocationRunShariahReviewStageApiTests`: created a `bank_pool` run, confirmed `shariah_review_required=True` on the API response, submitted it for checking, confirmed a Finance Checker's premature `approve/` is rejected with `400`, confirmed a Finance Checker cannot call `shariah-sign-off/` (`403`), had the Shariah Secretariat sign off successfully (`status` → `shariah_review`, note stored, signer recorded), then had the Finance Checker approve successfully (`status` → `signed`). A second test created an `investment_pool` run, confirmed `shariah_review_required=False`, confirmed `shariah-sign-off/` is rejected with `400` for a pool that doesn't need it, and confirmed the Finance Checker can approve directly from `pending_approval` as before. Two more tests cover `reject/`: one signs a `bank_pool` run off through Shariah Review and confirms the Finance Checker can reject it from `shariah_review` (`status` → `rejected`) while a Finance Maker gets `403`; the other confirms the pre-existing `pending_approval` → `rejected` path still works unchanged. `npm run build` is clean.

### Double-entry journal posting (`apps/accounting`)

`apps.accounting.services.create_journal_from_allocation(allocation_run, posted_by)` builds one balanced `JournalBatch` (`status="posted"`, linked 1:1 to the `AllocationRun` via `OneToOneField`) with a `JournalEntry` per line:

- **Per participant class** (from the run's `AllocationLine`s): `DEBIT "Profit Expense - {class}"` and `CREDIT "Depositor Payable - {class}"`, both equal to `allocated_amount` — recognizing the pool's obligation to pay depositors.
- **For the mudarib's own share**: `DEBIT "Mudarib Income Suspense"` and `CREDIT "Mudarib Income"`, both equal to `mudarib_share` — a self-contained pair recognizing the bank's own income, independent of the depositor entries above.

`total_debit` and `total_credit` are each the sum of their respective entries and are therefore equal by construction; `JournalBatch.clean()` (called from `save()`) still re-validates `total_debit == total_credit` and raises *"Journal batch is not balanced."* if not — this exists as a safety net even though the service always produces a balanced batch.

### Journal Batches API

- **`GET /api/v1/accounting/journal-batches/?pool={pool_id}`** — read-only list (with nested `entries`), any authenticated user, filterable by pool.

### Income/Expense Events

`IncomeExpenseEvent` is a manually-recorded income or expense item for a pool (e.g. a provision reversal, an ad-hoc operational expense) that doesn't come from the `AllocationRun` → `JournalBatch` pipeline. It's its own small maker-checker record, tracked independently — **posting an event does not create `JournalEntry` rows**; wiring it into the double-entry ledger is future scope, this only tracks the event's own `pending` → `posted` lifecycle for now.

- **`POST /api/v1/accounting/income-expense-events/`** — `IsFinanceMaker` only. Body: `{pool, event_type: "income"|"expense", category, amount, event_date, description}`. `category` is a free-text field (e.g. `profit_income`, `operational_expense`, `provision_reversal`), not an enum — kept open-ended rather than a fixed choice list since the categories in use will likely grow. New events start `pending`.
- **`GET /api/v1/accounting/income-expense-events/?pool={pool_id}`** — any authenticated user, filterable by pool.
- **`POST /api/v1/accounting/income-expense-events/{id}/post/`** — `IsFinanceChecker` only (a different role than the creator, mirroring the segregation-of-duties pattern used everywhere else — Allocation Runs, Subscriptions/Redemptions). Requires `status == "pending"`; sets `posted_by`, `posted_at`, `status = "posted"`.
- Every create and post writes an `AuditLog` entry.

**Frontend**: `src/pages/IncomeExpenseWorkbench.tsx`, added as the "Income & Expense" tab on a new `src/pages/FinanceLedger.tsx` page (routed at `/finance-ledger`), alongside the pre-existing Journal Batch Review as its "Journal Batches" tab (both pages had their own `PageHeader` removed/consolidated into the new parent, same pattern as the Shariah Governance and Risk & Compliance tabbed pages). A pool selector, a table (event type badge, category, amount, status badge), a **"+ New Event"** modal (Finance Maker), and a **Post** row action (Finance Checker, only shown for `pending` events).

**Verified via real HTTP requests** in `apps/accounting/tests.py::IncomeExpenseEventApiTests`: created an event as Finance Maker (`201`, `status: "pending"`); confirmed a Finance Maker cannot post their own event (`403`); posted it as Finance Checker (`200`, `status: "posted"`, `posted_by` set); confirmed posting it a second time is rejected (`400`); confirmed a Pool Manager cannot create an event (`403`); confirmed the list endpoint filters correctly by `?pool=`. `npm run build` is clean.

### Reconciliation Copilot

`apps/accounting/reconciliation.py` provides a **rule-based v1, simplified sanity check** after each journal batch is posted. It is not production-grade line-by-line reconciliation; it is a high-level control designed to catch large mismatches.

For the journal batch's pool, the check compares:

1. `journal_total`: the cumulative `amount` of all credit entries whose account name starts with `Depositor Payable` across that pool's posted `JournalBatch` records.
2. `snapshot_total`: the sum of all `DailyBalance.balance_amount` values in the pool's most recent `value_date` snapshot, across participant classes.

The percentage difference is:

```text
abs(journal_total - snapshot_total) / abs(snapshot_total) * 100
```

When the snapshot total is zero, the difference is `0%` if both totals are zero and `100%` otherwise. A difference of **5% or less** is tolerated because normal round-trip differences can occur. A difference above 5% creates an `ExceptionCase` with `source_module="accounting"`; severity is `medium` above 5% and `high` above 15%. The exception description includes both totals and the exact percentage difference. The check is best-effort and never blocks journal posting if it fails.

**Manually verified end-to-end via real HTTP requests:** created a `simulated` run as a `finance_maker`, submitted it for checking (`pending_approval`); a `pool_manager` got `403` attempting `submit-for-checking` (wrong role); confirmed via Django shell that when the same physical user is set as both `created_by` and the approving `finance_checker`, `approve/` correctly returns `400` with the exact maker-checker message (there's no way to trigger this through the API alone in the current single-role-per-user model, since `finance_checker` can't create runs — this was flagged and confirmed with the user before testing this way); a genuinely different `finance_checker` then approved successfully — `status` became `signed`, `checked_by`/`checked_at` were set, and a `JournalBatch` was created with `total_debit == total_credit == 11,000,000.00` across exactly 8 entries (3 debit/credit pairs for the participant classes plus the mudarib pair); a second run was rejected with a required `rejection_reason`, confirmed recorded on both the run and its `AuditLog` entry, with no `JournalBatch` created; a `shariah_board` user got `403` on both `approve/` and `reject/`; confirmed via shell (equivalent to what the Django admin list page shows) that the posted `JournalBatch`'s `total_debit` and `total_credit` are equal.

## Allocation Anomaly Detector

`apps/allocation/anomaly_detector.py` — `check_for_anomalies(allocation_run)` — runs automatically as the last step of `AllocationRun.approve/` (after the run is signed and its `JournalBatch` is posted; see [Maker-Checker Approval & Journal Posting](#maker-checker-approval--journal-posting) above), and flags an `ExceptionCase` if the just-signed run looks statistically unusual compared to that pool's recent history.

**This is a rule-based v1 check, not a statistical or ML model.** It compares two metrics against a simple moving average of the trailing 5 signed runs for the same pool:

1. **Profit margin** — `distributable_amount / gross_income` for the whole run.
2. **Per-participant-class allocation ratio** — `allocated_amount / daily_funds` for each `AllocationLine`, compared against the same participant class's average ratio across the baseline runs.

For each metric, `deviation = abs(current - average) / average`. A deviation of **40% or more** on *either* metric raises exactly one `ExceptionCase` (the first metric found to breach the threshold — profit margin is checked before per-class ratios). Severity is `high` if the deviation is **60% or more**, otherwise `medium`.

- **No baseline, no check.** If the pool has fewer than 5 prior *signed* runs, `check_for_anomalies()` returns `False` immediately and does nothing — there's no history to compare against yet, so a brand-new pool's first several runs are never flagged regardless of their numbers.
- **`ExceptionCase` fields**: `source_module="allocation"`, `source_object_id=str(allocation_run.id)`, `pool=allocation_run.pool`, `detected_by="system"`, and a `description` that states the actual numbers, e.g. *"Allocation ratio for 'Depositor' 84.00% is 233.33% different from the 5-run average of 25.20%."* — deliberately concrete rather than a generic "anomaly detected" message, so a Risk & Compliance reviewer can triage without re-deriving the math.
- **Never blocks approval.** `approve/` calls `check_for_anomalies()` in a `try/except`, logging (not raising) on failure — a bug or edge case in the anomaly check must never prevent a legitimately-approved run from being signed and posted. This is a detection/triage aid, not a gate.
- **Known limitation (accepted for v1):** the baseline is always "whatever the 5 most recent signed runs are," including runs that were themselves flagged as anomalous. A flagged run is not excluded from becoming part of the next run's baseline, so a real anomaly can temporarily skew what counts as "normal" for the pool's next couple of runs. This was a deliberate choice to keep v1 simple and match the spec exactly ("average of the previous 5 signed runs"); if this turns out to cause too much baseline noise in practice, a v2 could exclude runs with an open/unresolved `ExceptionCase` from the baseline calculation.

**Relationship to Mizan:** the team has a separate, general-purpose anomaly detection tool called **Mizan**, intended to eventually operate as a standalone General Reports/Analytics capability across the whole system (not allocation-specific). This rule-based allocation check is **not** Mizan and does not share code or infrastructure with it — it's a narrow, allocation-specific v1 safeguard that ships now. Mizan integration is future scope and, when it lands, may either subsume this check or run alongside it as a second, independent signal.

**Manually verified:** created 5 baseline `signed` runs for a pool with a consistent ~10% profit margin and 14%/70% depositor/mudarib allocation ratios; a 6th run with 5x the gross income deviated 400% on the depositor ratio and correctly raised a `high`-severity `ExceptionCase` with the exact numbers in the description; a 6th run with normal, in-line numbers against the same clean baseline raised nothing; a brand-new pool's first-ever run (no baseline at all) was correctly skipped with no `ExceptionCase` and no error; confirmed end-to-end through the real `POST /api/v1/allocation/allocation-runs/{id}/approve/` endpoint (not just the function directly) that an anomalous run's `approve/` call still returns `200` with the run signed and its journal posted, while a matching `ExceptionCase` (`source_module="allocation"`) appears via `GET /api/v1/governance/exceptions/` — confirming the check runs silently in the background and never surfaces as an approval failure.

### GL Export (`apps/accounting/exports.py`)

`generate_gl_csv(pool, date_from=None, date_to=None)` flattens every `posted` `JournalBatch` for a pool (and their nested `JournalEntry` rows) into a single standard general-ledger CSV, sorted by `batch_date` (oldest first). Only `status="posted"` batches are included — the filter is written against `JournalBatchStatus.POSTED` rather than hardcoding the string, so it stays correct if additional statuses (e.g. a future `"reversed"`) are introduced later. Optional `date_from`/`date_to` filter on `batch_date`.

CSV columns: `batch_date, journal_batch_id, allocation_run_id, account_name, entry_type, amount, pool_code, posted_by, posted_at`.

Sample row:

```
2026-09-01,3e5a4df9-666c-4749-8f49-dd377fc8c49e,f5f8dbd9-3a36-4caa-8fb4-82b831dfd911,Profit Expense - savings_tier_a,debit,4620000.00,PL-2026-014-01,finance.checker@novulabsdemo.test,2026-09-16 06:48:38.259219+00:00
```

**Endpoint: `GET /api/v1/accounting/journal-batches/gl-export/?pool={pool_id}&date_from=...&date_to=...`**

- Permissions: `IsFinanceMaker` or `IsFinanceChecker` (via `HasAnyRole`) — only the finance team can export GL data.
- Returns `Content-Type: text/csv` with `Content-Disposition: attachment; filename="gl_export_{pool_code}_{date_from}_{date_to}.csv"`.
- No matching posted batches (wrong pool, or a `date_from`/`date_to` range with nothing in it) returns an **empty CSV with just the header row**, not an error — this is a normal empty-result case, not a failure.
- Read-only, but still audit-logged: exporting financial data is compliance-worthy even though nothing is modified. Writes one `AuditLog` entry per call (`action="gl_export"`, `model_name="Pool"`) recording `{"pool": pool.code, "row_count": N, "date_from": ..., "date_to": ...}` — so who exported what, and how much, is always traceable.
- Tenant isolation relies on `JournalBatch`'s `TenantScopedManager` (same pattern as the rest of the codebase) rather than an explicit tenant filter inside `generate_gl_csv()`.

**Manually verified end-to-end via real HTTP requests:** exported a pool with 3 posted `JournalBatch`es (24 entries total) as `finance_maker` — got back a well-formed CSV; parsed it with Python's `csv.DictReader` and confirmed the debit column sum equals the credit column sum (`22,500,000.00 == 22,500,000.00`, balanced); a `date_from` in the far future returned an empty CSV (header only, `200 OK`); a pool with zero posted batches also returned an empty CSV; a `shariah_board` user got `403`; confirmed via Django shell that each call wrote an `AuditLog` row with the correct `row_count` and filter values, including `row_count: 0` for the empty-result cases.

## Reconciliation Copilot

`apps/accounting/reconciliation.py` — `check_reconciliation(journal_batch)` — runs automatically as the last step of `create_journal_from_allocation()` (right after a `JournalBatch` is posted; see [Double-entry journal posting](#double-entry-journal-posting-appsaccounting) above), and flags an `ExceptionCase` if what's been posted to the ledger looks materially out of line with the pool's most recent balance data.

**This is a simplified v1 sanity check, not production-grade reconciliation.** Real reconciliation matches individual transactions line-by-line; this instead compares two pool-level totals as a coarse "does the big picture make sense" gate:

1. **Posted depositor payable total** — the sum of `total_credit` across every `posted` `JournalBatch` for the pool, restricted to `JournalEntry` rows whose `account_name` starts with `"Depositor Payable"` (cumulative across all signed runs to date, not just the batch that triggered the check).
2. **Latest balance snapshot total** — the sum of `DailyBalance.balance_amount` across all participant classes for the pool's single most recent `value_date` (i.e. "what the balances say depositors are owed as of the latest known snapshot").

`percentage_difference = abs(journal_total - snapshot_total) / abs(snapshot_total) * 100` (treated as `100%` if `snapshot_total` is `0` but `journal_total` isn't, and `0%` if both are `0`). A mismatch **over 5%** (`MISMATCH_TOLERANCE`) raises exactly one `ExceptionCase` — the 5% tolerance exists because some day-to-day drift between a ledger total and a balance snapshot is normal (timing differences, in-flight transactions) and shouldn't page anyone. Severity is `high` if the mismatch is **over 15%** (`HIGH_SEVERITY_THRESHOLD`), otherwise `medium`.

- **`ExceptionCase` fields**: `source_module="accounting"`, `source_object_id=str(journal_batch.id)`, `pool=journal_batch.pool`, `detected_by="system"`, and a `description` stating both totals and the exact percentage difference, e.g. *"Posted depositor payable total is 42000.00; latest DailyBalance snapshot total is 10000.00; exact percentage difference is 320.00%."*
- **Never blocks posting.** `create_journal_from_allocation()` calls `check_reconciliation()` in a `try/except`, logging (not raising) on failure — the same pattern as the [Allocation Anomaly Detector](#allocation-anomaly-detector)'s hook into `approve/`. A bug or edge case in the reconciliation check must never prevent a legitimately-balanced journal batch from being posted.
- **Known limitation (accepted for v1):** this compares pool-level totals, not individual transactions — it can miss offsetting errors (e.g. one participant class over-credited and another under-credited by the same amount would net to a 0% pool-level difference) and it only ever looks at the *latest* `DailyBalance` snapshot, not a matching-date comparison against the journal batch's own `batch_date`. A true production reconciliation engine (transaction-level matching, per-date comparison) is future scope; this is deliberately a cheap, fast, "did something go badly wrong" tripwire, not a substitute for it.

**Manually verified:** with matching data (a `DailyBalance` snapshot of 42,000 against a posted `JournalBatch` with 42,000 in `Depositor Payable` credits), `create_journal_from_allocation()` posted the batch and correctly raised no `ExceptionCase`; deliberately altering the `DailyBalance` snapshot down to 10,000 against the same posted 42,000 and re-running `check_reconciliation()` correctly returned `True` and raised a `high`-severity `ExceptionCase` (320% mismatch, both exact totals in the description); `apps/accounting/tests.py`'s `test_reconciliation_failure_does_not_block_journal_posting` patches `check_reconciliation` to raise and confirms `create_journal_from_allocation()` still returns a valid, persisted `JournalBatch` — journal posting is provably unaffected by a reconciliation-check failure. All three `ReconciliationTests` pass (`python manage.py test apps.accounting.tests`).

## Investment Pools — Capital Accounts

`apps.investments` tracks unitized capital for `investment_pool`-operating-model pools (as opposed to the daily-balance-based bank pools everywhere else in this system): investors hold **units** rather than a raw cash balance, and money moves in/out via **subscriptions** (buying units at a NAV) and **redemptions** (selling units back at a NAV).

`apps.investments.CapitalAccount` (`TenantScopedModel`):

- `pool` FK — intended for `investment_pool`-model pools; this is a **convention, not an enforced constraint** yet (no validation blocks attaching a `CapitalAccount` to a `bank_pool`-model `Pool`).
- `investor_name` — a plain name for now. Not linked to a `User` — an `investor_member`-role User linkage is future scope, once investor self-service login exists.
- `investor_reference` — a human-readable code (e.g. `"INV-2026-001"`), unique per tenant (`unique_investor_reference_per_tenant` constraint).
- `units_held` — running balance, maintained only by `subscribe/` and `redeem/` (never editable directly via the API — `units_held` and `status` are both read-only in `CapitalAccountSerializer`).
- `status`: `active` / `closed`.

`Subscription` and `Redemption` (both `TenantScopedModel`, FK'd to `CapitalAccount` via `related_name="subscriptions"` / `"redemptions"`) are the two transaction types, each carrying its own `nav_per_unit`, a computed amount/unit figure, `transaction_date`, and `status` (`pending` / `processed` — both are always created as `processed`, since they're only ever created synchronously through the actions below; `pending` exists for a possible future async/batch flow).

### Endpoints (`apps/investments`)

- **`GET /api/v1/investments/capital-accounts/?pool={pool_id}`** — list, filterable by pool. Any authenticated user.
- **`GET /api/v1/investments/capital-accounts/{id}/`** — detail. Any authenticated user.
- **`POST /api/v1/investments/capital-accounts/`** — create. `IsPoolManager` or `IsFinanceMaker` (via `HasAnyRole`).
- **`POST /api/v1/investments/capital-accounts/{id}/subscribe/`** — body: `{amount, transaction_date}`. Computes `units_allotted = amount / nav_per_unit`, creates a `Subscription` (`status="processed"`), and increments `units_held` by that amount. `IsFinanceMaker` only. `nav_per_unit` is **not** an accepted input — see [NAV Calculation Engine](#nav-calculation-engine) below for where it comes from now.
- **`POST /api/v1/investments/capital-accounts/{id}/redeem/`** — body: `{units_redeemed, transaction_date}`. Validates `units_redeemed <= units_held` (`400` with *"Cannot redeem more units than held"* otherwise), computes `amount = units_redeemed * nav_per_unit`, creates a `Redemption` (`status="processed"`), and decrements `units_held`. **`IsFinanceChecker` only** — deliberately a different role than `subscribe/`'s `IsFinanceMaker`, so the same person can never both bring capital in and take it back out unchecked (segregation of duties, same principle as the [Maker-Checker Approval](#maker-checker-approval--journal-posting) flow elsewhere).

Every `subscribe/redeem` call writes an `AuditLog` entry (`model_name="CapitalAccount"`) recording the transaction id, amount/units, NAV (and which `NAVSnapshot` it came from), and the resulting `units_held`.

### Demo data (`seed_demo_investment_pool`)

`python manage.py seed_demo_investment_pool` creates a fully-approved `investment_pool`-operating-model `Product` + `Pool` (`INV-2026-001` / `INV-2026-001-01`), two `CapitalAccount`s (`INV-2026-001`, `INV-2026-002`), and processes one `Subscription` each — `amount=50000.00` at `nav_per_unit=100.00`, allotting `500` units — so there's ready-made data to exercise `redeem/` against without manually creating everything first. Idempotent: re-running it skips accounts/subscriptions that already exist.

**Manually verified end-to-end via real HTTP requests:** created a `CapitalAccount` as `pool_manager` (`201`, `units_held="0.000000"`); a `shariah_board` user got `403` attempting `subscribe/`; `finance_maker` subscribed `50000.00` at NAV `100.00` — `units_held` correctly became `500.000000`; a `finance_maker` got `403` attempting `redeem/` on the same account (segregation of duties — the maker of a subscription cannot also be the checker of a redemption); `finance_checker` attempting to redeem `600` units against `500` held correctly returned `400` with the exact message *"Cannot redeem more units than held"*; `finance_checker` then redeemed a valid `100` units at NAV `105.00` — got back `amount="10500.00"` and `units_held` correctly dropped to `400.000000`; confirmed **tenant isolation**: a `TENANT-B` `pool_manager` listing capital accounts got `[]` (no leak of the `NOVU-DEMO` account), and fetching that account directly by ID returned `404` (via `TenantScopedManager`, not a `403` that would otherwise confirm its existence).

### Investor KYC

Each `CapitalAccount` can have one tenant-scoped `InvestorProfile`, created or edited by a Finance Maker through `POST/PATCH /api/v1/investments/investor-profiles/`. It records identity details, date of birth, address, risk tolerance, and suitability notes. New profiles start as `pending`.

- Risk Compliance verifies or rejects a profile through `POST /api/v1/investments/investor-profiles/{id}/verify-kyc/` with `{ "kyc_status": "verified" | "rejected", "notes": "..." }`.
- Every create, edit, and verification writes an `AuditLog` entry.
- `subscribe/` rejects accounts without a verified profile with `KYC verification required before subscription`; the frontend also disables Subscribe and shows the tooltip `KYC verification required` until the profile is verified.
- Editing a profile resets its status to `pending`, clearing the previous verification metadata so changed identity data must be reviewed again.

### Investor Portfolio Summary (staff-facing, read-only)

There is no investor-facing login yet — the `investor_member` role exists but nothing issues investors their own credentials. Rather than build that full auth flow now, staff (Pool Manager, Finance Maker/Checker) can view a read-only per-investor summary instead:

- `src/pages/investments/CapitalAccountDetail.tsx`, routed at `/investments/capital-accounts/{id}` and linked via a **"View Portfolio Summary"** button on each expanded row in `InvestmentPools.tsx`. Shows `units_held`, current value (`units_held × latest published NAV`), and full `Subscription`/`Redemption` history tables.
- Backed by two new read-only endpoints: `GET /api/v1/investments/subscriptions/?capital_account={id}` and `GET /api/v1/investments/redemptions/?capital_account={id}` (`SubscriptionViewSet` / `RedemptionViewSet`, list+retrieve only, any authenticated user — same as the existing `CapitalAccountViewSet.retrieve()`). No new write paths; `subscribe/`/`redeem/` on `CapitalAccountViewSet` are unchanged.
- Current value shows "No published NAV" instead of a value when the pool has no published `NAVSnapshot` yet, rather than showing a stale or zero figure.
- Verified via real HTTP requests in `apps/investments/tests.py::CapitalAccountDetailApiTests`: subscribed then redeemed against a test account, confirmed `units_held` reflects both, and confirmed both new list endpoints return exactly the filtered records for that `capital_account`. `npm run build` is clean.

Building an actual investor login (issuing `investor_member` credentials, self-service registration, investor-scoped auth) is deliberately out of scope here and left for a future investor-facing portal phase.

### Pool Dashboard (aggregation tab, no new backend)

`InvestmentPools.tsx` now opens on a **"Dashboard"** tab (the new default, ahead of Capital Accounts / NAV History / Venture View) summarizing the selected pool at a glance. Pure client-side aggregation over data the page already fetches (`accounts`, `snapshots`, `latestNAV`) — **no new backend, no new endpoint calls**:

- **Total Capital** — sum of every account's `units_held × latest published NAV.nav_per_unit`; shows "No published NAV yet" instead of a zero/stale figure when there is none.
- **Total Investors** — simply `accounts.length`.
- **Latest NAV** — the latest published `NAVSnapshot.nav_per_unit`, with its valuation date.
- **NAV Trend** — percentage change between the two most recent **published** snapshots (`draft` snapshots are excluded from the trend, though they still count toward the raw fetched list); shows "Needs 2+ published snapshots" when there isn't enough history yet.
- A small inline SVG sparkline plots up to the last 8 published `nav_per_unit` values.

**Verified via a real end-to-end HTTP test** in `apps/investments/tests.py::PoolDashboardAggregationApiTests`: created 2 capital accounts (200 + 300 units), two published NAV snapshots (`10.00` then `11.00`) and one `draft` snapshot (`12.00`, deliberately excluded from the trend calc); reproduced the dashboard's exact call sequence (`capital-accounts?pool=`, `nav-snapshots?pool=`, `nav-snapshots/latest/?pool=`) and confirmed the resulting aggregation — `500` total units, `5500.00` total capital, and a `+10%` NAV trend computed only from the two published snapshots. `npm run build` is clean.

### Venture View (aggregation tab, no new backend)

A tab, **"Venture View"**, on `InvestmentPools.tsx` alongside Dashboard, Capital Accounts and NAV History — presents the same pool's existing data from an investment-committee angle rather than an operational one. Like the Risk Dashboard and Daily Operations Cockpit above, this is a pure client-side aggregation with **no new backend model**; it does add one small read-only fetch (`fetchImpairmentEvents()`, `GET /api/v1/investments/impairment-events/?pool={id}`) alongside the capital-accounts/NAV calls the page already made, since nothing on the page previously surfaced impairment events at all.

- **Partner Capital Ratios** — each `CapitalAccount.units_held` as a percentage of the pool's total units, rendered as a labeled progress bar per investor.
- **Results** — a table of each account's `units_held × latest published NAV.nav_per_unit` as its current value; shows "No published NAV yet — results cannot be shown" instead of a zero/stale figure when the pool has no published `NAVSnapshot`.
- **Governance** — two status rows, each a `Badge` (`Pending`/`Clear`) plus a one-line explanation: whether the latest `NAVSnapshot` is still `draft` (awaiting Finance Checker publish) or there is none at all, and whether any `ImpairmentEvent` for the pool is still `draft` (awaiting Shariah Board approval).

**Verified via a real end-to-end HTTP test** in `apps/investments/tests.py::VentureViewAggregationApiTests`: created two capital accounts (300 and 100 units), a published NAV snapshot (`nav_per_unit = 20.00`), and one `draft` impairment event; then reproduced the tab's exact call sequence (`capital-accounts?pool=`, `nav-snapshots/latest/?pool=`, `impairment-events?pool=`) and confirmed the resulting aggregation — 75%/25% capital ratios, `6000.00`/`2000.00` results, and 1 pending impairment event correctly detected. `npm run build` is clean.

### Impairment Events and Capital Loss Allocation

`ImpairmentEvent` records a pool valuation loss as a draft with a computed `loss_percentage` based on the published NAV's `total_pool_value` at the event's valuation date. A Shariah Board member approves the event through `POST /api/v1/investments/impairment-events/{id}/approve/`.

Approval is one atomic transaction: every active `CapitalAccount` in the pool has its `units_held` reduced by the same loss percentage, the final six-decimal rounding adjustment keeps the pool total reconciled, and each account reduction is audit-logged. An event cannot be approved twice and approval is restricted to `IsShariahBoard` because the basis for allocating a loss is Shariah-sensitive.

This implements the capital-loss principle of Mudarabah and Musharakah: genuine investment losses are borne by the capital providers (investors) in proportion to their capital participation, rather than being assigned arbitrarily to one investor or absorbed as operating profit. The Shariah Board approval is the control point confirming that the impairment and its allocation basis are appropriate before investor units change.

## NAV Calculation Engine

`apps.investments.NAVSnapshot` gives a pool a formal, maker-checker-approved Net Asset Value per unit at a point in time, and `subscribe/`/`redeem/` (above) now **always** use the pool's latest published NAV automatically — the earlier manual `nav_per_unit` request-body input has been removed entirely; sending one is simply ignored (it's not read from the request at all).

`apps.investments.nav_engine.calculate_nav(pool, total_pool_value)` is a **pure function** (no writes):

```
total_units_outstanding = sum(units_held for all active CapitalAccounts in the pool)
nav_per_unit = total_pool_value / total_units_outstanding   (Decimal, ROUND_HALF_UP, 6 dp)
```

Raises `ValueError` ("No active units outstanding for this pool — cannot calculate NAV.") if there are zero active units — there's no meaningful per-unit value to compute with nothing outstanding. `total_pool_value` is a **manual Finance Maker input for now**; in practice this figure should be derived from a Balance Sheet / asset valuation, but that integration is future scope — v1 trusts whatever the Finance Maker enters.

### Maker-checker flow

`NAVSnapshot.status`: `draft` → `published`, and reuses `apps.accounts.workflow.validate_maker_checker()` — the same helper `AllocationRun.approve/` uses (see [Maker-Checker Approval & Journal Posting](#maker-checker-approval--journal-posting)) — so the same rule applies: the `finance_checker` who publishes can never be the `finance_maker` who created the draft.

- **`POST /api/v1/investments/nav-snapshots/`** — body: `{pool, valuation_date, total_pool_value}`. Calls `calculate_nav()` and persists the result as `status="draft"`, `created_by=request.user`. `IsFinanceMaker` only. Multiple drafts for the same `pool`/`valuation_date` are allowed (e.g. re-entering a corrected `total_pool_value`).
- **`GET /api/v1/investments/nav-snapshots/?pool={pool_id}`** — list, filterable by pool. Any authenticated user.
- **`POST /api/v1/investments/nav-snapshots/{id}/publish/`** — requires `status="draft"`; sets `published_by=request.user`, `published_at=now()`, `status="published"`. `IsFinanceChecker` only, and additionally calls `validate_maker_checker(maker_user=snapshot.created_by, checker_user=request.user)` — `400` with *"Maker and checker cannot be the same user"* if they're the same person. Also blocked (`400`) if another snapshot for the same `pool`/`valuation_date` is already published — **only one published `NAVSnapshot` per pool per date, ever** (enforced both by an explicit pre-check for a clean error message, and by a partial `UniqueConstraint` on `(tenant, pool, valuation_date)` filtered to `status="published"` as the hard DB-level backstop).
- **`GET /api/v1/investments/nav-snapshots/latest/?pool={pool_id}`** — returns the most recent (`-valuation_date`) **published** `NAVSnapshot` for the pool; `400` with a clear message if none exists yet. This is exactly what `subscribe/`/`redeem/` call internally.

Every create/publish writes an `AuditLog` entry (`model_name="NAVSnapshot"`).

### Demo data (`seed_demo_nav_snapshot`)

`python manage.py seed_demo_nav_snapshot` publishes a `NAVSnapshot` for the `seed_demo_investment_pool` pool, baselined so `nav_per_unit` comes out to exactly `100.00` given that pool's existing `1000` units outstanding (`total_pool_value=100000.00`). Run `seed_demo_investment_pool` first. Idempotent.

**Manually verified end-to-end via real HTTP requests:** created a draft `NAVSnapshot` as `finance_maker` (`total_pool_value=105000.00` against `1000` units outstanding → `nav_per_unit="105.000000"`, `status="draft"`); a `shariah_board` user got `403` attempting to create one; the same `finance_maker` who created it got `403` attempting to publish it (wrong role, `IsFinanceChecker` only); a genuinely different `finance_checker` published it successfully; separately confirmed the **actual maker-checker violation** (not just the role gate) by creating a draft with `created_by` set to a `finance_checker` user and having that same user attempt to publish it — correctly returned `400` *"Maker and checker cannot be the same user"*; `subscribe/` on a brand-new pool with zero `NAVSnapshot`s returned exactly *"No published NAV available for this pool. Cannot process subscription/redemption."*; `subscribe/` against the pool with a published `105.00` NAV, sent with a deliberately wrong `nav_per_unit: "1.00"` in the request body, correctly ignored the body value entirely and used the real published NAV (`nav_per_unit="105.000000"` on the resulting `Subscription`, not `1.00`); with two published snapshots for the same pool (`100.00` @ 2026-09-01, `105.00` @ 2026-09-15), `latest/` correctly returned the `2026-09-15` one; attempting to publish a second draft for a `valuation_date` that already had a published snapshot initially surfaced a raw `500` (an uncaught `IntegrityError` from the partial unique constraint) — **fixed** by adding an explicit pre-check in `publish/` that now returns a clean `400` *"A NAVSnapshot for {pool_code} on {date} has already been published."* instead.

### Frontend Investments screen

The `/investments` screen (`frontend/src/pages/InvestmentPools.tsx`) filters the pool list client-side to products with `operating_model="investment_pool"`, then provides the current published NAV, Capital Accounts, and NAV History tabs. Subscribe and Redeem forms deliberately omit `nav_per_unit`: the backend uses the latest published NAV and the UI shows that value as read-only context. Subscribe is visible to `finance_maker`, Redeem and NAV publishing are visible to `finance_checker`, and a missing published NAV disables both account actions with a clear *"Publish a NAV snapshot first"* message. The API wrapper is in `frontend/src/api/investments.ts`; `fetchLatestNAV()` treats the backend's expected no-published-NAV `400` as `null` so the page can render its empty state.

## Depositor Statements

Once an `AllocationRun` is `signed`, one `DepositorStatement` per participant class can be generated — a plain-language, per-class explanation of that period's profit allocation (BRD Screen #41 style).

`apps.allocation.DepositorStatement` (`TenantScopedModel`) — `allocation_run` FK (`related_name="statements"`), `participant_class`, `period_start`/`period_end` (both the run's `value_date` for now — multi-day period tracking is future scope), `opening_balance` (simplified to the `AllocationLine`'s `daily_funds` for now, until real opening-balance/period tracking exists), `net_deposits` (placeholder `0` — a future feature), `profit_allocated` (from `AllocationLine.allocated_amount`), `closing_balance` (`opening_balance + net_deposits + profit_allocated`), `narrative`, `generated_at`.

### Narrative generation (`apps/allocation/statements.py`)

`generate_statement_narrative(participant_class, opening_balance, profit_allocated, weightage, allocation_run)` is a simple template-based function — expected to be replaced/enhanced later by a Disclosure Generator agent. Example output:

> Your daily funds and approved weightage (1.00x) determined your share of distributable pool profit. Based on a distributable amount of 11000000.00 and your class's weighted contribution, you were allocated 4620000.00 for this period.

### Endpoints

- **`POST /api/v1/allocation/allocation-runs/{id}/generate-statements/`** — `IsPoolManager` or `IsFinanceMaker` (via `HasAnyRole`). Requires `run.status == "signed"` (`400 "Statements can only be generated for signed allocation runs."` otherwise). Creates one `DepositorStatement` per `AllocationLine`. **Idempotent**: if statements already exist for this run, the existing records are returned as-is rather than creating duplicates. Writes one `AuditLog` entry (with the statement count) on first generation only — a repeat call doesn't log again, since nothing changed.
- **`GET /api/v1/allocation/allocation-runs/{id}/statements/`** — lists the run's statements. Any authenticated user.

**Manually verified end-to-end via real HTTP requests:** calling `generate-statements/` on a `simulated` (not yet signed) run correctly returned `400` with the exact spec'd message; on a `signed` run it created exactly 3 `DepositorStatement`s (one per participant class) with correct `closing_balance`s (e.g. `60,000,000.00 + 0 + 4,620,000.00 = 64,620,000.00`) and populated narratives; calling it again on the same run returned the same 3 records (confirmed via DB count — still exactly 3, no duplicates) and did **not** write a second `AuditLog` entry; `GET .../statements/` correctly listed all 3 for a `shariah_board` user (any authenticated role can view); a `shariah_board` user attempting `generate-statements/` itself correctly got `403`.

## Asset Assignment

`apps.pools` also has `Asset` and `AssetAssignment` (both `TenantScopedModel`), tracking which physical/financial assets back which pool.

- **`Asset`** — `reference_code` (unique per tenant), `asset_type` (murabahah/ijarah/diminishing_musharakah/other), `description`, `face_value`, `status` (available/assigned/matured/written_off).
- **`AssetAssignment`** — `asset` FK (`related_name="assignments"`), `pool` FK (`related_name="asset_assignments"`), `assigned_date`, `unassigned_date` (nullable = still active), `assigned_by`.

### One active assignment per asset (BR-003-style rule)

An asset can only be actively assigned to one pool at a time. `AssetAssignmentSerializer.validate()` checks — on create only — whether the asset already has an assignment with `unassigned_date__isnull=True`; if so, it raises `400 validation_error`: *"Asset already assigned to another pool. Unassign first."*

Creating an assignment sets `asset.status = "assigned"`; calling the `unassign` action sets `unassigned_date` to today and reverts `asset.status = "available"`, freeing it to be assigned elsewhere.

**Endpoints** (tenant-scoped, `?pool={pool_id}` filter on assignments):

| Endpoint | Create/Update | Notes |
|---|---|---|
| `/api/v1/pools/assets/` | `IsPoolManager` or `IsFinanceMaker` | Standard CRUD |
| `/api/v1/pools/asset-assignments/` | `IsPoolManager` | Standard CRUD + `POST /{id}/unassign/` (`IsPoolManager` only) |

Every create/unassign writes an `AuditLog` entry via `log_action()`.

**Seeding for manual testing:** `python manage.py seed_demo_asset` (after `seed_demo_pool`) creates three demo assets (`available`) and assigns the first one to the demo pool.

**Manually verified end-to-end**: created an asset (`available`) as `finance_maker`; assigned it to a pool as `pool_manager`, confirming `asset.status` flipped to `assigned` and `assigned_by` was set; attempting to assign the *same* asset to a different pool correctly failed with the exact spec'd message; `unassign` correctly set `unassigned_date` and reverted `asset.status` to `available`; the same asset could then be assigned to a *different* pool successfully; both a `finance_maker` (assignment create) and a `shariah_board` user (asset create) attempting actions outside their allowed roles correctly got `403`.

## Balance Import & Validation

`apps.pools` adds `DailyBalance` and `BalanceImportBatch` (both `TenantScopedModel`) for recording and reconciling per-day, per-participant-class balances against a pool.

- **`DailyBalance`** — `pool` FK (`related_name="daily_balances"`), `participant_class` (matches `WeightageBand.participant_class`), `value_date`, `balance_amount`, `source` (manual/file_import/api, default manual), `status` (pending/validated/rejected).
- **`BalanceImportBatch`** — `pool` FK (`related_name="import_batches"`), `value_date`, `total_records`, `matched_records`, `exception_count`, `control_total_expected` (nullable — the user's own calculated total), `control_total_actual` (nullable — the system's summed total), `status` (processing/balanced/exception), `imported_by`.

### `POST /api/v1/pools/balance-imports/` — bulk import

Body:

```json
{
  "pool": "<pool-id>",
  "value_date": "2026-09-01",
  "control_total_expected": "93000000.00",
  "records": [
    {"participant_class": "savings_tier_a", "balance_amount": "60000000.00"},
    {"participant_class": "term_tier_b", "balance_amount": "25000000.00"},
    {"participant_class": "institutional", "balance_amount": "8000000.00"}
  ]
}
```

Processing, inside one transaction:

1. For each record, if a `DailyBalance` already exists for the same `pool` + `value_date` + `participant_class`, it's **skipped** (not overwritten) and an entry is appended to the response's `errors` list; `exception_count` is incremented.
2. Every non-duplicate record creates a `DailyBalance` (`status="validated"`) and adds to a running `control_total_actual`.
3. The batch's `status` is `"balanced"` only if **both** hold: no records were skipped (`exception_count == 0`) **and**, when `control_total_expected` was supplied, it matches `control_total_actual` within a `0.01` tolerance. Any exception — a duplicate skip or a control-total mismatch — sets `status = "exception"`, even if the other check alone would have passed.
4. A `BalanceImportBatch` row is written, and the response returns a summary: `{id, total_records, matched_records, exception_count, control_total_expected, control_total_actual, status, errors}`.

Permission: `IsPoolManager` or `IsFinanceMaker` (via `HasAnyRole`).

**Other endpoints:**

- `GET /api/v1/pools/balance-imports/?pool={pool_id}` — batch history for a pool.
- `GET /api/v1/pools/daily-balances/?pool={pool_id}&value_date={date}` — the actual balance rows for a specific day.

Every import writes an `AuditLog` entry via `log_action()` with the full summary in `changes`.

**Implementation note:** `BulkBalanceImportSerializer`'s `pool` field is assigned in `__init__` rather than as a class-level `PrimaryKeyRelatedField(queryset=Pool.objects.all())` attribute — the same import-time-evaluation trap as the "BE-007 bug" documented under [Products API](#products-api), just one level down: `PrimaryKeyRelatedField.get_queryset()` calls `.all()` on the stored queryset to "re-evaluate" it, but `TenantScopedManager.objects.all()` evaluated at class-definition time (no tenant context yet) bakes in an empty result that a later `.all()` cannot undo. Building the field per-instantiation (after the tenant context is set) avoids this.

**Seeding for manual testing:** `python manage.py seed_demo_balances` (after `seed_demo_pool`) creates the BRD Allocation Simulator example — `savings_tier_a` 60M, `term_tier_b` 25M, `institutional` 8M (total 93M) — as validated `DailyBalance`s plus a pre-built `balanced` `BalanceImportBatch`, dated on the pool's `effective_date`.

**Manually verified end-to-end**: a 3-record bulk import with a correct `control_total_expected` (93M) returned `status: "balanced"` with no errors; re-importing the same `value_date` + `participant_class` correctly skipped it as a duplicate, incrementing `exception_count` and listing the exact error, with `status: "exception"`; a fresh import with a *wrong* `control_total_expected` (90M vs an actual 93M) correctly returned `status: "exception"` despite all 3 records matching cleanly; a `shariah_board` user (neither `pool_manager` nor `finance_maker`) attempting to import correctly got `403`. Confirmed `AuditLog` entries with the full summary for every import.

## Exception Handling Framework

A generic, module-agnostic way for anomalies detected anywhere in the system (a balance import mismatch today; allocation variances, pool lifecycle issues, or an AI agent's own findings in the future) to surface as a single triage queue for the Risk & Compliance team, instead of each module inventing its own ad-hoc "flag" mechanism.

`apps.governance.ExceptionCase` (`TenantScopedModel`):

- `source_module` (`accounting` / `allocation` / `balance_import` / `pool_lifecycle` / `asset_assignment` / `other`) and `source_object_id` (a free-text ID of the record that triggered it, e.g. a `BalanceImportBatch` id) — together they trace an exception back to what raised it, without a hard FK (the source could be any model in any app).
- `pool` FK (nullable — not every exception is pool-scoped).
- `severity` (`low` / `medium` / `high` / `critical`), `title`, `description`.
- `status` (`open` → `investigating` / `resolved` / `dismissed`), `detected_by` (`system` / `ai_agent` / `manual`, default `system`).
- `assigned_to` FK (nullable) for routing to a specific Risk & Compliance user; `resolution_notes`, `resolved_by`, `resolved_at` — all set together when a case is closed out.

### `apps.core.exceptions_helper.create_exception_case()`

```python
create_exception_case(
    tenant, source_module, title, description,
    severity="medium", pool=None, source_object_id=None, detected_by="system",
)
```

The single entry point any other module should call when it detects an anomaly — it just creates the `ExceptionCase` row. It imports `apps.governance.models` lazily inside the function body rather than at module level, so calling modules (like `apps.pools`) don't take on a hard import-time dependency on the governance app.

### First integration: Balance Import (`apps/pools/views.py`)

Immediately after a `BalanceImportBatch` is saved with `status == "exception"` (a duplicate skip and/or a control-total mismatch — see [Balance Import & Validation](#balance-import--validation)), the view calls `create_exception_case()` with `source_module="balance_import"`, `source_object_id=<batch id>`, `severity="medium"`, and a title/description that includes the pool code, value date, and a short summary of what went wrong. This is the reference pattern future modules (and future AI agents) should follow: detect the anomaly you already know about, then make one call to raise it into the shared queue rather than storing it in a module-local field.

### Endpoints (`apps/governance`)

- **`GET /api/v1/governance/exceptions/?pool={pool_id}&status={status}&severity={severity}`** — list, filterable by any combination of the three params. Any authenticated user.
- **`GET /api/v1/governance/exceptions/{id}/`** — detail. Any authenticated user.
- **`POST /api/v1/governance/exceptions/`** — manual creation. `IsRiskCompliance` or `IsPoolManager` (via `HasAnyRole`).
- **`PATCH /api/v1/governance/exceptions/{id}/`** — update (primarily for setting `assigned_to`); `status`/`resolution_notes`/`resolved_by`/`resolved_at` are read-only here and can only change via `resolve`/`dismiss`. `IsRiskCompliance` only.
- **`POST /api/v1/governance/exceptions/{id}/resolve/`** — `resolution_notes` required (`400` otherwise); sets `status="resolved"`, `resolved_by=request.user`, `resolved_at=now()`. `IsRiskCompliance` only.
- **`POST /api/v1/governance/exceptions/{id}/dismiss/`** — same shape as `resolve/` but sets `status="dismissed"` — for exceptions triaged as false positives or not worth acting on. `IsRiskCompliance` only.

Every create/update/resolve/dismiss writes an `AuditLog` entry via `log_action()`.

**Manually verified end-to-end via real HTTP requests:** manually created an `ExceptionCase` as `pool_manager` (`201`); a `shariah_board` user got `403` attempting the same; resolving without `resolution_notes` correctly returned `400`, with it correctly set `status="resolved"` and populated `resolved_by`/`resolved_at`; a `pool_manager` got `403` attempting `resolve/` (creation and resolution are different permission levels); `PATCH .../{id}/` correctly updated `assigned_to`; `dismiss/` without notes returned `400`, with notes set `status="dismissed"`; filtering by `status=open`, `status=resolved`, and `severity=high` each returned exactly the matching case(s); triggered a real balance-import control-total mismatch and a real duplicate-record skip via `POST /api/v1/pools/balance-imports/` and confirmed in both cases an `ExceptionCase` was auto-created with `source_module="balance_import"`, the correct `source_object_id` (the batch's id), the correct `pool`, and a title/description matching the actual mismatch details.

### Frontend UI

The Exception Queue is a tab on the **Risk & Compliance** page (`/risk-compliance`, `src/pages/AssetRegistry.tsx`, alongside the existing Asset Registry tab), rendered by `src/pages/governance/ExceptionQueue.tsx`:

- Status and severity filter dropdowns re-fetch the list on change.
- Clicking a row expands a detail `Card` (description, detected-by, assigned-to) with role-gated action buttons — "Assign to me", "Resolve", "Dismiss" — shown only to `risk_compliance` users, on cases still `open`/`investigating`.
- Resolve/Dismiss open `src/pages/governance/ResolutionModal.tsx`, a small modal requiring `resolution_notes`; a `400` from the backend for a missing reason surfaces as the exact field-level message via `extractErrorMessage`'s `validation_error` handling.
- `src/api/governance.ts` holds `fetchExceptions`, `updateExceptionAssignee`, `resolveException`, `dismissException`, all matching `apps/governance/serializers.py` field-for-field (`ExceptionCase` type in `src/types/index.ts`).
- Manually verified: filtering works; a non-`risk_compliance` role attempting resolve/dismiss/assign gets the backend's real `403`, surfaced as a normal error message (the action buttons are also hidden from those roles in the UI, so this is defense in depth, not the only gate).

## Purification Ledger

**Why this exists (Islamic finance context):** a Shariah-compliant pool must not retain or distribute income that itself comes from a non-compliant source. The most common real-world case is incidental conventional interest — e.g. a bank sweeps idle pool cash overnight and it happens to sit in a conventional interbank account that earns interest, or a counterparty pays a late fee structured as interest rather than a Shariah-compliant penalty. That income is never "the pool's profit" in a Shariah sense: it cannot be shared with depositors or the mudarib, because doing so would make their income impure (contaminated by riba). Standard practice (per AAOIFI-style governance) is **purification**: the tainted amount is identified, ring-fenced, ratified by the Shariah Board, and then donated to charity — deliberately *not* returned to the bank, the depositors, or the pool, since none of them are entitled to benefit from it. `apps.governance.PurificationEntry` gives this its own auditable lifecycle, separate from ordinary profit distribution, so it can never accidentally get folded back into an `AllocationRun`.

`apps.governance.PurificationEntry` (`TenantScopedModel`):

- `pool` FK, `source_description` (e.g. *"Conventional bank profit on idle cash balance"*), `amount`, `identified_date`.
- `status`: `identified` → `approved_for_purification` → `distributed` — a strict one-way lifecycle; there is no path back and no way to skip a step through the API.
- `shariah_decision` FK to `products.ShariahDecision` (nullable) — links to a specific Shariah Board ruling when one exists for this case, rather than relying only on the generic `approve` action.
- `charity_recipient`, `distributed_date` — both `null` until `mark-distributed/` is called, at which point both become required.
- `approved_by` (set by `approve/`), `notes`.

### Endpoints (`apps/governance`)

- **`GET /api/v1/governance/purification-entries/?pool={pool_id}`** — list, filterable by pool. Any authenticated user.
- **`GET /api/v1/governance/purification-entries/{id}/`** — detail. Any authenticated user.
- **`POST /api/v1/governance/purification-entries/`** — create. `IsFinanceMaker` or `IsRiskCompliance` (via `HasAnyRole`) — the people positioned to first notice a non-compliant income item. Always created with `status="identified"`, regardless of what's in the request body.
- **`POST /api/v1/governance/purification-entries/{id}/approve/`** — `identified` → `approved_for_purification`; sets `approved_by=request.user`. `IsShariahBoard` only — this is the ruling step, and only the Shariah Board can make it. `400` if the entry isn't currently `identified`.
- **`POST /api/v1/governance/purification-entries/{id}/mark-distributed/`** — `approved_for_purification` → `distributed`; `charity_recipient` and `distributed_date` are both required in the request body (`400` listing whichever is missing). `IsFinanceChecker` only — confirming an actual charity payment went out is a finance-operations step, deliberately separate from the Shariah ruling. `400` if the entry isn't currently `approved_for_purification` (this is what enforces the lifecycle order — `mark-distributed/` cannot be called before `approve/`).

Every create/approve/mark-distributed writes an `AuditLog` entry via `log_action()`.

**Manually verified end-to-end via real HTTP requests:** created an entry as `finance_maker` (`201`, `status="identified"`); calling `mark-distributed/` immediately (skipping `approve/`) correctly returned `400` with the exact state-machine message, confirming the lifecycle can't be short-circuited; a `finance_maker` got `403` attempting `approve/`; `shariah_board` then approved successfully — `status` became `approved_for_purification` with `approved_by` set; a `shariah_board` user got `403` attempting `mark-distributed/` (approval and distribution are different roles); `finance_checker` calling `mark-distributed/` without `charity_recipient` correctly returned `400`; with both `charity_recipient` ("Edhi Foundation") and `distributed_date` supplied, the entry correctly became `status="distributed"`; a `shariah_board` user got `403` attempting `POST` (create); `risk_compliance` successfully created a second entry, confirming both allowed creator roles work; `GET .../?pool={id}` correctly listed both entries; confirmed via Django shell that all four transitions (`create` x2, `approve`, `mark_distributed`) wrote the expected `AuditLog` entries with accurate `changes`.

### Frontend UI

`src/pages/PurificationLedger.tsx`, mounted at the **Shariah Governance** nav item (`/shariah-governance`):

- A pool selector drives which entries load (`fetchPurificationEntries(poolId)`); the table shows source, amount, identified date, a status badge (`identified`=neutral, `approved_for_purification`=gold, `distributed`=emerald), and — once distributed — the charity recipient and distributed date read-only.
- "+ New Entry" opens `src/pages/governance/NewPurificationEntryModal.tsx` (source description, amount, identified date).
- Per-row actions are role-gated exactly like the backend permissions: "Approve" only renders for `shariah_board` on `identified` rows; "Mark Distributed" (opening `src/pages/governance/MarkDistributedModal.tsx`, requiring both `charity_recipient` and `distributed_date`) only renders for `finance_checker` on `approved_for_purification` rows.
- `src/api/governance.ts` also holds `fetchPurificationEntries`, `createPurificationEntry`, `approvePurificationEntry`, `markDistributed`, matching the serializer fields (`PurificationEntry` type in `src/types/index.ts`).
- Manually verified the full lifecycle end-to-end through these exact endpoints: create (`identified`) → approve as `shariah_board` (`approved_for_purification`) → mark distributed as `finance_checker` (`distributed`, with `charity_recipient`/`distributed_date` populated and correctly displayed read-only in the table).

## Shariah Governance Dashboard

A single read-only rollup of everything currently awaiting Shariah Board / Secretariat attention across the whole system — draft rulings, draft contract templates, draft weightage/PSR schedules, open exception cases, unresolved purification entries, and pools awaiting Shariah sign-off. Without this, the Shariah team would have to check six different screens one at a time to know what's actually pending; this collapses that into one call.

**`GET /api/v1/governance/shariah-dashboard/?pool={pool_id}`** (optional `pool` filter) — `IsShariahBoard` or `IsShariahSecretariat` only (via `HasAnyRole`); a plain function-based view (`@api_view`), not a `ModelViewSet`, since it doesn't map to one model — it's a rollup across seven.

Response shape:

```json
{
  "pending_shariah_decisions": [
    {"id": "...", "decision_code": "SD-2026-004", "title": "...", "status": "draft", "effective_date": "2026-10-01"}
  ],
  "pending_contract_templates": [
    {"id": "...", "name": "Mudarabah Unrestricted v2", "contract_type": "mudarabah_unrestricted", "status": "draft"}
  ],
  "pending_weightage_bands": [
    {"id": "...", "pool_code": "PL-2026-014-01", "participant_class": "vip_tier", "weightage": 1.30, "status": "draft"}
  ],
  "pending_psr_schedules": [
    {"id": "...", "pool_code": "PL-2026-014-01", "depositor_share": 70.00, "mudarib_share": 30.00, "status": "draft"}
  ],
  "open_exception_cases": [
    {"id": "...", "title": "Control total mismatch on 2026-09-20 for pool PL-2026-014-02", "severity": "medium", "status": "open", "pool_code": "PL-2026-014-02"}
  ],
  "pending_purification_entries": [
    {"id": "...", "source_description": "Conventional bank profit on idle cash balance", "amount": 1250.00, "status": "identified", "pool_code": "PL-2026-014-01"}
  ],
  "pending_pool_approvals": [
    {"id": "...", "name": "Retail Mudarabah Pool 2026 - Series 1", "code": "PL-2026-014-01", "status": "approved"}
  ],
  "summary_counts": {
    "total_pending_items": 7,
    "critical_exceptions": 1
  }
}
```

Notes on scope and filtering:

- `?pool=` filters every pool-scoped list (`pending_weightage_bands`, `pending_psr_schedules`, `open_exception_cases`, `pending_purification_entries`, `pending_pool_approvals`). `pending_shariah_decisions` and `pending_contract_templates` are **always tenant-wide** regardless of `?pool=` — neither `ShariahDecision` nor `ContractTemplate` has a pool FK (a `ContractTemplate` sits a level above `Pool`, attached via `Product`), so there's nothing to filter them by.
- `pending_pool_approvals` lists `Pool`s with `status="approved"` — i.e. pools that have cleared their own workflow and are now awaiting the Shariah sign-off that lets them move to `open` (see [Pool Lifecycle](#pool-lifecycle)).
- `open_exception_cases` includes both `open` and `investigating` statuses (not just `open`) — an exception under active investigation still needs Shariah attention if it's high/critical.
- `summary_counts.total_pending_items` is the sum of all seven list lengths; `critical_exceptions` counts only the `open_exception_cases` entries with `severity` in `{high, critical}`.
- Each list is built with exactly one `.values(...)` query (no serializers, no per-row related-object access), so the whole dashboard is seven queries total regardless of how many rows come back — no N+1s.
- Purely a read/view endpoint: no `log_action()` calls. Nothing is modified, and viewing an internal dashboard isn't compliance-sensitive the way exporting financial data (see [GL Export](#gl-export-appsaccountingexportspy)) is.

**Manually verified end-to-end via real HTTP requests:** called the dashboard with only 2 pre-existing draft `WeightageBand`s in the system — every other list correctly returned `[]` (not an error), `total_pending_items` correctly read `2`; a `pool_manager` got `403`; created one draft `ShariahDecision`, one draft `ContractTemplate`, one `critical`-severity open `ExceptionCase`, one `identified` `PurificationEntry`, and flipped a `Pool` to `status="approved"` — the dashboard then correctly listed all of them in their respective categories, `total_pending_items` became `7`, `critical_exceptions` became `1`; filtering by a *different* pool's id correctly returned empty pool-scoped lists while still showing the tenant-wide `ShariahDecision`/`ContractTemplate` entries.

## User Management APIs

Platform administration for creating and managing `User` accounts, layered on top of the existing `accounts` app rather than a new one — it's the same model, just a different set of endpoints/permissions for administering it.

Three serializers on `User`, each shaped for its endpoint:

- **`UserListSerializer`** — `id, email, full_name, role, tenant_code, mfa_enabled, is_active`. Used for both list and detail.
- **`UserCreateSerializer`** — `id, email, full_name, role, tenant` (input fields only — no password field; see below).
- **`UserUpdateSerializer`** — `full_name, role, tenant, is_active`, all optional (`PATCH`-friendly). Notably **excludes `email`** — email is the login identifier (`USERNAME_FIELD`) and changing it isn't supported through this endpoint.

### Endpoints (`apps/accounts`, `UserManagementViewSet`)

- **`GET /api/v1/auth/users/`** — list. A `platform_super_admin` sees users across **every** tenant; any other role sees only their own tenant's users. Any authenticated user can call this (not gated to admins), but the queryset scoping means non-admins never see other tenants' rosters.
- **`GET /api/v1/auth/users/{id}/`** — detail.
- **`POST /api/v1/auth/users/`** — create. `IsPlatformSuperAdmin` only. The request body never carries a password — one is generated server-side the same way `create_test_user` does (`secrets.choice` over a 14-character alphanumeric alphabet) and returned **once**, as `generated_password` in the `201` response body, alongside the created user's normal fields. It is never stored anywhere retrievable and is not returned again by any other endpoint.
- **`PATCH /api/v1/auth/users/{id}/`** — update `full_name`/`role`/`tenant`/`is_active`. `IsPlatformSuperAdmin` only.
- **No `DELETE`** — deliberately not registered on the ViewSet (only `ListModelMixin`/`RetrieveModelMixin`/`CreateModelMixin`/`UpdateModelMixin` are mixed in), so hitting `DELETE` on a user detail URL returns a plain `405 Method Not Allowed`. Removing access is always a **soft deactivation** via `PATCH {"is_active": false}` — this preserves the user as the `actor`/`created_by`/etc. on every historical `AuditLog` entry, `AllocationRun`, etc. they touched, rather than leaving dangling references or requiring `SET_NULL` everywhere.

Deactivation itself relies on Django's own auth machinery rather than custom logic: `ModelBackend.user_can_authenticate()` (called from `authenticate()` inside `LoginView`) already refuses `is_active=False` users, so a deactivated user's login attempt fails with the same generic `"Invalid email or password."` as a wrong password — no separate check was needed.

`log_action()` is called on every `create` and every `update`, with the update action name set to `"deactivate"` or `"activate"` (not the generic `"update"`) when `is_active` actually flips — makes the audit trail read naturally ("who deactivated user X and when") without needing to diff `changes` to figure out what happened.

**Manually verified end-to-end via real HTTP requests:** a `pool_manager` got `403` on `POST` and `403` on `PATCH`; a `platform_super_admin` created a user and received `generated_password` in the response; logged in as the new user with that exact password — succeeded; the same `platform_super_admin` then `PATCH`ed `is_active: false` — the same login attempt afterward correctly failed with `"Invalid email or password."`; `DELETE` on the user's detail URL correctly returned `405` (no delete route exists at all); confirmed via Django shell that both the `create` and the `deactivate` were recorded as distinct `AuditLog` actions with accurate `changes`.

## Multi-Tenancy

Every API request (except the exempt paths below) must include an `X-Tenant-Code` header identifying which tenant the request is for:

```
X-Tenant-Code: NOVU-DEMO
```

- `apps/core/middleware.py` (`TenantMiddleware`) reads this header, looks up the matching `Tenant` (must exist, `is_active=True`, `is_suspended=False`), and attaches it to `request.tenant` and to a request-scoped contextvar (`apps/core/context.py`).
- Missing header → `403 {"detail": "X-Tenant-Code header is required."}`
- Unknown or suspended tenant → `403 {"detail": "Unknown or suspended tenant."}`
- **Exempt paths** (no tenant header required): `/api/v1/health/`, `/api/v1/auth/` (login happens before the client knows its tenant context), and `/admin/`.
- Any model inheriting `apps.core.TenantScopedModel` is automatically filtered to the current tenant via `TenantScopedManager` — if no tenant context is set, it returns an empty queryset rather than leaking data across tenants.

**Manual testing:**

```bash
# No header -> 403
curl http://localhost:8000/api/v1/<some-endpoint>/

# With header -> scoped to that tenant
curl -H "X-Tenant-Code: NOVU-DEMO" http://localhost:8000/api/v1/<some-endpoint>/
```

Run `python manage.py test_tenant_isolation` to see an end-to-end demonstration: two tenants are created, each gets its own scoped record, and the command proves that switching the tenant context only ever surfaces that tenant's data.

**Frontend note:** once real authentication (BE-004) is in place, the frontend must send `X-Tenant-Code` on every API request after login (e.g. as a default header on the shared axios instance, populated from the logged-in user's tenant).

## Shariah Policy Copilot Integration

The Shariah Policy Copilot is a **separate FastAPI service** (own repo/folder: `shariah-policy-copilot/`, sibling to this project) that ingests Shariah policy documents (PDF/DOCX), answers natural-language questions with cited "Evidence Packs" via an LLM (Gemini/Anthropic/Ollama), and lets a Shariah reviewer approve/reject those packs. The Django backend never talks to its database or LLM directly — it proxies requests through a thin internal HTTP client (`apps/ai_agents/services/shariah_copilot_client.py`), so the Copilot service can be redeployed, scaled, or swapped independently of the pool management system.

### Architecture

```
Frontend (React) → Django REST API (/api/v1/ai/shariah-copilot/*)
                       │
                       │  apps.ai_agents.services.shariah_copilot_client
                       │  (requests, internal service key + forwarded user identity)
                       ▼
              Shariah Policy Copilot (FastAPI, separate process, default :8001)
                       │
                       ▼
              SQLite + vector store (documents, evidence packs) + LLM provider
```

Django is the **only trusted caller** of the Copilot service. Instead of the Copilot service re-authenticating end users, Django forwards the acting user's identity on every call via internal headers:

| Header | Value |
|---|---|
| `X-Internal-Key` | Shared secret (`SHARIAH_COPILOT_INTERNAL_KEY`) — proves the call came from Django, not a public client |
| `X-User-Id` | `request.user.id` |
| `X-User-Role` | Django role mapped to a Copilot role (see below) |
| `X-Tenant-Id` | `request.user.tenant.code` — **taken from the authenticated user's own tenant, never from the raw `X-Tenant-Code` request header**, so a spoofed header can't be used to read another tenant's documents |

Django role → Copilot role mapping (`ROLE_MAP` in `shariah_copilot_client.py`):

| Django role | Copilot role |
|---|---|
| `shariah_board` | `shariah_reviewer` (only role allowed to approve/reject evidence packs) |
| `shariah_secretariat` | `shariah_officer` |
| `product_manager` | `product` |
| `risk_compliance` | `compliance` |
| anything else | `shariah_researcher` (fallback) |

### Running both services locally

**1. Shariah Policy Copilot (FastAPI), from `shariah-policy-copilot/backend/`:**

```bash
python -m venv venv          # use Python 3.11 — numpy/chromadb have no prebuilt wheels for 3.14 yet
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
# set GEMINI_API_KEY (or switch LLM_PROVIDER to ollama) and INTERNAL_SERVICE_KEY in .env
python -m uvicorn app.main:app --port 8001 --reload
```

Verify: `curl http://localhost:8001/health` → `{"status":"ok"}`.

**2. Django backend, from `pool management system/backend/`:**

Add to `.env`:

```
SHARIAH_COPILOT_BASE_URL=http://localhost:8001
SHARIAH_COPILOT_INTERNAL_KEY=<same value as the Copilot service's INTERNAL_SERVICE_KEY>
```

Then run as usual (`python manage.py runserver`). If the Copilot service is down or unreachable, every `/api/v1/ai/shariah-copilot/*` endpoint returns a clean `503 {"error": {"code": "service_unavailable", ...}}` instead of a Django error page or crash.

### API endpoints

All under `/api/v1/ai/shariah-copilot/`, all requiring `Authorization: Bearer <JWT>` and `X-Tenant-Code` like every other endpoint in this API:

| Method | Path | Allowed roles | Notes |
|---|---|---|---|
| `POST` | `documents/upload/` | `shariah_board`, `shariah_secretariat` | multipart/form-data (`file` + metadata fields); audit-logged as `shariah_copilot_document_upload` |
| `GET` | `documents/` | `shariah_board`, `shariah_secretariat`, `product_manager`, `risk_compliance` | supports `?current_only=true` and the Copilot service's other list filters as query params |
| `POST` | `ask/` | same as list documents | body: `{"question": "...", "filters": {...}}` → returns an Evidence Pack. Not audit-logged here — the Copilot service keeps its own query audit trail |
| `POST` | `review/{evidence_pack_id}/` | `shariah_board` only | body: `{"approve": true/false}`; audit-logged as `shariah_copilot_review_decision` |

Errors from the Copilot service (4xx/5xx) are forwarded with their original status code and detail message, wrapped in this project's standard `{"error": {...}}` shape.

### Manually verified

- Shariah Secretariat can upload a document; it shows up via a direct call to the Copilot service.
- Pool Manager attempting an upload is blocked with `403` at the Django layer (never reaches the Copilot service).
- `ask/` returns an Evidence Pack (falls back to a "human review required" pack when no approved document matches).
- Shariah Board can call `review/`; Shariah Secretariat is blocked with `403` (maps to `shariah_officer`, not `shariah_reviewer`).
- Stopping the Copilot service produces a clean `503` from Django; Django itself keeps serving other requests.
- **Cross-tenant isolation**: a document uploaded by one tenant's Shariah Secretariat does not appear in another tenant's document list — `X-Tenant-Id` is always derived from the authenticated user's own tenant, not a client-supplied value.

### Verified end-to-end (real Evidence Pack + review + audit)

An earlier pass only exercised the fallback ("no evidence found") path. With a realistic ~250-word policy document (Late Payment Charges / Ta'widh) uploaded pre-approved and a real question asked against it, the full pipeline was confirmed working:

- `ask/` returned a genuine Evidence Pack with a real UUID `id`, `is_fallback: false`, grounded `research_summary`, and correct citations back to the uploaded document — retrieval, chunking, embedding, and the LLM call all work correctly.
- Shariah Board approving that pack's `evidence_pack_id` via `review/` returned `review_status: "approved"`.
- A second Evidence Pack, generated the same way, was rejected via `review/` with `approve: false` and returned `review_status: "rejected"`.
- `AuditLog` (Django) confirmed one `ShariahCopilotDocument`/`create` entry per upload and one `ShariahCopilotEvidencePack` entry each for the `approve` and `reject` decisions, each with the correct actor and tenant.

**Root cause of the earlier fallback-only result:** not a bug in the Copilot's retrieval/chunking/embedding pipeline (all confirmed working — chunks were present in ChromaDB and correctly retrieved), but a stale `GEMINI_MODEL` value pointing at a model that either 404'd (deprecated) or was a preview model returning persistent `503 UNAVAILABLE` under load. Fixed by switching to `gemini-3-flash-preview` in the Copilot service's `.env`. Also bumped the Django client's timeout for the `ask/` call specifically (`shariah_copilot_client.py`) to 90s, since a real LLM-backed answer can take 20-30s+, longer than the 30s used for the other near-instant Copilot calls.

### Frontend UI

The Shariah Policy Copilot is now fully accessible from the app's UI, not just the API — no separate tool needed to use it.

- **Route**: `/ai-analytics` (the existing "AI & Analytics" sidebar entry), rendering `src/pages/ShariahCopilot.tsx`.
- **Ask tab**: a question box that calls `ask/` and renders the returned Evidence Pack — research summary, cited evidence excerpts, open issues, a review-status badge, a "Conflict Detected" badge when `conflict_flagged`, a fallback warning when `is_fallback`, and the disclaimer text (always shown, never hidden). A Shariah Board user sees Approve/Reject buttons on any pack still `human_review_required`, calling `review/`. Because a real LLM-backed answer can take 20-30s+, the loading state shows an explicit "Researching... this may take up to 30 seconds" message rather than a bare spinner.
- **Documents tab**: a table of documents (name, type, version, status badge, product category) from `documents/`, plus an "Upload Document" button (Shariah Board / Secretariat only) opening `src/pages/shariah-copilot/UploadDocumentModal.tsx`.
- **API layer**: `src/api/shariahCopilot.ts` (`uploadDocument`, `fetchDocuments`, `askQuestion`, `submitReview`) and the corresponding types in `src/types/index.ts` (`ShariahDocument`, `EvidencePack` and its nested shapes), matching `apps/ai_agents/views.py` and the Copilot service's Pydantic schemas field-for-field.
- **503 handling**: a `503` from the Copilot-backed endpoints (service down) shows a specific "Shariah Copilot service is temporarily unavailable. Please try again in a moment." message instead of a generic error, since it's a distinct microservice from the rest of the API.
- Manually verified: upload → document appears in the list on refetch; a real question against an approved document returns a genuine (non-fallback) Evidence Pack; Shariah Board sees Approve/Reject, Pool Manager cannot even reach the Ask tab's results (blocked with `403` before any UI state renders); stopping the Copilot service produces the specific 503 message. `npx tsc -b` and `npm run build` both pass clean.

### AI Model Governance and Kill Switch

The Django backend maintains a global `AIModelRegistry` for the three internal AI features: `shariah_copilot`, `allocation_anomaly_detector`, and `reconciliation_copilot`. A data migration seeds all three as `active` with version `1.0`.

- Authenticated users can list models at `GET /api/v1/ai/models/`.
- Only Platform Super Admins can toggle a model with `PATCH /api/v1/ai/models/{id}/`, for example `{ "status": "disabled", "disabled_reason": "Maintenance" }`.
- Every toggle is written to `AuditLog` with the actor, previous/new status, and disable reason.
- A disabled Shariah Copilot returns `503 This AI feature is currently disabled.` before the external Copilot service is called. Disabled allocation anomaly and reconciliation checks silently return their existing no-op result so background posting/signing workflows remain non-blocking.

The `/ai-analytics` page exposes this through a **Model Governance** tab. The registry table and controls are visible to all authenticated users, but only Platform Super Admins see the Disable/Enable controls.

## Community Circles — Rotation & Payouts

`apps.circles` implements the `community_circle` operating model: a ROSCA (rotating savings and credit association) where a fixed group of members each contribute a fixed amount per cycle, and the pooled amount is paid out in full to one member per cycle, in an order fixed by a one-time random draw.

### Models

- **`CircleMember`** (`TenantScopedModel`) — `pool` FK, `member_name`, `member_reference` (unique per tenant), `payout_position` (nullable `IntegerField`, unique per pool when set — enforced by a partial `UniqueConstraint` with `condition=Q(payout_position__isnull=False)`, the same pattern `NAVSnapshot` uses for "only one published snapshot per pool/date"), `status` (`active` / `paid_out` / `withdrawn`), `joined_date`.
- **`Contribution`** (`TenantScopedModel`) — `member` FK (`related_name="contributions"`), `amount`, `contribution_date`, `cycle_number`, `status` (`pending` / `received`).
- **`Payout`** (`TenantScopedModel`) — `member` FK (`related_name="payouts"`), `pool` FK, `cycle_number`, `amount`, `payout_date`, `status` (`pending` / `disbursed`), `disbursed_by` (nullable `User` FK), `draw_seed` (nullable — the seed from the draw that assigned this member's `payout_position`, copied here for per-payout traceability).
- **`ArrearsRecord`** (`TenantScopedModel`) — `member` FK (`related_name="arrears_records"`), `cycle_number`, `expected_amount`, `status` (`overdue` / `hardship_granted` / `resolved`), `hardship_reason` (nullable `TextField` — the Shariah-compliant justification for a waiver, required when granting one), `reviewed_by` (nullable `User` FK), `reviewed_at` (nullable). Tracks a member falling behind on an expected contribution. Created manually for now via the `flag-arrears` action below; automatic detection from a cycle deadline is out of scope until deadlines are modeled on the pool/cycle.

### The draw (`apps/circles/rotation.py::run_draw(pool)`)

Assigns `payout_position` to every `active` `CircleMember` of a pool whose position is still `null`, in a uniformly random order, inside `transaction.atomic()` with `select_for_update()` so two concurrent draw requests for the same pool can't race and hand out duplicate positions.

**Why `secrets`, not `random`:** Python's `random` module is a Mersenne Twister PRNG — its internal state can, in principle, be reconstructed from a large enough sample of its output, and it is explicitly documented as unsuitable for security purposes. A rotation draw is exactly the kind of decision (who gets paid first) that a party with insight into the server's PRNG state, or with influence over the seed, could otherwise bias in their favor. `run_draw()` instead uses `secrets.SystemRandom().shuffle()`, which draws from the OS's cryptographically secure random source (`os.urandom`), so the resulting order cannot be predicted or steered by anyone, including the process itself.

A `secrets.token_hex(16)` seed is generated per draw and returned (and stored, on the audit log entry and copied onto each `Payout`) purely as a transparency/audit token — proof that a specific randomized run produced the order, not a re-playable seed for `random.seed()`-style reproduction (which `secrets` deliberately does not support, precisely because reproducibility would reintroduce the predictability risk above).

Positions are assigned starting after whatever positions already exist for the pool, so `run_draw()` can be called again later if new members join an existing circle without disturbing already-assigned members.

### API

- **`POST /api/v1/circles/circle-members/run-draw/{pool_id}/`** — `IsPoolManager` only. Calls `run_draw()`, logs the seed and full assignment list to `AuditLog`, and returns `{"seed": ..., "assignments": [{"member_id": ..., "position": ...}]}`.
- **`POST /api/v1/circles/circle-members/{id}/record-contribution/`** — `IsFinanceMaker` only. Body: `{"amount", "contribution_date", "cycle_number"}`. Creates a `Contribution` with `status="received"`.
- **`POST /api/v1/circles/circle-members/{id}/disburse-payout/`** — `IsFinanceChecker` only. Body: `{"cycle_number", "amount", "payout_date"}`. Enforces the payout sequence server-side, not just in the UI:
  1. **Turn order** — among the pool's `active` members with an assigned `payout_position`, whichever has the *smallest* position and hasn't been paid yet is "next in line". Disbursing to any other member is rejected with a `400` naming the actual expected position — a member can't be paid out of turn even if a Finance Checker tries to target them directly by id.
  2. **Full contribution for the cycle** — every currently-`active` member must have a `Contribution` with `status="received"` for the given `cycle_number` before *anyone* can be disbursed to for that cycle; otherwise the `400` names how many members are still pending.

  On success: creates a `Payout` with `status="disbursed"`, sets `member.status = "paid_out"`. No further disbursement can target that member again for a later cycle (a paid-out member drops out of the `active` "who's next" query).
- **`GET /api/v1/circles/contributions/?pool={pool_id}`** and **`GET /api/v1/circles/payouts/?pool={pool_id}`** — read-only, any authenticated (tenant-scoped) user. Added for the frontend's Rotation & Payouts tab, which needs every member's contribution/payout status for a given cycle in one screen rather than issuing per-member requests; `Contribution`/`Payout` rows are still only ever created via the two actions above.
- **`POST /api/v1/circles/circle-members/{id}/flag-arrears/`** — `IsRiskCompliance` only. Body: `{"cycle_number", "expected_amount"}`. Creates an `ArrearsRecord` with `status="overdue"`. Manual for now; a future cycle-deadline model would let this be raised automatically instead.
- **`POST /api/v1/circles/arrears-records/{id}/grant-hardship/`** — `IsShariahSecretariat` or `IsShariahBoard` only (`HasAnyRole(["shariah_secretariat", "shariah_board"])`), never `IsRiskCompliance` alone. Body: `{"hardship_reason"}` (required). Sets `status="hardship_granted"`, stamps `reviewed_by`/`reviewed_at`. Waiving a member's contribution obligation is a Shariah-governance decision — Risk & Compliance can flag a member as behind, but only Shariah oversight can excuse the shortfall, mirroring the same maker/checker-style separation already used for `record_contribution` (Finance Maker) vs `disburse_payout` (Finance Checker).
- **`GET /api/v1/circles/arrears-records/?pool={pool_id}`** (also accepts `?member={member_id}`) — read-only, any authenticated (tenant-scoped) user; rows are otherwise only ever created via `flag-arrears`.

Every draw, contribution, disbursement, arrears flag, and hardship grant is written to `AuditLog` via `log_action()`.

### Demo data

`python manage.py seed_demo_community_circle` creates a demo `community_circle` Product + Pool, 5 `CircleMember`s, runs a draw (verifying afterward that positions `1..5` were assigned with no gaps or duplicates), and records each member's cycle-1 `Contribution` as `received`.

**Verified via real HTTP requests** in `apps/circles/tests.py::CircleRotationApiTests`: created 5 members, ran the draw as Pool Manager and confirmed a `403` for a Finance Checker attempting the same, confirmed the returned `assignments` cover all 5 members with unique positions `1..5`; recorded cycle-1 contributions for 4 of the 5 members; confirmed disbursing to the *second*-turn member is rejected (`400`, wrong turn) even once role/permission (`IsFinanceChecker`) passes; confirmed disbursing to the correct first-turn member is *also* rejected until the missing member's contribution is recorded (`400`, incomplete cycle); confirmed a Finance Maker gets `403` on disburse; then recorded the missing contribution and confirmed disbursement succeeds (`201`, `status="disbursed"`, member `status` becomes `"paid_out"`). Separate tests confirm a draw against another tenant's pool is rejected (the pool lookup is tenant-scoped) and that `CircleMember` listing is tenant-isolated.

**Arrears/hardship verified via real HTTP requests** in `apps/circles/test_arrears.py::ArrearsRecordTests` (6 tests, all passing): a Risk Compliance user can `flag-arrears` (`201`, `status="overdue"`), a Pool Manager attempting the same gets `403`; `flag-arrears` without `cycle_number`/`expected_amount` returns `400` naming both missing fields; a Shariah Secretariat can `grant-hardship` on an overdue record (`200`, `status="hardship_granted"`, `reviewed_by`/`reviewed_at` stamped), while a Risk Compliance user attempting `grant-hardship` gets `403` even though they were the one who flagged it; `grant-hardship` without `hardship_reason` returns `400`; and `GET /circles/arrears-records/?pool=` correctly filters to the given pool.

### Frontend (`src/pages/CommunityCircles.tsx`)

The **Community Circles** sidebar item (previously a placeholder) now renders a pool selector scoped to `product_detail.operating_model === "community_circle"` pools (same filtering pattern as `InvestmentPools.tsx`), with three tabs:

- **Member Roster** — a table of `member_reference` / `member_name` / `payout_position` (`"Not drawn yet"` while `null`) / status `Badge` / `joined_date`. A Pool Manager sees a **+ New Member** button (only while at least one member still has no `payout_position` — once a draw has run, the roster is closed to new members joining mid-rotation) and a **Run Draw** button (only while at least one member is un-drawn), which opens a confirmation modal ("This action will randomly assign a payout order... This cannot be undone.") before calling the draw. The returned `seed` is shown afterward as a small copy-able `Draw seed: {seed}` line for audit transparency.
- **Rotation & Payouts** — a cycle-number input plus a table (one row per member) showing that cycle's contribution status (`received` / `pending` / `not recorded`, from `GET /circles/contributions/?pool=`) and payout status (amount + date once disbursed, from `GET /circles/payouts/?pool=`). Each row gets a **Record Contribution** button (Finance Maker, if not yet recorded for the selected cycle) and, only on the row of the smallest-`payout_position` still-`active` member, a **Disburse Payout** button (Finance Checker) that's disabled with a `"Waiting for all members to contribute this cycle"` tooltip until every active member's contribution for that cycle is `received` — mirroring the backend's own turn-order and completeness checks so a Finance Checker sees why a disbursement isn't available yet instead of only discovering it from a rejected request.
- The Rotation & Payouts table also has a default **Table View / Calendar View** toggle. Calendar View uses the same `fetchContributionsForPool()` response to build a plain seven-column month grid for the selected cycle's `contribution_date` values. Days show emerald **Paid**, gold **Due** for overdue pending contributions, or neutral **Pending**; selecting a day lists that day's contributions beside the grid. No calendar library or new backend endpoint is used.
- **Hardship & Arrears** — a table (one row per `ArrearsRecord` for the pool, from `GET /circles/arrears-records/?pool=`) showing `member_reference`, `cycle_number`, `expected_amount`, and a status `Badge` (gold `overdue`, emerald `hardship_granted`, navy `resolved`). A Risk Compliance user sees a **Flag as Overdue...** member picker that opens a modal to record `cycle_number` + `expected_amount` against the chosen member. A Shariah Secretariat or Shariah Board user sees a **Grant Hardship** button on any still-`overdue` row, opening a modal with a required `hardship_reason` textarea (the Shariah-compliant justification) before calling `grant-hardship`; a Risk Compliance user never sees that button, since the waiver decision is reserved for Shariah oversight.

Errors from all seven write actions (create member, run draw, record contribution, disburse payout, flag arrears, grant hardship) go through the same `extractErrorMessage()` used elsewhere in the frontend, so backend messages like *"It is not this member's turn..."* and *"Not all active members have contributed for cycle..."* surface verbatim instead of a generic failure message.

**Manually verified** (real HTTP, both roles) against a running dev server: created 5 members as Pool Manager, ran the draw and got a valid random assignment with unique positions `1..5`; recorded contributions for 4 of 5 members and confirmed disbursing to the first-turn member was rejected (`400`, incomplete cycle); recorded the last contribution, then confirmed disbursing to the *second*-turn member was rejected (`400`, wrong turn) and disbursing as a Finance Maker was rejected (`403`); disbursed successfully to the correct first-turn member (`201`, `status="disbursed"`). `npm run build` is clean.

## Auditor Evidence Portal

A read-only view over `AuditLog` (`apps.core.models.AuditLog`, already written to by every business action's `log_action()` call — previously only inspectable via the Django shell) for the Auditor role and Platform Super Admin, with no new model: `AuditLog` itself already carried everything needed (`tenant`, `actor`, `action`, `model_name`, `object_id`, `changes`, `reason`, `ip_address`, `created_at`).

### Read access across existing ViewSets

Every `list`/`retrieve` action surveyed across `apps/pools`, `apps/allocation`, `apps/accounting`, `apps/governance`, `apps/investments`, and `apps/circles` already falls through `get_permissions()` to a bare `IsAuthenticated()` (no role restriction) — so an Auditor, being an authenticated user, already had read access to `PoolViewSet`, `AssetViewSet`, `DailyBalanceViewSet`, `AllocationRunViewSet`, `JournalBatchViewSet`, `ExceptionCaseViewSet`, `PurificationEntryViewSet`, `RelatedPartyTransactionViewSet`, `CapitalAccountViewSet`, `NAVSnapshotViewSet`, `CircleMemberViewSet`, `ContributionViewSet`, `PayoutViewSet`, and `ArrearsRecordViewSet` before this change. None of those `get_permissions()` methods needed editing: every write action (`create`/`update`/`destroy`/custom mutating `@action`s) is already gated to a specific maker/checker/approval role and never falls back to the bare `IsAuthenticated()` branch, so Auditor — who is never named in any of those write-action checks — was already read-only everywhere, matching the "Auditor can look, never touch" requirement without any code change to those files.

### API (`apps/core`)

- **`GET /api/v1/core/audit-log/`** — `AuditLogViewSet` (`ListModelMixin` + `RetrieveModelMixin`, read-only). `IsAuditor` or `IsPlatformSuperAdmin` (`HasAnyRole(["auditor", "platform_super_admin"])`) only. `AuditLog` is deliberately not a `TenantScopedModel` (see its docstring — it must remain queryable/immutable independent of tenant lifecycle), so there's no `TenantScopedManager` auto-filtering; `get_queryset()` filters explicitly to `request.user.tenant` for every role except Platform Super Admin, who may instead pass `?tenant={tenant_id}` to inspect a specific tenant's log (same cross-tenant pattern as `UserManagementViewSet`). Query params: `model_name` (exact match), `date_from`/`date_to` (inclusive, filtered on `created_at__date`).
- **`GET /api/v1/core/audit-log/export/`** — plain `@api_view` function, `IsAuditor` only (not Super Admin — export is an auditor-specific evidence-gathering action). Same filters as above, reused via a shared `_filtered_audit_log_queryset()` helper so list and export can never drift apart. Streams a `text/csv` response (`Content-Disposition: attachment; filename="audit_log_export.csv"`) with columns `id, created_at, tenant, actor_email, action, model_name, object_id, changes, reason, ip_address` — the same `csv.writer` + `HttpResponse(content_type="text/csv")` pattern already used by `apps.accounting.views.gl_export`.
- Neither endpoint calls `log_action()` on itself — reading or exporting the audit log is deliberately not itself audited, to avoid a recursive/ever-growing trail of the audit log auditing its own reads. `log_action()` continues to fire only from the normal business actions that already call it.

**Verified via real HTTP requests** in `apps/core/test_audit_log.py::AuditLogApiTests` (9 tests, all passing): seeded 3 `AuditLog` entries (2 for one tenant, 1 for another) via `log_action()` directly; confirmed an Auditor can list and sees only their own tenant's 2 entries (tenant isolation, even though `AuditLog` has no `TenantScopedManager`); confirmed a Pool Manager gets `403` on both list and export; confirmed `?model_name=` filters correctly on both list and CSV export; confirmed a Platform Super Admin can cross into the *other* tenant's log via `?tenant=`; confirmed the exported CSV's `Content-Type` is `text/csv` and contains the expected rows (and omits the other tenant's row) with the actor's email present; and confirmed calling the export endpoint does not itself write a new `AuditLog` row (before/after count unchanged).

### Frontend (`src/pages/AuditorPortal.tsx`)

Wired to the previously-placeholder **Reports** sidebar item (`/reports` in `CUSTOM_ROUTES`, `App.tsx`). Follows the same "Access restricted" early-return pattern as `UserAdministration.tsx`: only `user?.role === "auditor"` or `"platform_super_admin"` see the real page; everyone else gets a `Card` with an explanatory message instead of the table.

- **Filters** — a `model_name` dropdown (a fixed list of the model names actually written by `log_action()` across the app, e.g. `Pool`, `CircleMember`, `AllocationRun`, `ExceptionCase`, ...), and `date_from`/`date_to` date pickers, applied via an **Apply Filters** button that re-calls `GET /core/audit-log/`.
- **Table** — `created_at` (localized), `actor` (email via the serializer's `actor_email`, or "System" when `actor` is null — e.g. entries written outside a request context), `action` `Badge`, `model_name`, `object_id`, and a **Changes** cell that renders "View changes" and expands in place to a `<pre>`-formatted JSON dump of the `changes` field on click (no separate modal — keeps the row's context visible while inspecting the diff).
- **Export CSV** — calls `downloadAuditLogCsv()` in `src/api/auditLog.ts`, which fetches `GET /core/audit-log/export/` with `responseType: "blob"` (so axios's request interceptor still attaches the `Authorization: Bearer` header — unlike a plain `<a href>` navigation, which would carry no auth and get rejected, since this app authenticates via a `localStorage` token rather than a cookie) and then triggers a client-side download via a synthetic anchor + `URL.createObjectURL`.

`npm run build` is clean.

## Liquidity Forecast

A pure, stateless projection helper — `apps.pools.liquidity.calculate_liquidity_forecast(pool, as_of_date, horizon_days=30)` — no new model. It's a **simple trend-based projection, not an ML-based forecast**; an ML-based forecast (accounting for seasonality, cyclicality, pool-type-specific patterns, etc.) is explicitly future scope, not attempted here.

### Calculation

1. **Trend** — pulls the pool's `DailyBalance` history up to `as_of_date`, sums `balance_amount` per `value_date` (a pool can have multiple `DailyBalance` rows per day, one per `participant_class`, so each day's "total" is the sum across classes), then averages the day-over-day delta of those daily totals over the last 30 days of history.
2. **Known upcoming outflows** over `[as_of_date, as_of_date + horizon_days]`, by `product.operating_model`:
   - `investment_pool` — sums `amount` of `Redemption` rows with `status="pending"` whose `transaction_date` falls in that window (`Redemption.capital_account.pool` is the join, since `Redemption` has no direct `pool` FK).
   - `community_circle` — sums `amount` of `Payout` rows with `status="pending"` whose `payout_date` falls in that window.
   - any other operating model (e.g. `bank_pool`) — no known-outflow source is modeled yet, so `known_outflows` is `0`.
3. `projected_balance = current_balance + (trend_per_day * horizon_days) - known_outflows`.

If the pool has fewer than 5 `DailyBalance` records as of `as_of_date`, the function returns `insufficient_data: True` with `current_balance`/`trend_per_day`/`known_outflows`/`projected_balance` all `null` — a normal response, not an error, since a forecast from 1-4 data points wouldn't be meaningful.

### API

- **`GET /api/v1/pools/pools/{pool_id}/liquidity-forecast/?horizon_days=30`** — `IsAuthenticated` only (falls through `PoolViewSet.get_permissions()`'s default branch, same as `retrieve`/`versions` — a read-only aggregation, not a role-gated action). Optional `as_of_date` (defaults to today) and `horizon_days` (defaults to `30`) query params. Returns the plain dict from `calculate_liquidity_forecast()` directly via `Response(...)`, following the same no-serializer convention as `AllocationRunViewSet.simulate()`.

**Verified via real HTTP requests** in `apps/pools/test_liquidity_forecast.py::LiquidityForecastApiTests` (3 tests, all passing): a pool with only 3 `DailyBalance` records returns `insufficient_data: True` with a `null` projection; a pool with 10 days of history rising by a fixed 100/day returns the exact expected `current_balance`, `trend_per_day`, and `projected_balance` (`current_balance + trend_per_day * 30`); an investment pool with a pending `Redemption` inside the 30-day horizon has its `amount` counted in `known_outflows`, while a pending redemption *outside* the horizon and an already-`processed` redemption are both correctly excluded.

### Frontend (`src/pages/pool-detail/LiquidityForecastSection.tsx`)

No new page — added as a third `Card` in the existing Pool Detail "Overview" tab grid (`src/pages/PoolDetail.tsx`), next to "Product" and "Pool Info", following the same self-contained `poolId`-prop section pattern as `PSRSection`/`WeightageBandsSection`/`AssignedAssetsSection`. Fetches via `fetchLiquidityForecast()` in `src/api/liquidity.ts`. Shows `current_balance`, `projected_balance` (30-day), a trend indicator (▲ emerald when `trend_per_day >= 0`, ▼ gold when negative), and `known_outflows`, with an explicit "Simple trend-based projection... Not an ML-based forecast" caption. When `insufficient_data` is `true`, shows "Not enough history yet." instead. `npm run build` is clean.

## Dispute & Request Center

`apps.governance.models.SupportRequest` (`TenantScopedModel`, no new app — governance already aggregates this class of case-management model alongside `ExceptionCase`/`PurificationEntry`/`RelatedPartyTransaction`) tracks disputes/service requests raised on behalf of an investor or circle member: statement corrections, payout inquiries, KYC issues, general complaints. `raised_by_name` is a plain name for now (not linked to a User), same as `CapitalAccount.investor_name` — linking to an `investor_member` User is future scope.

### Model

- `pool` — nullable FK (some requests aren't pool-specific, e.g. a general KYC issue).
- `request_type` — `statement_correction` / `payout_inquiry` / `kyc_issue` / `general_complaint` / `other`.
- `subject`, `description`, `raised_by_name`.
- `status` — `open` (default) / `in_progress` / `resolved` / `closed`.
- `priority` — `low` / `medium` (default) / `high`.
- `assigned_to` (nullable `User` FK), `resolution_notes` (nullable), `resolved_by` (nullable `User` FK), `resolved_at` (nullable).

### API (`apps/governance`)

- **`GET/POST /api/v1/governance/support-requests/`** — `list`/`retrieve`/`create` all just `IsAuthenticated`: **any** authenticated user can file a request (staff filing on behalf of a member who called or emailed in) or read the queue. `assigned_to`/`status`/`resolution_notes`/`resolved_by`/`resolved_at` are all read-only on the serializer — the only way they change is through the two actions below, so every state transition is captured by an explicit, named `log_action()` call rather than a generic `update`. Filters: `status`, `priority`, `pool`.
- **`POST /api/v1/governance/support-requests/{id}/assign/`** — `IsRiskCompliance` or `IsPoolManager` only (`HasAnyRole(["risk_compliance", "pool_manager"])`). Body: `{"assigned_to_user_id"}` (validated to exist in the caller's own tenant). Sets `assigned_to`; if the request was still `open`, also advances it to `in_progress` (filing something and then assigning it are the two events that take a request out of the "nobody's looked at this yet" state).
- **`POST /api/v1/governance/support-requests/{id}/resolve/`** — **design call**: rather than restricting this to a fixed role at the `get_permissions()` layer (which can't express "whoever it's currently assigned to," since that varies per-object), the permission check happens *inside* the action: allowed if `request.user` is the request's current `assigned_to`, **or** if they're Risk & Compliance / a Pool Manager (the same roles that can assign work in the first place, so they can always reassign or close out something that's stuck). Anyone else gets a `403` via `PermissionDenied`, with a message naming who *is* allowed. Body: `{"resolution_notes"}` (required). Sets `status="resolved"`, stamps `resolved_by`/`resolved_at`.

Every create/assign/resolve call is written to `AuditLog` via `log_action()`.

**Verified via real HTTP requests** in `apps/governance/test_support_requests.py::SupportRequestApiTests` (9 tests, all passing): a Finance Maker can file a request (`201`, `status="open"`); Risk Compliance can assign it to that same Finance Maker (`200`, `status` advances to `"in_progress"`); a non-Risk/non-Pool-Manager user attempting to assign gets `403`; the assignee can then resolve it (`200`, `status="resolved"`, `resolved_by` is the assignee); Risk Compliance can *also* resolve a request assigned to someone else, without being the assignee (`200`); a **different**, uninvolved user (not the assignee, not Risk/Pool-Manager) gets `403` attempting to resolve; resolving without `resolution_notes` returns `400`; `?status=`/`?priority=` filter correctly; and tenant isolation is confirmed (a user in a different tenant sees zero requests).

### Frontend

No new top-level nav item — added as a 5th tab ("Dispute & Request Center") on the existing **Risk & Compliance** page (`src/pages/AssetRegistry.tsx`), alongside Asset Registry / Exception Queue / Related-Party / Risk Dashboard, since Risk & Compliance already has the tab scaffold and role overlap (`risk_compliance`, `pool_manager`) this workflow needs.

- **`src/pages/governance/DisputeCenter.tsx`** — a filtered table (`status`, `priority`) of `SupportRequest`s: `subject`, `request_type` (human-readable label), `priority`/`status` `Badge`s, `pool` (or `—`), `assigned_to`. A **+ New Request** button opens a modal form (`request_type`, `raised_by_name`, `subject`, `description`, `priority`). Row click opens a detail **modal** (not a separate route, unlike `ExceptionCaseDetail` — this is a simpler single-panel case, no multi-stage investigation pipeline to visualize) showing the full description, resolution notes once resolved, and, while `open`/`in_progress`: an **Assign to Me** button (Risk Compliance/Pool Manager) and, once assigned-or-privileged, a **Resolve** button that expands an inline resolution-notes form.
- **`src/api/supportRequests.ts`** — `fetchSupportRequests`, `fetchSupportRequest`, `createSupportRequest`, `assignSupportRequest`, `resolveSupportRequest`.

`npm run build` is clean.

## Contribution Receipts

No new endpoint — the existing `GET /api/v1/circles/contributions/{id}/` (added `RetrieveModelMixin` to `ContributionViewSet`, which was previously list-only: `Contribution`s are still only ever *created* via `CircleMemberViewSet.record_contribution()`, this just lets a single one be *read* back) now backs a member-facing receipt page.

`ContributionSerializer` gained five flat, read-only fields sourced from the related `CircleMember`/`Pool` (minimal change over introducing a nested serializer, since the receipt page only needs a handful of display fields, not the full member/pool objects): `member_reference`, `member_name` (via `source="member.member_reference"` etc.), and `pool`/`pool_name`/`pool_code` (via `source="member.pool_id"` / `"member.pool.name"` / `"member.pool.code"` — a `Contribution` has no direct `pool` FK, only through `member`).

### Frontend (`src/pages/circles/ContributionReceipt.tsx`)

New route `community-circles/contributions/:id`. Follows the same print-friendly full-page layout as `StatementView.tsx` (`src/pages/StatementView.tsx` — Depositor Statements): a centered card, section headings, a stat-grid for the key figures, and a print button (`window.print()`, hidden itself via `@media print` so it doesn't appear on the printed page — `StatementView` has no such button, since a full print CSS page-break stylesheet is enough there, but a single-record receipt page needs one to trigger the browser's print dialog directly). Adds an explicit "Amanah Pool OS" branding line above the receipt title, which `StatementView` doesn't have. Shows member name, `member_reference`, pool name + code, amount, contribution date, cycle number, and a status `Badge`.

In `CommunityCircles.tsx`'s **Rotation & Payouts** tab (table view), any row whose Contribution status is `received` now shows a small **View Receipt** link next to the status badge, navigating to the new route.

**Verified via real HTTP requests** in `apps/circles/test_member_mobile_smoke.py::MemberMobileHomeDataTests::test_contribution_detail_for_receipt`: fetches a specific contribution by id and confirms `member_reference`, `member_name`, `pool_name`, `pool_code`, `amount`, `contribution_date`, `cycle_number`, and `status` are all present and correct on the response (16/16 `apps.circles` tests passing). `npm run build` is clean.

## Notes

- Never commit `.env` (backend or frontend) — both are already in `.gitignore`.
- `db.sqlite3` is ignored too, in case it's accidentally generated (this project uses PostgreSQL).
- `node_modules/` and `dist/` are ignored in the frontend.
