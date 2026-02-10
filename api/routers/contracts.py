from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form, status
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List, Optional
import io
import logging
from datetime import datetime
from services.supabase import get_supabase_client, get_current_user_id, get_user_profile
from models.schemas import ContractResponse, ContractUpdate, ExecutiveNotesUpdate
from dependencies import get_current_user_with_profile, require_pm_role, require_executive_role

router = APIRouter()
security = HTTPBearer()
logger = logging.getLogger(__name__)

@router.get("/debug/test-query")
async def debug_test_query(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Debug endpoint to test database queries"""
    logger.info("[DEBUG] Testing database queries...")
    supabase = get_supabase_client()
    user_id = await get_current_user_id(credentials.credentials)

    try:
        contracts = supabase.table("contracts").select("id, file_name, project_id").limit(3).execute()
        projects = supabase.table("projects").select("id, project_name, project_number").limit(3).execute()

        if contracts.data and len(contracts.data) > 0:
            first_contract = contracts.data[0]
            project_id = first_contract.get('project_id')
            if project_id:
                supabase.table("projects").select("*").eq("id", project_id).execute()

        return {
            "contracts_count": len(contracts.data),
            "projects_count": len(projects.data),
            "contracts": contracts.data,
            "projects": projects.data
        }
    except Exception as e:
        logger.error(f"[DEBUG] Error: {e}")
        return {"error": str(e)}

@router.get("", response_model=List[ContractResponse])
@router.get("/", response_model=List[ContractResponse])
async def list_all_contracts(
    user_info: dict = Depends(get_current_user_with_profile),
):
    """
    List contracts for executive review.
    Only returns contracts for non-draft, non-archived projects.
    """
    logger.info("[CONTRACTS] ========== LIST ALL CONTRACTS ENDPOINT CALLED ==========")
    supabase = get_supabase_client()
    role = user_info["profile"].get("role")

    if role not in ("executive", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Executive or admin role required"
        )

    try:
        try:
            response = supabase.table("contracts")\
                .select("*, project:project_id(project_name, project_number, status)")\
                .order("created_at", desc=True)\
                .execute()

            result = []
            for contract in response.data:
                project_data = contract.pop("project", None) or {}
                project_status = project_data.get("status", "")
                # Filter out draft and archived projects
                if project_status in ("draft",):
                    continue
                contract['project_name'] = project_data.get('project_name')
                contract['project_number'] = project_data.get('project_number')
                result.append(contract)

            return result

        except Exception as join_error:
            logger.error(f"[CONTRACTS] Join query failed: {join_error}")
            # Fallback: manual join
            contracts_response = supabase.table("contracts")\
                .select("*")\
                .order("created_at", desc=True)\
                .execute()

            result = []
            for contract in contracts_response.data:
                project_id = contract.get('project_id')
                if project_id:
                    try:
                        project_response = supabase.table("projects")\
                            .select("project_name, project_number, status")\
                            .eq("id", project_id)\
                            .execute()

                        if project_response.data and len(project_response.data) > 0:
                            proj = project_response.data[0]
                            if proj.get("status") in ("draft",):
                                continue
                            contract['project_name'] = proj.get('project_name')
                            contract['project_number'] = proj.get('project_number')
                        else:
                            contract['project_name'] = None
                            contract['project_number'] = None
                    except Exception:
                        contract['project_name'] = None
                        contract['project_number'] = None
                else:
                    contract['project_name'] = None
                    contract['project_number'] = None
                result.append(contract)

            return result
    except Exception as e:
        logger.error(f"[CONTRACTS] Error fetching contracts: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch contracts: {str(e)}"
        )

@router.post("/upload", response_model=ContractResponse, status_code=status.HTTP_201_CREATED)
@router.post("/upload/", response_model=ContractResponse, status_code=status.HTTP_201_CREATED)
async def upload_contract(
    file: UploadFile = File(...),
    project_id: str = Form(...),
    contract_type: Optional[str] = Form(None),
    user_info: dict = Depends(require_pm_role),
):
    """Upload a contract PDF and extract text (PM/admin only)."""
    supabase = get_supabase_client()

    # Validate file type
    if not file.filename.endswith('.pdf'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are supported"
        )

    try:
        content = await file.read()

        file_path = f"{project_id}/{contract_type}_{file.filename}"
        supabase.storage.from_("contracts").upload(
            file_path,
            content,
            {"content-type": "application/pdf"}
        )

        contract_data = {
            "project_id": project_id,
            "file_name": file.filename,
            "file_path": file_path,
            "contract_type": contract_type or "prime",
            "extracted_text": "",
            "analysis_status": "pending"
        }

        response = supabase.table("contracts").insert(contract_data).execute()
        logger.info(f"Contract uploaded successfully: {response.data[0]['id']}")

        # Transition project from draft to processing if currently draft
        try:
            supabase.table("projects")\
                .update({"status": "processing"})\
                .eq("id", project_id)\
                .eq("status", "draft")\
                .execute()
        except Exception as e:
            logger.warning(f"Could not transition project to processing: {e}")

        return response.data[0]

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload contract: {str(e)}"
        )

@router.get("/project/{project_id}", response_model=List[ContractResponse])
@router.get("/project/{project_id}/", response_model=List[ContractResponse])
async def list_contracts(
    project_id: str,
    user_info: dict = Depends(get_current_user_with_profile),
):
    """List all contracts for a project — role-aware."""
    supabase = get_supabase_client()
    user_id = user_info["user_id"]
    role = user_info["profile"].get("role")

    try:
        # Check access based on role
        project = supabase.table("projects").select("*").eq("id", project_id).execute()
        if not project.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )

        proj = project.data[0]

        if role == "project_manager":
            if proj["project_manager_id"] != user_id:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
        elif role == "executive":
            allowed = (
                proj.get("claimed_by_id") == user_id
                or proj.get("status") in ("submitted", "in_review", "approved", "rejected")
            )
            if not allowed:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
        # admin: all allowed

        response = supabase.table("contracts").select("*").eq("project_id", project_id).execute()
        return response.data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/{contract_id}/pdf")
async def get_contract_pdf(
    contract_id: str,
    token: Optional[str] = Query(None),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
):
    """Download the original PDF for a contract — role-aware via parent project.

    Accepts auth via Authorization header OR ?token= query param (for iframe usage).
    """
    # Resolve token from header or query param
    bearer_token = None
    if credentials and credentials.credentials:
        bearer_token = credentials.credentials
    elif token:
        bearer_token = token

    if not bearer_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

    user_id = await get_current_user_id(bearer_token)
    profile = await get_user_profile(user_id)
    role = profile.get("role")

    supabase = get_supabase_client()

    try:
        response = supabase.table("contracts").select("file_path, file_name, project_id").eq("id", contract_id).execute()
        if not response.data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contract not found")

        contract = response.data[0]

        # Check access via parent project (same pattern as get_contract)
        project = supabase.table("projects").select("*").eq("id", contract["project_id"]).execute()
        if project.data:
            proj = project.data[0]
            if role == "project_manager":
                if proj["project_manager_id"] != user_id:
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contract not found")
            elif role == "executive":
                allowed = (
                    proj.get("claimed_by_id") == user_id
                    or proj.get("status") in ("submitted", "in_review", "approved", "rejected")
                )
                if not allowed:
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contract not found")

        file_path = contract["file_path"]
        file_name = contract.get("file_name", "contract.pdf")

        pdf_bytes = supabase.storage.from_("contracts").download(file_path)

        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": f'inline; filename="{file_name}"'},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[CONTRACTS] Error downloading PDF: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to download PDF: {str(e)}",
        )


@router.get("/{contract_id}", response_model=ContractResponse)
@router.get("/{contract_id}/", response_model=ContractResponse)
async def get_contract(
    contract_id: str,
    user_info: dict = Depends(get_current_user_with_profile),
):
    """Get a specific contract — role-aware via parent project."""
    supabase = get_supabase_client()
    user_id = user_info["user_id"]
    role = user_info["profile"].get("role")

    try:
        response = supabase.table("contracts").select("*").eq("id", contract_id).execute()
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Contract not found"
            )

        contract = response.data[0]

        # Check access via parent project
        project = supabase.table("projects").select("*").eq("id", contract["project_id"]).execute()
        if project.data:
            proj = project.data[0]
            if role == "project_manager":
                if proj["project_manager_id"] != user_id:
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contract not found")
            elif role == "executive":
                allowed = (
                    proj.get("claimed_by_id") == user_id
                    or proj.get("status") in ("submitted", "in_review", "approved", "rejected")
                )
                if not allowed:
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contract not found")

        return contract
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.put("/{contract_id}", response_model=ContractResponse)
async def update_contract(
    contract_id: str,
    contract_update: ContractUpdate,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Update contract metadata."""
    supabase = get_supabase_client()
    await get_current_user_id(credentials.credentials)

    try:
        update_data = contract_update.dict(exclude_unset=True)
        response = supabase.table("contracts").update(update_data).eq("id", contract_id).execute()
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Contract not found"
            )
        return response.data[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.put("/{contract_id}/executive-notes", response_model=ContractResponse)
@router.put("/{contract_id}/executive-notes/", response_model=ContractResponse)
async def update_executive_notes(
    contract_id: str,
    body: ExecutiveNotesUpdate,
    user_info: dict = Depends(require_executive_role),
):
    """Save executive notes on a contract (executive/admin only)."""
    supabase = get_supabase_client()
    user_id = user_info["user_id"]

    try:
        # Verify contract exists and get its project
        contract = supabase.table("contracts").select("project_id").eq("id", contract_id).execute()
        if not contract.data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contract not found")

        project_id = contract.data[0]["project_id"]

        # Verify the project is claimed by this executive (if claimed_by_id column exists)
        try:
            project = supabase.table("projects").select("claimed_by_id, status").eq("id", project_id).execute()
            if not project.data:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
            if project.data[0].get("claimed_by_id") != user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You must claim this project before adding notes"
                )
        except HTTPException:
            raise
        except Exception as e:
            if "42703" in str(e):
                # claimed_by_id column missing — allow if project is in review status
                project = supabase.table("projects").select("status").eq("id", project_id).execute()
                if not project.data or project.data[0].get("status") not in ("submitted", "in_review"):
                    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project not available for notes")
            else:
                raise

        update_data = {
            "executive_notes": body.executive_notes,
            "executive_notes_by_id": user_id,
            "executive_notes_at": datetime.utcnow().isoformat(),
        }

        try:
            response = supabase.table("contracts").update(update_data).eq("id", contract_id).execute()
        except Exception as e:
            if "42703" in str(e):
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Database migration required: executive_notes columns missing from contracts table."
                )
            raise

        if not response.data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contract not found")

        return response.data[0]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating executive notes: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update executive notes: {str(e)}"
        )

@router.delete("/{contract_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_contract(
    contract_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Delete a contract."""
    supabase = get_supabase_client()
    await get_current_user_id(credentials.credentials)

    try:
        contract = supabase.table("contracts").select("file_path").eq("id", contract_id).execute()
        if not contract.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Contract not found"
            )

        file_path = contract.data[0]["file_path"]
        supabase.storage.from_("contracts").remove([file_path])
        supabase.table("contracts").delete().eq("id", contract_id).execute()
        return None
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
