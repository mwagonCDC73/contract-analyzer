'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Header from '@/components/Header';
import { getCurrentUser } from '@/lib/supabase';
import { projectsAPI, contractsAPI, authAPI } from '@/lib/api';
import StateBadge from '@/components/StateBadge';
import StateFilter from '@/components/StateFilter';
import type { Project, Contract } from '@/types';

type SortField = 'project_name' | 'project_number' | 'contract_count' | 'status' | 'submitted_at';
type SortDirection = 'asc' | 'desc';

interface ProjectWithContracts extends Project {
  contracts?: Contract[];
  contract_count?: number;
}

export default function MySubmissionsPage() {
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(true);
  const [projects, setProjects] = useState<ProjectWithContracts[]>([]);
  const [error, setError] = useState('');
  const [sortField, setSortField] = useState<SortField>('submitted_at');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');
  const [statusFilter, setStatusFilter] = useState<string[]>(['processing', 'submitted', 'in_review', 'approved']);
  const [stateFilter, setStateFilter] = useState('');

  useEffect(() => {
    console.log('[MySubmissions] Component mounted, checking auth...');
    const checkAuth = async () => {
      try {
        console.log('[MySubmissions] Getting current user...');
        const user = await getCurrentUser();
        console.log('[MySubmissions] Current user:', user);

        if (!user) {
          router.push('/');
          return;
        }

        // Role guard: PM/admin only
        try {
          const profile = await authAPI.getCurrentUserProfile();
          if (profile.role !== 'project_manager' && profile.role !== 'admin') {
            router.push('/dashboard');
            return;
          }
        } catch {
          router.push('/dashboard');
          return;
        }

        // Load user's projects
        console.log('[MySubmissions] Loading user projects...');
        await loadProjects();
      } catch (error) {
        console.error('[MySubmissions] Error loading page:', error);
        router.push('/');
      } finally {
        setIsLoading(false);
        console.log('[MySubmissions] Loading complete');
      }
    };

    checkAuth();
  }, [router]);

  const loadProjects = async () => {
    try {
      console.log('[MySubmissions] Fetching projects from API...');
      const userProjects = await projectsAPI.list();
      console.log('[MySubmissions] Projects loaded:', userProjects.length, 'projects');

      // Filter out draft projects and load contract counts
      const submittedProjects = userProjects.filter(p => p.status !== 'draft');

      // Load contracts for each project to get count and details
      const projectsWithContracts = await Promise.all(
        submittedProjects.map(async (project) => {
          try {
            const contracts = await contractsAPI.listByProject(project.id);
            return {
              ...project,
              contracts,
              contract_count: contracts.length
            };
          } catch (error) {
            console.error(`[MySubmissions] Error loading contracts for project ${project.id}:`, error);
            return {
              ...project,
              contracts: [],
              contract_count: 0
            };
          }
        })
      );

      console.log('[MySubmissions] Projects with contracts:', projectsWithContracts);
      setProjects(projectsWithContracts);
    } catch (error: any) {
      console.error('[MySubmissions] Error loading projects:', error);
      console.error('[MySubmissions] Error details:', {
        message: error.message,
        response: error.response?.data,
        status: error.response?.status,
      });
      setError(error.response?.data?.detail || error.message || 'Failed to load submissions');
    }
  };

  const handleSort = (field: SortField) => {
    console.log('[MySubmissions] Sorting by:', field);
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('asc');
    }
  };

  const getSortedProjects = () => {
    // First filter by status
    let filtered = projects.filter(p => statusFilter.includes(p.status));
    if (stateFilter) {
      filtered = filtered.filter(p => p.state === stateFilter);
    }

    // Then sort
    const sorted = [...filtered].sort((a, b) => {
      let aVal: any, bVal: any;

      switch (sortField) {
        case 'project_name':
          aVal = a.project_name?.toLowerCase() || '';
          bVal = b.project_name?.toLowerCase() || '';
          break;
        case 'project_number':
          aVal = a.project_number?.toLowerCase() || '';
          bVal = b.project_number?.toLowerCase() || '';
          break;
        case 'contract_count':
          aVal = a.contract_count || 0;
          bVal = b.contract_count || 0;
          break;
        case 'status':
          aVal = a.status || '';
          bVal = b.status || '';
          break;
        case 'submitted_at':
          aVal = a.submitted_at ? new Date(a.submitted_at).getTime() : 0;
          bVal = b.submitted_at ? new Date(b.submitted_at).getTime() : 0;
          break;
        default:
          return 0;
      }

      if (aVal < bVal) return sortDirection === 'asc' ? -1 : 1;
      if (aVal > bVal) return sortDirection === 'asc' ? 1 : -1;
      return 0;
    });

    return sorted;
  };

  const SortIcon = ({ field }: { field: SortField }) => {
    if (sortField !== field) {
      return (
        <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16V4m0 0L3 8m4-4l4 4m6 0v12m0 0l4-4m-4 4l-4-4" />
        </svg>
      );
    }
    return sortDirection === 'asc' ? (
      <svg className="w-4 h-4 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
      </svg>
    ) : (
      <svg className="w-4 h-4 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
      </svg>
    );
  };

  const formatDate = (dateString: string | undefined) => {
    if (!dateString) return '—';
    const date = new Date(dateString);
    const dateStr = date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
    const timeStr = date.toLocaleTimeString('en-US', {
      hour: 'numeric',
      minute: '2-digit',
      hour12: true
    });
    return `${dateStr} at ${timeStr}`;
  };

  const getStatusBadgeEl = (status: string) => {
    const statusConfig: Record<string, { label: string; className: string }> = {
      'processing': {
        label: 'Processing',
        className: 'bg-amber-100 text-amber-800'
      },
      'submitted': {
        label: 'Awaiting Review',
        className: 'bg-blue-100 text-blue-800'
      },
      'in_review': {
        label: 'Under Review',
        className: 'bg-purple-100 text-purple-800'
      },
      'approved': {
        label: 'Approved',
        className: 'bg-green-100 text-green-800'
      },
      'rejected': {
        label: 'Rejected',
        className: 'bg-red-100 text-red-800'
      }
    };

    const config = statusConfig[status] || {
      label: status,
      className: 'bg-gray-100 text-gray-800'
    };

    return (
      <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${config.className}`}>
        {config.label}
      </span>
    );
  };

  const sortedProjects = getSortedProjects();
  const totalSubmissions = projects.length;
  const processing = projects.filter(p => p.status === 'processing').length;
  const awaitingReview = projects.filter(p => p.status === 'submitted' || p.status === 'in_review').length;
  const approved = projects.filter(p => p.status === 'approved').length;

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-gray-600">Loading...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Header />
      <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <div className="px-4 py-6 sm:px-0">
          {/* Page Header */}
          <div className="mb-8">
            <h1 className="text-3xl font-bold text-gray-900">My Submissions</h1>
            <p className="mt-2 text-sm text-gray-600">
              Track your contract submissions and their review status
            </p>
          </div>

          {/* Summary Metrics */}
          <div className="grid grid-cols-1 gap-5 sm:grid-cols-4 mb-6">
            <div className="bg-white overflow-hidden shadow rounded-lg">
              <div className="px-4 py-5 sm:p-6">
                <dt className="text-sm font-medium text-gray-500 truncate">Total Submissions</dt>
                <dd className="mt-1 text-3xl font-semibold text-gray-900">{totalSubmissions}</dd>
              </div>
            </div>
            <div className="bg-white overflow-hidden shadow rounded-lg">
              <div className="px-4 py-5 sm:p-6">
                <dt className="text-sm font-medium text-gray-500 truncate">Processing</dt>
                <dd className="mt-1 text-3xl font-semibold text-amber-600">{processing}</dd>
              </div>
            </div>
            <div className="bg-white overflow-hidden shadow rounded-lg">
              <div className="px-4 py-5 sm:p-6">
                <dt className="text-sm font-medium text-gray-500 truncate">Awaiting Review</dt>
                <dd className="mt-1 text-3xl font-semibold text-blue-600">{awaitingReview}</dd>
              </div>
            </div>
            <div className="bg-white overflow-hidden shadow rounded-lg">
              <div className="px-4 py-5 sm:p-6">
                <dt className="text-sm font-medium text-gray-500 truncate">Approved</dt>
                <dd className="mt-1 text-3xl font-semibold text-green-600">{approved}</dd>
              </div>
            </div>
          </div>

          {/* Filters */}
          <div className="bg-white shadow rounded-lg p-4 mb-6">
            <div className="flex items-center gap-4">
              <label className="text-sm font-medium text-gray-700">Filter by Status:</label>
              <div className="flex gap-3">
                {['processing', 'submitted', 'in_review', 'approved', 'rejected'].map((status) => (
                  <label key={status} className="inline-flex items-center">
                    <input
                      type="checkbox"
                      checked={statusFilter.includes(status)}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setStatusFilter([...statusFilter, status]);
                        } else {
                          setStatusFilter(statusFilter.filter(s => s !== status));
                        }
                      }}
                      className="rounded border-gray-300 text-blue-600 shadow-sm focus:border-blue-300 focus:ring focus:ring-blue-200 focus:ring-opacity-50"
                    />
                    <span className="ml-2 text-sm text-gray-700 capitalize">
                      {status.replace('_', ' ')}
                    </span>
                  </label>
                ))}
              </div>
              <div className="ml-auto">
                <StateFilter value={stateFilter} onChange={setStateFilter} />
              </div>
            </div>
          </div>

          {error && (
            <div className="mb-4 rounded-md bg-red-50 p-4">
              <div className="text-sm text-red-800">{error}</div>
            </div>
          )}

          {/* Projects Table */}
          <div className="bg-white shadow rounded-lg overflow-hidden">
            {sortedProjects.length === 0 ? (
              <div className="text-center py-12">
                <svg
                  className="mx-auto h-12 w-12 text-gray-400"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  aria-hidden="true"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                  />
                </svg>
                <h3 className="mt-2 text-sm font-medium text-gray-900">No submissions yet</h3>
                <p className="mt-1 text-sm text-gray-500">
                  {projects.length === 0
                    ? "You haven't submitted any contracts yet. Get started by submitting your first contract!"
                    : "No submissions match your filter criteria. Try adjusting the filters."}
                </p>
                {projects.length === 0 && (
                  <div className="mt-6">
                    <button
                      onClick={() => router.push('/submit')}
                      className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                    >
                      Submit Your First Contract
                    </button>
                  </div>
                )}
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th
                        onClick={() => handleSort('project_name')}
                        className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                      >
                        <div className="flex items-center gap-1">
                          Project Name
                          <SortIcon field="project_name" />
                        </div>
                      </th>
                      <th
                        onClick={() => handleSort('project_number')}
                        className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                      >
                        <div className="flex items-center gap-1">
                          Project #
                          <SortIcon field="project_number" />
                        </div>
                      </th>
                      <th
                        onClick={() => handleSort('contract_count')}
                        className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                      >
                        <div className="flex items-center gap-1">
                          Contracts
                          <SortIcon field="contract_count" />
                        </div>
                      </th>
                      <th
                        onClick={() => handleSort('submitted_at')}
                        className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                      >
                        <div className="flex items-center gap-1">
                          Submitted
                          <SortIcon field="submitted_at" />
                        </div>
                      </th>
                      <th
                        onClick={() => handleSort('status')}
                        className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                      >
                        <div className="flex items-center gap-1">
                          Status
                          <SortIcon field="status" />
                        </div>
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Actions
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {sortedProjects.map((project) => (
                      <tr key={project.id} className="hover:bg-gray-50">
                        <td className="px-6 py-4">
                          <div className="flex items-center gap-2">
                            <div className="text-sm font-medium text-gray-900">
                              {project.project_name}
                            </div>
                            <StateBadge state={project.state} />
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="text-sm text-gray-500">
                            {project.project_number || '—'}
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="text-sm text-gray-900">
                            {project.contract_count || 0} file{project.contract_count !== 1 ? 's' : ''}
                          </div>
                          {project.contracts && project.contracts.length > 0 && (
                            <div className="text-xs text-gray-500">
                              {project.contracts.map(c => c.contract_type).join(', ')}
                            </div>
                          )}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {formatDate(project.submitted_at)}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          {getStatusBadgeEl(project.status)}
                          {project.claimed_by_name && (
                            <div className="text-xs text-purple-600 mt-1">
                              Reviewer: {project.claimed_by_name}
                            </div>
                          )}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                          {project.contracts && project.contracts.length > 0 && (
                            <button
                              onClick={() => router.push(`/contract/${project.contracts![0].id}`)}
                              className="text-blue-600 hover:text-blue-900"
                            >
                              View Details
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {sortedProjects.length > 0 && (
            <div className="mt-4 text-sm text-gray-500">
              Showing {sortedProjects.length} of {projects.length} submission{projects.length !== 1 ? 's' : ''}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
