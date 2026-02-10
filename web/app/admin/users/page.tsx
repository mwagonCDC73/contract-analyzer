'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import Link from 'next/link';
import { getCurrentUser } from '@/lib/supabase';
import { adminAPI, authAPI } from '@/lib/api';
import Header from '@/components/Header';
import type { AdminUser, UserProfile } from '@/types';

type SortField = 'full_name' | 'email' | 'role' | 'active' | 'created_at' | 'last_sign_in_at';
type SortDir = 'asc' | 'desc';

interface CreateForm {
  first_name: string;
  last_name: string;
  email: string;
  role: string;
}

interface EditForm {
  full_name: string;
  role: string;
}

export default function AdminUsersPage() {
  const router = useRouter();
  const pathname = usePathname();
  const [isLoading, setIsLoading] = useState(true);
  const [userProfile, setUserProfile] = useState<UserProfile | null>(null);
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState(false);

  // Search / filter
  const [search, setSearch] = useState('');
  const [roleFilter, setRoleFilter] = useState('');

  // Sort
  const [sortField, setSortField] = useState<SortField>('full_name');
  const [sortDir, setSortDir] = useState<SortDir>('asc');

  // Create modal
  const [showCreate, setShowCreate] = useState(false);
  const [createForm, setCreateForm] = useState<CreateForm>({
    first_name: '', last_name: '', email: '', role: 'project_manager',
  });
  const [createLoading, setCreateLoading] = useState(false);

  // Edit modal
  const [editUser, setEditUser] = useState<AdminUser | null>(null);
  const [editForm, setEditForm] = useState<EditForm>({ full_name: '', role: '' });
  const [editLoading, setEditLoading] = useState(false);

  // Reset password dialog
  const [resetPwUser, setResetPwUser] = useState<AdminUser | null>(null);
  const [resetPwLoading, setResetPwLoading] = useState(false);

  // Delete dialog
  const [deleteUser, setDeleteUser] = useState<AdminUser | null>(null);
  const [deleteConfirmEmail, setDeleteConfirmEmail] = useState('');
  const [deleteLoading, setDeleteLoading] = useState(false);

  // Auth check
  useEffect(() => {
    const checkAuth = async () => {
      const user = await getCurrentUser();
      if (!user) { router.push('/'); return; }
      try {
        const profile = await authAPI.getCurrentUserProfile();
        if (profile.role !== 'admin') {
          router.push('/dashboard');
          return;
        }
        setUserProfile(profile);
      } catch {
        router.push('/');
      }
    };
    checkAuth();
  }, [router]);

  // Fetch users
  const fetchUsers = useCallback(async () => {
    if (!userProfile) return;
    setIsLoading(true);
    setError(null);
    try {
      const params: Record<string, string> = {};
      if (search) params.search = search;
      if (roleFilter) params.role = roleFilter;
      const data = await adminAPI.listUsers(params);
      setUsers(data);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to load users');
    } finally {
      setIsLoading(false);
    }
  }, [userProfile, search, roleFilter]);

  useEffect(() => { fetchUsers(); }, [fetchUsers]);

  // Auto-clear messages
  useEffect(() => {
    if (!successMsg) return;
    const t = setTimeout(() => setSuccessMsg(null), 4000);
    return () => clearTimeout(t);
  }, [successMsg]);
  useEffect(() => {
    if (!error) return;
    const t = setTimeout(() => setError(null), 6000);
    return () => clearTimeout(t);
  }, [error]);

  // Sort logic
  const sorted = [...users].sort((a, b) => {
    const aVal = String((a as any)[sortField] ?? '');
    const bVal = String((b as any)[sortField] ?? '');
    const cmp = aVal.localeCompare(bVal);
    return sortDir === 'asc' ? cmp : -cmp;
  });

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDir(prev => prev === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDir('asc');
    }
  };

  const sortIcon = (field: SortField) => {
    if (sortField !== field) return ' \u2195';
    return sortDir === 'asc' ? ' \u2191' : ' \u2193';
  };

  // ── Create user ──
  const handleCreate = async () => {
    const fullName = `${createForm.first_name.trim()} ${createForm.last_name.trim()}`.trim();
    if (!fullName || !createForm.email.trim()) {
      setError('Name and email are required');
      return;
    }
    setCreateLoading(true);
    try {
      await adminAPI.createUser({
        email: createForm.email.trim(),
        full_name: fullName,
        role: createForm.role,
      });
      setSuccessMsg(`User ${createForm.email} created. Password setup email sent.`);
      setShowCreate(false);
      setCreateForm({ first_name: '', last_name: '', email: '', role: 'project_manager' });
      await fetchUsers();
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to create user');
    } finally {
      setCreateLoading(false);
    }
  };

  // ── Edit user ──
  const openEdit = (user: AdminUser) => {
    setEditUser(user);
    setEditForm({ full_name: user.full_name, role: user.role });
  };

  const handleEdit = async () => {
    if (!editUser) return;
    setEditLoading(true);
    try {
      await adminAPI.updateUser(editUser.id, {
        full_name: editForm.full_name.trim(),
        role: editForm.role,
      });
      setSuccessMsg('User updated');
      setEditUser(null);
      await fetchUsers();
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to update user');
    } finally {
      setEditLoading(false);
    }
  };

  // ── Toggle active ──
  const handleToggleActive = async (user: AdminUser) => {
    setActionLoading(true);
    try {
      const result = await adminAPI.toggleUserActive(user.id);
      setSuccessMsg(result.message);
      await fetchUsers();
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to toggle user status');
    } finally {
      setActionLoading(false);
    }
  };

  // ── Reset password ──
  const handleResetPassword = async () => {
    if (!resetPwUser) return;
    setResetPwLoading(true);
    try {
      const result = await adminAPI.resetUserPassword(resetPwUser.id);
      setSuccessMsg(result.message);
      setResetPwUser(null);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to send reset email');
    } finally {
      setResetPwLoading(false);
    }
  };

  // ── Delete user ──
  const handleDelete = async () => {
    if (!deleteUser) return;
    setDeleteLoading(true);
    try {
      const result = await adminAPI.deleteUser(deleteUser.id, deleteConfirmEmail);
      setSuccessMsg(result.message);
      setDeleteUser(null);
      setDeleteConfirmEmail('');
      await fetchUsers();
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to delete user');
    } finally {
      setDeleteLoading(false);
    }
  };

  // ── Helpers ──
  const formatDate = (iso?: string) => {
    if (!iso) return '-';
    try {
      return new Date(iso).toLocaleDateString('en-US', {
        month: 'short', day: 'numeric', year: 'numeric',
      });
    } catch { return iso; }
  };

  const formatDateTime = (iso?: string) => {
    if (!iso) return 'Never';
    try {
      return new Date(iso).toLocaleDateString('en-US', {
        month: 'short', day: 'numeric', year: 'numeric',
        hour: 'numeric', minute: '2-digit',
      });
    } catch { return iso; }
  };

  const roleBadge = (role: string) => {
    const colors: Record<string, string> = {
      admin: 'bg-red-100 text-red-800',
      executive: 'bg-purple-100 text-purple-800',
      project_manager: 'bg-blue-100 text-blue-800',
    };
    const labels: Record<string, string> = {
      admin: 'Admin',
      executive: 'Executive',
      project_manager: 'Project Manager',
    };
    return (
      <span className={`inline-flex px-2 py-0.5 text-xs font-medium rounded-full ${colors[role] || 'bg-gray-100 text-gray-800'}`}>
        {labels[role] || role}
      </span>
    );
  };

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
          </nav>
        </div>

        {/* Page header */}
        <div className="mb-6 flex justify-between items-start">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">User Management</h1>
            <p className="mt-1 text-sm text-gray-500">
              Create, edit, and manage user accounts and roles.
            </p>
          </div>
          <button
            onClick={() => setShowCreate(true)}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 text-sm font-medium"
          >
            Create User
          </button>
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

        {/* Filters */}
        <div className="bg-white rounded-lg border border-gray-200 p-4 mb-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">Search</label>
              <input
                type="text"
                placeholder="Name or email..."
                value={search}
                onChange={e => setSearch(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">Role</label>
              <select
                value={roleFilter}
                onChange={e => setRoleFilter(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                <option value="">All roles</option>
                <option value="project_manager">Project Manager</option>
                <option value="executive">Executive</option>
                <option value="admin">Admin</option>
              </select>
            </div>
            <div className="flex items-end">
              <button
                onClick={() => { setSearch(''); setRoleFilter(''); }}
                className="text-sm text-gray-500 hover:text-gray-700"
              >
                Clear filters
              </button>
            </div>
          </div>
        </div>

        {/* Users table */}
        <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
          {isLoading ? (
            <div className="p-12 text-center text-gray-500">Loading users...</div>
          ) : sorted.length === 0 ? (
            <div className="p-12 text-center text-gray-500">No users found.</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th
                      className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:text-gray-700"
                      onClick={() => handleSort('full_name')}
                    >
                      Name{sortIcon('full_name')}
                    </th>
                    <th
                      className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:text-gray-700"
                      onClick={() => handleSort('email')}
                    >
                      Email{sortIcon('email')}
                    </th>
                    <th
                      className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:text-gray-700"
                      onClick={() => handleSort('role')}
                    >
                      Role{sortIcon('role')}
                    </th>
                    <th
                      className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:text-gray-700"
                      onClick={() => handleSort('active')}
                    >
                      Status{sortIcon('active')}
                    </th>
                    <th
                      className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:text-gray-700"
                      onClick={() => handleSort('created_at')}
                    >
                      Created{sortIcon('created_at')}
                    </th>
                    <th
                      className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:text-gray-700"
                      onClick={() => handleSort('last_sign_in_at')}
                    >
                      Last Login{sortIcon('last_sign_in_at')}
                    </th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {sorted.map(user => (
                    <tr key={user.id} className={`hover:bg-gray-50 ${!user.active ? 'opacity-60' : ''}`}>
                      <td className="px-4 py-3 text-sm font-medium text-gray-900">
                        {user.full_name}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600">
                        {user.email}
                      </td>
                      <td className="px-4 py-3">
                        {roleBadge(user.role)}
                      </td>
                      <td className="px-4 py-3">
                        <button
                          onClick={() => handleToggleActive(user)}
                          disabled={actionLoading || user.id === userProfile.id}
                          title={user.id === userProfile.id ? 'Cannot disable yourself' : (user.active ? 'Click to disable' : 'Click to enable')}
                          className={`inline-flex px-2 py-0.5 text-xs font-medium rounded-full cursor-pointer disabled:cursor-not-allowed ${
                            user.active
                              ? 'bg-green-100 text-green-800 hover:bg-green-200'
                              : 'bg-red-100 text-red-800 hover:bg-red-200'
                          }`}
                        >
                          {user.active ? 'Active' : 'Disabled'}
                        </button>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-500 whitespace-nowrap">
                        {formatDate(user.created_at)}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-500 whitespace-nowrap">
                        {formatDateTime(user.last_sign_in_at)}
                      </td>
                      <td className="px-4 py-3 text-right whitespace-nowrap">
                        <div className="flex justify-end gap-2">
                          <button
                            onClick={() => openEdit(user)}
                            className="text-blue-600 hover:text-blue-900 text-sm font-medium"
                          >
                            Edit
                          </button>
                          <button
                            onClick={() => setResetPwUser(user)}
                            className="text-yellow-600 hover:text-yellow-900 text-sm font-medium"
                          >
                            Reset PW
                          </button>
                          <button
                            onClick={() => { setDeleteUser(user); setDeleteConfirmEmail(''); }}
                            disabled={user.id === userProfile.id}
                            className="text-red-600 hover:text-red-900 text-sm font-medium disabled:opacity-30 disabled:cursor-not-allowed"
                          >
                            Delete
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {!isLoading && sorted.length > 0 && (
            <div className="px-4 py-3 bg-gray-50 border-t border-gray-200 text-sm text-gray-500">
              {sorted.length} user{sorted.length !== 1 ? 's' : ''}
            </div>
          )}
        </div>
      </main>

      {/* ── Create User Modal ── */}
      {showCreate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="fixed inset-0 bg-black/50" onClick={() => setShowCreate(false)} />
          <div className="relative bg-white rounded-lg shadow-xl max-w-md w-full mx-4 p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Create New User</h3>
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-500 mb-1">First Name</label>
                  <input
                    type="text"
                    value={createForm.first_name}
                    onChange={e => setCreateForm(prev => ({ ...prev, first_name: e.target.value }))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
                    autoFocus
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-500 mb-1">Last Name</label>
                  <input
                    type="text"
                    value={createForm.last_name}
                    onChange={e => setCreateForm(prev => ({ ...prev, last_name: e.target.value }))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
                  />
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-500 mb-1">Email</label>
                <input
                  type="email"
                  value={createForm.email}
                  onChange={e => setCreateForm(prev => ({ ...prev, email: e.target.value }))}
                  placeholder="user@caldrywall.com"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-500 mb-1">Role</label>
                <select
                  value={createForm.role}
                  onChange={e => setCreateForm(prev => ({ ...prev, role: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
                >
                  <option value="project_manager">Project Manager</option>
                  <option value="executive">Executive</option>
                  <option value="admin">Admin</option>
                </select>
              </div>
              <p className="text-xs text-gray-500">
                A password setup email will be sent to the user.
              </p>
            </div>
            <div className="flex justify-end space-x-3 mt-6">
              <button
                onClick={() => setShowCreate(false)}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200"
              >
                Cancel
              </button>
              <button
                onClick={handleCreate}
                disabled={createLoading || !createForm.first_name.trim() || !createForm.email.trim()}
                className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:opacity-50"
              >
                {createLoading ? 'Creating...' : 'Create User'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Edit User Modal ── */}
      {editUser && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="fixed inset-0 bg-black/50" onClick={() => setEditUser(null)} />
          <div className="relative bg-white rounded-lg shadow-xl max-w-md w-full mx-4 p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-1">Edit User</h3>
            <p className="text-sm text-gray-500 mb-4">{editUser.email}</p>
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-gray-500 mb-1">Full Name</label>
                <input
                  type="text"
                  value={editForm.full_name}
                  onChange={e => setEditForm(prev => ({ ...prev, full_name: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
                  autoFocus
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-500 mb-1">Role</label>
                <select
                  value={editForm.role}
                  onChange={e => setEditForm(prev => ({ ...prev, role: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
                >
                  <option value="project_manager">Project Manager</option>
                  <option value="executive">Executive</option>
                  <option value="admin">Admin</option>
                </select>
              </div>
            </div>
            <div className="flex justify-end space-x-3 mt-6">
              <button
                onClick={() => setEditUser(null)}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200"
              >
                Cancel
              </button>
              <button
                onClick={handleEdit}
                disabled={editLoading || !editForm.full_name.trim()}
                className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:opacity-50"
              >
                {editLoading ? 'Saving...' : 'Save Changes'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Reset Password Dialog ── */}
      {resetPwUser && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="fixed inset-0 bg-black/50" onClick={() => setResetPwUser(null)} />
          <div className="relative bg-white rounded-lg shadow-xl max-w-sm w-full mx-4 p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">Reset Password</h3>
            <p className="text-sm text-gray-600 mb-4">
              Send a password reset email to <span className="font-medium">{resetPwUser.email}</span>?
            </p>
            <div className="flex justify-end space-x-3">
              <button
                onClick={() => setResetPwUser(null)}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200"
              >
                Cancel
              </button>
              <button
                onClick={handleResetPassword}
                disabled={resetPwLoading}
                className="px-4 py-2 text-sm font-medium text-white bg-yellow-500 rounded-md hover:bg-yellow-600 disabled:opacity-50"
              >
                {resetPwLoading ? 'Sending...' : 'Send Reset Email'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Delete User Dialog ── */}
      {deleteUser && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="fixed inset-0 bg-black/50" onClick={() => { setDeleteUser(null); setDeleteConfirmEmail(''); }} />
          <div className="relative bg-white rounded-lg shadow-xl max-w-md w-full mx-4 p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="flex-shrink-0 w-10 h-10 rounded-full bg-red-100 flex items-center justify-center">
                <svg className="w-6 h-6 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
                </svg>
              </div>
              <h3 className="text-lg font-semibold text-gray-900">Delete User</h3>
            </div>
            <p className="text-sm text-gray-600 mb-2">
              Permanently delete <span className="font-medium">{deleteUser.full_name}</span> ({deleteUser.email})?
            </p>
            <p className="text-sm text-gray-500 mb-1">This will:</p>
            <ul className="text-sm text-gray-500 mb-4 list-disc list-inside space-y-1">
              <li>Remove the user from Supabase Auth</li>
              <li>Delete their profile and role</li>
              {deleteUser.role === 'executive' && (
                <li className="text-red-600 font-medium">Release any active reviews back to the queue</li>
              )}
            </ul>
            <p className="text-sm text-gray-500 mb-1">
              Consider <button
                onClick={() => { setDeleteUser(null); setDeleteConfirmEmail(''); handleToggleActive(deleteUser); }}
                className="text-blue-600 hover:underline font-medium"
              >disabling</button> the account instead to preserve the audit trail.
            </p>
            <div className="mt-4">
              <label className="block text-xs font-medium text-gray-500 mb-1">
                Type the user&apos;s email to confirm
              </label>
              <input
                type="text"
                value={deleteConfirmEmail}
                onChange={e => setDeleteConfirmEmail(e.target.value)}
                placeholder={deleteUser.email}
                className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-red-500"
              />
            </div>
            <div className="flex justify-end space-x-3 mt-4">
              <button
                onClick={() => { setDeleteUser(null); setDeleteConfirmEmail(''); }}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200"
              >
                Cancel
              </button>
              <button
                onClick={handleDelete}
                disabled={deleteLoading || deleteConfirmEmail.toLowerCase() !== deleteUser.email.toLowerCase()}
                className="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-md hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {deleteLoading ? 'Deleting...' : 'Delete Permanently'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
