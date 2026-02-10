'use client';

import { useEffect, useState, useCallback } from 'react';
import { useRouter, useParams } from 'next/navigation';
import Header from '@/components/Header';
import AnalysisResults from '@/components/AnalysisResults';
import { getCurrentUser, getSession } from '@/lib/supabase';
import { projectsAPI, contractsAPI, analysisAPI, authAPI } from '@/lib/api';
import { getStatusConfig } from '@/lib/statusUtils';
import StateBadge from '@/components/StateBadge';
import type { Project, Contract, RedFlag, UserProfile } from '@/types';

export default function ProjectReviewDetailPage() {
  const router = useRouter();
  const params = useParams();
  const projectId = params.projectId as string;

  const [isLoading, setIsLoading] = useState(true);
  const [userProfile, setUserProfile] = useState<UserProfile | null>(null);
  const [project, setProject] = useState<Project | null>(null);
  const [contracts, setContracts] = useState<Contract[]>([]);
  const [redFlagsMap, setRedFlagsMap] = useState<Record<string, RedFlag[]>>({});
  const [error, setError] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  const [actionLoading, setActionLoading] = useState('');
  const [showConfirm, setShowConfirm] = useState<'approve' | 'reject' | null>(null);

  // PDF modal state
  const [pdfModal, setPdfModal] = useState<{ fileName: string; contractId: string; pdfUrl: string } | null>(null);

  // Executive notes state per contract
  const [notesState, setNotesState] = useState<Record<string, string>>({});
  const [notesSaving, setNotesSaving] = useState<Record<string, boolean>>({});

  useEffect(() => {
    const loadData = async () => {
      try {
        const user = await getCurrentUser();
        if (!user) {
          router.push('/');
          return;
        }

        // Role guard
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

        // Load project
        const proj = await projectsAPI.get(projectId);
        setProject(proj);

        // Load contracts
        const contractsList = await contractsAPI.listByProject(projectId);
        setContracts(contractsList);

        // Initialize notes state
        const initialNotes: Record<string, string> = {};
        for (const c of contractsList) {
          initialNotes[c.id] = c.executive_notes || '';
        }
        setNotesState(initialNotes);

        // Load red flags for each contract
        const flagsMap: Record<string, RedFlag[]> = {};
        for (const c of contractsList) {
          try {
            const flags = await analysisAPI.listByContract(c.id);
            flagsMap[c.id] = flags;
          } catch {
            flagsMap[c.id] = [];
          }
        }
        setRedFlagsMap(flagsMap);
      } catch (error: any) {
        setError(error.response?.data?.detail || 'Failed to load project');
      } finally {
        setIsLoading(false);
      }
    };

    loadData();
  }, [projectId, router]);

  const handleSaveNotes = async (contractId: string) => {
    setNotesSaving((prev) => ({ ...prev, [contractId]: true }));
    try {
      await contractsAPI.updateExecutiveNotes(contractId, notesState[contractId] || '');
      setSuccessMessage('Notes saved');
      setTimeout(() => setSuccessMessage(''), 2000);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to save notes');
      setTimeout(() => setError(''), 3000);
    } finally {
      setNotesSaving((prev) => ({ ...prev, [contractId]: false }));
    }
  };

  const handleApprove = async () => {
    setShowConfirm(null);
    setActionLoading('approve');
    try {
      const updated = await projectsAPI.approve(projectId);
      setProject(updated);
      setSuccessMessage('Project approved!');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to approve project');
      setTimeout(() => setError(''), 3000);
    } finally {
      setActionLoading('');
    }
  };

  const handleReject = async () => {
    setShowConfirm(null);
    setActionLoading('reject');
    try {
      const updated = await projectsAPI.reject(projectId);
      setProject(updated);
      setSuccessMessage('Project rejected');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to reject project');
      setTimeout(() => setError(''), 3000);
    } finally {
      setActionLoading('');
    }
  };

  const handleUnclaim = async () => {
    setActionLoading('unclaim');
    try {
      await projectsAPI.unclaim(projectId);
      router.push('/review');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to release project');
      setTimeout(() => setError(''), 3000);
    } finally {
      setActionLoading('');
    }
  };

  const openPdfModal = useCallback(async (contractId: string, fileName: string) => {
    const session = await getSession();
    if (!session?.access_token) {
      setError('Session expired. Please log in again.');
      setTimeout(() => setError(''), 3000);
      return;
    }
    const baseUrl = contractsAPI.getPdfUrl(contractId);
    const pdfUrl = `${baseUrl}?token=${encodeURIComponent(session.access_token)}`;
    setPdfModal({ fileName, contractId, pdfUrl });
  }, []);

  // Close PDF modal on ESC key
  useEffect(() => {
    if (!pdfModal) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setPdfModal(null);
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [pdfModal]);

  const isClaimedByMe = project?.claimed_by_id === userProfile?.id;
  const isInReview = project?.status === 'in_review';
  const canTakeAction = isClaimedByMe && isInReview;

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-gray-600">Loading project review...</div>
      </div>
    );
  }

  if (!project) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Header />
        <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
          <div className="px-4 py-6">
            <div className="rounded-md bg-red-50 p-4">
              <div className="text-sm text-red-800">{error || 'Project not found'}</div>
            </div>
            <button onClick={() => router.push('/review')} className="mt-4 text-blue-600 hover:text-blue-900">
              Back to Review
            </button>
          </div>
        </main>
      </div>
    );
  }

  const statusCfg = getStatusConfig(project.status);

  return (
    <div className="min-h-screen bg-gray-50">
      <Header />
      <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <div className="px-4 py-6 sm:px-0">
          {/* Back link */}
          <button
            onClick={() => router.push('/review')}
            className="text-blue-600 hover:text-blue-900 mb-4 text-sm"
          >
            Back to Executive Review
          </button>

          {/* Project Header */}
          <div className="bg-white shadow rounded-lg p-6 mb-6">
            <div className="flex justify-between items-start">
              <div>
                <div className="flex items-center gap-3">
                  <h1 className="text-2xl font-bold text-gray-900">{project.project_name}</h1>
                  <StateBadge state={project.state} size="md" />
                </div>
                <p className="text-sm text-gray-600 mt-1">#{project.project_number}</p>
              </div>
              <span className={`px-3 py-1 rounded-full text-sm font-medium ${statusCfg.className}`}>
                {statusCfg.label}
              </span>
            </div>
            {project.pm_notes && (
              <div className="mt-4 p-3 bg-gray-50 rounded-md">
                <p className="text-xs font-medium text-gray-500 mb-1">PM Notes</p>
                <p className="text-sm text-gray-700">{project.pm_notes}</p>
              </div>
            )}
            <div className="mt-3 flex gap-4 text-xs text-gray-500">
              {project.submitted_at && (
                <span>Submitted: {new Date(project.submitted_at).toLocaleDateString()}</span>
              )}
              {project.claimed_at && (
                <span>Started: {new Date(project.claimed_at).toLocaleDateString()}</span>
              )}
              {project.reviewed_at && (
                <span>Reviewed: {new Date(project.reviewed_at).toLocaleDateString()}</span>
              )}
            </div>
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

          {/* Contracts */}
          <div className="space-y-6">
            {contracts.map((contract) => {
              const flags = redFlagsMap[contract.id] || [];
              return (
                <div key={contract.id} className="bg-white shadow rounded-lg p-6">
                  <div className="flex justify-between items-start mb-4">
                    <div>
                      <div className="flex items-center gap-2">
                        <button
                          onClick={(e) => { e.stopPropagation(); openPdfModal(contract.id, contract.file_name); }}
                          className="text-lg font-semibold text-blue-600 hover:text-blue-800 hover:underline text-left"
                          title="View Original PDF"
                        >
                          {contract.file_name}
                        </button>
                        <button
                          onClick={(e) => { e.stopPropagation(); openPdfModal(contract.id, contract.file_name); }}
                          className="text-blue-500 hover:text-blue-700"
                          title="View Original PDF"
                        >
                          <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                            <path d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" />
                            <path fillRule="evenodd" d="M8 11a1 1 0 011-1h2a1 1 0 110 2H9a1 1 0 01-1-1zm0-3a1 1 0 011-1h4a1 1 0 110 2H9a1 1 0 01-1-1z" clipRule="evenodd" />
                          </svg>
                        </button>
                      </div>
                      <div className="flex gap-3 mt-1">
                        <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-blue-100 text-blue-800">
                          {contract.contract_type}
                        </span>
                        <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                          contract.analysis_status === 'completed'
                            ? 'bg-green-100 text-green-800'
                            : 'bg-yellow-100 text-yellow-800'
                        }`}>
                          {contract.analysis_status}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Analysis Results */}
                  {contract.analysis_results && (
                    <div className="mb-4">
                      <h3 className="text-sm font-medium text-gray-700 mb-2">AI Analysis</h3>
                      <AnalysisResults analysisResults={contract.analysis_results} compact />
                    </div>
                  )}

                  {/* Red Flags */}
                  {flags.length > 0 && (
                    <div className="mb-4">
                      <h3 className="text-sm font-medium text-gray-700 mb-2">
                        Red Flags ({flags.length})
                      </h3>
                      <div className="space-y-3">
                        {flags.map((flag) => (
                          <div
                            key={flag.id}
                            className={`border-l-4 p-3 ${
                              flag.severity === 'critical' ? 'border-red-500 bg-red-50' :
                              flag.severity === 'high' ? 'border-orange-500 bg-orange-50' :
                              flag.severity === 'medium' ? 'border-yellow-500 bg-yellow-50' :
                              'border-blue-500 bg-blue-50'
                            }`}
                          >
                            <div className="flex items-center gap-2 mb-1">
                              <span className="text-sm font-medium text-gray-900">{flag.issue_title}</span>
                              <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                                flag.severity === 'critical' ? 'bg-red-100 text-red-800' :
                                flag.severity === 'high' ? 'bg-orange-100 text-orange-800' :
                                flag.severity === 'medium' ? 'bg-yellow-100 text-yellow-800' :
                                'bg-blue-100 text-blue-800'
                              }`}>
                                {flag.severity}
                              </span>
                            </div>
                            <p className="text-sm text-gray-700">{flag.details}</p>
                            {flag.location && (
                              <p className="text-xs text-gray-500 mt-1">Location: {flag.location}</p>
                            )}
                            {flag.recommendation && (
                              <p className="text-xs text-gray-600 mt-1">Recommendation: {flag.recommendation}</p>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Executive Notes */}
                  <div>
                    <h3 className="text-sm font-medium text-gray-700 mb-2">Executive Notes</h3>
                    {canTakeAction ? (
                      <div className="flex gap-2">
                        <textarea
                          value={notesState[contract.id] || ''}
                          onChange={(e) =>
                            setNotesState((prev) => ({ ...prev, [contract.id]: e.target.value }))
                          }
                          rows={3}
                          placeholder="Add your notes about this contract..."
                          className="flex-1 rounded-md border-gray-300 shadow-sm focus:border-purple-500 focus:ring-purple-500 sm:text-sm"
                        />
                        <button
                          onClick={() => handleSaveNotes(contract.id)}
                          disabled={notesSaving[contract.id]}
                          className="self-end px-4 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700 text-sm font-medium disabled:opacity-50"
                        >
                          {notesSaving[contract.id] ? 'Saving...' : 'Save'}
                        </button>
                      </div>
                    ) : contract.executive_notes ? (
                      <div className="bg-purple-50 rounded-md p-3">
                        <p className="text-sm text-gray-700">{contract.executive_notes}</p>
                        {contract.executive_notes_at && (
                          <p className="text-xs text-gray-500 mt-1">
                            {new Date(contract.executive_notes_at).toLocaleDateString()}
                          </p>
                        )}
                      </div>
                    ) : (
                      <p className="text-sm text-gray-400 italic">No notes added</p>
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Action Footer */}
          {canTakeAction && (
            <div className="mt-8 bg-white shadow rounded-lg p-6">
              <div className="flex justify-between items-center">
                <button
                  onClick={handleUnclaim}
                  disabled={!!actionLoading}
                  className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50"
                >
                  {actionLoading === 'unclaim' ? 'Releasing...' : 'Release Review'}
                </button>
                <div className="flex gap-3">
                  <button
                    onClick={() => setShowConfirm('reject')}
                    disabled={!!actionLoading}
                    className="px-6 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 text-sm font-medium disabled:opacity-50"
                  >
                    Reject Project
                  </button>
                  <button
                    onClick={() => setShowConfirm('approve')}
                    disabled={!!actionLoading}
                    className="px-6 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 text-sm font-medium disabled:opacity-50"
                  >
                    Approve Project
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </main>

      {/* PDF Viewer Modal */}
      {pdfModal && (
        <div className="fixed inset-0 z-50 flex flex-col bg-black bg-opacity-75">
          {/* Header bar */}
          <div className="flex items-center justify-between px-4 py-3 bg-gray-900 text-white shrink-0">
            <h3 className="text-sm font-medium truncate">{pdfModal.fileName}</h3>
            <button
              onClick={() => setPdfModal(null)}
              className="ml-4 p-1 rounded hover:bg-gray-700 text-gray-300 hover:text-white"
              title="Close (ESC)"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          {/* PDF iframe */}
          <iframe
            src={pdfModal.pdfUrl}
            className="flex-1 w-full bg-white"
            title={`PDF: ${pdfModal.fileName}`}
          />
        </div>
      )}

      {/* Confirmation Dialog */}
      {showConfirm && (
        <div className="fixed inset-0 z-50 overflow-y-auto">
          <div className="fixed inset-0 bg-gray-500 bg-opacity-75" onClick={() => setShowConfirm(null)}></div>
          <div className="flex min-h-full items-center justify-center p-4">
            <div className="relative bg-white rounded-lg shadow-xl max-w-sm w-full p-6">
              <h3 className="text-lg font-medium text-gray-900 mb-2">
                {showConfirm === 'approve' ? 'Approve Project?' : 'Reject Project?'}
              </h3>
              <p className="text-sm text-gray-500 mb-4">
                {showConfirm === 'approve'
                  ? 'This will mark the project as approved. The PM will be notified.'
                  : 'This will mark the project as rejected. The PM will be notified.'}
              </p>
              <div className="flex justify-end gap-3">
                <button
                  onClick={() => setShowConfirm(null)}
                  className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  onClick={showConfirm === 'approve' ? handleApprove : handleReject}
                  className={`px-4 py-2 rounded-md text-sm font-medium text-white ${
                    showConfirm === 'approve'
                      ? 'bg-green-600 hover:bg-green-700'
                      : 'bg-red-600 hover:bg-red-700'
                  }`}
                >
                  {showConfirm === 'approve' ? 'Approve' : 'Reject'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
