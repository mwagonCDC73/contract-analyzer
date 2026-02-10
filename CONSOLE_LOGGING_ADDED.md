# Console Logging Added for Debugging

## What Was Added

Comprehensive console.log statements throughout the application to help with debugging.

---

## Files Updated

### 1. ✅ `web/app/dashboard/page.tsx`

**Logs Added:**
- `[Dashboard] Component mounted, checking auth...`
- `[Dashboard] Getting current user...`
- `[Dashboard] Current user:` + user object
- `[Dashboard] Loading projects...`
- `[Dashboard] Projects loaded:` + count
- `[Dashboard] Projects data:` + full array
- `[Dashboard] Opening New Project modal`
- `[Dashboard] Form submitted - Creating project`
- `[Dashboard] Project data:` + form data
- `[Dashboard] Calling projectsAPI.create...`
- `[Dashboard] Project created successfully:` + new project
- `[Dashboard] Error creating project:` + error details

### 2. ✅ `web/app/submit/page.tsx`

**Logs Added:**
- `[Submit] Component mounted, loading data...`
- `[Submit] Getting current user...`
- `[Submit] Current user:` + user object
- `[Submit] Loading projects list...`
- `[Submit] Projects loaded:` + count
- `[Submit] Form submitted`
- `[Submit] Form data:` + all form fields
- `[Submit] Validation failed:` + reason (if fails)
- `[Submit] Validation passed, starting submission...`
- `[Submit] Creating new project:` + project data
- `[Submit] Project created:` + new project
- `[Submit] Uploading prime contract:` + filename
- `[Submit] Prime contract uploaded:` + contract object
- `[Submit] Uploading subcontract:` + filename
- `[Submit] All contracts uploaded:` + count
- `[Submit] Starting analysis phase...`
- `[Submit] Analyzing contract:` + id and type
- `[Submit] Analysis complete for contract:` + id
- `[Submit] Analysis result:` + full result
- `[Submit] Fetching red flags for contract:` + id
- `[Submit] Red flags found:` + count
- `[Submit] All analyses complete`
- `[Submit] Total red flags:` + count
- `[Submit] Submission error:` + full error details

### 3. ✅ `web/lib/api.ts`

**Logs Added:**
- `[API] Request:` + method and URL
- `[API] Request data:` + request body
- `[API] Auth token added to request` or warning if no token
- `[API] Response:` + status and URL
- `[API] Response data:` + response body
- `[API] Response error:` + error message and details
- `[projectsAPI] Fetching projects list...`
- `[projectsAPI] Projects fetched:` + count
- `[projectsAPI] Creating project:` + project data
- `[projectsAPI] Project created:` + new project
- `[contractsAPI] Uploading contract:` + file details
- `[contractsAPI] Contract uploaded:` + contract object
- `[analysisAPI] Starting analysis:` + request
- `[analysisAPI] Analysis complete:` + result
- `[analysisAPI] Fetching red flags for contract:` + id
- `[analysisAPI] Red flags fetched:` + count

---

## How to Use

### Open Browser Console:

**Chrome/Edge:**
- Press F12
- Click "Console" tab

**Firefox:**
- Press F12
- Click "Console" tab

**Mac:**
- Press Cmd + Option + J

### What You'll See:

All logs are prefixed with tags:
- `[Dashboard]` - Dashboard page events
- `[Submit]` - Submit contract page events
- `[API]` - All API calls (requests and responses)
- `[projectsAPI]` - Project API calls
- `[contractsAPI]` - Contract upload API calls
- `[analysisAPI]` - Analysis API calls

### Example Console Output:

```
[Dashboard] Component mounted, checking auth...
[Dashboard] Getting current user...
[Dashboard] Current user: {id: "abc-123", email: "user@example.com", ...}
[Dashboard] Loading projects...
[projectsAPI] Fetching projects list...
[API] Request: GET /api/projects/
[API] Auth token added to request
[API] Response: 200 /api/projects/
[API] Response data: [{id: "proj-1", project_name: "Test", ...}]
[projectsAPI] Projects fetched: 3
[Dashboard] Projects loaded: 3 projects
[Dashboard] Projects data: [{...}, {...}, {...}]
[Dashboard] Loading complete
```

