from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from services.supabase import get_supabase_client
from models.schemas import LoginRequest, LoginResponse, SignupRequest, UserResponse, UserProfileResponse
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
async def logout(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Logout user — the frontend Supabase client handles session cleanup.
    We just acknowledge the request; no server-side session to clear.
    """
    return {"message": "Successfully logged out"}

@router.get("/me", response_model=UserResponse)
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
