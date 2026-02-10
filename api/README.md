# Contract Analysis API

FastAPI backend for contract submission and AI-powered analysis.

## Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment variables:**
   Copy `.env` and fill in your credentials:
   - `SUPABASE_URL`: Your Supabase project URL
   - `SUPABASE_KEY`: Your Supabase anon key
   - `ANTHROPIC_API_KEY`: Your Anthropic API key

3. **Run the development server:**
   ```bash
   python main.py
   ```

   Or with uvicorn directly:
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

## API Documentation

Once running, visit:
- Interactive API docs: http://localhost:8000/docs
- Alternative docs: http://localhost:8000/redoc

## Project Structure

- `main.py` - FastAPI application entry point
- `routers/` - API endpoint definitions
  - `auth.py` - Authentication endpoints
  - `projects.py` - Project CRUD endpoints
  - `contracts.py` - Contract submission endpoints
  - `analysis.py` - Claude analysis endpoints
- `services/` - Business logic and external integrations
  - `supabase.py` - Supabase client setup
  - `claude.py` - Claude API integration
  - `pdf.py` - PDF text extraction
- `models/` - Pydantic schemas for request/response
- `utils/` - Utility functions

## Authentication

All endpoints except `/` and `/health` require authentication via Bearer token in the Authorization header:

```
Authorization: Bearer <your_token>
```

## Main Endpoints

- `POST /api/auth/login` - User login
- `POST /api/auth/signup` - User registration
- `GET /api/projects` - List projects
- `POST /api/projects` - Create project
- `POST /api/contracts/upload` - Upload contract PDF
- `POST /api/analysis/analyze` - Analyze contract with Claude
