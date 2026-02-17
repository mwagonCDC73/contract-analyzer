"""
Admin router for contract cleanup and management.

Requires migration — run this SQL in your Supabase SQL Editor:

    ALTER TABLE contracts ADD COLUMN IF NOT EXISTS archived BOOLEAN DEFAULT FALSE;
    CREATE INDEX IF NOT EXISTS idx_contracts_archived ON contracts(archived);
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime, timezone
import secrets
import string
import logging
from services.supabase import get_supabase_client, get_current_user_id, get_user_profile
from models.schemas import (
    AdminUserResponse, CreateUserRequest, UpdateUserRequest, DeleteUserRequest,
    ModuleResponse, UserWithModulesResponse,
    GrantModuleAccessRequest, RevokeModuleAccessRequest,
    BulkGrantModuleAccessRequest, BulkRevokeModuleAccessRequest,
    UpdateModuleRequest,
)

router = APIRouter()
security = HTTPBearer()
logger = logging.getLogger(__name__)


class BulkContractRequest(BaseModel):
    contract_ids: List[str]


class ResetConfirmRequest(BaseModel):
    confirmation: str  # Must be "DELETE ALL"


class AdminContractResponse(BaseModel):
    id: str
    created_at: str
    project_id: str
    contract_type: str
    file_name: str
    file_path: str
    analysis_status: str
    analysis_date: Optional[str] = None
    archived: bool = False
    project_name: Optional[str] = None
    project_number: Optional[str] = None
    submitter_name: Optional[str] = None
    state: Optional[str] = None


async def require_admin_role(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Verify the user has executive or admin role. Returns the user profile ID."""
    user_id = await get_current_user_id(credentials.credentials)
    profile = await get_user_profile(user_id)

    if profile.get("role") not in ("executive", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin or executive role required"
        )
    return user_id


