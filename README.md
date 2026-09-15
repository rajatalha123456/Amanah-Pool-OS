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

### Authentication (mock)

`/login` (SignIn) and `/verify-mfa` (VerifyMfa) implement the sign-in flow UI only, backed by a placeholder `isAuthenticated` flag (`src/api/auth.tsx`, persisted in `localStorage`). No real credentials or OTP codes are checked — any non-empty password and any 6-digit code are accepted. All other routes are wrapped in `ProtectedRoute` and redirect to `/login` when unauthenticated.

**This is mock auth only.** Once the real authentication API is available (BE-004), replace the mock `login()`/`logout()` calls in `SignIn.tsx` / `VerifyMfa.tsx` with real API calls and token handling.

## Data Model

Backend models are documented here as they are added.

- **`apps.core.BaseModel`** (abstract) — shared base for all models: UUID primary key, `created_at`, `updated_at`, and `is_active` (soft state only — no physical deletes, per BRD).
- **`apps.tenants.Tenant`** — a customer organization (`name`, unique `code`, unique `domain`, `data_residency`, `is_suspended`).
- **`apps.tenants.LegalEntity`** — a legal entity under a `Tenant` (`tenant` FK, `name`, `registration_number`, `jurisdiction`, `base_currency`, `timezone`).

## Notes

- Never commit `.env` (backend or frontend) — both are already in `.gitignore`.
- `db.sqlite3` is ignored too, in case it's accidentally generated (this project uses PostgreSQL).
- `node_modules/` and `dist/` are ignored in the frontend.
