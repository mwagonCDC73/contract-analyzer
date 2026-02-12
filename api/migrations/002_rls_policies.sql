-- ============================================================
-- RLS Migration: Role-Aware Policies for All Tables
-- ============================================================
--
-- Run this in the Supabase SQL Editor.
--
-- WHAT THIS DOES:
--   1. Creates a helper function get_my_role() to check the
--      current user's role from user_profiles
--   2. Drops all old single-user-only policies
--   3. Enables RLS on user_profiles and red_flags (previously missing)
--   4. Creates role-aware policies for all 6 tables:
--      user_profiles, projects, contracts, red_flags, analyses, api_usage_logs
--
-- NOTE: The backend uses the service_role key, which bypasses RLS
-- entirely. These policies protect against direct Supabase client
-- access (frontend anon key, Supabase Data API, etc.).
--
-- COLUMN NAMES: This migration uses 'project_manager_id' on the
-- projects table (matching the production schema). If your DB still
-- uses 'user_id', find-and-replace project_manager_id -> user_id.
-- ============================================================


-- ============================================================
-- STEP 1: Helper function to get current user's role
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
-- STEP 2: Drop all existing (outdated) policies
-- ============================================================

-- projects (old policies reference 'user_id', don't account for roles)
DROP POLICY IF EXISTS "Users can view own projects" ON public.projects;
DROP POLICY IF EXISTS "Users can insert own projects" ON public.projects;
DROP POLICY IF EXISTS "Users can update own projects" ON public.projects;
DROP POLICY IF EXISTS "Users can delete own projects" ON public.projects;

-- contracts
DROP POLICY IF EXISTS "Users can view own contracts" ON public.contracts;
DROP POLICY IF EXISTS "Users can insert own contracts" ON public.contracts;
DROP POLICY IF EXISTS "Users can update own contracts" ON public.contracts;
DROP POLICY IF EXISTS "Users can delete own contracts" ON public.contracts;

-- analyses
DROP POLICY IF EXISTS "Users can view own analyses" ON public.analyses;
DROP POLICY IF EXISTS "Users can insert own analyses" ON public.analyses;
DROP POLICY IF EXISTS "Users can update own analyses" ON public.analyses;
DROP POLICY IF EXISTS "Users can delete own analyses" ON public.analyses;

-- api_usage_logs (old policy was USING(true) — way too permissive)
DROP POLICY IF EXISTS "Service role full access on api_usage_logs" ON public.api_usage_logs;


-- ============================================================
-- STEP 3: Enable RLS on all tables (idempotent)
-- ============================================================

ALTER TABLE public.user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.projects      ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.contracts     ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.red_flags     ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.analyses      ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.api_usage_logs ENABLE ROW LEVEL SECURITY;


-- ============================================================
-- STEP 4: user_profiles policies
-- ============================================================

-- Any authenticated user can read their own profile
CREATE POLICY "user_profiles: select own"
  ON public.user_profiles FOR SELECT
  USING (auth.uid() = id);

-- Admin can read all profiles (for user management UI)
CREATE POLICY "user_profiles: admin select all"
  ON public.user_profiles FOR SELECT
  USING (public.get_my_role() = 'admin');

-- No INSERT/UPDATE/DELETE policies for end users.
-- The backend (service_role) handles all user management.


-- ============================================================
-- STEP 5: projects policies
-- ============================================================

-- PM: read own projects (project_manager_id = auth.uid())
-- This also lets any user who is the PM see their project, regardless of role label.
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
-- STEP 6: contracts policies
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

-- Executive: update contracts in projects they've claimed (executive notes, etc.)
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
-- STEP 7: red_flags policies
-- ============================================================
-- Read access mirrors contracts (tied to contract/project access).
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
-- STEP 8: analyses policies (legacy table)
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
-- STEP 9: api_usage_logs policies
-- ============================================================
-- Only admins can read cost/usage data. No end-user write access.
-- Service_role inserts logs and bypasses RLS automatically.

CREATE POLICY "api_usage_logs: admin select"
  ON public.api_usage_logs FOR SELECT
  USING (public.get_my_role() = 'admin');

-- No INSERT/UPDATE/DELETE policies — service_role handles all writes.


-- ============================================================
-- STEP 10: Verification queries
-- ============================================================

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
