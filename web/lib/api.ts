import axios from 'axios';
import { getValidAccessToken, supabase } from './supabase';
import type {
  LoginRequest,
  LoginResponse,
  Project,
  ProjectCreate,
  Contract,
  AnalysisRequest,
  RedFlag,
  AdminContract,
  AdminUser,
  Submitter,
  CostSummary,
  CostLog,
  StateOption,
  Module,
  UserWithModules,
} from '@/types';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Create axios instance with interceptors
const apiClient = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth token to requests — uses getValidAccessToken() which
// checks expiration and refreshes automatically before sending.
apiClient.interceptors.request.use(async (config) => {
  console.log('[API] Request:', config.method?.toUpperCase(), config.url);

  const token = await getValidAccessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  } else {
    console.warn('[API] No valid session token available');
  }

  return config;
}, (error) => {
  console.error('[API] Request error:', error);
  return Promise.reject(error);
});

// Response interceptor: retry once on 401 after refreshing the session.
// This handles the race condition where a token expires between the
// request interceptor's check and the backend receiving it.
apiClient.interceptors.response.use(
  (response) => {
    console.log('[API] Response:', response.status, response.config.url);
    return response;
  },
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      console.warn('[API] Got 401, attempting session refresh and retry...');

      try {
        const { data: { session }, error: refreshError } =
          await supabase.auth.refreshSession();
        if (!refreshError && session?.access_token) {
          console.log('[API] Session refreshed, retrying request');
          // The request interceptor will pick up the fresh token
          return apiClient(originalRequest);
        }
      } catch (refreshErr) {
        console.error('[API] Session refresh failed:', refreshErr);
      }
    }

    // Log errors that aren't retryable
    if (error.response) {
      console.error('[API] Error:', error.response.status, error.config?.url, error.response.data);
    } else if (error.request) {
      console.error('[API] No response received:', error.request);
    }
    return Promise.reject(error);
  }
);

// Auth API
export const authAPI = {
  login: async (credentials: LoginRequest): Promise<LoginResponse> => {
    const { data } = await apiClient.post('/api/auth/login', credentials);
    return data;
  },

  signup: async (credentials: LoginRequest) => {
    const { data } = await apiClient.post('/api/auth/signup', credentials);
    return data;
  },

  logout: async () => {
    const { data } = await apiClient.post('/api/auth/logout');
    return data;
  },

  getCurrentUser: async () => {
    const { data } = await apiClient.get('/api/auth/me');
    return data;
  },

  getCurrentUserProfile: async () => {
    const { data } = await apiClient.get('/api/auth/profile');
    return data;
  },

  getMyModules: async (): Promise<Module[]> => {
    const { data } = await apiClient.get('/api/auth/my-modules');
    return data;
  },
};

// Projects API
export const projectsAPI = {
  list: async (): Promise<Project[]> => {
    console.log('[projectsAPI] Fetching projects list...');
    const { data } = await apiClient.get('/api/projects/');
    console.log('[projectsAPI] Projects fetched:', data.length);
    return data;
  },

  create: async (project: ProjectCreate): Promise<Project> => {
    console.log('[projectsAPI] Creating project:', project);
    const { data } = await apiClient.post('/api/projects/', project);
    console.log('[projectsAPI] Project created:', data);
    return data;
  },

  get: async (id: string): Promise<Project> => {
    const { data } = await apiClient.get(`/api/projects/${id}`);
    return data;
  },

  update: async (id: string, updates: Partial<ProjectCreate>): Promise<Project> => {
    const { data } = await apiClient.put(`/api/projects/${id}`, updates);
    return data;
  },

  delete: async (id: string): Promise<void> => {
    await apiClient.delete(`/api/projects/${id}`);
  },

  submit: async (id: string): Promise<Project> => {
    const { data } = await apiClient.post(`/api/projects/${id}/submit`);
    return data;
  },

  claim: async (id: string): Promise<Project> => {
    const { data } = await apiClient.post(`/api/projects/${id}/claim`);
    return data;
  },

  unclaim: async (id: string): Promise<Project> => {
    const { data } = await apiClient.post(`/api/projects/${id}/unclaim`);
    return data;
  },

  approve: async (id: string): Promise<Project> => {
    const { data } = await apiClient.post(`/api/projects/${id}/approve`);
    return data;
  },

  reject: async (id: string): Promise<Project> => {
    const { data } = await apiClient.post(`/api/projects/${id}/reject`);
    return data;
  },
};

