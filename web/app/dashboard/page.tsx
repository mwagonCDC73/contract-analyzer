'use client';

import { useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import Header from '@/components/Header';
import StateBadge from '@/components/StateBadge';
import StateFilter from '@/components/StateFilter';
import { getCurrentUser } from '@/lib/supabase';
import { projectsAPI, contractsAPI, authAPI } from '@/lib/api';
import { getStatusConfig } from '@/lib/statusUtils';
import type { Project, Contract, UserProfile } from '@/types';

interface ProjectWithContracts extends Project {
  contracts?: Contract[];
}

export default function DashboardPage() {
  const router = useRouter();
  const [user, setUser] = useState<any>(null);
  const [userProfile, setUserProfile] = useState<UserProfile | null>(null);
  const [projects, setProjects] = useState<ProjectWithContracts[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // New Project Modal state
  const [showModal, setShowModal] = useState(false);
  const [projectName, setProjectName] = useState('');
  const [projectNumber, setProjectNumber] = useState('');
  const [projectNotes, setProjectNotes] = useState('');
  const [projectState, setProjectState] = useState('CA');
  const [isCreating, setIsCreating] = useState(false);
  const [error, setError] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  const [claimLoading, setClaimLoading] = useState<string | null>(null);
  const [sortBy, setSortBy] = useState('name-asc');
  const [stateFilter, setStateFilter] = useState('');

  useEffect(() => {
    const checkAuth = async () => {
      try {
        const currentUser = await getCurrentUser();
        if (!currentUser) {
          router.push('/');
          return;
        }
        setUser(currentUser);

        // Fetch profile for role
        try {
          const profile = await authAPI.getCurrentUserProfile();
          setUserProfile(profile);
        } catch {
          // Profile fetch failed, continue with basic view
        }

        await loadProjects();
      } catch (error) {
        console.error('[Dashboard] Error loading dashboard:', error);
        router.push('/');
      } finally {
        setIsLoading(false);
      }
    };

    checkAuth();
  }, [router]);

  const loadProjects = async () => {
    try {
      const userProjects = await projectsAPI.list();

      const projectsWithContracts = await Promise.all(
        userProjects.map(async (project) => {
          try {
            const contracts = await contractsAPI.listByProject(project.id);
            return { ...project, contracts };
          } catch {
            return { ...project, contracts: [] };
          }
        })
      );

      setProjects(projectsWithContracts);
    } catch (error) {
      console.error('[Dashboard] Error loading projects:', error);
    }
  };

  const openModal = () => {
    setShowModal(true);
    setProjectName('');
    setProjectNumber('');
    setProjectState('CA');
    setProjectNotes('');
    setError('');
  };

  const closeModal = () => {
    setShowModal(false);
    setProjectName('');
    setProjectNumber('');
    setProjectState('CA');
    setProjectNotes('');
    setError('');
  };

  const handleCreateProject = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsCreating(true);

    try {
      await projectsAPI.create({
        project_name: projectName,
        project_number: projectNumber,
        state: projectState,
        pm_notes: projectNotes || undefined,
      });

      setSuccessMessage(`Project "${projectName}" created successfully!`);
      setTimeout(() => setSuccessMessage(''), 3000);
      await loadProjects();
      closeModal();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to create project');
    } finally {
      setIsCreating(false);
    }
  };

  const handleClaim = async (projectId: string) => {
    setClaimLoading(projectId);
    try {
      await projectsAPI.claim(projectId);
      setSuccessMessage('Review started!');
      setTimeout(() => setSuccessMessage(''), 3000);
      await loadProjects();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to begin review');
      setTimeout(() => setError(''), 3000);
    } finally {
      setClaimLoading(null);
    }
  };

  const sortedProjects = useMemo(() => {
    const filtered = stateFilter
      ? projects.filter((p) => p.state === stateFilter)
      : projects;

    const statusOrder: Record<string, number> = {
      in_review: 0,
      submitted: 1,
      approved: 2,
      rejected: 3,
      draft: 4,
      processing: 5,
    };

    return [...filtered].sort((a, b) => {
      switch (sortBy) {
        case 'name-asc':
          return a.project_name.localeCompare(b.project_name, undefined, { sensitivity: 'base' });
        case 'name-desc':
          return b.project_name.localeCompare(a.project_name, undefined, { sensitivity: 'base' });
        case 'date-newest':
          return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
        case 'date-oldest':
          return new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
        case 'status':
          return (statusOrder[a.status] ?? 99) - (statusOrder[b.status] ?? 99);
        default:
          return 0;
      }
    });
  }, [projects, sortBy, stateFilter]);

  const role = userProfile?.role;
  const isExec = role === 'executive' || role === 'admin';

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
            <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
            <p className="mt-2 text-sm text-gray-600">
              Welcome back, {userProfile?.full_name || user?.email}
            </p>
          </div>

          {successMessage && (
            <div className="mb-4 rounded-md bg-green-50 p-4">
              <div className="flex">
                <div className="flex-shrink-0">
                  <svg className="h-5 w-5 text-green-400" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                  </svg>
                </div>
                <div className="ml-3">
                  <p className="text-sm font-medium text-green-800">{successMessage}</p>
                </div>
              </div>
            </div>
          )}

          {error && (
            <div className="mb-4 rounded-md bg-red-50 p-4">
              <div className="text-sm text-red-800">{error}</div>
            </div>
          )}

          {/* Executive View */}
          {isExec ? (
            <div className="space-y-8">
              {/* Unclaimed projects awaiting review */}
              <div className="bg-white shadow rounded-lg p-6">
                <h2 className="text-xl font-semibold text-gray-900 mb-4">Projects Awaiting Review</h2>
                {(() => {
                  const unclaimed = projects.filter(
                    (p) => p.status === 'submitted' && !p.claimed_by_id
                  );
                  if (unclaimed.length === 0) {
                    return (
                      <p className="text-sm text-gray-500 py-4">
                        No projects are currently awaiting review.
                      </p>
                    );
                  }
                  return (
                    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                      {unclaimed.map((project) => (
                        <div
                          key={project.id}
                          className="border border-gray-200 rounded-lg p-4"
                        >
                          <div className="flex justify-between items-start mb-2">
                            <div className="flex items-center gap-2">
                              <h3 className="text-lg font-medium text-gray-900">{project.project_name}</h3>
                              <StateBadge state={project.state} />
                            </div>
                            <span className={`text-xs px-2 py-1 rounded-full ${getStatusConfig(project.status).className}`}>
                              {getStatusConfig(project.status).label}
                            </span>
                          </div>
                          <p className="text-sm text-gray-600">#{project.project_number}</p>
                          <p className="text-sm text-gray-500 mt-1">
                            {project.contracts?.length || 0} contract(s)
                          </p>
                          {project.submitted_at && (
                            <p className="mt-1 text-xs text-gray-400">
                              Submitted {new Date(project.submitted_at).toLocaleDateString()}
                            </p>
                          )}
                          <button
                            onClick={() => handleClaim(project.id)}
                            disabled={claimLoading === project.id}
                            className="mt-3 w-full px-3 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700 text-sm font-medium disabled:opacity-50"
                          >
                            {claimLoading === project.id ? 'Starting...' : 'Begin Review'}
                          </button>
                        </div>
                      ))}
                    </div>
                  );
                })()}
              </div>

              {/* My Reviews */}
              <div className="bg-white shadow rounded-lg p-6">
                <h2 className="text-xl font-semibold text-gray-900 mb-4">My Reviews</h2>
                {(() => {
                  const myReviews = projects.filter(
                    (p) => p.claimed_by_id && p.claimed_by_id === userProfile?.id
                  );
                  if (myReviews.length === 0) {
                    return (
                      <p className="text-sm text-gray-500 py-4">
                        You haven't started reviewing any projects yet.
                      </p>
                    );
                  }

                  const inReview = myReviews.filter((p) => p.status === 'in_review');
                  const completed = myReviews.filter((p) => p.status === 'approved' || p.status === 'rejected');

                  return (
                    <div className="space-y-6">
                      {inReview.length > 0 && (
                        <div>
                          <h3 className="text-sm font-medium text-gray-700 mb-3">In Progress</h3>
                          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                            {inReview.map((project) => (
                              <div
                                key={project.id}
                                onClick={() => router.push(`/review/${project.id}`)}
                                className="border border-purple-200 rounded-lg p-4 hover:border-purple-500 cursor-pointer transition-colors bg-purple-50"
                              >
                                <div className="flex justify-between items-start mb-2">
                                  <div className="flex items-center gap-2">
                                    <h3 className="text-lg font-medium text-gray-900">{project.project_name}</h3>
                                    <StateBadge state={project.state} />
                                  </div>
                                  <span className={`text-xs px-2 py-1 rounded-full ${getStatusConfig(project.status).className}`}>
                                    {getStatusConfig(project.status).label}
                                  </span>
                                </div>
                                <p className="text-sm text-gray-600">#{project.project_number}</p>
                                <p className="text-sm text-gray-500 mt-1">
                                  {project.contracts?.length || 0} contract(s)
                                </p>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                      {completed.length > 0 && (
                        <div>
                          <h3 className="text-sm font-medium text-gray-700 mb-3">Completed</h3>
                          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                            {completed.map((project) => (
                              <div
                                key={project.id}
                                onClick={() => router.push(`/review/${project.id}`)}
                                className="border border-gray-200 rounded-lg p-4 hover:border-gray-400 cursor-pointer transition-colors"
                              >
                                <div className="flex justify-between items-start mb-2">
                                  <div className="flex items-center gap-2">
                                    <h3 className="text-lg font-medium text-gray-900">{project.project_name}</h3>
                                    <StateBadge state={project.state} />
                                  </div>
                                  <span className={`text-xs px-2 py-1 rounded-full ${getStatusConfig(project.status).className}`}>
                                    {getStatusConfig(project.status).label}
                                  </span>
                                </div>
                                <p className="text-sm text-gray-600">#{project.project_number}</p>
                                {project.reviewed_at && (
                                  <p className="mt-1 text-xs text-gray-400">
                                    Reviewed {new Date(project.reviewed_at).toLocaleDateString()}
                                  </p>
                                )}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })()}
              </div>
            </div>
          ) : (
            /* PM/Admin View */
            <div className="bg-white shadow rounded-lg p-6">
              <div className="flex justify-between items-center mb-6">
                <h2 className="text-xl font-semibold text-gray-900">Your Projects</h2>
                <button
                  onClick={openModal}
                  className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 text-sm font-medium focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                >
                  New Project
                </button>
              </div>

              {projects.length > 0 && (
                <div className="mb-4 flex items-center gap-2">
                  <label htmlFor="sort-projects" className="text-sm text-gray-500">Sort by</label>
                  <select
                    id="sort-projects"
                    value={sortBy}
                    onChange={(e) => setSortBy(e.target.value)}
                    className="text-sm text-gray-600 border-gray-300 rounded-md shadow-sm focus:border-blue-500 focus:ring-blue-500"
                  >
                    <option value="name-asc">Project Name (A–Z)</option>
                    <option value="name-desc">Project Name (Z–A)</option>
                    <option value="date-newest">Date Created (Newest)</option>
                    <option value="date-oldest">Date Created (Oldest)</option>
                    <option value="status">Status</option>
                  </select>
                  <StateFilter value={stateFilter} onChange={setStateFilter} />
                </div>
              )}

              {projects.length === 0 ? (
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
                      d="M9 13h6m-3-3v6m-9 1V7a2 2 0 012-2h6l2 2h6a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2z"
                    />
                  </svg>
                  <h3 className="mt-2 text-sm font-medium text-gray-900">No projects</h3>
                  <p className="mt-1 text-sm text-gray-500">
                    Get started by creating a new project.
                  </p>
                  <button
                    onClick={openModal}
                    className="mt-4 inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                  >
                    Create Your First Project
                  </button>
                </div>
              ) : (
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                  {sortedProjects.map((project) => {
                    const statusCfg = getStatusConfig(project.status);
                    return (
                      <div
                        key={project.id}
                        onClick={() => {
                          if (project.contracts && project.contracts.length > 0) {
                            router.push(`/contract/${project.contracts[0].id}`);
                          } else if (project.status === 'draft') {
                            router.push(`/submit?projectId=${project.id}`);
                          } else {
                            router.push('/submissions');
                          }
                        }}
                        className="border border-gray-200 rounded-lg p-4 hover:border-blue-500 cursor-pointer transition-colors"
                      >
                        <div className="flex justify-between items-start mb-2">
                          <div className="flex items-center gap-2">
                            <h3 className="text-lg font-medium text-gray-900">{project.project_name}</h3>
                            <StateBadge state={project.state} />
                          </div>
                          <span className={`text-xs px-2 py-1 rounded-full ${statusCfg.className}`}>
                            {statusCfg.label}
                          </span>
                        </div>
                        <p className="text-sm text-gray-600">#{project.project_number}</p>
                        {project.pm_notes && (
                          <p className="mt-2 text-sm text-gray-500">{project.pm_notes}</p>
                        )}
                        {project.claimed_by_name && (
                          <p className="mt-1 text-xs text-purple-600">
                            Reviewer: {project.claimed_by_name}
                          </p>
                        )}
                        <p className="mt-2 text-xs text-gray-400">
                          Created {new Date(project.created_at).toLocaleDateString()}
                        </p>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}
        </div>
      </main>

      {/* New Project Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 overflow-y-auto" style={{display: 'block'}}>
          <div
            className="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity"
            onClick={closeModal}
          ></div>

          <div className="flex min-h-full items-center justify-center p-4">
            <div className="relative bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all w-full max-w-lg">
              <form onSubmit={handleCreateProject}>
                <div className="bg-white px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
                  <div className="sm:flex sm:items-start">
                    <div className="mt-3 text-center sm:mt-0 sm:text-left w-full">
                      <h3 className="text-lg leading-6 font-medium text-gray-900 mb-4">
                        Create New Project
                      </h3>

                      <div className="space-y-4">
                        <div>
                          <label htmlFor="project-name" className="block text-sm font-medium text-gray-700">
                            Project Name *
                          </label>
                          <input
                            type="text"
                            id="project-name"
                            value={projectName}
                            onChange={(e) => setProjectName(e.target.value)}
                            placeholder="e.g., Mission Valley Construction"
                            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                            required
                          />
                        </div>

                        <div>
                          <label htmlFor="project-number" className="block text-sm font-medium text-gray-700">
                            Project Number *
                          </label>
                          <input
                            type="text"
                            id="project-number"
                            value={projectNumber}
                            onChange={(e) => setProjectNumber(e.target.value)}
                            placeholder="e.g., 2026-150"
                            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                            required
                          />
                        </div>

                        <div>
                          <label htmlFor="project-state" className="block text-sm font-medium text-gray-700">
                            State *
                          </label>
                          <select
                            id="project-state"
                            value={projectState}
                            onChange={(e) => setProjectState(e.target.value)}
                            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                            required
                          >
                            <option value="CA">CA - California</option>
                            <option value="NV">NV - Nevada</option>
                          </select>
                        </div>

                        <div>
                          <label htmlFor="project-notes" className="block text-sm font-medium text-gray-700">
                            Notes (Optional)
                          </label>
                          <textarea
                            id="project-notes"
                            value={projectNotes}
                            onChange={(e) => setProjectNotes(e.target.value)}
                            rows={3}
                            placeholder="Add any notes about this project..."
                            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                          />
                        </div>

                        {error && (
                          <div className="rounded-md bg-red-50 p-4">
                            <div className="text-sm text-red-800">{error}</div>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                </div>

                <div className="bg-gray-50 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse">
                  <button
                    type="submit"
                    disabled={isCreating}
                    className="w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-blue-600 text-base font-medium text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 sm:ml-3 sm:w-auto sm:text-sm disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {isCreating ? 'Creating...' : 'Create Project'}
                  </button>
                  <button
                    type="button"
                    onClick={closeModal}
                    disabled={isCreating}
                    className="mt-3 w-full inline-flex justify-center rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 sm:mt-0 sm:ml-3 sm:w-auto sm:text-sm disabled:opacity-50"
                  >
                    Cancel
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
