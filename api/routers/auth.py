from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List
from services.supabase import get_supabase_client
from models.schemas import LoginRequest, LoginResponse, SignupRequest, UserResponse, UserProfileResponse, ModuleResponse
from supabase import create_client
import os
import logging

logger = logging.getLogger(__name__)

router = APIRouter()
security = HTTPBearer()


def _create_auth_client():
    """
    Create a throwaway Supabase client for login/signup/logout.

    These operations call sign_in_with_password / sign_up / sign_out which
    mutate the client's internal auth session.  Using the shared singleton
    would pollute its state and can cause get_user(jwt) to misbehave for
    concurrent requests from other users.
    """
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    return create_client(url, key)


@router.post("/login", response_model=LoginResponse)
@router.post("/login/", response_model=LoginResponse)
async def login(credentials: LoginRequest):
    """
    Authenticate user and return access token
    """
    auth_client = _create_auth_client()
    try:
        response = auth_client.auth.sign_in_with_password({
            "email": credentials.email,
            "password": credentials.password
        })
        return LoginResponse(
            access_token=response.session.access_token,
            user=UserResponse(**response.user.dict())
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )

@router.post("/signup", response_model=UserResponse)
@router.post("/signup/", response_model=UserResponse)
async def signup(user_data: SignupRequest):
    """
    Register a new user
    """
    auth_client = _create_auth_client()
    try:
        response = auth_client.auth.sign_up({
            "email": user_data.email,
            "password": user_data.password
        })
        return UserResponse(**response.user.dict())
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/logout")
@router.post("/logout/")
async def logout(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Logout user — the frontend Supabase client handles session cleanup.
    We just acknowledge the request; no server-side session to clear.
    """
    return {"message": "Successfully logged out"}

@router.get("/me", response_model=UserResponse)
@router.get("/me/", response_model=UserResponse)
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Get current authenticated user
    """
    supabase = get_supabase_client()
    try:
        user = supabase.auth.get_user(credentials.credentials)
        return UserResponse(**user.user.dict())
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )

@router.get("/profile", response_model=UserProfileResponse)
@router.get("/profile/", response_model=UserProfileResponse)
async def get_current_user_profile(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Get current authenticated user's profile with full name and role
    """
    supabase = get_supabase_client()
    token = credentials.credentials

    # --- Step 1: Validate JWT ---
    try:
        logger.info(f"[Profile] Validating token (prefix: {token[:20]}...)")
        user = supabase.auth.get_user(token)

        if not user or not user.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token"
            )

        auth_user_id = user.user.id
        logger.info(f"[Profile] Authenticated user ID: {auth_user_id}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Profile] Token validation failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token validation failed: {str(e)}"
        )

    # --- Step 2: Fetch profile (DB error ≠ auth error) ---
    try:
        profile = supabase.table("user_profiles").select("*").eq("id", auth_user_id).execute()

        if not profile.data:
            logger.error(f"[Profile] No profile for user: {auth_user_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User profile not found for user ID: {auth_user_id}"
            )

        logger.info(f"[Profile] Profile retrieved for: {auth_user_id}")
        return UserProfileResponse(**profile.data[0])
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Profile] Profile lookup failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Profile lookup failed: {str(e)}"
        )


@router.get("/my-modules", response_model=List[ModuleResponse])
@router.get("/my-modules/", response_model=List[ModuleResponse])
async def get_my_modules(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Get the list of modules the current user has access to.
    Admins get all enabled modules. Others get modules via user_module_access.
    """
    supabase = get_supabase_client()
    token = credentials.credentials

    # Validate JWT
    try:
        user = supabase.auth.get_user(token)
        if not user or not user.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token"
            )
        auth_user_id = user.user.id
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token validation failed: {str(e)}"
        )

    # Get user profile for role check
    try:
        profile_resp = supabase.table("user_profiles").select("role").eq("id", auth_user_id).execute()
        if not profile_resp.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User profile not found"
            )
        role = profile_resp.data[0].get("role")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[MyModules] Profile lookup failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to look up user profile"
        )

    # Fetch modules
    try:
        if role == "admin":
            # Admins see all enabled modules
            modules_resp = supabase.table("modules") \
                .select("*") \
                .eq("enabled", True) \
                .order("display_order") \
                .execute()
        else:
            # Non-admins: join through user_module_access
            # First get user's granted module IDs
            access_resp = supabase.table("user_module_access") \
                .select("module_id") \
                .eq("user_id", auth_user_id) \
                .execute()

            if not access_resp.data:
                return []

            module_ids = [a["module_id"] for a in access_resp.data]
            modules_resp = supabase.table("modules") \
                .select("*") \
                .eq("enabled", True) \
                .in_("id", module_ids) \
                .order("display_order") \
                .execute()

        return modules_resp.data or []

    except HTTPException:
        raise
    except Exception as e:
        # If modules table doesn't exist yet, return empty list gracefully
        if "42P01" in str(e):
            logger.warning("[MyModules] modules table not found — migration may not have been run")
            return []
        logger.error(f"[MyModules] Error fetching modules: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch modules: {str(e)}"
        )