async def require_strict_admin_role(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Verify the user has admin role only. Returns the user profile ID."""
    user_id = await get_current_user_id(credentials.credentials)
    profile = await get_user_profile(user_id)

    if profile.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required"
        )
    return user_id


def _enrich_contracts(supabase, contracts: list) -> list:
    """Add project and submitter info to a list of contract rows."""
    if not contracts:
        return []

    # Collect unique project IDs
    project_ids = list({c["project_id"] for c in contracts if c.get("project_id")})

    # Batch-fetch projects
    projects_map = {}
    if project_ids:
        projects_resp = supabase.table("projects") \
            .select("id, project_name, project_number, project_manager_id, state") \
            .in_("id", project_ids) \
            .execute()
        for p in projects_resp.data:
            projects_map[p["id"]] = p

    # Collect unique submitter (PM) IDs
    pm_ids = list({p["project_manager_id"] for p in projects_map.values() if p.get("project_manager_id")})

    # Batch-fetch user profiles
    profiles_map = {}
    if pm_ids:
        profiles_resp = supabase.table("user_profiles") \
            .select("id, full_name") \
            .in_("id", pm_ids) \
            .execute()
        for prof in profiles_resp.data:
            profiles_map[prof["id"]] = prof.get("full_name", "Unknown")

    # Merge into contracts
    result = []
    for c in contracts:
        proj = projects_map.get(c.get("project_id"), {})
        pm_id = proj.get("project_manager_id")
        c["project_name"] = proj.get("project_name")
        c["project_number"] = proj.get("project_number")
        c["submitter_name"] = profiles_map.get(pm_id) if pm_id else None
        c["state"] = proj.get("state", "CA")
        # Ensure archived has a default
        if c.get("archived") is None:
            c["archived"] = False
        result.append(c)

    return result


@router.get("/contracts", response_model=List[AdminContractResponse])
@router.get("/contracts/", response_model=List[AdminContractResponse])
async def list_admin_contracts(
    archived: bool = False,
    analysis_status: Optional[str] = None,
    search: Optional[str] = None,
    submitter: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    user_id: str = Depends(require_admin_role),
):
    """List contracts for admin cleanup. Supports filtering by archived state, status, date range, submitter, and search."""
    logger.info(f"[ADMIN] Listing contracts: archived={archived}, status={analysis_status}, search={search}")
    supabase = get_supabase_client()

    try:
        query = supabase.table("contracts") \
            .select("id, created_at, project_id, contract_type, file_name, file_path, analysis_status, analysis_date, archived") \
            .eq("archived", archived) \
            .order("created_at", desc=True)

        if analysis_status:
            query = query.eq("analysis_status", analysis_status)
        if date_from:
            query = query.gte("created_at", date_from)
        if date_to:
            query = query.lte("created_at", date_to + "T23:59:59Z")

        response = query.execute()
        contracts = response.data
        logger.info(f"[ADMIN] Found {len(contracts)} contracts")

        enriched = _enrich_contracts(supabase, contracts)

        # Client-side filters that require joined data
        if search:
            search_lower = search.lower()
            enriched = [
                c for c in enriched
                if search_lower in (c.get("project_name") or "").lower()
                or search_lower in (c.get("file_name") or "").lower()
                or search_lower in (c.get("project_number") or "").lower()
            ]
        if submitter:
            enriched = [c for c in enriched if c.get("submitter_name") == submitter]

        return enriched

    except Exception as e:
        logger.error(f"[ADMIN] Error listing contracts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list contracts: {str(e)}"
        )


@router.get("/submitters")
@router.get("/submitters/")
async def list_submitters(user_id: str = Depends(require_admin_role)):
    """List all users who have submitted contracts (for filter dropdown)."""
    supabase = get_supabase_client()
    try:
        response = supabase.table("user_profiles") \
            .select("id, full_name") \
            .eq("active", True) \
            .order("full_name") \
            .execute()
        return response.data
    except Exception as e:
        logger.error(f"[ADMIN] Error listing submitters: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/contracts/archive")
@router.post("/contracts/archive/")
async def archive_contracts(
    request: BulkContractRequest,
    user_id: str = Depends(require_admin_role),
):
    """Archive selected contracts (soft-delete: hides from normal views)."""
    logger.info(f"[ADMIN] Archiving {len(request.contract_ids)} contracts")
    supabase = get_supabase_client()

    try:
        response = supabase.table("contracts") \
            .update({"archived": True}) \
            .in_("id", request.contract_ids) \
            .execute()
        count = len(response.data) if response.data else 0
        logger.info(f"[ADMIN] Archived {count} contracts")
        return {"archived": count}

    except Exception as e:
        logger.error(f"[ADMIN] Error archiving contracts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/contracts/restore")
@router.post("/contracts/restore/")
async def restore_contracts(
    request: BulkContractRequest,
    user_id: str = Depends(require_admin_role),
):
    """Restore archived contracts back to active state."""
    logger.info(f"[ADMIN] Restoring {len(request.contract_ids)} contracts")
    supabase = get_supabase_client()

    try:
        response = supabase.table("contracts") \
            .update({"archived": False}) \
            .in_("id", request.contract_ids) \
            .execute()
        count = len(response.data) if response.data else 0
        logger.info(f"[ADMIN] Restored {count} contracts")
        return {"restored": count}

    except Exception as e:
        logger.error(f"[ADMIN] Error restoring contracts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/contracts/delete")
@router.post("/contracts/delete/")
async def delete_contracts(
    request: BulkContractRequest,
    user_id: str = Depends(require_admin_role),
):
    """Permanently delete selected contracts and their storage files."""
    logger.info(f"[ADMIN] Permanently deleting {len(request.contract_ids)} contracts")
    supabase = get_supabase_client()

    try:
        # Fetch file paths so we can clean up storage
        contracts_resp = supabase.table("contracts") \
            .select("id, file_path") \
            .in_("id", request.contract_ids) \
            .execute()

        if not contracts_resp.data:
            return {"deleted": 0}

        # Delete files from storage bucket
        file_paths = [c["file_path"] for c in contracts_resp.data if c.get("file_path")]
        if file_paths:
            try:
                supabase.storage.from_("contracts").remove(file_paths)
                logger.info(f"[ADMIN] Removed {len(file_paths)} files from storage")
            except Exception as storage_err:
                logger.warning(f"[ADMIN] Storage cleanup partial failure (continuing): {storage_err}")

        # Delete related red_flags first (foreign key constraint)
        try:
            supabase.table("red_flags") \
                .delete() \
                .in_("contract_id", request.contract_ids) \
                .execute()
        except Exception:
            pass  # Table may not have matching rows

        # Delete related analyses
        try:
            supabase.table("analyses") \
                .delete() \
                .in_("contract_id", request.contract_ids) \
                .execute()
        except Exception:
            pass

        # Delete the contract records
        supabase.table("contracts") \
            .delete() \
            .in_("id", request.contract_ids) \
            .execute()

        logger.info(f"[ADMIN] Deleted {len(contracts_resp.data)} contracts")
        return {"deleted": len(contracts_resp.data)}

    except Exception as e:
        logger.error(f"[ADMIN] Error deleting contracts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete contracts: {str(e)}"
        )


@router.post("/reset-test-data")
@router.post("/reset-test-data/")
async def reset_test_data(
    request: ResetConfirmRequest,
    user_id: str = Depends(require_admin_role),
):
    """Delete ALL contracts, analysis data, and storage files. Resets projects to draft. Keeps users/profiles."""
    if request.confirmation != "DELETE ALL":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Confirmation text must be exactly 'DELETE ALL'"
        )

    supabase = get_supabase_client()
    profile = await get_user_profile(user_id)
    user_name = profile.get("full_name", "Unknown")
    timestamp = datetime.now(timezone.utc).isoformat()

    logger.warning(f"[ADMIN] RESET TEST DATA initiated by {user_name} ({user_id}) at {timestamp}")

    results = {
        "red_flags_deleted": 0,
        "analyses_deleted": 0,
        "api_usage_logs_deleted": 0,
        "contracts_deleted": 0,
        "storage_files_removed": 0,
        "projects_reset": 0,
        "performed_by": user_name,
        "performed_at": timestamp,
    }

    try:
        # 1. Delete all red_flags
        try:
            resp = supabase.table("red_flags").select("id").execute()
            if resp.data:
                ids = [r["id"] for r in resp.data]
                # Delete in batches to avoid URL length limits
                for i in range(0, len(ids), 50):
                    batch = ids[i:i+50]
                    supabase.table("red_flags").delete().in_("id", batch).execute()
                results["red_flags_deleted"] = len(ids)
                logger.info(f"[ADMIN] Deleted {len(ids)} red_flags")
        except Exception as e:
            logger.warning(f"[ADMIN] Error deleting red_flags (continuing): {e}")

        # 2. Delete all api_usage_logs
        try:
            resp = supabase.table("api_usage_logs").select("id").execute()
            if resp.data:
                ids = [r["id"] for r in resp.data]
                for i in range(0, len(ids), 50):
                    batch = ids[i:i+50]
                    supabase.table("api_usage_logs").delete().in_("id", batch).execute()
                results["api_usage_logs_deleted"] = len(ids)
                logger.info(f"[ADMIN] Deleted {len(ids)} api_usage_logs")
        except Exception as e:
            logger.warning(f"[ADMIN] Error deleting api_usage_logs (continuing): {e}")

        # 3. Delete all analyses (legacy table)
        try:
            resp = supabase.table("analyses").select("id").execute()
            if resp.data:
                ids = [r["id"] for r in resp.data]
                for i in range(0, len(ids), 50):
                    batch = ids[i:i+50]
                    supabase.table("analyses").delete().in_("id", batch).execute()
                results["analyses_deleted"] = len(ids)
                logger.info(f"[ADMIN] Deleted {len(ids)} analyses")
        except Exception as e:
            logger.warning(f"[ADMIN] Error deleting analyses (continuing): {e}")

        # 4. Get all contract file paths, then delete from storage
        try:
            resp = supabase.table("contracts").select("id, file_path").execute()
            if resp.data:
                file_paths = [c["file_path"] for c in resp.data if c.get("file_path")]
                if file_paths:
                    # Storage remove in batches
                    for i in range(0, len(file_paths), 50):
                        batch = file_paths[i:i+50]
                        try:
                            supabase.storage.from_("contracts").remove(batch)
                        except Exception as storage_err:
                            logger.warning(f"[ADMIN] Storage batch removal error (continuing): {storage_err}")
                    results["storage_files_removed"] = len(file_paths)
                    logger.info(f"[ADMIN] Removed {len(file_paths)} files from storage")

                # Delete all contract records
                contract_ids = [c["id"] for c in resp.data]
                for i in range(0, len(contract_ids), 50):
                    batch = contract_ids[i:i+50]
                    supabase.table("contracts").delete().in_("id", batch).execute()
                results["contracts_deleted"] = len(contract_ids)
                logger.info(f"[ADMIN] Deleted {len(contract_ids)} contracts")
        except Exception as e:
            logger.warning(f"[ADMIN] Error deleting contracts (continuing): {e}")

        # 5. Reset all projects to draft status
        try:
            resp = supabase.table("projects").select("id").execute()
            if resp.data:
                project_ids = [p["id"] for p in resp.data]
                reset_fields = {
                    "status": "draft",
                    "submitted_at": None,
                    "reviewed_at": None,
                    "claimed_by_id": None,
                    "claimed_at": None,
                }
                for i in range(0, len(project_ids), 50):
                    batch = project_ids[i:i+50]
                    supabase.table("projects").update(reset_fields).in_("id", batch).execute()
                results["projects_reset"] = len(project_ids)
                logger.info(f"[ADMIN] Reset {len(project_ids)} projects to draft")
        except Exception as e:
            logger.warning(f"[ADMIN] Error resetting projects (continuing): {e}")

        logger.warning(f"[ADMIN] RESET TEST DATA complete: {results}")
        return results

    except Exception as e:
        logger.error(f"[ADMIN] Fatal error during reset: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Reset failed: {str(e)}"
        )


# ─── Cost Tracking Endpoints (admin-only) ─────────────────────────────────


class CostLogResponse(BaseModel):
    id: str
    contract_id: Optional[str] = None
    user_id: Optional[str] = None
    analysis_type: str
    model_used: str
    input_tokens: int
    output_tokens: int
    estimated_cost_usd: float
    created_at: str
    # Enriched fields
    file_name: Optional[str] = None
    project_name: Optional[str] = None


@router.get("/costs/summary")
@router.get("/costs/summary/")
async def get_cost_summary(user_id: str = Depends(require_strict_admin_role)):
    """Get aggregated cost summary for the admin dashboard."""
    supabase = get_supabase_client()

    try:
        response = supabase.table("api_usage_logs") \
            .select("*") \
            .order("created_at", desc=True) \
            .execute()

        logs = response.data or []

        total_cost = 0.0
        month_cost = 0.0
        total_input_tokens = 0
        total_output_tokens = 0
        model_breakdown: dict = {}

        now = datetime.now(timezone.utc)
        current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        for log in logs:
            cost = float(log.get("estimated_cost_usd", 0))
            inp = log.get("input_tokens", 0)
            out = log.get("output_tokens", 0)
            model = log.get("model_used", "unknown")

            total_cost += cost
            total_input_tokens += inp
            total_output_tokens += out

            # Check if this month
            created = log.get("created_at", "")
            if created >= current_month_start.isoformat():
                month_cost += cost

            # Model breakdown
            if model not in model_breakdown:
                model_breakdown[model] = {"count": 0, "cost": 0.0, "input_tokens": 0, "output_tokens": 0}
            model_breakdown[model]["count"] += 1
            model_breakdown[model]["cost"] += cost
            model_breakdown[model]["input_tokens"] += inp
            model_breakdown[model]["output_tokens"] += out

        analysis_count = len(logs)
        avg_cost = total_cost / analysis_count if analysis_count > 0 else 0.0

        return {
            "total_cost": round(total_cost, 6),
            "month_cost": round(month_cost, 6),
            "avg_cost_per_analysis": round(avg_cost, 6),
            "analysis_count": analysis_count,
            "total_input_tokens": total_input_tokens,
            "total_output_tokens": total_output_tokens,
            "model_breakdown": {
                model: {
                    "count": data["count"],
                    "cost": round(data["cost"], 6),
                    "input_tokens": data["input_tokens"],
                    "output_tokens": data["output_tokens"],
                }
                for model, data in model_breakdown.items()
            },
        }

    except Exception as e:
        logger.error(f"[ADMIN] Error fetching cost summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch cost summary: {str(e)}"
        )


@router.get("/costs/logs", response_model=List[CostLogResponse])
@router.get("/costs/logs/", response_model=List[CostLogResponse])
async def get_cost_logs(
    limit: int = 100,
    user_id: str = Depends(require_strict_admin_role),
):
    """Get individual API usage log entries for the admin dashboard."""
    supabase = get_supabase_client()

    try:
        response = supabase.table("api_usage_logs") \
            .select("*") \
            .order("created_at", desc=True) \
            .limit(limit) \
            .execute()

        logs = response.data or []

        # Enrich with contract/project info
        contract_ids = list({log["contract_id"] for log in logs if log.get("contract_id")})
        contracts_map: dict = {}
        projects_map: dict = {}

        if contract_ids:
            contracts_resp = supabase.table("contracts") \
                .select("id, file_name, project_id") \
                .in_("id", contract_ids) \
                .execute()
            for c in (contracts_resp.data or []):
                contracts_map[c["id"]] = c

            project_ids = list({c["project_id"] for c in contracts_map.values() if c.get("project_id")})
            if project_ids:
                projects_resp = supabase.table("projects") \
                    .select("id, project_name") \
                    .in_("id", project_ids) \
                    .execute()
                for p in (projects_resp.data or []):
                    projects_map[p["id"]] = p

        result = []
        for log in logs:
            contract = contracts_map.get(log.get("contract_id"), {})
            project = projects_map.get(contract.get("project_id"), {})
            log["file_name"] = contract.get("file_name")
            log["project_name"] = project.get("project_name")
            result.append(log)

        return result

    except Exception as e:
        logger.error(f"[ADMIN] Error fetching cost logs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch cost logs: {str(e)}"
        )


# ─── User Management Endpoints (admin-only) ─────────────────────────────────


def _generate_temp_password(length: int = 24) -> str:
    """Generate a secure temporary password."""
    alphabet = string.ascii_letters + string.digits + "!@#$%"
    return ''.join(secrets.choice(alphabet) for _ in range(length))


@router.get("/users", response_model=List[AdminUserResponse])
@router.get("/users/", response_model=List[AdminUserResponse])
async def list_users(
    search: Optional[str] = None,
    role: Optional[str] = None,
    user_id: str = Depends(require_strict_admin_role),
):
    """List all users with profile and auth metadata."""
    logger.info(f"[ADMIN] Listing users: search={search}, role={role}")
    supabase = get_supabase_client()

    try:
        # Get all profiles
        query = supabase.table("user_profiles") \
            .select("*") \
            .order("created_at", desc=True)
        if role:
            query = query.eq("role", role)
        profiles_resp = query.execute()
        profiles = profiles_resp.data or []

        # Get auth users for email + last_sign_in_at
        auth_map = {}
        try:
            auth_resp = supabase.auth.admin.list_users()
            auth_users = auth_resp if isinstance(auth_resp, list) else getattr(auth_resp, 'users', [])
            for au in auth_users:
                uid = au.id if hasattr(au, 'id') else au.get('id')
                email = au.email if hasattr(au, 'email') else au.get('email', '')
                last_sign_in = None
                if hasattr(au, 'last_sign_in_at'):
                    last_sign_in = str(au.last_sign_in_at) if au.last_sign_in_at else None
                elif isinstance(au, dict):
                    last_sign_in = au.get('last_sign_in_at')
                created_at = None
                if hasattr(au, 'created_at'):
                    created_at = str(au.created_at) if au.created_at else None
                elif isinstance(au, dict):
                    created_at = au.get('created_at')
                auth_map[uid] = {
                    "email": email,
                    "last_sign_in_at": last_sign_in,
                    "auth_created_at": created_at,
                }
        except Exception as e:
            logger.warning(f"[ADMIN] Could not fetch auth users (continuing with profiles only): {e}")

        # Merge
        result = []
        for p in profiles:
            auth_info = auth_map.get(p["id"], {})
            user = {
                "id": p["id"],
                "full_name": p.get("full_name", "Unknown"),
                "email": auth_info.get("email") or p.get("email") or "",
                "role": p.get("role", "project_manager"),
                "active": p.get("active", True),
                "created_at": p.get("created_at") or auth_info.get("auth_created_at"),
                "last_sign_in_at": auth_info.get("last_sign_in_at"),
            }
            result.append(user)

        # Client-side search filter
        if search:
            search_lower = search.lower()
            result = [
                u for u in result
                if search_lower in u["full_name"].lower()
                or search_lower in u["email"].lower()
            ]

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ADMIN] Error listing users: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list users: {str(e)}"
        )


@router.post("/users", response_model=AdminUserResponse)
@router.post("/users/", response_model=AdminUserResponse)
async def create_user(
    request: CreateUserRequest,
    user_id: str = Depends(require_strict_admin_role),
):
    """Create a new user in Supabase Auth and user_profiles."""
    logger.info(f"[ADMIN] Creating user: {request.email}, role={request.role}")
    supabase = get_supabase_client()

    valid_roles = ("project_manager", "executive", "admin")
    if request.role not in valid_roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role. Must be one of: {', '.join(valid_roles)}"
        )

    try:
        # Create auth user with a temporary password
        temp_password = _generate_temp_password()
        auth_resp = supabase.auth.admin.create_user({
            "email": request.email,
            "password": temp_password,
            "email_confirm": True,
        })
        auth_user = auth_resp.user if hasattr(auth_resp, 'user') else auth_resp
        new_user_id = auth_user.id if hasattr(auth_user, 'id') else auth_user['id']
        logger.info(f"[ADMIN] Auth user created: {new_user_id}")

        # Create profile
        profile_data = {
            "id": new_user_id,
            "full_name": request.full_name,
            "email": request.email,
            "role": request.role,
            "active": True,
        }
        supabase.table("user_profiles").insert(profile_data).execute()
        logger.info(f"[ADMIN] Profile created for {new_user_id}")

        # Auto-grant contracts module to the new user
        try:
            mod_resp = supabase.table("modules").select("id").eq("key", "contracts").execute()
            if mod_resp.data:
                supabase.table("user_module_access").insert({
                    "user_id": new_user_id,
                    "module_id": mod_resp.data[0]["id"],
                    "granted_by": user_id,
                }).execute()
                logger.info(f"[ADMIN] Auto-granted contracts module to {new_user_id}")
        except Exception as mod_err:
            logger.warning(f"[ADMIN] Could not auto-grant contracts module (migration may not be run): {mod_err}")

        # Send password reset email so user can set their own password
        try:
            supabase.auth.reset_password_email(request.email)
            logger.info(f"[ADMIN] Password reset email sent to {request.email}")
        except Exception as email_err:
            logger.warning(f"[ADMIN] Could not send password reset email: {email_err}")

        return AdminUserResponse(
            id=new_user_id,
            full_name=request.full_name,
            email=request.email,
            role=request.role,
            active=True,
            created_at=datetime.now(timezone.utc).isoformat(),
            last_sign_in_at=None,
        )

    except HTTPException:
        raise
    except Exception as e:
        error_str = str(e)
        if "already been registered" in error_str or "already exists" in error_str:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A user with this email already exists"
            )
        logger.error(f"[ADMIN] Error creating user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create user: {error_str}"
        )


@router.put("/users/{target_user_id}")
@router.put("/users/{target_user_id}/")
async def update_user(
    target_user_id: str,
    request: UpdateUserRequest,
    user_id: str = Depends(require_strict_admin_role),
):
    """Update a user's name or role."""
    logger.info(f"[ADMIN] Updating user {target_user_id}: {request}")
    supabase = get_supabase_client()

    valid_roles = ("project_manager", "executive", "admin")
    if request.role is not None and request.role not in valid_roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role. Must be one of: {', '.join(valid_roles)}"
        )

    try:
        update_data = {}
        if request.full_name is not None:
            update_data["full_name"] = request.full_name
        if request.role is not None:
            update_data["role"] = request.role

        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update"
            )

        resp = supabase.table("user_profiles") \
            .update(update_data) \
            .eq("id", target_user_id) \
            .execute()

        if not resp.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        logger.info(f"[ADMIN] Updated user {target_user_id}")
        return resp.data[0]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ADMIN] Error updating user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update user: {str(e)}"
        )


