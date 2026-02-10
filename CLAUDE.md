# California Drywall Contract Analyzer

AI-powered contract review system for California Drywall Co., specializing in wall & ceiling subcontractor agreements.

## Architecture

### Frontend — Next.js (`web/`)

- Next.js 16 with React 19, TypeScript, Tailwind CSS 4
- App Router: `web/app/` contains routes for dashboard, submit, review, contract detail, and submissions
- Supabase JS client for auth and data access: `web/lib/`
- Shared components in `web/components/`
- Run: `cd web && npm run dev`

### Backend — FastAPI (`api/`)

- FastAPI app entry point: `api/main.py`
- Routers: `api/routers/` — auth, projects, contracts, analysis
- Services: `api/services/` — business logic layer
- Models: `api/models/` — data models
- Utils: `api/utils/` — shared utilities
- Database schema: `api/schema.sql`
- Run: `cd api && uvicorn main:app --reload`

### Database & Auth — Supabase

- PostgreSQL database hosted on Supabase
- Row-level security (RLS) for data access control
- Supabase Auth for user authentication
- Supabase Storage for contract PDF file uploads
- Client configured via `SUPABASE_URL` and `SUPABASE_KEY` env vars

### AI — Anthropic Claude API

- Used by the analysis router (`api/routers/analysis.py`) to analyze uploaded contracts
- Extracts risk items, categorizes by severity (critical/warning/informational)
- Analysis tailored for wall & ceiling specialty subcontractor context
- Configured via `ANTHROPIC_API_KEY` env var

## Key Dependencies

**Backend** (`api/requirements.txt`): fastapi, uvicorn, supabase, anthropic, pdfplumber, python-dotenv

**Frontend** (`web/package.json`): next, react, @supabase/supabase-js, axios, tailwindcss

## Environment Variables

Required in `.env` at project root:

- `SUPABASE_URL` — Supabase project URL
- `SUPABASE_KEY` — Supabase anon/public key
- `SUPABASE_SERVICE_ROLE_KEY` — Supabase service role key (for admin operations)
- `ANTHROPIC_API_KEY` — Anthropic API key for contract analysis
- `ALLOWED_ORIGINS` — CORS origins for the FastAPI backend (defaults to `*`)

## Archived

The original Streamlit app is archived in `archive/streamlit-legacy/` and is no longer active. It was the v1 prototype with multi-page Streamlit UI (Home, PM Submit, Executive Review, Admin Panel). The current system uses the Next.js + FastAPI stack described above.
