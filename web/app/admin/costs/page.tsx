'use client';

import { useState, useEffect } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import Link from 'next/link';
import { getCurrentUser } from '@/lib/supabase';
import { adminAPI, authAPI } from '@/lib/api';
import Header from '@/components/Header';
import type { CostSummary, CostLog, UserProfile } from '@/types';

export default function AdminCostsPage() {
  const router = useRouter();
  const pathname = usePathname();
  const [isLoading, setIsLoading] = useState(true);
  const [userProfile, setUserProfile] = useState<UserProfile | null>(null);
  const [summary, setSummary] = useState<CostSummary | null>(null);
  const [logs, setLogs] = useState<CostLog[]>([]);
  const [error, setError] = useState<string | null>(null);

  // Auth check — admin only
  useEffect(() => {
    const checkAuth = async () => {
      const user = await getCurrentUser();
      if (!user) {
        router.push('/');
        return;
      }
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

  // Fetch data
  useEffect(() => {
    if (!userProfile) return;
    const load = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const [summaryData, logsData] = await Promise.all([
          adminAPI.getCostSummary(),
          adminAPI.getCostLogs(200),
        ]);
        setSummary(summaryData);
        setLogs(logsData);
      } catch (err: any) {
        setError(err.response?.data?.detail || 'Failed to load cost data');
      } finally {
        setIsLoading(false);
      }
    };
    load();
  }, [userProfile]);

  if (!userProfile) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-gray-600">Checking permissions...</div>
      </div>
    );
  }

  const formatCost = (cost: number) => {
    if (cost < 0.01) return `$${cost.toFixed(4)}`;
    return `$${cost.toFixed(2)}`;
  };

  const formatTokens = (n: number) => n.toLocaleString();

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

        <h1 className="text-2xl font-bold text-gray-900 mb-6">API Cost Tracking</h1>

        {error && (
          <div className="mb-4 rounded-md bg-red-50 p-4">
            <p className="text-sm text-red-800">{error}</p>
          </div>
        )}

        {isLoading ? (
          <div className="text-center py-12 text-gray-500">Loading cost data...</div>
        ) : summary ? (
          <>
            {/* Summary Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
              <div className="bg-white rounded-lg shadow p-5">
                <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Total Spend</p>
                <p className="mt-1 text-2xl font-bold text-gray-900">{formatCost(summary.total_cost)}</p>
                <p className="mt-1 text-xs text-gray-400">
                  {formatTokens(summary.total_input_tokens + summary.total_output_tokens)} total tokens
                </p>
              </div>
              <div className="bg-white rounded-lg shadow p-5">
                <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">This Month</p>
                <p className="mt-1 text-2xl font-bold text-gray-900">{formatCost(summary.month_cost)}</p>
              </div>
              <div className="bg-white rounded-lg shadow p-5">
                <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Avg Cost / Analysis</p>
                <p className="mt-1 text-2xl font-bold text-gray-900">{formatCost(summary.avg_cost_per_analysis)}</p>
              </div>
              <div className="bg-white rounded-lg shadow p-5">
                <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Analyses Run</p>
                <p className="mt-1 text-2xl font-bold text-gray-900">{summary.analysis_count}</p>
              </div>
            </div>

            {/* Model Breakdown */}
            {Object.keys(summary.model_breakdown).length > 0 && (
              <div className="bg-white rounded-lg shadow mb-8">
                <div className="px-5 py-4 border-b border-gray-200">
                  <h2 className="text-sm font-semibold text-gray-900">Cost by Model</h2>
                </div>
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase">Model</th>
                        <th className="px-5 py-3 text-right text-xs font-medium text-gray-500 uppercase">Analyses</th>
                        <th className="px-5 py-3 text-right text-xs font-medium text-gray-500 uppercase">Input Tokens</th>
                        <th className="px-5 py-3 text-right text-xs font-medium text-gray-500 uppercase">Output Tokens</th>
                        <th className="px-5 py-3 text-right text-xs font-medium text-gray-500 uppercase">Total Cost</th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {Object.entries(summary.model_breakdown).map(([model, data]) => (
                        <tr key={model}>
                          <td className="px-5 py-3 text-sm font-mono text-gray-900">{model}</td>
                          <td className="px-5 py-3 text-sm text-gray-700 text-right">{data.count}</td>
                          <td className="px-5 py-3 text-sm text-gray-700 text-right">{formatTokens(data.input_tokens)}</td>
                          <td className="px-5 py-3 text-sm text-gray-700 text-right">{formatTokens(data.output_tokens)}</td>
                          <td className="px-5 py-3 text-sm font-medium text-gray-900 text-right">{formatCost(data.cost)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Usage Log Table */}
            <div className="bg-white rounded-lg shadow">
              <div className="px-5 py-4 border-b border-gray-200">
                <h2 className="text-sm font-semibold text-gray-900">Analysis Log</h2>
              </div>
              {logs.length === 0 ? (
                <div className="px-5 py-8 text-center text-sm text-gray-400">
                  No analyses have been run yet.
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase">Date</th>
                        <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase">Contract</th>
                        <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase">Project</th>
                        <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
                        <th className="px-5 py-3 text-right text-xs font-medium text-gray-500 uppercase">Input</th>
                        <th className="px-5 py-3 text-right text-xs font-medium text-gray-500 uppercase">Output</th>
                        <th className="px-5 py-3 text-right text-xs font-medium text-gray-500 uppercase">Cost</th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {logs.map((log) => (
                        <tr key={log.id} className="hover:bg-gray-50">
                          <td className="px-5 py-3 text-sm text-gray-600 whitespace-nowrap">
                            {new Date(log.created_at).toLocaleDateString()}{' '}
                            <span className="text-gray-400">{new Date(log.created_at).toLocaleTimeString()}</span>
                          </td>
                          <td className="px-5 py-3 text-sm text-gray-900 max-w-[200px] truncate">
                            {log.file_name || '—'}
                          </td>
                          <td className="px-5 py-3 text-sm text-gray-700 max-w-[200px] truncate">
                            {log.project_name || '—'}
                          </td>
                          <td className="px-5 py-3 text-sm">
                            <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-700">
                              {log.analysis_type}
                            </span>
                          </td>
                          <td className="px-5 py-3 text-sm text-gray-700 text-right">{formatTokens(log.input_tokens)}</td>
                          <td className="px-5 py-3 text-sm text-gray-700 text-right">{formatTokens(log.output_tokens)}</td>
                          <td className="px-5 py-3 text-sm font-medium text-gray-900 text-right">{formatCost(log.estimated_cost_usd)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </>
        ) : null}
      </main>
    </div>
  );
}