@router.post("/users/{target_user_id}/reset-password")
@router.post("/users/{target_user_id}/reset-password/")
async def reset_user_password(
    target_user_id: str,
    user_id: str = Depends(require_strict_admin_role),
):
    """Send a password reset email to a user."""
    logger.info(f"[ADMIN] Resetting password for user {target_user_id}")
    supabase = get_supabase_client()

    try:
        # Get user email from profile or auth
        profile_resp = supabase.table("user_profiles") \
            .select("email, full_name") \
            .eq("id", target_user_id) \
            .execute()

        email = None
        if profile_resp.data and profile_resp.data[0].get("email"):
            email = profile_resp.data[0]["email"]
        else:
            # Fall back to auth user
            try:
                auth_user = supabase.auth.admin.get_user_by_id(target_user_id)
                user_obj = auth_user.user if hasattr(auth_user, 'user') else auth_user
                email = user_obj.email if hasattr(user_obj, 'email') else user_obj.get('email')
            except Exception:
                pass

        if not email:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Could not find email for this user"
            )

        supabase.auth.reset_password_email(email)
        logger.info(f"[ADMIN] Password reset email sent to {email}")
        return {"message": f"Password reset email sent to {email}"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ADMIN] Error resetting password: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send password reset: {str(e)}"
        )


