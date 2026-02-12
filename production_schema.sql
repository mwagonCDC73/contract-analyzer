-- ============================================================
-- California Drywall Contract Analyzer — Production Schema
-- ============================================================
--
-- Run this ONCE in the Supabase SQL Editor to set up a fresh
-- production database. Creates all tables, indexes, functions,
-- RLS policies, storage buckets, and triggers.
--
-- Generated from:
--   api/schema.sql
--   api/migrations/002_rls_policies.sql
--   supabase/migrations/20260209000000_add_review_columns.sql
--   SCHEMA_MAPPING.md (production column names)
--
-- Tables:
--   1. user_profiles
--   2. projects
--   3. contracts
--   4. red_flags
--   5. analyses        (legacy — kept for compatibility)
--   6. api_usage_logs
--
-- ============================================================


-- ============================================================
-- 0. EXTENSIONS
-- ============================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";


-- ============================================================
-- 1. TABLES
-- ============================================================

-- user_profiles — one row per auth user, stores role & display name
CREATE TABLE IF NOT EXISTS user_profiles (
  id          UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  created_at  TIMESTAMPTZ DEFAULT NOW(),
  full_name   TEXT NOT NULL,
  email       TEXT,
  role        TEXT NOT NULL,          -- 'project_manager', 'executive', 'admin'
  active      BOOLEAN DEFAULT TRUE
);

-- projects — each project submitted by a PM for review
CREATE TABLE IF NOT EXISTS projects (
  id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  created_at          TIMESTAMPTZ DEFAULT NOW(),
  updated_at          TIMESTAMPTZ DEFAULT NOW(),
  project_name        TEXT NOT NULL,
  project_number      TEXT NOT NULL,
  state               TEXT NOT NULL DEFAULT 'CA',
  status              TEXT NOT NULL DEFAULT 'draft',  -- draft, submitted, processing, in_review, approved, rejected
  project_manager_id  UUID NOT NULL REFERENCES user_profiles(id) ON DELETE CASCADE,
  pm_notes            TEXT,
  submitted_at        TIMESTAMPTZ,
  reviewed_at         TIMESTAMPTZ,
  -- Executive claim workflow
  claimed_by_id       UUID REFERENCES user_profiles(id) ON DELETE SET NULL,
  claimed_at          TIMESTAMPTZ
);

-- contracts — PDF uploads linked to a project
CREATE TABLE IF NOT EXISTS contracts (
  id                    UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  created_at            TIMESTAMPTZ DEFAULT NOW(),
  updated_at            TIMESTAMPTZ DEFAULT NOW(),
  project_id            UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  contract_type         TEXT NOT NULL,           -- 'prime', 'subcontract'
  file_name             TEXT NOT NULL,
  file_path             TEXT NOT NULL,
  extracted_text        TEXT,
  analysis_status       TEXT NOT NULL DEFAULT 'pending',  -- pending, analyzing, completed, error
  analysis_date         TIMESTAMPTZ,
  analysis_results      JSONB,
  archived              BOOLEAN DEFAULT FALSE,
  -- Per-contract executive notes
  executive_notes       TEXT,
  executive_notes_by_id UUID REFERENCES user_profiles(id) ON DELETE SET NULL,
  executive_notes_at    TIMESTAMPTZ
);

-- red_flags — individual risk items found during AI analysis
CREATE TABLE IF NOT EXISTS red_flags (
  id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  created_at        TIMESTAMPTZ DEFAULT NOW(),
  contract_id       UUID NOT NULL REFERENCES contracts(id) ON DELETE CASCADE,
  category          TEXT NOT NULL,
  severity          TEXT NOT NULL,              -- 'critical', 'high', 'medium', 'low'
  issue_title       TEXT NOT NULL,
  details           TEXT NOT NULL,
  location          TEXT NOT NULL,
  recommendation    TEXT NOT NULL,
  review_status     TEXT DEFAULT 'needs_review',  -- needs_review, approved, rejected
  executive_comment TEXT,
  reviewed_by_id    UUID REFERENCES user_profiles(id) ON DELETE SET NULL,
  reviewed_at       TIMESTAMPTZ,
  disregarded       BOOLEAN DEFAULT FALSE
);

