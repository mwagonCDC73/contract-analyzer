# Admin & Data Management Guide

## Quick Access

### Admin Panel (Recommended for Regular Use)
```bash
streamlit run admin_panel.py
```
**Features:**
- Visual interface for managing projects
- Archive or delete individual projects
- Bulk actions by status
- System statistics dashboard
- Search and filter capabilities

### Cleanup Script (For Complete Data Wipes)
```bash
python cleanup_database.py
```
**Features:**
- Delete all projects and contracts
- Delete all red flags
- Delete all storage files
- Full database reset
- Delete specific project by ID
- Delete projects by status

## Usage Scenarios

### Scenario 1: Clean Up Test Data
**Use Admin Panel** - Archive or delete test projects individually

### Scenario 2: Remove All Draft Projects
**Option A - Admin Panel:**
1. Run `streamlit run admin_panel.py`
2. Go to "Bulk Actions" tab
3. Select "draft" status
4. Click "Delete All Projects with This Status"

**Option B - Cleanup Script:**
1. Run `python cleanup_database.py`
2. Choose option `6` (Delete projects by status)
3. Enter status: `draft`
4. Confirm deletion

### Scenario 3: Complete Database Reset
**Use Cleanup Script:**
1. Run `python cleanup_database.py`
2. Choose option `4` (Full database reset)
3. Type "DELETE EVERYTHING" to confirm
4. All projects, contracts, red flags, and files will be deleted

### Scenario 4: Delete Specific Project
**Option A - Admin Panel:**
1. Run `streamlit run admin_panel.py`
2. Find the project in the list
3. Click "Delete" button
4. Confirm deletion

**Option B - Cleanup Script:**
1. Run `python cleanup_database.py`
2. Choose option `5` (Delete specific project)
3. Enter the project UUID
4. Confirm deletion

## Access Requirements

### Admin Panel
- Requires login
- User must have `admin` or `executive` role
- Safe for regular use

### Cleanup Script
- No authentication required (runs with service key)
- **DANGEROUS** - Can delete all data
- Use only when you need to completely reset the system

## What Gets Deleted

When you delete a project, the following data is removed:
1. **Project record** from `projects` table
2. **All contracts** associated with the project from `contracts` table
3. **All red flags** for those contracts from `red_flags` table
4. **All uploaded files** from Supabase Storage

## Archive vs Delete

### Archive (Recommended)
- Project is marked as `archived` status
- Data remains in database but hidden from normal views
- Can be restored by changing status back
- Safe and reversible

### Delete
- **Permanently removes** all data
- Cannot be undone
- Use only for test data or mistakes

## Safety Tips

1. **Always archive before deleting** - You can always delete later
2. **Use Admin Panel for production** - Visual confirmation of what you're deleting
3. **Use Cleanup Script for development** - Quick resets during testing
4. **Backup important data** - Export analysis results before bulk deletion
5. **Test on draft projects first** - Make sure you understand the process

## Project Statuses

- `draft` - Created but not submitted
- `submitted` - Waiting for executive review
- `under_review` - Being reviewed by executive
- `approved` - Approved by executive
- `rejected` - Rejected by executive
- `archived` - Archived (hidden from normal views)

## Database Schema Notes

If you need to add the `archived_at` timestamp column to track when projects were archived:

```sql
ALTER TABLE projects ADD COLUMN archived_at TIMESTAMP WITH TIME ZONE;
```

This is optional but helpful for auditing.
