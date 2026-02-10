"""
Reusable FastAPI dependencies for role-based access control.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from services.supabase import get_current_user_id, get_user_profile

security = HTTPBearer()


async def get_current_user_with_profile(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """Return {'user_id': ..., 'profile': ...} for the authenticated user."""
    user_id = await get_current_user_id(credentials.credentials)
    profile = await get_user_profile(user_id)
    return {"user_id": user_id, "profile": profile}


async def require_pm_role(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """Allow project_manager and admin roles. Returns user info dict."""
    info = await get_current_user_with_profile(credentials)
    if info["profile"].get("role") not in ("project_manager", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Project manager or admin role required",
        )
    return info


async def require_executive_role(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """Allow executive and admin roles. Returns user info dict."""
    info = await get_current_user_with_profile(credentials)
    if info["profile"].get("role") not in ("executive", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Executive or admin role required",
        )
    return info