-- analyses — legacy table kept for compatibility with original schema
CREATE TABLE IF NOT EXISTS analyses (
  id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  created_at    TIMESTAMPTZ DEFAULT NOW(),
  updated_at    TIMESTAMPTZ DEFAULT NOW(),
  contract_id   UUID NOT NULL REFERENCES contracts(id) ON DELETE CASCADE,
  analysis_type TEXT NOT NULL,
  results       JSONB NOT NULL,
  status        TEXT NOT NULL DEFAULT 'pending'
);

-- api_usage_logs — tracks Claude API usage and estimated costs
CREATE TABLE IF NOT EXISTS api_usage_logs (
  id                 UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  created_at         TIMESTAMPTZ DEFAULT NOW(),
  contract_id        UUID REFERENCES contracts(id) ON DELETE SET NULL,
  user_id            UUID REFERENCES auth.users(id) ON DELETE SET NULL,
  analysis_type      TEXT NOT NULL DEFAULT 'general',
  model_used         TEXT NOT NULL,
  input_tokens       INTEGER NOT NULL DEFAULT 0,
  output_tokens      INTEGER NOT NULL DEFAULT 0,
  estimated_cost_usd NUMERIC(10, 6) NOT NULL DEFAULT 0
);


-- ============================================================
-- 2. INDEXES
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_projects_project_manager_id ON projects(project_manager_id);
CREATE INDEX IF NOT EXISTS idx_projects_status             ON projects(status);
CREATE INDEX IF NOT EXISTS idx_projects_state              ON projects(state);
CREATE INDEX IF NOT EXISTS idx_projects_claimed_by         ON projects(claimed_by_id);

CREATE INDEX IF NOT EXISTS idx_contracts_project_id  ON contracts(project_id);
CREATE INDEX IF NOT EXISTS idx_contracts_archived    ON contracts(archived);

CREATE INDEX IF NOT EXISTS idx_red_flags_contract_id ON red_flags(contract_id);

CREATE INDEX IF NOT EXISTS idx_analyses_contract_id  ON analyses(contract_id);

CREATE INDEX IF NOT EXISTS idx_api_usage_logs_contract_id ON api_usage_logs(contract_id);
CREATE INDEX IF NOT EXISTS idx_api_usage_logs_created_at  ON api_usage_logs(created_at);


-- ============================================================
-- 3. UPDATED_AT TRIGGER FUNCTION
-- ============================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_projects_updated_at
  BEFORE UPDATE ON projects
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_contracts_updated_at
  BEFORE UPDATE ON contracts
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_analyses_updated_at
  BEFORE UPDATE ON analyses
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();


-- ============================================================
-- 4. STORAGE BUCKET
-- ============================================================

INSERT INTO storage.buckets (id, name, public)
VALUES ('contracts', 'contracts', false)
ON CONFLICT (id) DO NOTHING;

-- Storage policies for contracts bucket
CREATE POLICY "Users can upload own contracts"
  ON storage.objects FOR INSERT
  WITH CHECK (
    bucket_id = 'contracts'
    AND auth.uid()::text = (storage.foldername(name))[1]
  );

CREATE POLICY "Users can view own contracts"
  ON storage.objects FOR SELECT
  USING (
    bucket_id = 'contracts'
    AND auth.uid()::text = (storage.foldername(name))[1]
  );

CREATE POLICY "Users can delete own contracts"
  ON storage.objects FOR DELETE
  USING (
    bucket_id = 'contracts'
    AND auth.uid()::text = (storage.foldername(name))[1]
  );


-- ============================================================
-- 5. HELPER FUNCTION FOR RLS
-- ============================================================
-- SECURITY DEFINER runs as the function owner (postgres), which
-- bypasses RLS. This avoids circular dependency when user_profiles
-- itself has RLS enabled.

CREATE OR REPLACE FUNCTION public.get_my_role()
RETURNS TEXT
LANGUAGE sql
SECURITY DEFINER
STABLE
SET search_path = public
AS $$
  SELECT role FROM user_profiles WHERE id = auth.uid()
$$;


-- ============================================================
-- 6. ENABLE ROW LEVEL SECURITY ON ALL TABLES
-- ============================================================

ALTER TABLE public.user_profiles  ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.projects       ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.contracts      ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.red_flags      ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.analyses       ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.api_usage_logs ENABLE ROW LEVEL SECURITY;


-- ============================================================
-- 7. RLS POLICIES — user_profiles
-- ============================================================

