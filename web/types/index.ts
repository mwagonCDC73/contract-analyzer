// User types
export interface User {
  id: string;
  email: string;
  created_at?: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  user: User;
}

// User Profile types (from existing database)
export interface UserProfile {
  id: string;
  full_name: string;
  email?: string | null;  // Allow null emails
  role: 'project_manager' | 'executive' | 'admin';
  active: boolean;
  created_at?: string;
}

// Project types (matching existing database schema)
export interface Project {
  id: string;
  created_at: string;
  project_name: string;
  project_number: string;
  state: string;
  status: string;
  project_manager_id: string;
  pm_notes?: string;
  submitted_at?: string;
  reviewed_at?: string;
  claimed_by_id?: string;
  claimed_at?: string;
  claimed_by_name?: string;
}

export interface ProjectCreate {
  project_name: string;
  project_number: string;
  state: string;
  pm_notes?: string;
}

export interface StateOption {
  code: string;
  name: string;
  label: string;
}

// Contract types (matching existing database schema)
export interface Contract {
  id: string;
  created_at: string;
  project_id: string;
  contract_type: 'prime' | 'subcontract';
  file_name: string;
  file_path: string;
  extracted_text?: string;
  analysis_status: string;
  analysis_date?: string;
  analysis_results?: {
    analysis: string;
    model: string;
    tokens_used: {
      input: number;
      output: number;
    };
  };
  // Project information (joined from projects table)
  project_name?: string;
  project_number?: string;
  // Executive notes (per-document)
  executive_notes?: string;
  executive_notes_by_id?: string;
  executive_notes_at?: string;
}

// Analysis types
export interface AnalysisRequest {
  contract_id: string;
  analysis_type: 'general' | 'risk' | 'compliance' | 'financial';
  custom_prompt?: string;
}

// Admin contract view (enriched with project + submitter info)
export interface AdminContract {
  id: string;
  created_at: string;
  project_id: string;
  contract_type: string;
  file_name: string;
  file_path: string;
  analysis_status: string;
  analysis_date?: string;
  archived: boolean;
  project_name?: string;
  project_number?: string;
  submitter_name?: string;
  state?: string;
}

export interface Submitter {
  id: string;
  full_name: string;
}

// Admin user management
export interface AdminUser {
  id: string;
  full_name: string;
  email: string;
  role: 'project_manager' | 'executive' | 'admin';
  active: boolean;
  created_at?: string;
  last_sign_in_at?: string;
}

// Cost tracking types
export interface CostSummary {
  total_cost: number;
  month_cost: number;
  avg_cost_per_analysis: number;
  analysis_count: number;
  total_input_tokens: number;
  total_output_tokens: number;
  model_breakdown: Record<string, {
    count: number;
    cost: number;
    input_tokens: number;
    output_tokens: number;
  }>;
}

export interface CostLog {
  id: string;
  contract_id?: string;
  user_id?: string;
  analysis_type: string;
  model_used: string;
  input_tokens: number;
  output_tokens: number;
  estimated_cost_usd: number;
  created_at: string;
  file_name?: string;
  project_name?: string;
}

// Module system types
export interface Module {
  id: string;
  key: string;
  name: string;
  description?: string;
  icon?: string;
  enabled: boolean;
  display_order: number;
  created_at?: string;
}

export interface UserModuleAccess {
  id: string;
  user_id: string;
  module_id: string;
  module_key?: string;
  module_name?: string;
  granted_by?: string;
  granted_at?: string;
}

export interface UserWithModules {
  id: string;
  full_name: string;
  email: string;
  role: 'project_manager' | 'executive' | 'admin';
  active: boolean;
  modules: string[];
}

// Red Flag types (from existing database)
export interface RedFlag {
  id: string;
  created_at: string;
  contract_id: string;
  category: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  issue_title: string;
  details: string;
  location: string;
  recommendation: string;
  review_status: 'needs_review' | 'approved' | 'rejected';
  executive_comment?: string;
  reviewed_by_id?: string;
  reviewed_at?: string;
  disregarded: boolean;
}
