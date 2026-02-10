from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List, Optional
import logging
from datetime import datetime
from services.supabase import get_supabase_client, get_current_user_id
from models.schemas import ProjectCreate, ProjectResponse, ProjectUpdate
from dependencies import get_current_user_with_profile, require_pm_role, require_executive_role

router = APIRouter()
security = HTTPBearer()
logger = logging.getLogger(__name__)

# Cache schema check result so we don't query every request
_has_claimed_by_id: Optional[bool] = None


def _check_claimed_by_id_exists(supabase) -> bool:
    """Check whether the claimed_by_id column exists on the projects table."""
    global _has_claimed_by_id
    if _has_claimed_by_id is not None:
        return _has_claimed_by_id
    try:
        supabase.table("projects").select("claimed_by_id").limit(0).execute()
        _has_claimed_by_id = True
    except Exception as e:
        if "42703" in str(e):
            _has_claimed_by_id = False
            logger.warning(
                "Column 'claimed_by_id' missing from projects table. "
                "Run the database migration to enable executive claim workflow. "
                "See CLAUDE.md or plan file for the migration SQL."
            )
        else:
            # Unknown error — assume column exists to avoid masking real issues
            _has_claimed_by_id = True
    return _has_claimed_by_id


def _enrich_project_with_claimed_by_name(supabase, project: dict) -> dict:
    """Add claimed_by_name to a project dict if claimed_by_id is set."""
    claimed_by_id = project.get("claimed_by_id")
    if claimed_by_id:
        try:
            profile = supabase.table("user_profiles").select("full_name").eq("id", claimed_by_id).execute()
            if profile.data:
                project["claimed_by_name"] = profile.data[0].get("full_name")
        except Exception:
            pass
    return project


def _enrich_projects_with_claimed_by_name(supabase, projects: list) -> list:
    """Batch-enrich projects with claimed_by_name."""
    claimed_ids = list({p["claimed_by_id"] for p in projects if p.get("claimed_by_id")})
    if not claimed_ids:
        return projects
    try:
        profiles = supabase.table("user_profiles").select("id, full_name").in_("id", claimed_ids).execute()
        name_map = {p["id"]: p.get("full_name") for p in profiles.data}
    except Exception:
        name_map = {}
    for p in projects:
        if p.get("claimed_by_id"):
            p["claimed_by_name"] = name_map.get(p["claimed_by_id"])
    return projects


@router.get("", response_model=List[ProjectResponse])
@router.get("/", response_model=List[ProjectResponse])
async def list_projects(
    view: Optional[str] = Query(None),
    user_info: dict = Depends(get_current_user_with_profile),
):
    """
    List projects — role-aware.
    PM/admin: own projects.
    Executive: claimed projects + unclaimed submitted queue.
    """
    try:
        supabase = get_supabase_client()
        user_id = user_info["user_id"]
        role = user_info["profile"].get("role")

        if role in ("project_manager",):
            response = supabase.table("projects").select("*").eq("project_manager_id", user_id).execute()
            return _enrich_projects_with_claimed_by_name(supabase, response.data)

        if role in ("executive",):
            if _check_claimed_by_id_exists(supabase):
                # Full workflow: filter by claimed/unclaimed
                claimed = supabase.table("projects").select("*").eq("claimed_by_id", user_id).execute()
                unclaimed = supabase.table("projects").select("*").eq("status", "submitted").is_("claimed_by_id", "null").execute()

                combined = {p["id"]: p for p in claimed.data}
                for p in unclaimed.data:
                    combined[p["id"]] = p

                if view == "claimed":
                    result = claimed.data
                elif view == "unclaimed":
                    result = unclaimed.data
                else:
                    result = list(combined.values())
            else:
                # Migration not run yet — fallback: show all non-draft projects
                response = supabase.table("projects").select("*").in_(
                    "status", ["submitted", "in_review", "approved", "rejected", "processing"]
                ).execute()
                result = response.data

            return _enrich_projects_with_claimed_by_name(supabase, result)

        # admin — return all
        response = supabase.table("projects").select("*").execute()
        return _enrich_projects_with_claimed_by_name(supabase, response.data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing projects: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list projects: {str(e)}"
        )


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project: ProjectCreate,
    user_info: dict = Depends(require_pm_role),
):
    """Create a new project (PM/admin only)."""
    supabase = get_supabase_client()
    try:
        project_data = project.dict()
        project_data["project_manager_id"] = user_info["user_id"]
        project_data["status"] = "draft"
        response = supabase.table("projects").insert(project_data).execute()
        return response.data[0]
    except Exception as e:
        logger.error(f"Error creating project: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create project: {str(e)}"
        )


