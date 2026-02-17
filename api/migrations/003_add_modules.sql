-- ============================================================
-- Module System Migration
-- ============================================================
--
-- Run this in the Supabase SQL Editor.
--
-- WHAT THIS DOES:
--   1. Creates `modules` table to define available platform modules
--   2. Creates `user_module_access` table for per-user module grants
--   3. Seeds the contracts module (enabled) and labor module (disabled)
--   4. Auto-grants all existing users access to the contracts module
--   5. Adds indexes and RLS policies
--
-- NOTE: The backend uses the service_role key, which bypasses RLS
-- entirely. These policies protect against direct Supabase client
-- access (frontend anon key, Supabase Data API, etc.).
-- ============================================================


-- ============================================================
-- STEP 1: Create modules table
-- ============================================================

CREATE TABLE IF NOT EXISTS public.modules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    icon TEXT,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    display_order INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_modules_key ON public.modules(key);
CREATE INDEX IF NOT EXISTS idx_modules_enabled ON public.modules(enabled);


-- ============================================================
-- STEP 2: Create user_module_access table
-- ============================================================

CREATE TABLE IF NOT EXISTS public.user_module_access (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    module_id UUID NOT NULL REFERENCES public.modules(id) ON DELETE CASCADE,
    granted_by UUID REFERENCES auth.users(id),
    granted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(user_id, module_id)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_user_module_access_user_id ON public.user_module_access(user_id);
CREATE INDEX IF NOT EXISTS idx_user_module_access_module_id ON public.user_module_access(module_id);


-- ============================================================
-- STEP 3: Seed module data
-- ============================================================

INSERT INTO public.modules (key, name, description, icon, enabled, display_order)
VALUES
    ('contracts', 'Contract Analyzer', 'AI-powered contract review and risk analysis', 'FileText', TRUE, 1),
    ('labor', 'Labor Tracking', 'Weekly labor reports and workforce management', 'Users', FALSE, 2)
ON CONFLICT (key) DO NOTHING;


-- ============================================================
-- STEP 4: Auto-grant contracts module to all existing users
-- ============================================================

INSERT INTO public.user_module_access (user_id, module_id)
SELECT
    up.id,
    m.id
FROM public.user_profiles up
CROSS JOIN public.modules m
WHERE m.key = 'contracts'
ON CONFLICT (user_id, module_id) DO NOTHING;


-- ============================================================
-- STEP 5: RLS policies
-- ============================================================

-- Enable RLS
ALTER TABLE public.modules ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_module_access ENABLE ROW LEVEL SECURITY;

-- modules: all authenticated users can read enabled modules
CREATE POLICY "modules_select_authenticated"
    ON public.modules
    FOR SELECT
    TO authenticated
    USING (enabled = TRUE);

-- modules: admins can read all modules (including disabled)
CREATE POLICY "modules_select_admin"
    ON public.modules
    FOR SELECT
    TO authenticated
    USING (public.get_my_role() = 'admin');

-- modules: admins can update modules
CREATE POLICY "modules_update_admin"
    ON public.modules
    FOR UPDATE
    TO authenticated
    USING (public.get_my_role() = 'admin')
    WITH CHECK (public.get_my_role() = 'admin');

-- user_module_access: users can read their own access
CREATE POLICY "user_module_access_select_own"
    ON public.user_module_access
    FOR SELECT
    TO authenticated
    USING (user_id = auth.uid());

-- user_module_access: admins can read all access records
CREATE POLICY "user_module_access_select_admin"
    ON public.user_module_access
    FOR SELECT
    TO authenticated
    USING (public.get_my_role() = 'admin');

-- user_module_access: admins can insert access records
CREATE POLICY "user_module_access_insert_admin"
    ON public.user_module_access
    FOR INSERT
    TO authenticated
    WITH CHECK (public.get_my_role() = 'admin');

-- user_module_access: admins can delete access records
CREATE POLICY "user_module_access_delete_admin"
    ON public.user_module_access
    FOR DELETE
    TO authenticated
    USING (public.get_my_role() = 'admin');
