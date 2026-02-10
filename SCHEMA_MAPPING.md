# Schema Mapping - FastAPI ↔ Existing Database

## Summary

The FastAPI backend has been updated to work with your existing Supabase database schema from the Streamlit app. **No database changes were made** - only the Python code was modified to match the existing tables.

---

## Database Schema

### user_profiles
- `id` (UUID) - Primary key
- `created_at` (timestamp)
- `full_name` (text)
- `email` (text)
- `role` (text) - Values: 'project_manager', 'executive'
- `active` (boolean)

### projects
- `id` (UUID) - Primary key
- `created_at` (timestamp)
- `project_name` (text) - **Note: not just "name"**
- `project_number` (text)
- `status` (text) - Values: 'draft', 'submitted', etc.
- `project_manager_id` (UUID) - FK to user_profiles.id
- `pm_notes` (text)
- `submitted_at` (timestamp, nullable)
- `reviewed_at` (timestamp, nullable)

### contracts
- `id` (UUID) - Primary key
- `created_at` (timestamp)
- `project_id` (UUID) - FK to projects.id
- `contract_type` (text) - Values: 'prime', 'subcontract'
- `file_name` (text) - **Note: not "filename"**
- `file_path` (text)
- `extracted_text` (text, nullable)
- `analysis_status` (text) - **Note: not just "status"**
- `analysis_date` (timestamp, nullable)
- `analysis_results` (jsonb, nullable)

### red_flags
- `id` (UUID) - Primary key
- `created_at` (timestamp)
- `contract_id` (UUID) - FK to contracts.id
- `category` (text)
- `severity` (text) - Values: 'critical', 'high', 'medium', 'low'
- `issue_title` (text)
- `details` (text)
- `location` (text)
- `recommendation` (text)
- `review_status` (text) - Values: 'needs_review', 'approved', 'rejected'
- `executive_comment` (text, nullable)
- `reviewed_by_id` (UUID, nullable) - FK to user_profiles.id
- `reviewed_at` (timestamp, nullable)
- `disregarded` (boolean)

---

## Key Differences from Original Design

### 1. No Separate Analyses Table
- **Original:** Separate `analyses` table
- **Actual:** Analysis results stored directly in `contracts` table
- **Fields:** `analysis_results`, `analysis_status`, `analysis_date`

### 2. User Management
- **Original:** Direct `auth.users` reference
- **Actual:** Separate `user_profiles` table with roles
- **Benefit:** Can distinguish between project_manager and executive roles

### 3. Project Manager Relationship
- **Original:** `user_id` column in projects
- **Actual:** `project_manager_id` column
- **Benefit:** More explicit relationship naming

### 4. Column Naming
- **Original:** `name`, `filename`, `status`
- **Actual:** `project_name`, `file_name`, `analysis_status`
- **Benefit:** More explicit and avoids ambiguity

---

## FastAPI Code Changes Made

### ✅ models/schemas.py
- Updated all Pydantic models to match existing column names
- Changed `User` to `UserProfile` with role field
- Changed `name` → `project_name`
- Changed `filename` → `file_name`
- Changed `status` → `analysis_status`
- Added `RedFlagResponse` and `RedFlagUpdate` models
- Removed separate `AnalysisResponse` (merged into `ContractResponse`)

### ✅ services/supabase.py
- Updated `get_current_user_id()` to look up `user_profiles` table
- Added `get_user_profile()` function
- Returns profile ID instead of auth user ID

### ✅ routers/projects.py
- Changed all queries from `user_id` → `project_manager_id`
- Updated create endpoint to set `project_manager_id`
- Updated create endpoint to set initial `status` = "draft"
- Added `/submit` endpoint to update status to "submitted"

### ✅ routers/contracts.py
- Changed `filename` → `file_name`
- Changed `status` → `analysis_status`
- Updated file path format to match existing pattern
- Changed project ownership checks to use `project_manager_id`

### ✅ routers/analysis.py
- **Major change:** Analysis results stored directly in contracts table
- POST `/analyze` now returns `ContractResponse` (not separate analysis)
- Updates `analysis_results`, `analysis_status`, `analysis_date` in contracts table
- Added GET `/contract/{id}/red-flags` endpoint for red flags

### ✅ web/types/index.ts
- Updated all TypeScript interfaces to match new schema
- Changed `name` → `project_name`
- Changed `filename` → `file_name`
- Changed `status` → `analysis_status`
- Added `UserProfile` interface
- Added `RedFlag` interface

---

## API Endpoints (Updated)

### Projects
```
GET    /api/projects/              - List user's projects (by project_manager_id)
POST   /api/projects/              - Create project (sets project_manager_id)
GET    /api/projects/{id}/         - Get project
PUT    /api/projects/{id}/         - Update project
DELETE /api/projects/{id}/         - Delete project
POST   /api/projects/{id}/submit/  - Submit project for review
```

### Contracts
```
POST   /api/contracts/upload/          - Upload PDF (extracts text)
GET    /api/contracts/project/{id}/    - List project contracts
GET    /api/contracts/{id}/            - Get contract
PUT    /api/contracts/{id}/            - Update contract
DELETE /api/contracts/{id}/            - Delete contract
```

### Analysis
```
POST   /api/analysis/analyze/                  - Analyze contract (updates contracts table)
GET    /api/analysis/contract/{id}/red-flags/  - Get contract red flags
```

---

## Testing with Existing Data

### 1. Create Test User Profile
Your database already has users:
```
pm.test@caldrywall.com (project_manager)
exec.test@californiadrywall.com (executive)
```

### 2. Create Auth User
Go to Supabase Authentication and create a user with the SAME email as one of your profiles.

### 3. Test API
```bash
# Login at http://localhost:3000
# Token will be automatically added to requests

# List projects (will return existing projects)
curl -H "Authorization: Bearer TOKEN" http://localhost:8000/api/projects/
```

### 4. Expected Results
- Should see existing projects from your Streamlit app
- Should see existing contracts
- Can create new projects/contracts that work with both apps

---

## Compatibility

✅ **Fully compatible** with your existing Streamlit app
✅ **No database migrations** needed
✅ **Existing data** works as-is
✅ **Both apps** can use the same database simultaneously

---

## Next Steps

1. ✅ FastAPI adapted to existing schema (Complete)
2. ✅ Frontend types updated (Complete)
3. 🔄 Test with existing Supabase user
4. 🔄 Verify projects list loads correctly
5. 🔄 Test contract upload
6. 🔄 Test Claude analysis

See `QUICK_TEST.md` for step-by-step testing instructions.