-- Any authenticated user can read their own profile
CREATE POLICY "user_profiles: select own"
  ON public.user_profiles FOR SELECT
  USING (auth.uid() = id);

-- Admin can read all profiles (for user management UI)
CREATE POLICY "user_profiles: admin select all"
  ON public.user_profiles FOR SELECT
  USING (public.get_my_role() = 'admin');

-- No INSERT/UPDATE/DELETE for end users — service_role handles all user management.


-- ============================================================
-- 8. RLS POLICIES — projects
-- ============================================================

-- PM: read own projects
CREATE POLICY "projects: pm select own"
  ON public.projects FOR SELECT
  USING (auth.uid() = project_manager_id);

-- PM: create projects (can only set themselves as PM)
CREATE POLICY "projects: pm insert"
  ON public.projects FOR INSERT
  WITH CHECK (auth.uid() = project_manager_id);

-- PM: update own projects
CREATE POLICY "projects: pm update own"
  ON public.projects FOR UPDATE
  USING (auth.uid() = project_manager_id)
  WITH CHECK (auth.uid() = project_manager_id);

-- PM: delete own projects
CREATE POLICY "projects: pm delete own"
  ON public.projects FOR DELETE
  USING (auth.uid() = project_manager_id);

-- Executive: read all non-draft projects (review queue)
CREATE POLICY "projects: executive select reviewable"
  ON public.projects FOR SELECT
  USING (
    public.get_my_role() = 'executive'
    AND status IN ('submitted', 'processing', 'in_review', 'approved', 'rejected')
  );

-- Executive: update projects they have claimed (status changes, notes)
-- NOTE: The initial claim (setting claimed_by_id from NULL) is done via
-- the backend service_role, which bypasses RLS.
CREATE POLICY "projects: executive update claimed"
  ON public.projects FOR UPDATE
  USING (
    public.get_my_role() = 'executive'
    AND claimed_by_id = auth.uid()
  )
  WITH CHECK (
    public.get_my_role() = 'executive'
  );

-- Admin: full access to all projects
CREATE POLICY "projects: admin all"
  ON public.projects FOR ALL
  USING (public.get_my_role() = 'admin')
  WITH CHECK (public.get_my_role() = 'admin');


-- ============================================================
-- 9. RLS POLICIES — contracts
-- ============================================================

-- PM: read contracts in own projects
CREATE POLICY "contracts: pm select own"
  ON public.contracts FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM public.projects
      WHERE projects.id = contracts.project_id
        AND projects.project_manager_id = auth.uid()
    )
  );

-- PM: insert contracts into own projects
CREATE POLICY "contracts: pm insert"
  ON public.contracts FOR INSERT
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM public.projects
      WHERE projects.id = contracts.project_id
        AND projects.project_manager_id = auth.uid()
    )
  );

-- PM: update contracts in own projects
CREATE POLICY "contracts: pm update own"
  ON public.contracts FOR UPDATE
  USING (
    EXISTS (
      SELECT 1 FROM public.projects
      WHERE projects.id = contracts.project_id
        AND projects.project_manager_id = auth.uid()
    )
  );

-- PM: delete contracts in own projects
CREATE POLICY "contracts: pm delete own"
  ON public.contracts FOR DELETE
  USING (
    EXISTS (
      SELECT 1 FROM public.projects
      WHERE projects.id = contracts.project_id
        AND projects.project_manager_id = auth.uid()
    )
  );

-- Executive: read contracts in reviewable projects
CREATE POLICY "contracts: executive select"
  ON public.contracts FOR SELECT
  USING (
    public.get_my_role() = 'executive'
    AND EXISTS (
      SELECT 1 FROM public.projects
      WHERE projects.id = contracts.project_id
        AND projects.status IN ('submitted', 'in_review', 'approved', 'rejected')
    )
  );

-- Executive: update contracts in projects they've claimed (executive notes)
CREATE POLICY "contracts: executive update claimed"
  ON public.contracts FOR UPDATE
  USING (
    public.get_my_role() = 'executive'
    AND EXISTS (
      SELECT 1 FROM public.projects
      WHERE projects.id = contracts.project_id
        AND projects.claimed_by_id = auth.uid()
    )
  )
  WITH CHECK (
    public.get_my_role() = 'executive'
  );

-- Admin: full access to all contracts
CREATE POLICY "contracts: admin all"
  ON public.contracts FOR ALL
  USING (public.get_my_role() = 'admin')
  WITH CHECK (public.get_my_role() = 'admin');


