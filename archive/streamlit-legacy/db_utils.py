import os
from supabase import create_client, Client
from dotenv import load_dotenv
import streamlit as st

# Load environment variables (override=True ensures .env file takes precedence)
load_dotenv(override=True)

@st.cache_resource
def get_supabase_client() -> Client:
    """Get Supabase client (cached)"""
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    
    if not supabase_url or not supabase_key:
        st.error("Missing Supabase credentials in .env file")
        st.stop()
    
    return create_client(supabase_url, supabase_key)


def authenticate_user(email: str, password: str):
    """Authenticate user with email and password"""
    supabase = get_supabase_client()
    
    try:
        response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        return response
    except Exception as e:
        st.error(f"Login failed: {str(e)}")
        return None


def get_user_profile(user_id: str):
    """Get user profile from database"""
    supabase = get_supabase_client()

    try:
        response = supabase.table("user_profiles").select("*").eq("id", user_id).execute()

        if response.data and len(response.data) > 0:
            return response.data[0]
        else:
            st.error(f"No user profile found for user ID: {user_id}")
            return None
    except Exception as e:
        st.error(f"Error fetching user profile: {str(e)}")
        import traceback
        st.error(f"Traceback: {traceback.format_exc()}")
        return None


def create_project(project_data: dict, user_id: str):
    """Create a new project in database"""
    supabase = get_supabase_client()
    
    project_data['project_manager_id'] = user_id
    project_data['status'] = 'draft'
    
    try:
        response = supabase.table("projects").insert(project_data).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        st.error(f"Error creating project: {str(e)}")
        return None


def upload_contract_file(file, project_id: str, contract_type: str):
    """Upload contract file to Supabase Storage"""
    supabase = get_supabase_client()
    
    file_path = f"{project_id}/{contract_type}_{file.name}"
    
    try:
        response = supabase.storage.from_("contracts").upload(
            file_path, 
            file.getvalue(), 
            {"content-type": file.type}
        )
        
        file_url = supabase.storage.from_("contracts").get_public_url(file_path)
        
        return {
            "file_path": file_path,
            "file_url": file_url,
            "file_name": file.name
        }
    except Exception as e:
        st.error(f"Error uploading file: {str(e)}")
        return None


def create_contract_record(project_id: str, contract_type: str, file_info: dict):
    """Create contract record in database"""
    supabase = get_supabase_client()
    
    contract_data = {
        "project_id": project_id,
        "contract_type": contract_type,
        "file_name": file_info["file_name"],
        "file_path": file_info["file_path"],
        "analysis_status": "pending"
    }
    
    try:
        response = supabase.table("contracts").insert(contract_data).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        st.error(f"Error creating contract record: {str(e)}")
        return None


def update_contract_analysis(contract_id: str, analysis_results: dict):
    """Update contract with AI analysis results"""
    supabase = get_supabase_client()
    
    try:
        response = supabase.table("contracts").update({
            "analysis_status": "complete",
            "analysis_date": "now()",
            "analysis_results": analysis_results
        }).eq("id", contract_id).execute()
        
        return response.data[0] if response.data else None
    except Exception as e:
        st.error(f"Error updating contract analysis: {str(e)}")
        return None


def create_red_flags(contract_id: str, findings: list):
    """Create red flag records from AI findings"""
    supabase = get_supabase_client()
    
    red_flags = []
    for finding in findings:
        red_flag = {
            "contract_id": contract_id,
            "category": finding.get("category"),
            "severity": finding.get("severity"),
            "issue_title": finding.get("issue"),
            "details": finding.get("details"),
            "location": finding.get("location"),
            "recommendation": finding.get("recommendation"),
            "review_status": "needs_review"
        }
        red_flags.append(red_flag)
    
    try:
        response = supabase.table("red_flags").insert(red_flags).execute()
        return response.data
    except Exception as e:
        st.error(f"Error creating red flags: {str(e)}")
        return None


def update_project_status(project_id: str, status: str):
    """Update project status"""
    supabase = get_supabase_client()
    
    update_data = {"status": status}
    
    if status == "submitted":
        update_data["submitted_at"] = "now()"
    
    try:
        response = supabase.table("projects").update(update_data).eq("id", project_id).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        st.error(f"Error updating project status: {str(e)}")
        return None