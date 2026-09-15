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

**Manual testing:** run `python manage.py create_test_user` to create a `pool_manager` user under the `NOVU-DEMO` tenant and print its email/password, then walk through the flow above with curl.

**Frontend integration:** the frontend (`frontend/src/pages/auth/`, `frontend/src/api/auth.tsx`, `frontend/src/api/axios.ts`) is now connected to this flow — see [Authentication (connected)](#authentication-connected) above.

## Data Model

Backend models are documented here as they are added.

- **`apps.core.BaseModel`** (abstract) — shared base for all models: UUID primary key, `created_at`, `updated_at`, and `is_active` (soft state only — no physical deletes, per BRD).
- **`apps.tenants.Tenant`** — a customer organization (`name`, unique `code`, unique `domain`, `data_residency`, `is_suspended`).
- **`apps.tenants.LegalEntity`** — a legal entity under a `Tenant` (`tenant` FK, `name`, `registration_number`, `jurisdiction`, `base_currency`, `timezone`).
- **`apps.core.TenantScopedModel`** (abstract, inherits `BaseModel`) — adds a required `tenant` FK and swaps in `TenantScopedManager` as the default manager. All future business models (Product, Pool, etc.) should inherit from this instead of `BaseModel` directly.
- **`apps.accounts.User`** (`AUTH_USER_MODEL`, extends `AbstractUser`) — email-based login (`USERNAME_FIELD = "email"`), `full_name`, `role` (one of the BRD roles: platform super admin, product manager, pool manager, finance maker/checker, Shariah secretariat/board, risk & compliance, auditor, investor/member), `tenant` FK (nullable, for platform super admins), `totp_secret`, `mfa_enabled`.

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