@router.post("/users/{target_user_id}/toggle-active")
@router.post("/users/{target_user_id}/toggle-active/")
async def toggle_user_active(
    target_user_id: str,
    user_id: str = Depends(require_strict_admin_role),
):
    """Enable or disable a user account."""
    logger.info(f"[ADMIN] Toggling active status for user {target_user_id}")
    supabase = get_supabase_client()

    # Prevent self-disable
    if target_user_id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot disable your own account"
        )

    try:
        # Get current state
        profile_resp = supabase.table("user_profiles") \
            .select("active, full_name") \
            .eq("id", target_user_id) \
            .execute()

        if not profile_resp.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        current_active = profile_resp.data[0].get("active", True)
        new_active = not current_active

        # Update profile
        supabase.table("user_profiles") \
            .update({"active": new_active}) \
            .eq("id", target_user_id) \
            .execute()

        # Ban/unban in Supabase Auth
        try:
            if new_active:
                supabase.auth.admin.update_user_by_id(target_user_id, {"ban_duration": "none"})
            else:
                supabase.auth.admin.update_user_by_id(target_user_id, {"ban_duration": "876600h"})
        except Exception as auth_err:
            logger.warning(f"[ADMIN] Could not update auth ban status (continuing): {auth_err}")

        action = "enabled" if new_active else "disabled"
        logger.info(f"[ADMIN] User {target_user_id} {action}")
        return {"active": new_active, "message": f"User {action}"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ADMIN] Error toggling user active: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to toggle user status: {str(e)}"
        )


