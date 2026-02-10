from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List
import logging
from datetime import datetime
from services.supabase import get_supabase_client, get_current_user_id
from services.claude import analyze_contract
from services.cost_tracking import calculate_cost, log_api_usage
from models.schemas import AnalysisRequest, ContractResponse, RedFlagResponse

router = APIRouter()
security = HTTPBearer()
logger = logging.getLogger(__name__)

@router.post("/analyze", response_model=ContractResponse, status_code=status.HTTP_201_CREATED)
@router.post("/analyze/", response_model=ContractResponse, status_code=status.HTTP_201_CREATED)
async def analyze_contract_endpoint(
    analysis_request: AnalysisRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Analyze a contract using Claude AI and store results in contracts table
    """
    supabase = get_supabase_client()
    user_id = await get_current_user_id(credentials.credentials)

    try:
        # Get contract
        logger.info(f"Fetching contract {analysis_request.contract_id}")
        contract = supabase.table("contracts").select("*").eq("id", analysis_request.contract_id).execute()
        if not contract.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Contract not found"
            )

        contract_data = contract.data[0]

        # Verify project ownership (using project_manager_id)
        project = supabase.table("projects").select("id, state").eq("id", contract_data["project_id"]).eq("project_manager_id", user_id).execute()
        if not project.data:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        project_state = project.data[0].get("state", "CA")

        # Download PDF from Supabase Storage
        file_path = contract_data.get("file_path")
        if not file_path:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Contract has no file stored"
            )

        logger.info(f"Downloading PDF from storage: {file_path}")
        pdf_bytes = supabase.storage.from_("contracts").download(file_path)

        # Perform analysis by sending PDF directly to Claude
        logger.info(f"Starting Claude analysis for contract {analysis_request.contract_id}")
        analysis_result = await analyze_contract(
            pdf_content=pdf_bytes,
            analysis_type=analysis_request.analysis_type,
            custom_prompt=analysis_request.custom_prompt,
            state=project_state
        )

        # Update contract with analysis results (stored directly in contracts table)
        update_data = {
            "analysis_results": analysis_result,
            "analysis_status": "completed",
            "analysis_date": datetime.utcnow().isoformat()
        }

        logger.info(f"Saving analysis results to contract {analysis_request.contract_id}")
        response = supabase.table("contracts").update(update_data).eq("id", analysis_request.contract_id).execute()

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save analysis results"
            )

        logger.info(f"Analysis completed successfully for contract {analysis_request.contract_id}")

        # Log API usage and cost
        try:
            tokens_used = analysis_result.get("tokens_used", {})
            model_used = analysis_result.get("model", "unknown")
            input_tokens = tokens_used.get("input", 0)
            output_tokens = tokens_used.get("output", 0)
            estimated_cost = calculate_cost(model_used, input_tokens, output_tokens)

            log_api_usage(
                supabase=supabase,
                contract_id=analysis_request.contract_id,
                user_id=user_id,
                analysis_type=analysis_request.analysis_type,
                model_used=model_used,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                estimated_cost=estimated_cost,
            )
            logger.info(f"API usage logged: {input_tokens} in / {output_tokens} out, cost=${estimated_cost:.6f}")
        except Exception as cost_err:
            logger.warning(f"Failed to log API usage (non-fatal): {cost_err}")

        # Auto-transition: if all contracts in the project are completed,
        # move project from 'processing' to 'submitted'
        try:
            project_id = contract_data["project_id"]
            all_contracts = supabase.table("contracts").select("analysis_status").eq("project_id", project_id).execute()
            if all_contracts.data:
                all_completed = all(c.get("analysis_status") == "completed" for c in all_contracts.data)
                if all_completed:
                    supabase.table("projects")\
                        .update({
                            "status": "submitted",
                            "submitted_at": datetime.utcnow().isoformat(),
                        })\
                        .eq("id", project_id)\
                        .eq("status", "processing")\
                        .execute()
                    logger.info(f"Auto-transitioned project {project_id} to submitted")
        except Exception as auto_err:
            logger.warning(f"Auto-transition check failed (non-fatal): {auto_err}")

        return response.data[0]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Analysis failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed: {str(e)}"
        )

@router.get("/contract/{contract_id}/red-flags", response_model=List[RedFlagResponse])
@router.get("/contract/{contract_id}/red-flags/", response_model=List[RedFlagResponse])
async def get_contract_red_flags(
    contract_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Get all red flags for a contract
    Authorization:
    - Project Managers: Can view red flags for their OWN submissions
    - Executives: Can view red flags for ALL submissions
    """
    supabase = get_supabase_client()
    user_id = await get_current_user_id(credentials.credentials)

    try:
        # Get user profile to check role
        logger.info(f"[RedFlags] Checking access for user {user_id}")
        user_profile = supabase.table("user_profiles").select("role").eq("id", user_id).execute()
        if not user_profile.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User profile not found"
            )

        user_role = user_profile.data[0]["role"]
        logger.info(f"[RedFlags] User role: {user_role}")

        # Verify access to contract
        contract = supabase.table("contracts").select("project_id").eq("id", contract_id).execute()
        if not contract.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Contract not found"
            )

        project_id = contract.data[0]["project_id"]

        # Authorization logic based on role
        if user_role in ("executive", "admin"):
            # Executives and admins can view red flags for ALL contracts
            logger.info(f"[RedFlags] {user_role} access granted for contract {contract_id}")
        elif user_role == "project_manager":
            # Project managers can only view red flags for their own projects
            project = supabase.table("projects").select("id").eq("id", project_id).eq("project_manager_id", user_id).execute()
            if not project.data:
                logger.warning(f"[RedFlags] PM {user_id} denied access to contract {contract_id} (not their project)")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: You can only view red flags for your own submissions"
                )
            logger.info(f"[RedFlags] PM access granted for their own contract {contract_id}")
        else:
            logger.error(f"[RedFlags] Unknown role: {user_role}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Invalid user role"
            )

        # Get red flags
        response = supabase.table("red_flags").select("*").eq("contract_id", contract_id).execute()
        logger.info(f"[RedFlags] Found {len(response.data)} red flags for contract {contract_id}")
        return response.data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[RedFlags] Error fetching red flags: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch red flags: {str(e)}"
        )
