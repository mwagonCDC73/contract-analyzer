# ✅ Contract Submit Page Complete

## What Was Built

The "Submit Contract" page at `/submit` is now fully functional with a complete workflow for uploading and analyzing contracts.

---

## Features Implemented

### 1. Project Selection
- **Select Existing Project** - Dropdown of user's projects
- **Create New Project** - Inline project creation with name and number
- Radio button toggle between modes
- Project list automatically loaded from API

### 2. File Uploads
- **Prime Contract PDF** (optional)
- **Subcontract PDF** (optional)
- At least one PDF required
- Drag-and-drop support
- File type validation (.pdf only)
- Display selected filename with remove option

### 3. Notes Field
- Optional notes field
- Saved to project (pm_notes)
- Supports multi-line text

### 4. Form Validation
- Must select/create project
- Must upload at least one contract
- New project requires name and number
- Clear error messages

### 5. Submission Workflow

**Step 1: Uploading**
- Shows loading spinner
- Progress messages:
  - "Creating project..." (if new)
  - "Uploading prime contract..."
  - "Uploading subcontract..."

**Step 2: Analyzing**
- Shows loading spinner
- "Analyzing with AI..."
- Displays which contract being analyzed

**Step 3: Results**
- Success message with count
- List of uploaded contracts with status
- Red flags display (if any found)
- Color-coded by severity:
  - 🔴 Critical - Red
  - 🟠 High - Orange
  - 🟡 Medium - Yellow
  - 🔵 Low - Blue

### 6. Red Flags Display
Each red flag shows:
- Issue title
- Severity badge
- Details
- Location
- Recommendation

### 7. Error Handling
- Network errors caught and displayed
- API errors shown with detail
- "Try Again" button to reset form

---

## API Integration

### Endpoints Called:

1. **GET /api/projects/**
   - Load existing projects on page load

2. **POST /api/projects/** (if creating new)
   - Create new project
   - Returns project with ID

3. **POST /api/contracts/upload/**
   - Upload prime contract (if provided)
   - Upload subcontract (if provided)
   - Includes: file, project_id, contract_type

4. **POST /api/analysis/analyze/**
   - Analyze each uploaded contract
   - Uses "risk" analysis type by default
   - Returns updated contract with analysis_results

5. **GET /api/analysis/contract/{id}/red-flags/**
   - Fetch red flags for each contract
   - Returns array of RedFlag objects

6. **PUT /api/projects/{id}** (optional)
   - Update project notes if adding to existing project

---

## User Flow

```
1. User visits /submit

2. Choose project:
   [•] Select existing → Dropdown list
   [ ] Create new → Name + Number fields

3. Upload contracts:
   □ Prime Contract (optional)
   □ Subcontract (optional)
   (At least one required)

4. Add notes (optional)

5. Click "Submit for Analysis"
   ↓
6. Loading: "Uploading Contracts..."
   ↓
7. Loading: "Analyzing with AI..."
   ↓
8. Results:
   ✅ Success message
   📄 Uploaded contracts list
   🚩 Red flags (if any)
   [Submit Another] [Go to Dashboard]
```

---

## File Structure

### Updated Files:

**`web/app/submit/page.tsx`**
- Complete form implementation
- Multi-step submission workflow
- Loading states
- Results display
- Error handling

**`web/lib/api.ts`**
- Updated `analysisAPI.analyze()` return type to `Contract`
- Updated `analysisAPI.listByContract()` to fetch red-flags endpoint
- Added `RedFlag` type import

---

## State Management

### Form State:
- `selectedProjectId` - Selected existing project
- `createNewProject` - Toggle for new project mode
- `newProjectName` - New project name
- `newProjectNumber` - New project number
- `primeContractFile` - Prime contract File object
- `subcontractFile` - Subcontract File object
- `notes` - Optional notes

### Submission State:
- `submissionStep` - Current step: form | uploading | analyzing | complete | error
- `uploadProgress` - Current progress message
- `uploadedContracts` - Array of uploaded Contract objects
- `analysisResults` - Array of analysis results
- `redFlags` - Array of RedFlag objects
- `error` - Error message if any

---

## UI Components

### Form View:
- Project selection (radio + dropdown/inputs)
- File upload dropzones (2)
- Notes textarea
- Cancel + Submit buttons
- Error message display

### Loading View:
- Spinner animation
- Progress message
- "This may take a few moments" helper text

### Success View:
- Green success banner
- Uploaded contracts card
- Red flags card (conditionally shown)
- "Submit Another" + "Go to Dashboard" buttons

### Error View:
- Red error banner
- Error details
- "Try Again" + "Go to Dashboard" buttons

---

## Validation Rules

1. **Project Required**
   - Must select existing OR create new
   - New project needs name + number

2. **At Least One Contract**
   - Either prime or subcontract (or both)
   - Only .pdf files accepted

3. **Notes Optional**
   - Can be left blank

---

## Example Usage

### Creating New Project:
```
[•] Create new project
    Project Name: Mission Valley Construction
    Project Number: 2026-150

Prime Contract: [Upload] mission-valley-prime.pdf
Subcontract: [Upload] mission-valley-sub.pdf

Notes: Initial contract review for Mission Valley project

[Submit for Analysis]
```

### Using Existing Project:
```
[•] Select existing project
    [v] Test Project - 2026 - 100 (#2026-100)

Prime Contract: [Upload] updated-contract.pdf

Notes: Updated contract with new terms

[Submit for Analysis]
```

---

## Testing Checklist

- [ ] Page loads without errors
- [ ] Projects dropdown populated
- [ ] Can toggle between existing/new project
- [ ] Can upload prime contract
- [ ] Can upload subcontract
- [ ] Validates at least one contract required
- [ ] Shows loading state during upload
- [ ] Shows loading state during analysis
- [ ] Displays success message on completion
- [ ] Shows uploaded contracts
- [ ] Displays red flags (if any)
- [ ] Can reset form and submit another
- [ ] Can navigate back to dashboard
- [ ] Error handling works correctly

---

## Next Steps

The submit page is complete and functional. You can now:

1. **Test the workflow**:
   - Upload test PDFs
   - Verify analysis runs
   - Check red flags display

2. **Customize**:
   - Adjust analysis type (currently hardcoded to "risk")
   - Modify red flag display
   - Add more validation

3. **Build Executive Review**:
   - `/review` page for executives
   - View submitted projects
   - Review and approve/reject

---

## Integration with Existing System

✅ **Uses existing database schema**
✅ **Works with existing projects**
✅ **Creates contracts in same format as Streamlit app**
✅ **Follows same analysis workflow**
✅ **Displays red flags from database**

---

## Status

🟢 **Complete and ready for testing!**

Visit http://localhost:3000/submit to try it out.