@router.delete("/users/{target_user_id}")
@router.delete("/users/{target_user_id}/")
async def delete_user(
    target_user_id: str,
    request: DeleteUserRequest,
    user_id: str = Depends(require_strict_admin_role),
):
    """Permanently delete a user from auth and profiles."""
    logger.warning(f"[ADMIN] Deleting user {target_user_id}")
    supabase = get_supabase_client()

    # Prevent self-delete
    if target_user_id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )

    try:
        # Verify the user exists and email matches
        email = None
        profile_resp = supabase.table("user_profiles") \
            .select("email, full_name, role") \
            .eq("id", target_user_id) \
            .execute()

        if profile_resp.data and profile_resp.data[0].get("email"):
            email = profile_resp.data[0]["email"]
        else:
            try:
                auth_user = supabase.auth.admin.get_user_by_id(target_user_id)
                user_obj = auth_user.user if hasattr(auth_user, 'user') else auth_user
                email = user_obj.email if hasattr(user_obj, 'email') else user_obj.get('email')
            except Exception:
                pass

        if not email:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        if request.confirmation_email.lower() != email.lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Confirmation email does not match"
            )

        # Warn about active reviews for executives
        user_role = profile_resp.data[0].get("role") if profile_resp.data else None
        if user_role == "executive":
            try:
                reviews_resp = supabase.table("projects") \
                    .select("id") \
                    .eq("claimed_by_id", target_user_id) \
                    .eq("status", "in_review") \
                    .execute()
                if reviews_resp.data:
                    # Release those projects back to submitted
                    project_ids = [p["id"] for p in reviews_resp.data]
                    supabase.table("projects") \
                        .update({"status": "submitted", "claimed_by_id": None, "claimed_at": None}) \
                        .in_("id", project_ids) \
                        .execute()
                    logger.info(f"[ADMIN] Released {len(project_ids)} reviews from deleted executive")
            except Exception as rev_err:
                logger.warning(f"[ADMIN] Error checking/releasing reviews: {rev_err}")

        # Delete profile
        try:
            supabase.table("user_profiles") \
                .delete() \
                .eq("id", target_user_id) \
                .execute()
        except Exception as prof_err:
            logger.warning(f"[ADMIN] Error deleting profile: {prof_err}")

        # Delete auth user
        try:
            supabase.auth.admin.delete_user(target_user_id)
        except Exception as auth_err:
            logger.warning(f"[ADMIN] Error deleting auth user: {auth_err}")

        logger.warning(f"[ADMIN] Deleted user {target_user_id} ({email})")
        return {"message": f"User {email} permanently deleted"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ADMIN] Error deleting user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete user: {str(e)}"
        )


