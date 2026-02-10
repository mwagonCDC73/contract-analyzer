from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from services.supabase import get_supabase_client
from models.schemas import LoginRequest, LoginResponse, SignupRequest, UserResponse, UserProfileResponse
import logging

logger = logging.getLogger(__name__)

router = APIRouter()
security = HTTPBearer()

@router.post("/login", response_model=LoginResponse)
async def login(credentials: LoginRequest):
    """
    Authenticate user and return access token
    """
    supabase = get_supabase_client()
    try:
        response = supabase.auth.sign_in_with_password({
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
    supabase = get_supabase_client()
    try:
        response = supabase.auth.sign_up({
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
    Logout user and invalidate token
    """
    supabase = get_supabase_client()
    try:
        supabase.auth.sign_out()
        return {"message": "Successfully logged out"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

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
    try:
        logger.info("[Profile] Validating user token...")
        token = credentials.credentials
        logger.info(f"[Profile] Token prefix: {token[:20]}...")

        # Get the authenticated user
        user = supabase.auth.get_user(token)
        logger.info(f"[Profile] User object: {user}")

        if not user or not user.user:
            logger.error("[Profile] No user found in token validation")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token"
            )

        auth_user_id = user.user.id
        logger.info(f"[Profile] Authenticated user ID: {auth_user_id}")

        # Fetch the user profile from user_profiles table
        logger.info(f"[Profile] Fetching profile for user ID: {auth_user_id}")
        profile = supabase.table("user_profiles").select("*").eq("id", auth_user_id).execute()
        logger.info(f"[Profile] Profile query result: {profile.data}")

        if not profile.data:
            logger.error(f"[Profile] No user profile found for user ID: {auth_user_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User profile not found for user ID: {auth_user_id}"
            )

        logger.info(f"[Profile] Successfully retrieved profile: {profile.data[0]}")
        return UserProfileResponse(**profile.data[0])
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Profile] Error getting user profile: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}"
        )
