'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Header from '@/components/Header';
import { getCurrentUser } from '@/lib/supabase';
import { projectsAPI, contractsAPI, authAPI } from '@/lib/api';
import { getStatusConfig } from '@/lib/statusUtils';
import StateBadge from '@/components/StateBadge';
import StateFilter from '@/components/StateFilter';
import type { Project, Contract, UserProfile } from '@/types';

type Tab = 'unclaimed' | 'my_reviews' | 'completed';

interface ProjectWithContracts extends Project {
  contracts?: Contract[];
}

export default function ReviewPage() {
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(true);
  const [userProfile, setUserProfile] = useState<UserProfile | null>(null);
  const [projects, setProjects] = useState<ProjectWithContracts[]>([]);
  const [activeTab, setActiveTab] = useState<Tab>('unclaimed');
  const [error, setError] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  const [stateFilter, setStateFilter] = useState('');
  const [claimLoading, setClaimLoading] = useState<string | null>(null);

  useEffect(() => {
    const checkAuth = async () => {
      try {
        const user = await getCurrentUser();
        if (!user) {
          router.push('/');
          return;
        }

        // Role guard: executive/admin only
        try {
          const profile = await authAPI.getCurrentUserProfile();
          if (profile.role !== 'executive' && profile.role !== 'admin') {
            router.push('/dashboard');
            return;
          }
          setUserProfile(profile);
        } catch {
          router.push('/dashboard');
          return;
        }

        await loadProjects();
      } catch (error) {
        console.error('[Review] Error loading review page:', error);
        router.push('/');
      } finally {
        setIsLoading(false);
      }
    };

    checkAuth();
  }, [router]);

  const loadProjects = async () => {
    try {
      const allProjects = await projectsAPI.list();

      const projectsWithContracts = await Promise.all(
        allProjects.map(async (project) => {
          try {
            const contracts = await contractsAPI.listByProject(project.id);
            return { ...project, contracts };
          } catch {
            return { ...project, contracts: [] };
          }
        })
      );

      setProjects(projectsWithContracts);
    } catch (error: any) {
      setError(error.response?.data?.detail || error.message || 'Failed to load projects');
    }
  };

  const handleClaim = async (projectId: string) => {
    setClaimLoading(projectId);
    try {
      await projectsAPI.claim(projectId);
      setSuccessMessage('Review started!');
      setTimeout(() => setSuccessMessage(''), 3000);
      await loadProjects();
      setActiveTab('my_reviews');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to begin review');
      setTimeout(() => setError(''), 3000);
    } finally {
      setClaimLoading(null);
    }
  };

  const formatDate = (dateString: string | undefined) => {
    if (!dateString) return '';
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  const unclaimed = projects.filter(
    (p) => p.status === 'submitted' && !p.claimed_by_id && (!stateFilter || p.state === stateFilter)
  );
  const myReviews = projects.filter(
    (p) => p.claimed_by_id === userProfile?.id && p.status === 'in_review' && (!stateFilter || p.state === stateFilter)
  );
  const completed = projects.filter(
    (p) =>
      p.claimed_by_id === userProfile?.id &&
      (p.status === 'approved' || p.status === 'rejected') &&
      (!stateFilter || p.state === stateFilter)
  );

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
          <div className="mb-8">
            <h1 className="text-3xl font-bold text-gray-900">Executive Review</h1>
            <p className="mt-2 text-sm text-gray-600">
              Review and approve submitted projects
            </p>
          </div>

          {successMessage && (
            <div className="mb-4 rounded-md bg-green-50 p-4">
              <p className="text-sm font-medium text-green-800">{successMessage}</p>
            </div>
          )}

          {error && (
            <div className="mb-4 rounded-md bg-red-50 p-4">
              <div className="text-sm text-red-800">{error}</div>
            </div>
          )}

          {/* State Filter */}
          <div className="mb-4">
            <StateFilter value={stateFilter} onChange={setStateFilter} />
          </div>

          {/* Tabs */}
          <div className="border-b border-gray-200 mb-6">
            <nav className="-mb-px flex space-x-8">
              <button
                onClick={() => setActiveTab('unclaimed')}
                className={`whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm ${
                  activeTab === 'unclaimed'
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                Available ({unclaimed.length})
              </button>
              <button
                onClick={() => setActiveTab('my_reviews')}
                className={`whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm ${
                  activeTab === 'my_reviews'
                    ? 'border-purple-500 text-purple-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                My Reviews ({myReviews.length})
              </button>
              <button
                onClick={() => setActiveTab('completed')}
                className={`whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm ${
                  activeTab === 'completed'
                    ? 'border-green-500 text-green-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                Completed ({completed.length})
              </button>
            </nav>
          </div>

          {/* Tab Content */}
          <div className="bg-white shadow rounded-lg overflow-hidden">
            {activeTab === 'unclaimed' && (
              <>
                {unclaimed.length === 0 ? (
                  <div className="text-center py-12">
                    <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    <h3 className="mt-2 text-sm font-medium text-gray-900">No available projects</h3>
                    <p className="mt-1 text-sm text-gray-500">
                      New submitted projects will appear here
                    </p>
                  </div>
                ) : (
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Project</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Project #</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Contracts</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Submitted</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Action</th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {unclaimed.map((project) => (
                        <tr key={project.id} className="hover:bg-gray-50">
                          <td className="px-6 py-4">
                            <div className="flex items-center gap-2">
                              <div className="text-sm font-medium text-gray-900">{project.project_name}</div>
                              <StateBadge state={project.state} />
                            </div>
                          </td>
                          <td className="px-6 py-4 text-sm text-gray-500">
                            {project.project_number}
                          </td>
                          <td className="px-6 py-4 text-sm text-gray-500">
                            {project.contracts?.length || 0}
                          </td>
                          <td className="px-6 py-4 text-sm text-gray-500">
                            {formatDate(project.submitted_at)}
                          </td>
                          <td className="px-6 py-4">
                            <button
                              onClick={() => handleClaim(project.id)}
                              disabled={claimLoading === project.id}
                              className="px-3 py-1 bg-purple-600 text-white rounded-md hover:bg-purple-700 text-sm font-medium disabled:opacity-50"
                            >
                              {claimLoading === project.id ? 'Starting...' : 'Begin Review'}
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </>
            )}

            {activeTab === 'my_reviews' && (
              <>
                {myReviews.length === 0 ? (
                  <div className="text-center py-12">
                    <h3 className="mt-2 text-sm font-medium text-gray-900">No active reviews</h3>
                    <p className="mt-1 text-sm text-gray-500">
                      Select a project from the Available tab to begin reviewing
                    </p>
                  </div>
                ) : (
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Project</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Project #</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Contracts</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Started</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Action</th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {myReviews.map((project) => (
                        <tr
                          key={project.id}
                          className="hover:bg-gray-50 cursor-pointer"
                          onClick={() => router.push(`/review/${project.id}`)}
                        >
                          <td className="px-6 py-4">
                            <div className="flex items-center gap-2">
                              <div className="text-sm font-medium text-gray-900">{project.project_name}</div>
                              <StateBadge state={project.state} />
                            </div>
                          </td>
                          <td className="px-6 py-4 text-sm text-gray-500">
                            {project.project_number}
                          </td>
                          <td className="px-6 py-4 text-sm text-gray-500">
                            {project.contracts?.length || 0}
                          </td>
                          <td className="px-6 py-4 text-sm text-gray-500">
                            {formatDate(project.claimed_at)}
                          </td>
                          <td className="px-6 py-4">
                            <span className="text-blue-600 hover:text-blue-900 text-sm font-medium">
                              Review
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </>
            )}

            {activeTab === 'completed' && (
              <>
                {completed.length === 0 ? (
                  <div className="text-center py-12">
                    <h3 className="mt-2 text-sm font-medium text-gray-900">No completed reviews</h3>
                    <p className="mt-1 text-sm text-gray-500">
                      Approved and rejected projects will appear here
                    </p>
                  </div>
                ) : (
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Project</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Project #</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Reviewed</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Action</th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {completed.map((project) => {
                        const statusCfg = getStatusConfig(project.status);
                        return (
                          <tr
                            key={project.id}
                            className="hover:bg-gray-50 cursor-pointer"
                            onClick={() => router.push(`/review/${project.id}`)}
                          >
                            <td className="px-6 py-4">
                              <div className="flex items-center gap-2">
                                <div className="text-sm font-medium text-gray-900">{project.project_name}</div>
                                <StateBadge state={project.state} />
                              </div>
                            </td>
                            <td className="px-6 py-4 text-sm text-gray-500">
                              {project.project_number}
                            </td>
                            <td className="px-6 py-4">
                              <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${statusCfg.className}`}>
                                {statusCfg.label}
                              </span>
                            </td>
                            <td className="px-6 py-4 text-sm text-gray-500">
                              {formatDate(project.reviewed_at)}
                            </td>
                            <td className="px-6 py-4">
                              <span className="text-blue-600 hover:text-blue-900 text-sm font-medium">
                                View
                              </span>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                )}
              </>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