# ─── Module Management Endpoints (admin-only) ─────────────────────────────────


@router.get("/modules", response_model=List[ModuleResponse])
@router.get("/modules/", response_model=List[ModuleResponse])
async def list_modules(user_id: str = Depends(require_strict_admin_role)):
    """List all modules (including disabled ones)."""
    supabase = get_supabase_client()
    try:
        resp = supabase.table("modules") \
            .select("*") \
            .order("display_order") \
            .execute()
        return resp.data or []
    except Exception as e:
        logger.error(f"[ADMIN] Error listing modules: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list modules: {str(e)}"
        )


@router.put("/modules/{module_key}")
@router.put("/modules/{module_key}/")
async def update_module(
    module_key: str,
    request: UpdateModuleRequest,
    user_id: str = Depends(require_strict_admin_role),
):
    """Update a module (e.g. enable/disable)."""
    supabase = get_supabase_client()
    try:
        update_data = {}
        if request.enabled is not None:
            update_data["enabled"] = request.enabled

        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update"
            )

        resp = supabase.table("modules") \
            .update(update_data) \
            .eq("key", module_key) \
            .execute()

        if not resp.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Module '{module_key}' not found"
            )

        logger.info(f"[ADMIN] Updated module {module_key}: {update_data}")
        return resp.data[0]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ADMIN] Error updating module: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update module: {str(e)}"
        )