@router.get("/{project_id}", response_model=ProjectResponse)
@router.get("/{project_id}/", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    user_info: dict = Depends(get_current_user_with_profile),
):
    """Get a specific project — role-aware access."""
    supabase = get_supabase_client()
    user_id = user_info["user_id"]
    role = user_info["profile"].get("role")

    try:
        response = supabase.table("projects").select("*").eq("id", project_id).execute()
        if not response.data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

        project = response.data[0]

        if role == "project_manager":
            if project["project_manager_id"] != user_id:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
        elif role == "executive":
            allowed = (
                project.get("claimed_by_id") == user_id
                or project.get("status") in ("submitted", "in_review", "approved", "rejected")
            )
            if not allowed:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
        # admin: all allowed

        return _enrich_project_with_claimed_by_name(supabase, project)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting project: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get project: {str(e)}"
        )


@router.put("/{project_id}", response_model=ProjectResponse)
@router.put("/{project_id}/", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    project_update: ProjectUpdate,
    user_info: dict = Depends(require_pm_role),
):
    """Update a project (PM/admin only, own projects)."""
    supabase = get_supabase_client()
    try:
        update_data = project_update.dict(exclude_unset=True)
        response = supabase.table("projects").update(update_data).eq("id", project_id).eq("project_manager_id", user_info["user_id"]).execute()
        if not response.data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
        return response.data[0]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating project: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update project: {str(e)}"
        )


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
@router.delete("/{project_id}/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: str,
    user_info: dict = Depends(require_pm_role),
):
    """Delete a project (PM/admin only, own projects)."""
    supabase = get_supabase_client()
    try:
        response = supabase.table("projects").delete().eq("id", project_id).eq("project_manager_id", user_info["user_id"]).execute()
        if not response.data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting project: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete project: {str(e)}"
        )


@router.post("/{project_id}/submit", response_model=ProjectResponse)
@router.post("/{project_id}/submit/", response_model=ProjectResponse)
async def submit_project(
    project_id: str,
    user_info: dict = Depends(require_pm_role),
):
    """Submit a project for executive review. All contracts must be analyzed."""
    supabase = get_supabase_client()
    user_id = user_info["user_id"]

    try:
        # Verify ownership
        project = supabase.table("projects").select("*").eq("id", project_id).eq("project_manager_id", user_id).execute()
        if not project.data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

        # Check all contracts have completed analysis
        contracts = supabase.table("contracts").select("analysis_status").eq("project_id", project_id).execute()
        if not contracts.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Project has no contracts to submit"
            )

        incomplete = [c for c in contracts.data if c.get("analysis_status") != "completed"]
        if incomplete:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{len(incomplete)} contract(s) have not completed analysis"
            )

        update_data = {
            "status": "submitted",
            "submitted_at": datetime.utcnow().isoformat(),
        }
        response = supabase.table("projects").update(update_data).eq("id", project_id).eq("project_manager_id", user_id).execute()
        if not response.data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
        return response.data[0]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting project: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit project: {str(e)}"
        )


