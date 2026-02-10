'use client';

import { useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Header from '@/components/Header';
import { getCurrentUser } from '@/lib/supabase';
import { projectsAPI, contractsAPI, analysisAPI, authAPI } from '@/lib/api';
import type { Project, Contract, RedFlag } from '@/types';

type SubmissionStep = 'form' | 'uploading' | 'analyzing' | 'complete' | 'error';

export default function SubmitPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [isLoading, setIsLoading] = useState(true);
  const [projects, setProjects] = useState<Project[]>([]);

  // Form state
  const [selectedProjectId, setSelectedProjectId] = useState<string>('');
  const [createNewProject, setCreateNewProject] = useState(false);
  const [newProjectName, setNewProjectName] = useState('');
  const [newProjectNumber, setNewProjectNumber] = useState('');
  const [newProjectState, setNewProjectState] = useState('CA');
  const [primeContractFile, setPrimeContractFile] = useState<File | null>(null);
  const [subcontractFile, setSubcontractFile] = useState<File | null>(null);
  const [notes, setNotes] = useState('');

  // Submission state
  const [submissionStep, setSubmissionStep] = useState<SubmissionStep>('form');
  const [uploadProgress, setUploadProgress] = useState('');
  const [uploadedContracts, setUploadedContracts] = useState<Contract[]>([]);
  const [analysisResults, setAnalysisResults] = useState<any[]>([]);
  const [redFlags, setRedFlags] = useState<RedFlag[]>([]);
  const [error, setError] = useState('');

  useEffect(() => {
    console.log('[Submit] Component mounted, loading data...');
    const loadData = async () => {
      try {
        console.log('[Submit] Getting current user...');
        const user = await getCurrentUser();
        console.log('[Submit] Current user:', user);

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

        // Load existing projects
        console.log('[Submit] Loading projects list...');
        const projectsList = await projectsAPI.list();
        console.log('[Submit] Projects loaded:', projectsList.length, 'projects');
        setProjects(projectsList);

        // Pre-select project from URL query param
        const projectIdParam = searchParams.get('projectId');
        if (projectIdParam && projectsList.some((p) => p.id === projectIdParam)) {
          setSelectedProjectId(projectIdParam);
        }
      } catch (error) {
        console.error('[Submit] Error loading data:', error);
        router.push('/');
      } finally {
        setIsLoading(false);
        console.log('[Submit] Loading complete');
      }
    };

    loadData();
  }, [router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    console.log('[Submit] Form submitted');
    console.log('[Submit] Form data:', {
      createNewProject,
      selectedProjectId,
      newProjectName,
      newProjectNumber,
      primeContract: primeContractFile?.name,
      subcontract: subcontractFile?.name,
      notes,
    });

    setError('');

    // Validation
    if (!primeContractFile && !subcontractFile) {
      console.log('[Submit] Validation failed: No contracts uploaded');
      setError('Please upload at least one contract (Prime or Subcontract)');
      return;
    }

    if (!createNewProject && !selectedProjectId) {
      console.log('[Submit] Validation failed: No project selected');
      setError('Please select a project or create a new one');
      return;
    }

    if (createNewProject && (!newProjectName || !newProjectNumber)) {
      console.log('[Submit] Validation failed: Missing project name/number');
      setError('Please enter project name and number');
      return;
    }

    console.log('[Submit] Validation passed, starting submission...');

    try {
      setSubmissionStep('uploading');
      let projectId = selectedProjectId;

      // Create new project if needed
      if (createNewProject) {
        console.log('[Submit] Creating new project:', { newProjectName, newProjectNumber });
        setUploadProgress('Creating project...');
        const newProject = await projectsAPI.create({
          project_name: newProjectName,
          project_number: newProjectNumber,
          state: newProjectState,
          pm_notes: notes || undefined,
        });
        console.log('[Submit] Project created:', newProject);
        projectId = newProject.id;
      }

      console.log('[Submit] Using project ID:', projectId);
      const contracts: Contract[] = [];

      // Upload prime contract
      if (primeContractFile) {
        console.log('[Submit] Uploading prime contract:', primeContractFile.name);
        setUploadProgress('Uploading prime contract...');
        const contract = await contractsAPI.upload(primeContractFile, projectId, 'prime');
        console.log('[Submit] Prime contract uploaded:', contract);
        contracts.push(contract);
      }

      // Upload subcontract
      if (subcontractFile) {
        console.log('[Submit] Uploading subcontract:', subcontractFile.name);
        setUploadProgress('Uploading subcontract...');
        const contract = await contractsAPI.upload(subcontractFile, projectId, 'subcontract');
        console.log('[Submit] Subcontract uploaded:', contract);
        contracts.push(contract);
      }

      console.log('[Submit] All contracts uploaded:', contracts.length);
      setUploadedContracts(contracts);
      setSubmissionStep('analyzing');

      // Analyze each contract
      console.log('[Submit] Starting analysis phase...');
      const results = [];
      const allRedFlags: RedFlag[] = [];

      for (const contract of contracts) {
        console.log('[Submit] Analyzing contract:', contract.id, contract.contract_type);
        setUploadProgress(`Analyzing ${contract.contract_type} contract...`);

        const analysisResult = await analysisAPI.analyze({
          contract_id: contract.id,
          analysis_type: 'risk', // Use risk analysis by default
        });
        console.log('[Submit] Analysis complete for contract:', contract.id);
        console.log('[Submit] Analysis result:', analysisResult);
        results.push(analysisResult);

        // Fetch red flags for this contract
        try {
          console.log('[Submit] Fetching red flags for contract:', contract.id);
          const flags = await analysisAPI.listByContract(contract.id);
          console.log('[Submit] Red flags found:', flags.length);
          allRedFlags.push(...flags);
        } catch (err) {
          console.error('[Submit] Error fetching red flags:', err);
        }
      }

      console.log('[Submit] All analyses complete');
      console.log('[Submit] Total red flags:', allRedFlags.length);
      setAnalysisResults(results);
      setRedFlags(allRedFlags);
      setSubmissionStep('complete');

      // Update project notes if not creating new
      if (!createNewProject && notes) {
        try {
          await projectsAPI.update(projectId, { pm_notes: notes });
        } catch (err) {
          console.error('Error updating project notes:', err);
        }
      }

    } catch (err: any) {
      console.error('[Submit] Submission error:', err);
      console.error('[Submit] Error details:', {
        message: err.message,
        response: err.response?.data,
        status: err.response?.status,
        stack: err.stack,
      });
      setError(err.response?.data?.detail || err.message || 'Failed to submit contracts');
      setSubmissionStep('error');
    }
  };

  const resetForm = () => {
    setSelectedProjectId('');
    setCreateNewProject(false);
    setNewProjectName('');
    setNewProjectNumber('');
    setNewProjectState('CA');
    setPrimeContractFile(null);
    setSubcontractFile(null);
    setNotes('');
    setSubmissionStep('form');
    setUploadedContracts([]);
    setAnalysisResults([]);
    setRedFlags([]);
    setError('');
  };

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
            <h1 className="text-3xl font-bold text-gray-900">Submit Contract</h1>
            <p className="mt-2 text-sm text-gray-600">
              Upload contracts for AI-powered risk analysis
            </p>
          </div>

          {/* Form */}
          {submissionStep === 'form' && (
            <div className="bg-white shadow rounded-lg p-6">
              <form onSubmit={handleSubmit} className="max-w-3xl mx-auto space-y-6">
                {/* Project Selection */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Project
                  </label>

                  <div className="space-y-4">
                    {/* Existing Project */}
                    <div className="flex items-center">
                      <input
                        type="radio"
                        id="existing-project"
                        checked={!createNewProject}
                        onChange={() => setCreateNewProject(false)}
                        className="h-4 w-4 text-blue-600 focus:ring-blue-500"
                      />
                      <label htmlFor="existing-project" className="ml-2 block text-sm text-gray-900">
                        Select existing project
                      </label>
                    </div>

                    {!createNewProject && (
                      <select
                        value={selectedProjectId}
                        onChange={(e) => setSelectedProjectId(e.target.value)}
                        className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                        required={!createNewProject}
                      >
                        <option value="">Select a project...</option>
                        {projects.map((project) => (
                          <option key={project.id} value={project.id}>
                            {project.project_name} (#{project.project_number})
                          </option>
                        ))}
                      </select>
                    )}

                    {/* New Project */}
                    <div className="flex items-center">
                      <input
                        type="radio"
                        id="new-project"
                        checked={createNewProject}
                        onChange={() => setCreateNewProject(true)}
                        className="h-4 w-4 text-blue-600 focus:ring-blue-500"
                      />
                      <label htmlFor="new-project" className="ml-2 block text-sm text-gray-900">
                        Create new project
                      </label>
                    </div>

                    {createNewProject && (
                      <div className="ml-6 space-y-4">
                        <div>
                          <label className="block text-sm font-medium text-gray-700">
                            Project Name
                          </label>
                          <input
                            type="text"
                            value={newProjectName}
                            onChange={(e) => setNewProjectName(e.target.value)}
                            placeholder="e.g., Mission Valley Construction"
                            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                            required={createNewProject}
                          />
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-gray-700">
                            Project Number
                          </label>
                          <input
                            type="text"
                            value={newProjectNumber}
                            onChange={(e) => setNewProjectNumber(e.target.value)}
                            placeholder="e.g., 2026-150"
                            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                            required={createNewProject}
                          />
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-gray-700">
                            State
                          </label>
                          <select
                            value={newProjectState}
                            onChange={(e) => setNewProjectState(e.target.value)}
                            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                            required={createNewProject}
                          >
                            <option value="CA">CA - California</option>
                            <option value="NV">NV - Nevada</option>
                          </select>
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                {/* Prime Contract Upload */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Prime Contract (Optional)
                  </label>
                  <div className="mt-1 flex justify-center px-6 pt-5 pb-6 border-2 border-gray-300 border-dashed rounded-md hover:border-gray-400">
                    <div className="space-y-1 text-center">
                      {primeContractFile ? (
                        <div>
                          <p className="text-sm text-gray-900">{primeContractFile.name}</p>
                          <button
                            type="button"
                            onClick={() => setPrimeContractFile(null)}
                            className="mt-2 text-sm text-red-600 hover:text-red-500"
                          >
                            Remove
                          </button>
                        </div>
                      ) : (
                        <>
                          <svg className="mx-auto h-12 w-12 text-gray-400" stroke="currentColor" fill="none" viewBox="0 0 48 48">
                            <path d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" />
                          </svg>
                          <div className="flex text-sm text-gray-600">
                            <label className="relative cursor-pointer bg-white rounded-md font-medium text-blue-600 hover:text-blue-500 focus-within:outline-none">
                              <span>Upload a file</span>
                              <input
                                type="file"
                                accept=".pdf"
                                onChange={(e) => setPrimeContractFile(e.target.files?.[0] || null)}
                                className="sr-only"
                              />
                            </label>
                            <p className="pl-1">or drag and drop</p>
                          </div>
                          <p className="text-xs text-gray-500">PDF up to 10MB</p>
                        </>
                      )}
                    </div>
                  </div>
                </div>

                {/* Subcontract Upload */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Subcontract (Optional)
                  </label>
                  <div className="mt-1 flex justify-center px-6 pt-5 pb-6 border-2 border-gray-300 border-dashed rounded-md hover:border-gray-400">
                    <div className="space-y-1 text-center">
                      {subcontractFile ? (
                        <div>
                          <p className="text-sm text-gray-900">{subcontractFile.name}</p>
                          <button
                            type="button"
                            onClick={() => setSubcontractFile(null)}
                            className="mt-2 text-sm text-red-600 hover:text-red-500"
                          >
                            Remove
                          </button>
                        </div>
                      ) : (
                        <>
                          <svg className="mx-auto h-12 w-12 text-gray-400" stroke="currentColor" fill="none" viewBox="0 0 48 48">
                            <path d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" />
                          </svg>
                          <div className="flex text-sm text-gray-600">
                            <label className="relative cursor-pointer bg-white rounded-md font-medium text-blue-600 hover:text-blue-500 focus-within:outline-none">
                              <span>Upload a file</span>
                              <input
                                type="file"
                                accept=".pdf"
                                onChange={(e) => setSubcontractFile(e.target.files?.[0] || null)}
                                className="sr-only"
                              />
                            </label>
                            <p className="pl-1">or drag and drop</p>
                          </div>
                          <p className="text-xs text-gray-500">PDF up to 10MB</p>
                        </>
                      )}
                    </div>
                  </div>
                </div>

                {/* Notes */}
                <div>
                  <label className="block text-sm font-medium text-gray-700">
                    Notes (Optional)
                  </label>
                  <textarea
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    rows={3}
                    placeholder="Add any notes about this submission..."
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                  />
                </div>

                {/* Error Message */}
                {error && (
                  <div className="rounded-md bg-red-50 p-4">
                    <div className="text-sm text-red-800">{error}</div>
                  </div>
                )}

                {/* Submit Button */}
                <div className="flex justify-end space-x-3">
                  <button
                    type="button"
                    onClick={() => router.push('/dashboard')}
                    className="px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                  >
                    Submit for Analysis
                  </button>
                </div>
              </form>
            </div>
          )}

          {/* Loading State */}
          {(submissionStep === 'uploading' || submissionStep === 'analyzing') && (
            <div className="bg-white shadow rounded-lg p-6">
              <div className="max-w-3xl mx-auto text-center py-12">
                <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mb-4"></div>
                <h3 className="text-lg font-medium text-gray-900 mb-2">
                  {submissionStep === 'uploading' ? 'Uploading Contracts...' : 'Analyzing with AI...'}
                </h3>
                <p className="text-sm text-gray-600">{uploadProgress}</p>
                <p className="text-xs text-gray-500 mt-4">This may take a few moments</p>
              </div>
            </div>
          )}

          {/* Success/Results State */}
          {submissionStep === 'complete' && (
            <div className="space-y-6">
              {/* Success Message */}
              <div className="bg-green-50 border border-green-200 rounded-lg p-6">
                <div className="flex">
                  <div className="flex-shrink-0">
                    <svg className="h-6 w-6 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  </div>
                  <div className="ml-3">
                    <h3 className="text-lg font-medium text-green-800">Analysis Complete!</h3>
                    <p className="mt-2 text-sm text-green-700">
                      {uploadedContracts.length} contract(s) uploaded and analyzed successfully.
                    </p>
                  </div>
                </div>
              </div>

              {/* Uploaded Contracts */}
              <div className="bg-white shadow rounded-lg p-6">
                <h3 className="text-lg font-medium text-gray-900 mb-4">Uploaded Contracts</h3>
                <div className="space-y-3">
                  {uploadedContracts.map((contract) => (
                    <div key={contract.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-md">
                      <div>
                        <p className="text-sm font-medium text-gray-900">
                          {contract.contract_type === 'prime' ? 'Prime Contract' : 'Subcontract'}
                        </p>
                        <p className="text-xs text-gray-500">{contract.file_name}</p>
                      </div>
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                        {contract.analysis_status}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Red Flags */}
              {redFlags.length > 0 && (
                <div className="bg-white shadow rounded-lg p-6">
                  <h3 className="text-lg font-medium text-gray-900 mb-4">
                    Red Flags Found ({redFlags.length})
                  </h3>
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
                        <div className="flex items-start">
                          <div className="flex-1">
                            <div className="flex items-center">
                              <h4 className="text-sm font-medium text-gray-900">{flag.issue_title}</h4>
                              <span className={`ml-2 inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                                flag.severity === 'critical' ? 'bg-red-100 text-red-800' :
                                flag.severity === 'high' ? 'bg-orange-100 text-orange-800' :
                                flag.severity === 'medium' ? 'bg-yellow-100 text-yellow-800' :
                                'bg-blue-100 text-blue-800'
                              }`}>
                                {flag.severity}
                              </span>
                            </div>
                            <p className="mt-1 text-sm text-gray-700">{flag.details}</p>
                            <p className="mt-2 text-xs text-gray-600">
                              <span className="font-medium">Location:</span> {flag.location}
                            </p>
                            <p className="mt-2 text-xs text-gray-600">
                              <span className="font-medium">Recommendation:</span> {flag.recommendation}
                            </p>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Actions */}
              <div className="flex justify-end space-x-3">
                <button
                  onClick={resetForm}
                  className="px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
                >
                  Submit Another
                </button>
                <button
                  onClick={() => router.push('/dashboard')}
                  className="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700"
                >
                  Go to Dashboard
                </button>
              </div>
            </div>
          )}

          {/* Error State */}
          {submissionStep === 'error' && (
            <div className="bg-white shadow rounded-lg p-6">
              <div className="max-w-3xl mx-auto">
                <div className="rounded-md bg-red-50 p-4 mb-6">
                  <div className="flex">
                    <div className="flex-shrink-0">
                      <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                      </svg>
                    </div>
                    <div className="ml-3">
                      <h3 className="text-sm font-medium text-red-800">Submission Failed</h3>
                      <div className="mt-2 text-sm text-red-700">{error}</div>
                    </div>
                  </div>
                </div>
                <div className="flex justify-end space-x-3">
                  <button
                    onClick={resetForm}
                    className="px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
                  >
                    Try Again
                  </button>
                  <button
                    onClick={() => router.push('/dashboard')}
                    className="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700"
                  >
                    Go to Dashboard
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