// Contracts API
export const contractsAPI = {
  listAll: async (): Promise<Contract[]> => {
    console.log('[contractsAPI] Fetching all contracts...');
    const { data } = await apiClient.get('/api/contracts/');
    console.log('[contractsAPI] All contracts fetched:', data.length);
    return data;
  },

  upload: async (file: File, projectId: string, contractType?: string): Promise<Contract> => {
    console.log('[contractsAPI] Uploading contract:', {
      fileName: file.name,
      fileSize: file.size,
      fileType: file.type,
      projectId,
      contractType,
    });

    const formData = new FormData();
    formData.append('file', file);
    formData.append('project_id', projectId);
    if (contractType) {
      formData.append('contract_type', contractType);
    }

    const { data } = await apiClient.post('/api/contracts/upload/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    console.log('[contractsAPI] Contract uploaded:', data);
    return data;
  },

  listByProject: async (projectId: string): Promise<Contract[]> => {
    const { data } = await apiClient.get(`/api/contracts/project/${projectId}/`);
    return data;
  },

  get: async (id: string): Promise<Contract> => {
    const { data } = await apiClient.get(`/api/contracts/${id}/`);
    return data;
  },

  update: async (id: string, updates: { contract_type?: string; status?: string }): Promise<Contract> => {
    const { data } = await apiClient.put(`/api/contracts/${id}/`, updates);
    return data;
  },

  delete: async (id: string): Promise<void> => {
    await apiClient.delete(`/api/contracts/${id}/`);
  },

  updateExecutiveNotes: async (id: string, notes: string): Promise<Contract> => {
    const { data } = await apiClient.put(`/api/contracts/${id}/executive-notes`, { executive_notes: notes });
    return data;
  },

  getPdfUrl: (id: string) => `${API_URL}/api/contracts/${id}/pdf`,
};

// Analysis API
export const analysisAPI = {
  analyze: async (request: AnalysisRequest): Promise<Contract> => {
    console.log('[analysisAPI] Starting analysis:', request);
    const { data } = await apiClient.post('/api/analysis/analyze/', request);
    console.log('[analysisAPI] Analysis complete:', data);
    return data;
  },

  listByContract: async (contractId: string): Promise<RedFlag[]> => {
    console.log('[analysisAPI] Fetching red flags for contract:', contractId);
    const { data } = await apiClient.get(`/api/analysis/contract/${contractId}/red-flags/`);
    console.log('[analysisAPI] Red flags fetched:', data.length);
    return data;
  },
};

// Config API
export const configAPI = {
  getStates: async (): Promise<StateOption[]> => {
    const { data } = await apiClient.get('/api/config/states');
    return data;
  },
};

// Admin API
export const adminAPI = {
  listContracts: async (params: {
    archived?: boolean;
    analysis_status?: string;
    search?: string;
    submitter?: string;
    date_from?: string;
    date_to?: string;
  } = {}): Promise<AdminContract[]> => {
    console.log('[adminAPI] Fetching admin contracts:', params);
    const { data } = await apiClient.get('/api/admin/contracts', { params });
    console.log('[adminAPI] Admin contracts fetched:', data.length);
    return data;
  },

  listSubmitters: async (): Promise<Submitter[]> => {
    const { data } = await apiClient.get('/api/admin/submitters');
    return data;
  },

  archiveContracts: async (contractIds: string[]): Promise<{ archived: number }> => {
    console.log('[adminAPI] Archiving contracts:', contractIds.length);
    const { data } = await apiClient.post('/api/admin/contracts/archive', { contract_ids: contractIds });
    return data;
  },

  restoreContracts: async (contractIds: string[]): Promise<{ restored: number }> => {
    console.log('[adminAPI] Restoring contracts:', contractIds.length);
    const { data } = await apiClient.post('/api/admin/contracts/restore', { contract_ids: contractIds });
    return data;
  },

  deleteContracts: async (contractIds: string[]): Promise<{ deleted: number }> => {
    console.log('[adminAPI] Deleting contracts:', contractIds.length);
    const { data } = await apiClient.post('/api/admin/contracts/delete', { contract_ids: contractIds });
    return data;
  },

  resetTestData: async (confirmation: string): Promise<{
    red_flags_deleted: number;
    analyses_deleted: number;
    contracts_deleted: number;
    storage_files_removed: number;
    projects_reset: number;
    performed_by: string;
    performed_at: string;
  }> => {
    console.log('[adminAPI] Resetting test data...');
    const { data } = await apiClient.post('/api/admin/reset-test-data', { confirmation });
    return data;
  },

  // User management
  listUsers: async (params: { search?: string; role?: string } = {}): Promise<AdminUser[]> => {
    const { data } = await apiClient.get('/api/admin/users', { params });
    return data;
  },

  createUser: async (user: { email: string; full_name: string; role: string }): Promise<AdminUser> => {
    const { data } = await apiClient.post('/api/admin/users', user);
    return data;
  },

  updateUser: async (id: string, updates: { full_name?: string; role?: string }): Promise<AdminUser> => {
    const { data } = await apiClient.put(`/api/admin/users/${id}`, updates);
    return data;
  },

  resetUserPassword: async (id: string): Promise<{ message: string }> => {
    const { data } = await apiClient.post(`/api/admin/users/${id}/reset-password`);
    return data;
  },

  toggleUserActive: async (id: string): Promise<{ active: boolean; message: string }> => {
    const { data } = await apiClient.post(`/api/admin/users/${id}/toggle-active`);
    return data;
  },

  deleteUser: async (id: string, confirmationEmail: string): Promise<{ message: string }> => {
    const { data } = await apiClient.delete(`/api/admin/users/${id}`, {
      data: { confirmation_email: confirmationEmail },
    });
    return data;
  },

  // Cost tracking
  getCostSummary: async (): Promise<CostSummary> => {
    const { data } = await apiClient.get('/api/admin/costs/summary');
    return data;
  },

  getCostLogs: async (limit: number = 100): Promise<CostLog[]> => {
    const { data } = await apiClient.get('/api/admin/costs/logs', { params: { limit } });
    return data;
  },

  // Module management
  listModules: async (): Promise<Module[]> => {
    const { data } = await apiClient.get('/api/admin/modules');
    return data;
  },

  updateModule: async (moduleKey: string, updates: { enabled?: boolean }): Promise<Module> => {
    const { data } = await apiClient.put(`/api/admin/modules/${moduleKey}`, updates);
    return data;
  },

  listModuleUsers: async (moduleKey: string): Promise<UserWithModules[]> => {
    const { data } = await apiClient.get(`/api/admin/modules/${moduleKey}/users`);
    return data;
  },

  grantModuleAccess: async (moduleKey: string, userId: string): Promise<{ message: string }> => {
    const { data } = await apiClient.post(`/api/admin/modules/${moduleKey}/grant`, { user_id: userId });
    return data;
  },

  revokeModuleAccess: async (moduleKey: string, userId: string): Promise<{ message: string }> => {
    const { data } = await apiClient.post(`/api/admin/modules/${moduleKey}/revoke`, { user_id: userId });
    return data;
  },

  grantModuleToAll: async (moduleKey: string): Promise<{ message: string; granted: number }> => {
    const { data } = await apiClient.post(`/api/admin/modules/${moduleKey}/grant-all`);
    return data;
  },

  revokeModuleFromAll: async (moduleKey: string): Promise<{ message: string; revoked: number }> => {
    const { data } = await apiClient.post(`/api/admin/modules/${moduleKey}/revoke-all`);
    return data;
  },
};
