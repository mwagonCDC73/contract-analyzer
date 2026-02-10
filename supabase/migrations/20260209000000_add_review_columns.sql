-- Add columns for executive claim workflow
ALTER TABLE projects ADD COLUMN IF NOT EXISTS claimed_by_id UUID;
ALTER TABLE projects ADD COLUMN IF NOT EXISTS claimed_at TIMESTAMPTZ;

-- Add columns for per-contract executive notes
ALTER TABLE contracts ADD COLUMN IF NOT EXISTS executive_notes TEXT;
ALTER TABLE contracts ADD COLUMN IF NOT EXISTS executive_notes_by_id UUID;
ALTER TABLE contracts ADD COLUMN IF NOT EXISTS executive_notes_at TIMESTAMPTZ;

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_projects_claimed_by ON projects(claimed_by_id);
CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status);

-- Migrate legacy status values
UPDATE projects SET status = 'in_review' WHERE status = 'under_review';
