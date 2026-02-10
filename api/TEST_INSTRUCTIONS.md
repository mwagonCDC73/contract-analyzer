# Testing the /api/auth/profile Endpoint

## Step 1: Restart the Backend

Make sure the backend server is restarted to load the new endpoint:

```bash
cd api
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Step 2: Test in Browser Console

1. Open your browser and log into the application
2. Open Developer Tools (F12) and go to the Console tab
3. Run these commands:

```javascript
// Get the current session
const session = await (await fetch('/_next/static/chunks/src_lib_supabase_ts.js')).text()

// Or test the API directly
const response = await fetch('http://localhost:8000/api/auth/profile', {
  headers: {
    'Authorization': 'Bearer YOUR_TOKEN_HERE'
  }
});
console.log(await response.json());
```

## Step 3: Check Browser Network Tab

1. Refresh the page after logging in
2. Open Developer Tools (F12) → Network tab
3. Look for the request to `/api/auth/profile`
4. Check:
   - Request Headers → Is `Authorization: Bearer ...` present?
   - Response → What is the status code and response body?

## Step 4: Check Backend Logs

Look at the terminal where the backend is running. You should see:
- `[Profile] Validating user token...`
- `[Profile] Token prefix: ...`
- `[Profile] Authenticated user ID: ...`
- `[Profile] Successfully retrieved profile: ...`

If you see errors, they will indicate exactly what's going wrong.

## Common Issues

### Issue 1: 401 Unauthorized
- **Cause**: Backend hasn't been restarted with the new endpoint
- **Fix**: Restart the backend server

### Issue 2: 404 Not Found (User profile not found)
- **Cause**: User exists in auth but not in user_profiles table
- **Fix**: Run `python create_exec_profiles.py` to create profiles

### Issue 3: Token not being sent
- **Cause**: Frontend session not established
- **Fix**: Log out and log back in
