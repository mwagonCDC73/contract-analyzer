# Contract Analyzer - Web Frontend

Next.js frontend for the Contract Analysis platform.

## Setup

1. **Install dependencies:**
   ```bash
   npm install
   ```

2. **Configure environment variables:**
   Create `.env.local` with:
   ```
   NEXT_PUBLIC_API_URL=http://localhost:8000
   NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
   NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_key
   ```

3. **Run the development server:**
   ```bash
   npm run dev
   ```

4. **Open the app:**
   Navigate to http://localhost:3000

## Project Structure

- `app/` - Next.js app router pages
  - `page.tsx` - Login page (public)
  - `dashboard/` - Main dashboard
  - `submit/` - Contract submission
  - `review/` - Executive review
- `components/` - React components
  - `Header.tsx` - Navigation header
- `lib/` - Utilities and API clients
  - `supabase.ts` - Supabase authentication
  - `api.ts` - FastAPI client functions
- `types/` - TypeScript type definitions

## Authentication Flow

1. User logs in on the homepage
2. Supabase authentication is handled
3. Session token is stored
4. Protected routes check for valid session
5. API requests include Bearer token automatically

## Pages

- **/** - Login page
- **/dashboard** - Project overview and management
- **/submit** - Contract upload and submission
- **/review** - Executive review queue

## Development

The app requires the FastAPI backend to be running on port 8000.

Start the API:
```bash
cd ../api
python main.py
```

Then start the frontend:
```bash
npm run dev
```
