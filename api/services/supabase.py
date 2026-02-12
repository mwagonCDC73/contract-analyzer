from supabase import create_client, Client
from fastapi import HTTPException, status
import logging
import os

logger = logging.getLogger(__name__)
_supabase_client: Client = None

def get_supabase_client() -> Client:
    """
    Get or create Supabase client instance using service_role key

    Uses service_role key to bypass RLS (Row Level Security) policies.
    This is appropriate for an internal tool where the backend handles
    all authorization logic.
    """
    global _supabase_client

    if _supabase_client is None:
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")

        if not supabase_url or not supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment variables")

        if supabase_key == "PASTE_YOUR_SERVICE_ROLE_KEY_HERE":
            raise ValueError(
                "Please update SUPABASE_KEY in .env with your service_role key. "
                "Get it from: Supabase Dashboard → Settings → API → service_role key"
            )

        logger.info(f"Creating Supabase client with URL: {supabase_url}")
        _supabase_client = create_client(supabase_url, supabase_key)

    return _supabase_client

async def get_current_user_id(token: str) -> str:
    """
    Extract user ID from authentication token and return user profile ID.

    Raises:
        401 — if the JWT token is invalid or expired
        404 — if no user_profiles row exists for the authenticated user
        500 — if the profile database query itself fails
    """
    supabase = get_supabase_client()

    # --- Step 1: Validate the JWT with Supabase Auth ---
    try:
        logger.info("Validating user token")
        user = supabase.auth.get_user(token)

        if not user or not user.user:
            logger.warning("Invalid token - no user found")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token"
            )

        auth_user_id = user.user.id
        logger.info(f"Token validated for auth user: {auth_user_id}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token validation failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token validation failed: {str(e)}"
        )

    # --- Step 2: Look up the user profile (separate from auth) ---
    try:
        profile = supabase.table("user_profiles").select("*").eq("id", auth_user_id).execute()

        if not profile.data:
            logger.warning(f"No user profile found for auth user: {auth_user_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User profile not found"
            )

        profile_id = profile.data[0]["id"]
        logger.info(f"User profile found: {profile_id}")
        return profile_id

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Profile lookup failed for user {auth_user_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Profile lookup failed: {str(e)}"
        )

async def get_user_profile(user_id: str):
    """
    Get user profile by ID
    """
    supabase = get_supabase_client()
    try:
        profile = supabase.table("user_profiles").select("*").eq("id", user_id).execute()
        if not profile.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User profile not found"
            )
        return profile.data[0]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching user profile: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch user profile: {str(e)}"
        )

def verify_user_access(user_id: str, resource_user_id: str) -> bool:
    """
    Verify that user has access to a resource
    """
    return user_id == resource_user_id
