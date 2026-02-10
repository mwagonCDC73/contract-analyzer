from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, Dict, Any, List
from datetime import datetime
from config.states import get_state_codes

# Authentication Schemas
class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)

class UserResponse(BaseModel):
    id: str
    email: str
    created_at: Optional[str] = None

class LoginResponse(BaseModel):
    access_token: str
    user: UserResponse

# User Profile Schemas (from existing user_profiles table)
class UserProfileResponse(BaseModel):
    id: str
    full_name: str
    email: Optional[str] = None  # Allow null emails
    role: str  # 'project_manager' or 'executive'
    active: bool = True
    created_at: Optional[str] = None

# Project Schemas (matching existing projects table)
class ProjectCreate(BaseModel):
    project_name: str = Field(..., min_length=1, max_length=255)
    project_number: str
    state: str = Field(default="CA")
    pm_notes: Optional[str] = None

    @validator("state")
    def validate_state(cls, v):
        if v not in get_state_codes():
            raise ValueError(f"Unsupported state: {v}. Must be one of {get_state_codes()}")
        return v

class ProjectUpdate(BaseModel):
    project_name: Optional[str] = Field(None, min_length=1, max_length=255)
    project_number: Optional[str] = None
    state: Optional[str] = None
    status: Optional[str] = None
    pm_notes: Optional[str] = None

    @validator("state")
    def validate_state(cls, v):
        if v is not None and v not in get_state_codes():
            raise ValueError(f"Unsupported state: {v}. Must be one of {get_state_codes()}")
        return v

class ProjectResponse(BaseModel):
    id: str
    created_at: str
    project_name: str
    project_number: str
    state: str = "CA"
    status: str
    project_manager_id: str
    pm_notes: Optional[str] = None
    submitted_at: Optional[str] = None
    reviewed_at: Optional[str] = None
    claimed_by_id: Optional[str] = None
    claimed_at: Optional[str] = None
    claimed_by_name: Optional[str] = None

# Contract Schemas (matching existing contracts table)
class ContractUpdate(BaseModel):
    contract_type: Optional[str] = None
    analysis_status: Optional[str] = None
    extracted_text: Optional[str] = None
    analysis_results: Optional[Dict[str, Any]] = None

class ContractResponse(BaseModel):
    id: str
    created_at: str
    project_id: str
    contract_type: str  # 'prime' or 'subcontract'
    file_name: str
    file_path: str
    extracted_text: Optional[str] = None
    analysis_status: str  # 'pending', 'completed', etc.
    analysis_date: Optional[str] = None
    analysis_results: Optional[Dict[str, Any]] = None
    # Project information (joined from projects table)
    project_name: Optional[str] = None
    project_number: Optional[str] = None
    # Executive notes (per-document)
    executive_notes: Optional[str] = None
    executive_notes_by_id: Optional[str] = None
    executive_notes_at: Optional[str] = None

# Analysis Request (for triggering new analysis)
class AnalysisRequest(BaseModel):
    contract_id: str
    analysis_type: str = Field(
        default="general",
        description="Type of analysis: general, risk, compliance, financial"
    )
    custom_prompt: Optional[str] = Field(
        None,
        description="Custom prompt for specific analysis requirements"
    )

# Red Flag Schemas (matching existing red_flags table)
class RedFlagResponse(BaseModel):
    id: str
    created_at: str
    contract_id: str
    category: str
    severity: str  # 'critical', 'high', 'medium', 'low'
    issue_title: str
    details: str
    location: str
    recommendation: str
    review_status: str  # 'needs_review', 'approved', 'rejected'
    executive_comment: Optional[str] = None
    reviewed_by_id: Optional[str] = None
    reviewed_at: Optional[str] = None
    disregarded: bool

class ExecutiveNotesUpdate(BaseModel):
    executive_notes: str

class RedFlagUpdate(BaseModel):
    review_status: Optional[str] = None
    executive_comment: Optional[str] = None
    disregarded: Optional[bool] = None


# Admin User Management Schemas
class AdminUserResponse(BaseModel):
    id: str
    full_name: str
    email: str
    role: str
    active: bool = True
    created_at: Optional[str] = None
    last_sign_in_at: Optional[str] = None


class CreateUserRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=255)
    role: str = Field(..., description="project_manager, executive, or admin")


class UpdateUserRequest(BaseModel):
    full_name: Optional[str] = Field(None, min_length=1, max_length=255)
    role: Optional[str] = None


class DeleteUserRequest(BaseModel):
    confirmation_email: str
