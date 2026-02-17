"""
Reusable FastAPI dependencies for role-based access control.
"""

import logging
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from services.supabase import get_current_user_id, get_user_profile, get_supabase_client

security = HTTPBearer()
logger = logging.getLogger(__name__)


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


def require_module_access(module_key: str):
    """
    Factory that returns a FastAPI dependency verifying the user has access
    to the given module.  Admins bypass the check.

    Not wired to any existing routes — infrastructure for future modules.
    """

    async def _check_module_access(
        credentials: HTTPAuthorizationCredentials = Depends(security),
    ) -> dict:
        info = await get_current_user_with_profile(credentials)
        user_id = info["user_id"]
        role = info["profile"].get("role")

        # Admins bypass module access checks
        if role == "admin":
            return info

        supabase = get_supabase_client()

        # Verify module exists and is enabled
        try:
            mod_resp = supabase.table("modules") \
                .select("id, enabled") \
                .eq("key", module_key) \
                .execute()
        except Exception as e:
            logger.warning(f"[ModuleAccess] Could not query modules table: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Module system unavailable",
            )

        if not mod_resp.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Module '{module_key}' not found",
            )

        module = mod_resp.data[0]
        if not module.get("enabled"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Module '{module_key}' is not currently enabled",
            )

        # Check user has access
        try:
            access_resp = supabase.table("user_module_access") \
                .select("id") \
                .eq("user_id", user_id) \
                .eq("module_id", module["id"]) \
                .execute()
        except Exception as e:
            logger.warning(f"[ModuleAccess] Could not query user_module_access: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Module access check failed",
            )

        if not access_resp.data:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"You do not have access to the '{module_key}' module",
            )

        return info

    return _check_module_access
