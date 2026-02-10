'use client';

import { useEffect, useState } from 'react';
import { useRouter, useParams } from 'next/navigation';
import Header from '@/components/Header';
import AnalysisResults from '@/components/AnalysisResults';
import { getCurrentUser } from '@/lib/supabase';
import { contractsAPI, analysisAPI, projectsAPI, authAPI } from '@/lib/api';
import { getStatusConfig } from '@/lib/statusUtils';
import type { Contract, RedFlag, Project, UserProfile } from '@/types';

export default function ContractDetailPage() {
  const router = useRouter();
  const params = useParams();
  const contractId = params.id as string;

  const [isLoading, setIsLoading] = useState(true);
  const [contract, setContract] = useState<Contract | null>(null);
  const [project, setProject] = useState<Project | null>(null);
  const [userProfile, setUserProfile] = useState<UserProfile | null>(null);
  const [redFlags, setRedFlags] = useState<RedFlag[]>([]);
  const [error, setError] = useState('');

  // Executive notes editing
  const [execNotes, setExecNotes] = useState('');
  const [notesSaving, setNotesSaving] = useState(false);
  const [notesSaved, setNotesSaved] = useState(false);

  useEffect(() => {
    const loadData = async () => {
      try {
        const user = await getCurrentUser();
        if (!user) {
          router.push('/');
          return;
        }

        // Get user profile
        try {
          const profile = await authAPI.getCurrentUserProfile();
          setUserProfile(profile);
        } catch {
          // continue
        }

        const contractData = await contractsAPI.get(contractId);
        setContract(contractData);
        setExecNotes(contractData.executive_notes || '');

        // Load project info
        try {
          const proj = await projectsAPI.get(contractData.project_id);
          setProject(proj);
        } catch {
          // Project info is optional for this view
        }

        // Load red flags
        try {
          const flags = await analysisAPI.listByContract(contractId);
          setRedFlags(flags);
        } catch {
          // Red flags are optional
        }
      } catch (error: any) {
        setError('Failed to load contract details');
      } finally {
        setIsLoading(false);
      }
    };

    loadData();
  }, [contractId, router]);

  const handleSaveNotes = async () => {
    setNotesSaving(true);
    try {
      const updated = await contractsAPI.updateExecutiveNotes(contractId, execNotes);
      setContract(updated);
      setNotesSaved(true);
      setTimeout(() => setNotesSaved(false), 2000);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to save notes');
      setTimeout(() => setError(''), 3000);
    } finally {
      setNotesSaving(false);
    }
  };

  const isExecWhoClaimedProject =
    userProfile &&
    project &&
    (userProfile.role === 'executive' || userProfile.role === 'admin') &&
    project.claimed_by_id === userProfile.id &&
    project.status === 'in_review';

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-gray-600">Loading contract details...</div>
      </div>
    );
  }

  if (error || !contract) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Header />
        <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
          <div className="px-4 py-6 sm:px-0">
            <div className="rounded-md bg-red-50 p-4">
              <div className="text-sm text-red-800">{error || 'Contract not found'}</div>
            </div>
            <button
              onClick={() => router.back()}
              className="mt-4 text-blue-600 hover:text-blue-900"
            >
              Go Back
            </button>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Header />
      <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <div className="px-4 py-6 sm:px-0">
          {/* Header */}
          <div className="mb-6">
            <button
              onClick={() => router.back()}
              className="text-blue-600 hover:text-blue-900 mb-4 text-sm"
            >
              Back
            </button>
            <h1 className="text-3xl font-bold text-gray-900">Contract Details</h1>
          </div>

          {/* Project Status Banner */}
          {project && (
            <div className="bg-white shadow rounded-lg p-4 mb-6">
              <div className="flex justify-between items-center">
                <div>
                  <p className="text-sm font-medium text-gray-900">{project.project_name}</p>
                  <p className="text-xs text-gray-500">#{project.project_number}</p>
                </div>
                <span className={`px-3 py-1 rounded-full text-sm font-medium ${getStatusConfig(project.status).className}`}>
                  {getStatusConfig(project.status).label}
                </span>
              </div>
              {project.claimed_by_name && (
                <p className="text-xs text-purple-600 mt-2">Reviewer: {project.claimed_by_name}</p>
              )}
            </div>
          )}

          {/* Contract Info Card */}
          <div className="bg-white shadow rounded-lg p-6 mb-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">Contract Information</h2>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-sm font-medium text-gray-500">File Name</p>
                <p className="mt-1 text-sm text-gray-900">{contract.file_name}</p>
              </div>
              <div>
                <p className="text-sm font-medium text-gray-500">Contract Type</p>
                <p className="mt-1 text-sm text-gray-900 capitalize">{contract.contract_type || 'prime'}</p>
              </div>
              <div>
                <p className="text-sm font-medium text-gray-500">Analysis Status</p>
                <span className={`mt-1 inline-flex px-2 py-1 text-xs leading-5 font-semibold rounded-full ${
                  contract.analysis_status === 'completed'
                    ? 'bg-green-100 text-green-800'
                    : contract.analysis_status === 'pending'
                    ? 'bg-yellow-100 text-yellow-800'
                    : 'bg-gray-100 text-gray-800'
                }`}>
                  {contract.analysis_status || 'pending'}
                </span>
              </div>
              <div>
                <p className="text-sm font-medium text-gray-500">Uploaded</p>
                <p className="mt-1 text-sm text-gray-900">
                  {new Date(contract.created_at).toLocaleDateString('en-US', {
                    year: 'numeric',
                    month: 'short',
                    day: 'numeric'
                  })}
                </p>
              </div>
            </div>
          </div>

          {/* Executive Notes */}
          {(contract.executive_notes || isExecWhoClaimedProject) && (
            <div className="bg-white shadow rounded-lg p-6 mb-6">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">Executive Notes</h2>
              {isExecWhoClaimedProject ? (
                <div className="space-y-3">
                  <textarea
                    value={execNotes}
                    onChange={(e) => setExecNotes(e.target.value)}
                    rows={4}
                    placeholder="Add your executive review notes..."
                    className="w-full rounded-md border-gray-300 shadow-sm focus:border-purple-500 focus:ring-purple-500 sm:text-sm"
                  />
                  <div className="flex items-center gap-3">
                    <button
                      onClick={handleSaveNotes}
                      disabled={notesSaving}
                      className="px-4 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700 text-sm font-medium disabled:opacity-50"
                    >
                      {notesSaving ? 'Saving...' : 'Save Notes'}
                    </button>
                    {notesSaved && (
                      <span className="text-sm text-green-600">Saved!</span>
                    )}
                  </div>
                </div>
              ) : (
                <div className="bg-purple-50 rounded-md p-4">
                  <p className="text-sm text-gray-700">{contract.executive_notes}</p>
                  {contract.executive_notes_at && (
                    <p className="text-xs text-gray-500 mt-2">
                      Added {new Date(contract.executive_notes_at).toLocaleDateString()}
                    </p>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Analysis Results */}
          {contract.analysis_results && (
            <div className="bg-white shadow rounded-lg p-6 mb-6">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">Analysis Results</h2>
              <AnalysisResults analysisResults={contract.analysis_results} />
            </div>
          )}

          {/* Red Flags */}
          {redFlags.length > 0 && (
            <div className="bg-white shadow rounded-lg p-6">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">
                Red Flags ({redFlags.length})
              </h2>
              <div className="space-y-4">
                {redFlags.map((flag) => (
                  <div
                    key={flag.id}
                    className={`border-l-4 p-4 ${
                      flag.severity === 'critical' ? 'border-red-500 bg-red-50' :
                      flag.severity === 'high' ? 'border-orange-500 bg-orange-50' :
                      flag.severity === 'medium' ? 'border-yellow-500 bg-yellow-50' :
                      'border-blue-500 bg-blue-50'
                    }`}
                  >
                    <div className="flex">
                      <div className="flex-1">
                        <div className="flex items-center">
                          <h4 className="text-sm font-medium text-gray-900">{flag.issue_title || 'Issue'}</h4>
                          {flag.severity && (
                            <span className={`ml-2 inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                              flag.severity === 'critical' ? 'bg-red-100 text-red-800' :
                              flag.severity === 'high' ? 'bg-orange-100 text-orange-800' :
                              flag.severity === 'medium' ? 'bg-yellow-100 text-yellow-800' :
                              'bg-blue-100 text-blue-800'
                            }`}>
                              {flag.severity}
                            </span>
                          )}
                        </div>
                        <p className="mt-1 text-sm text-gray-700">{flag.details}</p>
                        {flag.location && (
                          <p className="mt-2 text-xs text-gray-600">
                            <span className="font-medium">Location:</span> {flag.location}
                          </p>
                        )}
                        {flag.recommendation && (
                          <p className="mt-1 text-xs text-gray-600">
                            <span className="font-medium">Recommendation:</span> {flag.recommendation}
                          </p>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* No Analysis Yet */}
          {!contract.analysis_results && contract.analysis_status === 'pending' && (
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6">
              <div className="flex">
                <div className="flex-shrink-0">
                  <svg className="h-5 w-5 text-yellow-400" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                  </svg>
                </div>
                <div className="ml-3">
                  <h3 className="text-sm font-medium text-yellow-800">Analysis Pending</h3>
                  <p className="mt-2 text-sm text-yellow-700">
                    This contract is waiting to be analyzed. Analysis results will appear here once complete.
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
