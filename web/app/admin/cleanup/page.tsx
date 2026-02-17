'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import Link from 'next/link';
import { getCurrentUser } from '@/lib/supabase';
import { adminAPI, authAPI } from '@/lib/api';
import Header from '@/components/Header';
import StateBadge from '@/components/StateBadge';
import StateFilter from '@/components/StateFilter';
import type { AdminContract, Submitter, UserProfile } from '@/types';

type Tab = 'active' | 'archived';
type SortField = 'project_name' | 'file_name' | 'submitter_name' | 'created_at' | 'analysis_status';
type SortDir = 'asc' | 'desc';

interface ConfirmDialog {
  open: boolean;
  action: 'archive' | 'delete' | 'restore';
  count: number;
}

interface ResetDialog {
  step: 'closed' | 'warning' | 'confirm';
}

interface ResetResult {
  red_flags_deleted: number;
  analyses_deleted: number;
  contracts_deleted: number;
  storage_files_removed: number;
  projects_reset: number;
  performed_by: string;
  performed_at: string;
}

export default function AdminCleanupPage() {
  const router = useRouter();
  const pathname = usePathname();
  const [isLoading, setIsLoading] = useState(true);
  const [userProfile, setUserProfile] = useState<UserProfile | null>(null);
  const [contracts, setContracts] = useState<AdminContract[]>([]);
  const [submitters, setSubmitters] = useState<Submitter[]>([]);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState(false);

  // Tab
  const [activeTab, setActiveTab] = useState<Tab>('active');

  // Filters
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [submitterFilter, setSubmitterFilter] = useState('');
  const [stateFilter, setStateFilter] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');

  // Sort
  const [sortField, setSortField] = useState<SortField>('created_at');
  const [sortDir, setSortDir] = useState<SortDir>('desc');

  // Confirmation dialog
  const [confirm, setConfirm] = useState<ConfirmDialog>({ open: false, action: 'archive', count: 0 });

  // Reset test data dialog
  const [resetDialog, setResetDialog] = useState<ResetDialog>({ step: 'closed' });
  const [resetConfirmText, setResetConfirmText] = useState('');
  const [resetLoading, setResetLoading] = useState(false);
  const [resetResult, setResetResult] = useState<ResetResult | null>(null);

  // Auth check
  useEffect(() => {
    const checkAuth = async () => {
      console.log('[AdminCleanup] Checking authentication...');
      const user = await getCurrentUser();
      if (!user) {
        console.log('[AdminCleanup] No user, redirecting to login');
        router.push('/');
        return;
      }
      try {
        const profile = await authAPI.getCurrentUserProfile();
        console.log('[AdminCleanup] Profile:', profile);
        if (profile.role !== 'executive' && profile.role !== 'admin') {
          console.log('[AdminCleanup] Insufficient role:', profile.role);
          router.push('/dashboard');
          return;
        }
        setUserProfile(profile);
      } catch (err) {
        console.error('[AdminCleanup] Auth error:', err);
        router.push('/');
      }
    };
    checkAuth();
  }, [router]);

  // Fetch contracts
  const fetchContracts = useCallback(async () => {
    if (!userProfile) return;
    setIsLoading(true);
    setError(null);
    try {
      const params: Record<string, string> = {
        archived: String(activeTab === 'archived'),
      };
      if (statusFilter) params.analysis_status = statusFilter;
      if (search) params.search = search;
      if (submitterFilter) params.submitter = submitterFilter;
      if (dateFrom) params.date_from = dateFrom;
      if (dateTo) params.date_to = dateTo;

      console.log('[AdminCleanup] Fetching contracts with params:', params);
      const data = await adminAPI.listContracts(params);
      setContracts(data);
      setSelectedIds(new Set());
    } catch (err: any) {
      console.error('[AdminCleanup] Error fetching contracts:', err);
      setError(err?.response?.data?.detail || 'Failed to load contracts');
    } finally {
      setIsLoading(false);
    }
  }, [userProfile, activeTab, statusFilter, search, submitterFilter, dateFrom, dateTo]);

  useEffect(() => {
    fetchContracts();
  }, [fetchContracts]);

  // Fetch submitters for filter dropdown
  useEffect(() => {
    if (!userProfile) return;
    adminAPI.listSubmitters()
      .then(setSubmitters)
      .catch(err => console.error('[AdminCleanup] Error fetching submitters:', err));
  }, [userProfile]);

  // Clear success message after 4s
  useEffect(() => {
    if (!successMsg) return;
    const t = setTimeout(() => setSuccessMsg(null), 4000);
    return () => clearTimeout(t);
  }, [successMsg]);

  // Sort logic
  const stateFiltered = stateFilter
    ? contracts.filter((c) => c.state === stateFilter)
    : contracts;
  const sorted = [...stateFiltered].sort((a, b) => {
    const aVal = (a[sortField] ?? '') as string;
    const bVal = (b[sortField] ?? '') as string;
    const cmp = aVal.localeCompare(bVal);
    return sortDir === 'asc' ? cmp : -cmp;
  });

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDir(prev => (prev === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortField(field);
      setSortDir('asc');
    }
  };

  const sortIcon = (field: SortField) => {
    if (sortField !== field) return ' \u2195';
    return sortDir === 'asc' ? ' \u2191' : ' \u2193';
  };

  // Selection
  const toggleSelect = (id: string) => {
    setSelectedIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleSelectAll = () => {
    if (selectedIds.size === sorted.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(sorted.map(c => c.id)));
    }
  };

  // Bulk actions
  const openConfirm = (action: ConfirmDialog['action']) => {
    setConfirm({ open: true, action, count: selectedIds.size });
  };

  const executeAction = async () => {
    const ids = Array.from(selectedIds);
    setConfirm({ ...confirm, open: false });
    setActionLoading(true);
    setError(null);
    try {
      if (confirm.action === 'archive') {
        const res = await adminAPI.archiveContracts(ids);
        setSuccessMsg(`Archived ${res.archived} contract${res.archived !== 1 ? 's' : ''}`);
      } else if (confirm.action === 'restore') {
        const res = await adminAPI.restoreContracts(ids);
        setSuccessMsg(`Restored ${res.restored} contract${res.restored !== 1 ? 's' : ''}`);
      } else if (confirm.action === 'delete') {
        const res = await adminAPI.deleteContracts(ids);
        setSuccessMsg(`Permanently deleted ${res.deleted} contract${res.deleted !== 1 ? 's' : ''}`);
      }
      await fetchContracts();
    } catch (err: any) {
      console.error('[AdminCleanup] Action error:', err);
      setError(err?.response?.data?.detail || `Failed to ${confirm.action} contracts`);
    } finally {
      setActionLoading(false);
    }
  };

  const executeReset = async () => {
    setResetLoading(true);
    setError(null);
    try {
      const result = await adminAPI.resetTestData('DELETE ALL');
      setResetResult(result);
      setResetDialog({ step: 'closed' });
      setResetConfirmText('');
      setSuccessMsg(
        `Reset complete: ${result.contracts_deleted} contracts, ${result.red_flags_deleted} red flags, ${result.analyses_deleted} analyses deleted. ${result.projects_reset} projects reset to draft.`
      );
      await fetchContracts();
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to reset test data');
      setResetDialog({ step: 'closed' });
      setResetConfirmText('');
    } finally {
      setResetLoading(false);
    }
  };

  const formatDate = (iso: string) => {
    try {
      return new Date(iso).toLocaleDateString('en-US', {
        month: 'short', day: 'numeric', year: 'numeric',
        hour: 'numeric', minute: '2-digit',
      });
    } catch {
      return iso;
    }
  };

  const statusBadge = (s: string) => {
    const colors: Record<string, string> = {
      completed: 'bg-green-100 text-green-800',
      pending: 'bg-yellow-100 text-yellow-800',
      error: 'bg-red-100 text-red-800',
    };
    return colors[s] || 'bg-gray-100 text-gray-800';
  };

  // Don't render until auth is confirmed
  if (!userProfile) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <p className="text-gray-500">Checking permissions...</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Header />
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Admin sub-nav */}
        <div className="border-b border-gray-200 mb-6">
          <nav className="flex space-x-8">
            <Link
              href="/admin/cleanup"
              className={`pb-3 px-1 text-sm font-medium border-b-2 ${
                pathname === '/admin/cleanup'
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Contract Cleanup
            </Link>
            {userProfile.role === 'admin' && (
              <>
                <Link
                  href="/admin/users"
                  className={`pb-3 px-1 text-sm font-medium border-b-2 ${
                    pathname === '/admin/users'
                      ? 'border-blue-600 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  User Management
                </Link>
                <Link
                  href="/admin/costs"
                  className={`pb-3 px-1 text-sm font-medium border-b-2 ${
                    pathname === '/admin/costs'
                      ? 'border-blue-600 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  Cost Tracking
                </Link>
                <Link
                  href="/admin/modules"
                  className={`pb-3 px-1 text-sm font-medium border-b-2 ${
                    pathname === '/admin/modules'
                      ? 'border-blue-600 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  Module Access
                </Link>
              </>
            )}
          </nav>
        </div>

        {/* Page header */}
        <div className="mb-6 flex justify-between items-start">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Contract Cleanup</h1>
            <p className="mt-1 text-sm text-gray-500">
              Manage, archive, or permanently remove submitted contracts.
            </p>
          </div>
          {userProfile.role === 'admin' && (
            <button
              onClick={() => setResetDialog({ step: 'warning' })}
              disabled={resetLoading}
              className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 text-sm font-medium disabled:opacity-50"
            >
              Clear All Test Data
            </button>
          )}
        </div>

        {/* Alerts */}
        {error && (
          <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
            {error}
          </div>
        )}
        {successMsg && (
          <div className="mb-4 p-4 bg-green-50 border border-green-200 rounded-lg text-green-700 text-sm">
            {successMsg}
          </div>
        )}

        {/* Tabs */}
        <div className="border-b border-gray-200 mb-6">
          <nav className="flex space-x-8">
            <button
              onClick={() => { setActiveTab('active'); setSelectedIds(new Set()); }}
              className={`pb-3 px-1 text-sm font-medium border-b-2 ${
                activeTab === 'active'
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Active Contracts
            </button>
            <button
              onClick={() => { setActiveTab('archived'); setSelectedIds(new Set()); }}
              className={`pb-3 px-1 text-sm font-medium border-b-2 ${
                activeTab === 'archived'
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Archived
            </button>
          </nav>
        </div>

        {/* Filters */}
        <div className="bg-white rounded-lg border border-gray-200 p-4 mb-4">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-6 gap-4">
            {/* Search */}
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">Search</label>
              <input
                type="text"
                placeholder="Project name or file..."
                value={search}
                onChange={e => setSearch(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>
            {/* Status */}
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">Status</label>
              <select
                value={statusFilter}
                onChange={e => setStatusFilter(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                <option value="">All statuses</option>
                <option value="pending">Pending</option>
                <option value="completed">Completed</option>
                <option value="error">Error</option>
              </select>
            </div>
            {/* Submitter */}
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">Submitter</label>
              <select
                value={submitterFilter}
                onChange={e => setSubmitterFilter(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                <option value="">All submitters</option>
                {submitters.map(s => (
                  <option key={s.id} value={s.full_name}>{s.full_name}</option>
                ))}
              </select>
            </div>
            {/* State */}
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">State</label>
              <StateFilter value={stateFilter} onChange={setStateFilter} />
            </div>
            {/* Date from */}
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">From</label>
              <input
                type="date"
                value={dateFrom}
                onChange={e => setDateFrom(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>
            {/* Date to */}
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">To</label>
              <input
                type="date"
                value={dateTo}
                onChange={e => setDateTo(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>
          </div>
          <div className="mt-3 flex justify-end">
            <button
              onClick={() => { setSearch(''); setStatusFilter(''); setSubmitterFilter(''); setStateFilter(''); setDateFrom(''); setDateTo(''); }}
              className="text-sm text-gray-500 hover:text-gray-700"
            >
              Clear filters
            </button>
          </div>
        </div>

        {/* Bulk action bar */}
        {selectedIds.size > 0 && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 mb-4 flex items-center justify-between">
            <span className="text-sm text-blue-800 font-medium">
              {selectedIds.size} contract{selectedIds.size !== 1 ? 's' : ''} selected
            </span>
            <div className="flex space-x-3">
              {activeTab === 'active' ? (
                <>
                  <button
                    onClick={() => openConfirm('archive')}
                    disabled={actionLoading}
                    className="px-4 py-1.5 text-sm font-medium bg-yellow-500 text-white rounded-md hover:bg-yellow-600 disabled:opacity-50"
                  >
                    Archive Selected
                  </button>
                  <button
                    onClick={() => openConfirm('delete')}
                    disabled={actionLoading}
                    className="px-4 py-1.5 text-sm font-medium bg-red-600 text-white rounded-md hover:bg-red-700 disabled:opacity-50"
                  >
                    Delete Selected
                  </button>
                </>
              ) : (
                <>
                  <button
                    onClick={() => openConfirm('restore')}
                    disabled={actionLoading}
                    className="px-4 py-1.5 text-sm font-medium bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50"
                  >
                    Restore Selected
                  </button>
                  <button
                    onClick={() => openConfirm('delete')}
                    disabled={actionLoading}
                    className="px-4 py-1.5 text-sm font-medium bg-red-600 text-white rounded-md hover:bg-red-700 disabled:opacity-50"
                  >
                    Delete Permanently
                  </button>
                </>
              )}
            </div>
          </div>
        )}

        {/* Table */}
        <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
          {isLoading ? (
            <div className="p-12 text-center text-gray-500">Loading contracts...</div>
          ) : sorted.length === 0 ? (
            <div className="p-12 text-center text-gray-500">
              {activeTab === 'archived' ? 'No archived contracts.' : 'No contracts match the current filters.'}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 w-10">
                      <input
                        type="checkbox"
                        checked={selectedIds.size === sorted.length && sorted.length > 0}
                        onChange={toggleSelectAll}
                        className="rounded border-gray-300"
                      />
                    </th>
                    <th
                      className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:text-gray-700"
                      onClick={() => handleSort('project_name')}
                    >
                      Project{sortIcon('project_name')}
                    </th>
                    <th
                      className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:text-gray-700"
                      onClick={() => handleSort('submitter_name')}
                    >
                      Submitter{sortIcon('submitter_name')}
                    </th>
                    <th
                      className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:text-gray-700"
                      onClick={() => handleSort('created_at')}
                    >
                      Submitted{sortIcon('created_at')}
                    </th>
                    <th
                      className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:text-gray-700"
                      onClick={() => handleSort('analysis_status')}
                    >
                      Status{sortIcon('analysis_status')}
                    </th>
                    <th
                      className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:text-gray-700"
                      onClick={() => handleSort('file_name')}
                    >
                      File{sortIcon('file_name')}
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {sorted.map(c => (
                    <tr key={c.id} className={`hover:bg-gray-50 ${selectedIds.has(c.id) ? 'bg-blue-50' : ''}`}>
                      <td className="px-4 py-3">
                        <input
                          type="checkbox"
                          checked={selectedIds.has(c.id)}
                          onChange={() => toggleSelect(c.id)}
                          className="rounded border-gray-300"
                        />
                      </td>
                      <td className="px-4 py-3 text-sm">
                        <div className="flex items-center gap-2">
                          <div className="font-medium text-gray-900">{c.project_name || 'Unnamed Project'}</div>
                          {c.state && <StateBadge state={c.state} />}
                        </div>
                        {c.project_number && (
                          <div className="text-gray-500 text-xs">#{c.project_number}</div>
                        )}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-700">
                        {c.submitter_name || 'Unknown'}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-500 whitespace-nowrap">
                        {formatDate(c.created_at)}
                      </td>
                      <td className="px-4 py-3">
                        <span className={`inline-flex px-2 py-0.5 text-xs font-medium rounded-full ${statusBadge(c.analysis_status)}`}>
                          {c.analysis_status}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-700 max-w-xs truncate" title={c.file_name}>
                        {c.file_name}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {!isLoading && sorted.length > 0 && (
            <div className="px-4 py-3 bg-gray-50 border-t border-gray-200 text-sm text-gray-500">
              {sorted.length} contract{sorted.length !== 1 ? 's' : ''}
            </div>
          )}
        </div>
      </main>

      {/* Reset Test Data dialog — Step 1: Warning */}
      {resetDialog.step === 'warning' && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="fixed inset-0 bg-black/50" onClick={() => setResetDialog({ step: 'closed' })} />
          <div className="relative bg-white rounded-lg shadow-xl max-w-md w-full mx-4 p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="flex-shrink-0 w-10 h-10 rounded-full bg-red-100 flex items-center justify-center">
                <svg className="w-6 h-6 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
                </svg>
              </div>
              <h3 className="text-lg font-semibold text-gray-900">Clear All Test Data</h3>
            </div>
            <p className="text-sm text-gray-600 mb-2">
              This will permanently delete:
            </p>
            <ul className="text-sm text-gray-600 mb-4 list-disc list-inside space-y-1">
              <li>All contracts and uploaded PDF files</li>
              <li>All analysis results and red flags</li>
              <li>All project statuses will be reset to draft</li>
            </ul>
            <p className="text-sm font-medium text-red-600 mb-4">
              User accounts, profiles, and roles will NOT be affected.
            </p>
            <div className="flex justify-end space-x-3">
              <button
                onClick={() => setResetDialog({ step: 'closed' })}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200"
              >
                Cancel
              </button>
              <button
                onClick={() => { setResetDialog({ step: 'confirm' }); setResetConfirmText(''); }}
                className="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-md hover:bg-red-700"
              >
                Continue
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Reset Test Data dialog — Step 2: Type to confirm */}
      {resetDialog.step === 'confirm' && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="fixed inset-0 bg-black/50" onClick={() => { setResetDialog({ step: 'closed' }); setResetConfirmText(''); }} />
          <div className="relative bg-white rounded-lg shadow-xl max-w-md w-full mx-4 p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">Confirm Reset</h3>
            <p className="text-sm text-gray-600 mb-4">
              Type <span className="font-mono font-bold text-red-600">DELETE ALL</span> to confirm this action. This cannot be undone.
            </p>
            <input
              type="text"
              value={resetConfirmText}
              onChange={(e) => setResetConfirmText(e.target.value)}
              placeholder="Type DELETE ALL"
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-red-500 mb-4"
              autoFocus
            />
            <div className="flex justify-end space-x-3">
              <button
                onClick={() => { setResetDialog({ step: 'closed' }); setResetConfirmText(''); }}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200"
              >
                Cancel
              </button>
              <button
                onClick={executeReset}
                disabled={resetConfirmText !== 'DELETE ALL' || resetLoading}
                className="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-md hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {resetLoading ? 'Resetting...' : 'Delete Everything'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Confirmation dialog */}
      {confirm.open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="fixed inset-0 bg-black/50" onClick={() => setConfirm({ ...confirm, open: false })} />
          <div className="relative bg-white rounded-lg shadow-xl max-w-md w-full mx-4 p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              {confirm.action === 'delete' ? 'Permanently Delete Contracts?' : confirm.action === 'archive' ? 'Archive Contracts?' : 'Restore Contracts?'}
            </h3>
            <p className="text-sm text-gray-600 mb-6">
              {confirm.action === 'delete'
                ? `This will permanently remove ${confirm.count} contract${confirm.count !== 1 ? 's' : ''} and their files from storage. This cannot be undone.`
                : confirm.action === 'archive'
                  ? `This will archive ${confirm.count} contract${confirm.count !== 1 ? 's' : ''}. They will be hidden from normal views but can be restored later.`
                  : `This will restore ${confirm.count} contract${confirm.count !== 1 ? 's' : ''} back to active status.`}
            </p>
            <div className="flex justify-end space-x-3">
              <button
                onClick={() => setConfirm({ ...confirm, open: false })}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200"
              >
                Cancel
              </button>
              <button
                onClick={executeAction}
                className={`px-4 py-2 text-sm font-medium text-white rounded-md ${
                  confirm.action === 'delete'
                    ? 'bg-red-600 hover:bg-red-700'
                    : confirm.action === 'archive'
                      ? 'bg-yellow-500 hover:bg-yellow-600'
                      : 'bg-green-600 hover:bg-green-700'
                }`}
              >
                {confirm.action === 'delete' ? 'Delete Permanently' : confirm.action === 'archive' ? 'Archive' : 'Restore'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