@router.post("/{project_id}/claim", response_model=ProjectResponse)
@router.post("/{project_id}/claim/", response_model=ProjectResponse)
async def claim_project(
    project_id: str,
    user_info: dict = Depends(require_executive_role),
):
    """Executive claims a submitted project for review."""
    supabase = get_supabase_client()
    user_id = user_info["user_id"]

    if not _check_claimed_by_id_exists(supabase):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database migration required: claimed_by_id column missing from projects table. "
                   "Run the migration SQL in the Supabase SQL Editor.",
        )

    try:
        # Conditional update to prevent race conditions
        response = (
            supabase.table("projects")
            .update({
                "claimed_by_id": user_id,
                "claimed_at": datetime.utcnow().isoformat(),
                "status": "in_review",
            })
            .eq("id", project_id)
            .eq("status", "submitted")
            .is_("claimed_by_id", "null")
            .execute()
        )

        if not response.data:
            # Check why it failed
            check = supabase.table("projects").select("status, claimed_by_id").eq("id", project_id).execute()
            if not check.data:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
            proj = check.data[0]
            if proj.get("claimed_by_id"):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Project has already been claimed by another reviewer"
                )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Project cannot be claimed (current status: {proj.get('status')})"
            )

        return _enrich_project_with_claimed_by_name(supabase, response.data[0])

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error claiming project: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to claim project: {str(e)}"
        )


@router.post("/{project_id}/unclaim", response_model=ProjectResponse)
@router.post("/{project_id}/unclaim/", response_model=ProjectResponse)
async def unclaim_project(
    project_id: str,
    user_info: dict = Depends(require_executive_role),
):
    """Release a claimed project back to the queue."""
    supabase = get_supabase_client()
    user_id = user_info["user_id"]

    if not _check_claimed_by_id_exists(supabase):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database migration required: claimed_by_id column missing.",
        )

    try:
        response = (
            supabase.table("projects")
            .update({
                "claimed_by_id": None,
                "claimed_at": None,
                "status": "submitted",
            })
            .eq("id", project_id)
            .eq("claimed_by_id", user_id)
            .execute()
        )

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Project not found or not claimed by you"
            )

        return response.data[0]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error unclaiming project: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to unclaim project: {str(e)}"
        )


@router.post("/{project_id}/approve", response_model=ProjectResponse)
@router.post("/{project_id}/approve/", response_model=ProjectResponse)
async def approve_project(
    project_id: str,
    user_info: dict = Depends(require_executive_role),
):
    """Approve a project that is under review."""
    supabase = get_supabase_client()
    user_id = user_info["user_id"]

    if not _check_claimed_by_id_exists(supabase):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database migration required: claimed_by_id column missing.",
        )

    try:
        response = (
            supabase.table("projects")
            .update({
                "status": "approved",
                "reviewed_at": datetime.utcnow().isoformat(),
            })
            .eq("id", project_id)
            .eq("claimed_by_id", user_id)
            .eq("status", "in_review")
            .execute()
        )

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Project not found, not claimed by you, or not in review"
            )

        return _enrich_project_with_claimed_by_name(supabase, response.data[0])

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error approving project: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to approve project: {str(e)}"
        )


@router.post("/{project_id}/reject", response_model=ProjectResponse)
@router.post("/{project_id}/reject/", response_model=ProjectResponse)
async def reject_project(
    project_id: str,
    user_info: dict = Depends(require_executive_role),
):
    """Reject a project that is under review."""
    supabase = get_supabase_client()
    user_id = user_info["user_id"]

    if not _check_claimed_by_id_exists(supabase):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database migration required: claimed_by_id column missing.",
        )

    try:
        response = (
            supabase.table("projects")
            .update({
                "status": "rejected",
                "reviewed_at": datetime.utcnow().isoformat(),
            })
            .eq("id", project_id)
            .eq("claimed_by_id", user_id)
            .eq("status", "in_review")
            .execute()
        )

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Project not found, not claimed by you, or not in review"
            )

        return _enrich_project_with_claimed_by_name(supabase, response.data[0])

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rejecting project: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reject project: {str(e)}"
        )
