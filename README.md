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

### Balance Import & Validation (new page, connected)

`src/pages/BalanceImport.tsx` (routed at `/daily-operations`, matching the BRD catalogue's own screen placement) is a standalone page (not part of `PoolDetail.tsx`, since it needs its own pool selector and a wide multi-row form) with:

- A **Pool** dropdown (`fetchPools()`), **Value Date**, optional **Control Total Expected**, and dynamic **participant_class / balance_amount** rows (**"+ Add Row"**, minimum 1 row, each row removable except the last).
- **Import** calls `importBalances()` and renders an **Import Summary** card: total/matched/exception counts, a status `Badge` (`balanced`→emerald, `exception`→gold), and — when present — the backend's `errors` array rendered as a red bulleted list (not folded into a single string), so multiple duplicate-skip messages are all visible at once.
- An **Import History** table below (`fetchImportHistory(poolId)`), re-fetched after every import.

**Manually verified via real HTTP requests:** a 3-record import with a matching control total returns `status: "balanced"` with an empty `errors` array; re-importing the same `value_date` + `participant_class` returns `status: "exception"` with the exact duplicate-skip message in `errors`, confirming the list-rendering path is exercised by a real backend response rather than just a hardcoded example; `fetchImportHistory()` returns entries matching the `BalanceImportBatch` interface exactly, in the shape the history table's columns read.

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

`simulated` → (Finance Maker submits) → `pending_approval` → (Finance Checker decides) → `signed` **or** `rejected`

- **`POST /api/v1/allocation/allocation-runs/{id}/submit-for-checking/`** — `IsFinanceMaker` only. Requires `status == "simulated"`.
- **`POST /api/v1/allocation/allocation-runs/{id}/approve/`** — `IsFinanceChecker` only. Requires `status == "pending_approval"`. Calls `apps.accounts.workflow.validate_maker_checker(maker_user=run.created_by, checker_user=request.user)` — if the same user created and is now approving the run, the request fails with `400`: *"Maker and checker cannot be the same user"*. On success: sets `checked_by`, `checked_at`, `status = "signed"`, and immediately calls `create_journal_from_allocation()` to post the ledger entries (below). The response includes the nested `journal_batch`.
- **`POST /api/v1/allocation/allocation-runs/{id}/reject/`** — `IsFinanceChecker` only. Requires `status == "pending_approval"` and a required `rejection_reason` in the body (`400` if missing). Sets `checked_by`, `checked_at`, `rejection_reason`, `status = "rejected"`. No journal is posted.

Every transition writes an `AuditLog` entry; for `reject`, the `rejection_reason` is also stored in the `AuditLog.reason` field, not just on the run.

### Double-entry journal posting (`apps/accounting`)

`apps.accounting.services.create_journal_from_allocation(allocation_run, posted_by)` builds one balanced `JournalBatch` (`status="posted"`, linked 1:1 to the `AllocationRun` via `OneToOneField`) with a `JournalEntry` per line:

- **Per participant class** (from the run's `AllocationLine`s): `DEBIT "Profit Expense - {class}"` and `CREDIT "Depositor Payable - {class}"`, both equal to `allocated_amount` — recognizing the pool's obligation to pay depositors.
- **For the mudarib's own share**: `DEBIT "Mudarib Income Suspense"` and `CREDIT "Mudarib Income"`, both equal to `mudarib_share` — a self-contained pair recognizing the bank's own income, independent of the depositor entries above.

`total_debit` and `total_credit` are each the sum of their respective entries and are therefore equal by construction; `JournalBatch.clean()` (called from `save()`) still re-validates `total_debit == total_credit` and raises *"Journal batch is not balanced."* if not — this exists as a safety net even though the service always produces a balanced batch.

### Journal Batches API

- **`GET /api/v1/accounting/journal-batches/?pool={pool_id}`** — read-only list (with nested `entries`), any authenticated user, filterable by pool.

**Manually verified end-to-end via real HTTP requests:** created a `simulated` run as a `finance_maker`, submitted it for checking (`pending_approval`); a `pool_manager` got `403` attempting `submit-for-checking` (wrong role); confirmed via Django shell that when the same physical user is set as both `created_by` and the approving `finance_checker`, `approve/` correctly returns `400` with the exact maker-checker message (there's no way to trigger this through the API alone in the current single-role-per-user model, since `finance_checker` can't create runs — this was flagged and confirmed with the user before testing this way); a genuinely different `finance_checker` then approved successfully — `status` became `signed`, `checked_by`/`checked_at` were set, and a `JournalBatch` was created with `total_debit == total_credit == 11,000,000.00` across exactly 8 entries (3 debit/credit pairs for the participant classes plus the mudarib pair); a second run was rejected with a required `rejection_reason`, confirmed recorded on both the run and its `AuditLog` entry, with no `JournalBatch` created; a `shariah_board` user got `403` on both `approve/` and `reject/`; confirmed via shell (equivalent to what the Django admin list page shows) that the posted `JournalBatch`'s `total_debit` and `total_credit` are equal.

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

## Notes

- Never commit `.env` (backend or frontend) — both are already in `.gitignore`.
- `db.sqlite3` is ignored too, in case it's accidentally generated (this project uses PostgreSQL).
- `node_modules/` and `dist/` are ignored in the frontend.