@router.get("/modules/{module_key}/users", response_model=List[UserWithModulesResponse])
@router.get("/modules/{module_key}/users/", response_model=List[UserWithModulesResponse])
async def list_module_users(
    module_key: str,
    user_id: str = Depends(require_strict_admin_role),
):
    """List all users with their access status for a specific module."""
    supabase = get_supabase_client()
    try:
        # Get module
        mod_resp = supabase.table("modules").select("id, key").eq("key", module_key).execute()
        if not mod_resp.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Module '{module_key}' not found"
            )
        module_id = mod_resp.data[0]["id"]

        # Get all user profiles
        profiles_resp = supabase.table("user_profiles") \
            .select("id, full_name, email, role, active") \
            .order("full_name") \
            .execute()
        profiles = profiles_resp.data or []

        # Get access records for this module
        access_resp = supabase.table("user_module_access") \
            .select("user_id") \
            .eq("module_id", module_id) \
            .execute()
        granted_user_ids = {a["user_id"] for a in (access_resp.data or [])}

        # Get auth users for email fallback
        auth_map = {}
        try:
            auth_resp = supabase.auth.admin.list_users()
            auth_users = auth_resp if isinstance(auth_resp, list) else getattr(auth_resp, 'users', [])
            for au in auth_users:
                uid = au.id if hasattr(au, 'id') else au.get('id')
                email = au.email if hasattr(au, 'email') else au.get('email', '')
                auth_map[uid] = email
        except Exception as e:
            logger.warning(f"[ADMIN] Could not fetch auth users for emails: {e}")

        # Build response
        result = []
        for p in profiles:
            user_modules = [module_key] if p["id"] in granted_user_ids else []
            result.append({
                "id": p["id"],
                "full_name": p.get("full_name", "Unknown"),
                "email": auth_map.get(p["id"]) or p.get("email") or "",
                "role": p.get("role", "project_manager"),
                "active": p.get("active", True),
                "modules": user_modules,
            })

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ADMIN] Error listing module users: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list module users: {str(e)}"
        )