-- ============================================================
-- 10. RLS POLICIES — red_flags
-- ============================================================
-- Read access mirrors contracts (tied to contract → project access).
-- Only service_role can INSERT (created during AI analysis).

-- PM: read red flags for own contracts
CREATE POLICY "red_flags: pm select own"
  ON public.red_flags FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM public.contracts
      JOIN public.projects ON projects.id = contracts.project_id
      WHERE contracts.id = red_flags.contract_id
        AND projects.project_manager_id = auth.uid()
    )
  );

-- Executive: read red flags for reviewable contracts
CREATE POLICY "red_flags: executive select"
  ON public.red_flags FOR SELECT
  USING (
    public.get_my_role() = 'executive'
    AND EXISTS (
      SELECT 1 FROM public.contracts
      JOIN public.projects ON projects.id = contracts.project_id
      WHERE contracts.id = red_flags.contract_id
        AND projects.status IN ('submitted', 'in_review', 'approved', 'rejected')
    )
  );

-- Executive: update red flags on claimed projects (review_status, executive_comment)
CREATE POLICY "red_flags: executive update claimed"
  ON public.red_flags FOR UPDATE
  USING (
    public.get_my_role() = 'executive'
    AND EXISTS (
      SELECT 1 FROM public.contracts
      JOIN public.projects ON projects.id = contracts.project_id
      WHERE contracts.id = red_flags.contract_id
        AND projects.claimed_by_id = auth.uid()
    )
  );

-- Admin: full access to all red flags
CREATE POLICY "red_flags: admin all"
  ON public.red_flags FOR ALL
  USING (public.get_my_role() = 'admin')
  WITH CHECK (public.get_my_role() = 'admin');

-- No INSERT/DELETE for end users — service_role inserts during analysis.


-- ============================================================
-- 11. RLS POLICIES — analyses (legacy table)
-- ============================================================

-- PM: read analyses for own contracts
CREATE POLICY "analyses: pm select own"
  ON public.analyses FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM public.contracts
      JOIN public.projects ON projects.id = contracts.project_id
      WHERE contracts.id = analyses.contract_id
        AND projects.project_manager_id = auth.uid()
    )
  );

-- Executive: read analyses for reviewable contracts
CREATE POLICY "analyses: executive select"
  ON public.analyses FOR SELECT
  USING (
    public.get_my_role() = 'executive'
    AND EXISTS (
      SELECT 1 FROM public.contracts
      JOIN public.projects ON projects.id = contracts.project_id
      WHERE contracts.id = analyses.contract_id
        AND projects.status IN ('submitted', 'in_review', 'approved', 'rejected')
    )
  );

-- Admin: full access
CREATE POLICY "analyses: admin all"
  ON public.analyses FOR ALL
  USING (public.get_my_role() = 'admin')
  WITH CHECK (public.get_my_role() = 'admin');

-- No INSERT/UPDATE/DELETE for end users — service_role handles analysis.


-- ============================================================
-- 12. RLS POLICIES — api_usage_logs
-- ============================================================
-- Only admins can read cost/usage data. No end-user write access.
-- Service_role inserts logs and bypasses RLS automatically.

CREATE POLICY "api_usage_logs: admin select"
  ON public.api_usage_logs FOR SELECT
  USING (public.get_my_role() = 'admin');

-- No INSERT/UPDATE/DELETE policies — service_role handles all writes.


-- ============================================================
-- 13. VERIFICATION QUERIES
-- ============================================================
-- Run these after the script to confirm everything was created.

-- Verify all tables exist
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name IN (
    'user_profiles', 'projects', 'contracts',
    'red_flags', 'analyses', 'api_usage_logs'
  )
ORDER BY table_name;

-- Verify RLS is enabled on all tables
SELECT tablename, rowsecurity
FROM pg_tables
WHERE schemaname = 'public'
  AND tablename IN (
    'user_profiles', 'projects', 'contracts',
    'red_flags', 'analyses', 'api_usage_logs'
  )
ORDER BY tablename;

-- List all policies
SELECT tablename, policyname, permissive, roles, cmd
FROM pg_policies
WHERE schemaname = 'public'
  AND tablename IN (
    'user_profiles', 'projects', 'contracts',
    'red_flags', 'analyses', 'api_usage_logs'
  )
ORDER BY tablename, policyname;