### When Creating a Project:

```
[Dashboard] Opening New Project modal
[Dashboard] Form submitted - Creating project
[Dashboard] Project data: {project_name: "Test", project_number: "2026-001", pm_notes: undefined}
[Dashboard] Calling projectsAPI.create...
[projectsAPI] Creating project: {project_name: "Test", ...}
[API] Request: POST /api/projects/
[API] Request data: {project_name: "Test", ...}
[API] Auth token added to request
[API] Response: 201 /api/projects/
[API] Response data: {id: "new-id", project_name: "Test", status: "draft", ...}
[projectsAPI] Project created: {id: "new-id", ...}
[Dashboard] Project created successfully: {id: "new-id", ...}
[Dashboard] Reloading projects list...
```

### When Submitting a Contract:

```
[Submit] Form submitted
[Submit] Form data: {
  createNewProject: false,
  selectedProjectId: "proj-123",
  primeContract: "contract.pdf",
  subcontract: null,
  notes: "Test submission"
}
[Submit] Validation passed, starting submission...
[Submit] Using project ID: proj-123
[Submit] Uploading prime contract: contract.pdf
[contractsAPI] Uploading contract: {
  fileName: "contract.pdf",
  fileSize: 123456,
  fileType: "application/pdf",
  projectId: "proj-123",
  contractType: "prime"
}
[API] Request: POST /api/contracts/upload/
[API] Auth token added to request
[API] Response: 201 /api/contracts/upload/
[contractsAPI] Contract uploaded: {id: "contract-id", ...}
[Submit] Prime contract uploaded: {id: "contract-id", ...}
[Submit] All contracts uploaded: 1
[Submit] Starting analysis phase...
[Submit] Analyzing contract: contract-id prime
[analysisAPI] Starting analysis: {contract_id: "contract-id", analysis_type: "risk"}
[API] Request: POST /api/analysis/analyze/
```

### When Errors Occur:

```
[Dashboard] Error creating project: Error: Request failed with status code 500
[Dashboard] Error details: {
  message: "Request failed with status code 500",
  response: {
    detail: "new row violates row-level security policy"
  },
  status: 500
}
[API] Response error: Request failed with status code 500
[API] Error status: 500
[API] Error data: {detail: "new row violates row-level security policy"}
```

---

## Debugging Checklist

When something doesn't work:

1. ✅ Open browser console (F12)
2. ✅ Look for logs with prefixes: `[Dashboard]`, `[Submit]`, `[API]`
3. ✅ Check for error logs (red text)
4. ✅ Follow the sequence of logs to see where it stops
5. ✅ Check if auth token is added (`[API] Auth token added to request`)
6. ✅ Check API response status codes
7. ✅ Look at response data to see what's returned

### Common Issues to Look For:

**No auth token:**
```
[API] No session token found!
```
**Fix:** User needs to log in again

**API errors:**
```
[API] Response error: Request failed with status code 500
[API] Error data: {detail: "..."}
```
**Fix:** Check backend logs and fix server-side issue

**Validation failures:**
```
[Submit] Validation failed: No contracts uploaded
```
**Fix:** User needs to upload at least one file

**Network issues:**
```
[API] No response received: {...}
```
**Fix:** Check backend is running on port 8000

---

## Filtering Console Logs

### Show Only Dashboard Logs:
```javascript
// In browser console, enter:
console.defaultLog = console.log.bind(console);
console.logs = [];
console.log = function(){
    console.logs.push(Array.from(arguments));
    if(arguments[0].includes('[Dashboard]')) {
        console.defaultLog.apply(console, arguments);
    }
}
```

### Show Only API Logs:
Filter by: `[API]` or `[projectsAPI]` or `[contractsAPI]` or `[analysisAPI]`

### Show Only Errors:
Click the "Errors" button in browser console (funnel/filter icon)

---

## Summary

✅ **Dashboard page:** 15+ log statements
✅ **Submit page:** 25+ log statements
✅ **API client:** 10+ log statements for requests/responses
✅ **All API functions:** Individual logging

Now you can see exactly what's happening at every step of the application!

Open F12 → Console tab and watch the logs as you interact with the app.