@router.post("/modules/{module_key}/grant")
@router.post("/modules/{module_key}/grant/")
async def grant_module_access(
    module_key: str,
    request: GrantModuleAccessRequest,
    user_id: str = Depends(require_strict_admin_role),
):
    """Grant a single user access to a module."""
    supabase = get_supabase_client()
    try:
        mod_resp = supabase.table("modules").select("id").eq("key", module_key).execute()
        if not mod_resp.data:
            raise HTTPException(status_code=404, detail=f"Module '{module_key}' not found")

        supabase.table("user_module_access").upsert({
            "user_id": request.user_id,
            "module_id": mod_resp.data[0]["id"],
            "granted_by": user_id,
        }, on_conflict="user_id,module_id").execute()

        logger.info(f"[ADMIN] Granted {module_key} to user {request.user_id}")
        return {"message": "Access granted"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ADMIN] Error granting module access: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to grant access: {str(e)}"
        )


@router.post("/modules/{module_key}/revoke")
@router.post("/modules/{module_key}/revoke/")
async def revoke_module_access(
    module_key: str,
    request: RevokeModuleAccessRequest,
    user_id: str = Depends(require_strict_admin_role),
):
    """Revoke a single user's access to a module."""
    supabase = get_supabase_client()
    try:
        mod_resp = supabase.table("modules").select("id").eq("key", module_key).execute()
        if not mod_resp.data:
            raise HTTPException(status_code=404, detail=f"Module '{module_key}' not found")

        supabase.table("user_module_access") \
            .delete() \
            .eq("user_id", request.user_id) \
            .eq("module_id", mod_resp.data[0]["id"]) \
            .execute()

        logger.info(f"[ADMIN] Revoked {module_key} from user {request.user_id}")
        return {"message": "Access revoked"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ADMIN] Error revoking module access: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to revoke access: {str(e)}"
        )


@router.post("/modules/{module_key}/grant-all")
@router.post("/modules/{module_key}/grant-all/")
async def grant_module_to_all(
    module_key: str,
    user_id: str = Depends(require_strict_admin_role),
):
    """Grant all active users access to a module."""
    supabase = get_supabase_client()
    try:
        mod_resp = supabase.table("modules").select("id").eq("key", module_key).execute()
        if not mod_resp.data:
            raise HTTPException(status_code=404, detail=f"Module '{module_key}' not found")
        module_id = mod_resp.data[0]["id"]

        profiles_resp = supabase.table("user_profiles") \
            .select("id") \
            .eq("active", True) \
            .execute()

        granted = 0
        for p in (profiles_resp.data or []):
            try:
                supabase.table("user_module_access").upsert({
                    "user_id": p["id"],
                    "module_id": module_id,
                    "granted_by": user_id,
                }, on_conflict="user_id,module_id").execute()
                granted += 1
            except Exception:
                pass

        logger.info(f"[ADMIN] Granted {module_key} to {granted} users")
        return {"message": f"Access granted to {granted} users", "granted": granted}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ADMIN] Error granting module to all: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to grant access to all: {str(e)}"
        )


@router.post("/modules/{module_key}/revoke-all")
@router.post("/modules/{module_key}/revoke-all/")
async def revoke_module_from_all(
    module_key: str,
    user_id: str = Depends(require_strict_admin_role),
):
    """Revoke all users' access to a module."""
    supabase = get_supabase_client()
    try:
        mod_resp = supabase.table("modules").select("id").eq("key", module_key).execute()
        if not mod_resp.data:
            raise HTTPException(status_code=404, detail=f"Module '{module_key}' not found")
        module_id = mod_resp.data[0]["id"]

        # Get all access records for this module to count them
        access_resp = supabase.table("user_module_access") \
            .select("id") \
            .eq("module_id", module_id) \
            .execute()
        count = len(access_resp.data) if access_resp.data else 0

        if count > 0:
            access_ids = [a["id"] for a in access_resp.data]
            for i in range(0, len(access_ids), 50):
                batch = access_ids[i:i + 50]
                supabase.table("user_module_access") \
                    .delete() \
                    .in_("id", batch) \
                    .execute()

        logger.info(f"[ADMIN] Revoked {module_key} from {count} users")
        return {"message": f"Access revoked from {count} users", "revoked": count}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ADMIN] Error revoking module from all: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to revoke access from all: {str(e)}"
        )
