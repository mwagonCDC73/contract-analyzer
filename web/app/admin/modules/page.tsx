'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import Link from 'next/link';
import { getCurrentUser } from '@/lib/supabase';
import { adminAPI, authAPI } from '@/lib/api';
import Header from '@/components/Header';
import type { Module, UserWithModules, UserProfile } from '@/types';

export default function AdminModulesPage() {
  const router = useRouter();
  const pathname = usePathname();
  const [isLoading, setIsLoading] = useState(true);
  const [userProfile, setUserProfile] = useState<UserProfile | null>(null);
  const [modules, setModules] = useState<Module[]>([]);
  const [selectedModuleKey, setSelectedModuleKey] = useState<string>('');
  const [users, setUsers] = useState<UserWithModules[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState(false);

  // Auth check — admin only
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

  // Fetch modules list
  useEffect(() => {
    if (!userProfile) return;
    adminAPI.listModules()
      .then((data) => {
        setModules(data);
        if (data.length > 0 && !selectedModuleKey) {
          setSelectedModuleKey(data[0].key);
        }
      })
      .catch((err) => {
        setError(err?.response?.data?.detail || 'Failed to load modules');
      });
  }, [userProfile, selectedModuleKey]);

  // Fetch users for selected module
  const fetchUsers = useCallback(async () => {
    if (!userProfile || !selectedModuleKey) return;
    setIsLoading(true);
    setError(null);
    try {
      const data = await adminAPI.listModuleUsers(selectedModuleKey);
      setUsers(data);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to load module users');
    } finally {
      setIsLoading(false);
    }
  }, [userProfile, selectedModuleKey]);

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

  const selectedModule = modules.find(m => m.key === selectedModuleKey);

  const handleToggleAccess = async (userId: string, hasAccess: boolean) => {
    setActionLoading(true);
    try {
      if (hasAccess) {
        await adminAPI.revokeModuleAccess(selectedModuleKey, userId);
        setSuccessMsg('Access revoked');
      } else {
        await adminAPI.grantModuleAccess(selectedModuleKey, userId);
        setSuccessMsg('Access granted');
      }
      await fetchUsers();
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to update access');
    } finally {
      setActionLoading(false);
    }
  };

  const handleGrantAll = async () => {
    setActionLoading(true);
    try {
      const result = await adminAPI.grantModuleToAll(selectedModuleKey);
      setSuccessMsg(result.message);
      await fetchUsers();
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to grant access to all');
    } finally {
      setActionLoading(false);
    }
  };

  const handleRevokeAll = async () => {
    setActionLoading(true);
    try {
      const result = await adminAPI.revokeModuleFromAll(selectedModuleKey);
      setSuccessMsg(result.message);
      await fetchUsers();
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to revoke access from all');
    } finally {
      setActionLoading(false);
    }
  };

  const handleToggleEnabled = async () => {
    if (!selectedModule) return;
    setActionLoading(true);
    try {
      await adminAPI.updateModule(selectedModuleKey, { enabled: !selectedModule.enabled });
      setSuccessMsg(`Module ${selectedModule.enabled ? 'disabled' : 'enabled'}`);
      // Refresh modules list
      const data = await adminAPI.listModules();
      setModules(data);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to update module');
    } finally {
      setActionLoading(false);
    }
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

  const grantedCount = users.filter(u => u.modules.includes(selectedModuleKey)).length;

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
          </nav>
        </div>

        {/* Page header */}
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-900">Module Access</h1>
          <p className="mt-1 text-sm text-gray-500">
            Manage which users can access each platform module.
          </p>
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

        {/* Module selector + controls */}
        <div className="bg-white rounded-lg border border-gray-200 p-4 mb-4">
          <div className="flex items-center justify-between flex-wrap gap-4">
            <div className="flex items-center gap-4">
              <div>
                <label className="block text-xs font-medium text-gray-500 mb-1">Module</label>
                <select
                  value={selectedModuleKey}
                  onChange={e => setSelectedModuleKey(e.target.value)}
                  className="px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
                >
                  {modules.map(m => (
                    <option key={m.key} value={m.key}>{m.name}</option>
                  ))}
                </select>
              </div>
              {selectedModule && (
                <div className="flex items-center gap-2 mt-5">
                  <span className={`inline-flex px-2 py-0.5 text-xs font-medium rounded-full ${
                    selectedModule.enabled
                      ? 'bg-green-100 text-green-800'
                      : 'bg-gray-100 text-gray-600'
                  }`}>
                    {selectedModule.enabled ? 'Enabled' : 'Disabled'}
                  </span>
                  <button
                    onClick={handleToggleEnabled}
                    disabled={actionLoading}
                    className="text-sm text-blue-600 hover:text-blue-800 font-medium disabled:opacity-50"
                  >
                    {selectedModule.enabled ? 'Disable' : 'Enable'}
                  </button>
                </div>
              )}
            </div>
            <div className="flex gap-2 mt-5">
              <button
                onClick={handleGrantAll}
                disabled={actionLoading}
                className="px-3 py-1.5 text-sm font-medium bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50"
              >
                Grant to All
              </button>
              <button
                onClick={handleRevokeAll}
                disabled={actionLoading}
                className="px-3 py-1.5 text-sm font-medium bg-red-600 text-white rounded-md hover:bg-red-700 disabled:opacity-50"
              >
                Revoke from All
              </button>
            </div>
          </div>
        </div>

        {/* Users table */}
        <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
          {isLoading ? (
            <div className="p-12 text-center text-gray-500">Loading users...</div>
          ) : users.length === 0 ? (
            <div className="p-12 text-center text-gray-500">No users found.</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Name
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Email
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Role
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Status
                    </th>
                    <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Access
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {users.map(user => {
                    const hasAccess = user.modules.includes(selectedModuleKey);
                    return (
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
                          <span className={`inline-flex px-2 py-0.5 text-xs font-medium rounded-full ${
                            user.active
                              ? 'bg-green-100 text-green-800'
                              : 'bg-red-100 text-red-800'
                          }`}>
                            {user.active ? 'Active' : 'Disabled'}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-center">
                          <button
                            onClick={() => handleToggleAccess(user.id, hasAccess)}
                            disabled={actionLoading}
                            className="relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50"
                            style={{ backgroundColor: hasAccess ? '#2563eb' : '#d1d5db' }}
                          >
                            <span
                              className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
                                hasAccess ? 'translate-x-5' : 'translate-x-0'
                              }`}
                            />
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
          {!isLoading && users.length > 0 && (
            <div className="px-4 py-3 bg-gray-50 border-t border-gray-200 text-sm text-gray-500">
              {grantedCount} of {users.length} user{users.length !== 1 ? 's' : ''} have access
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
