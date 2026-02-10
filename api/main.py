from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import logging
import os

from routers import auth, projects, contracts, analysis, admin
from config.states import get_states_for_api

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Force .env file to override any existing environment variables
load_dotenv(override=True)

app = FastAPI(
    title="Contract Analysis API",
    description="API for contract submission and AI-powered analysis",
    version="1.0.0",
    redirect_slashes=False  # Disable automatic trailing slash redirects
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(projects.router, prefix="/api/projects", tags=["Projects"])
app.include_router(contracts.router, prefix="/api/contracts", tags=["Contracts"])
app.include_router(analysis.router, prefix="/api/analysis", tags=["Analysis"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])

@app.on_event("startup")
async def check_schema():
    """Check for required database columns and log warnings about pending migrations."""
    logger = logging.getLogger("startup")
    try:
        from services.supabase import get_supabase_client
        supabase = get_supabase_client()
        missing = []

        # Check projects columns
        for col in ["claimed_by_id", "claimed_at", "state"]:
            try:
                supabase.table("projects").select(col).limit(0).execute()
            except Exception as e:
                if "42703" in str(e):
                    missing.append(f"projects.{col}")

        # Check contracts columns
        for col in ["executive_notes", "executive_notes_by_id", "executive_notes_at"]:
            try:
                supabase.table("contracts").select(col).limit(0).execute()
            except Exception as e:
                if "42703" in str(e):
                    missing.append(f"contracts.{col}")

        if missing:
            logger.warning(
                "\n"
                "================================================================\n"
                "  DATABASE MIGRATION REQUIRED\n"
                "  Missing columns: %s\n"
                "  Run this SQL in Supabase SQL Editor:\n"
                "\n"
                "  ALTER TABLE projects ADD COLUMN IF NOT EXISTS claimed_by_id UUID;\n"
                "  ALTER TABLE projects ADD COLUMN IF NOT EXISTS claimed_at TIMESTAMPTZ;\n"
                "  ALTER TABLE projects ADD COLUMN IF NOT EXISTS state TEXT NOT NULL DEFAULT 'CA';\n"
                "  ALTER TABLE contracts ADD COLUMN IF NOT EXISTS executive_notes TEXT;\n"
                "  ALTER TABLE contracts ADD COLUMN IF NOT EXISTS executive_notes_by_id UUID;\n"
                "  ALTER TABLE contracts ADD COLUMN IF NOT EXISTS executive_notes_at TIMESTAMPTZ;\n"
                "  CREATE INDEX IF NOT EXISTS idx_projects_claimed_by ON projects(claimed_by_id);\n"
                "  CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status);\n"
                "  CREATE INDEX IF NOT EXISTS idx_projects_state ON projects(state);\n"
                "================================================================",
                ", ".join(missing),
            )
        else:
            logger.info("Database schema check passed — all required columns present.")
    except Exception as e:
        logger.error(f"Schema check failed: {e}")


@app.get("/api/config/states")
async def list_states():
    """Return supported states for the frontend."""
    return get_states_for_api()

@app.get("/")
async def root():
    return {"message": "Contract Analysis API", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
