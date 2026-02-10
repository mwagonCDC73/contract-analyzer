'use client';

import Link from 'next/link';
import { useRouter, usePathname } from 'next/navigation';
import { signOut, getSession } from '@/lib/supabase';
import { useState, useEffect } from 'react';
import { authAPI } from '@/lib/api';
import type { UserProfile } from '@/types';

export default function Header() {
  const router = useRouter();
  const pathname = usePathname();
  const [isLoading, setIsLoading] = useState(false);
  const [userProfile, setUserProfile] = useState<UserProfile | null>(null);

  useEffect(() => {
    const fetchUserProfile = async () => {
      try {
        const session = await getSession();
        if (!session) return;
        const profile = await authAPI.getCurrentUserProfile();
        setUserProfile(profile);
      } catch (error: any) {
        console.error('[Header] Error fetching user profile:', error);
      }
    };

    fetchUserProfile();
  }, []);

  const handleSignOut = async () => {
    try {
      setIsLoading(true);
      await signOut();
      router.push('/');
    } catch (error) {
      console.error('Error signing out:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const isActive = (path: string) => pathname === path;

  const role = userProfile?.role;
  const isPm = role === 'project_manager';
  const isExecOrAdmin = role === 'executive' || role === 'admin';
  const isAdmin = role === 'admin';

  return (
    <header className="bg-white border-b border-gray-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          <div className="flex items-center space-x-8">
            <Link href="/dashboard" className="text-xl font-bold text-gray-900">
              Contract Analyzer
            </Link>
            <nav className="flex space-x-4">
              <Link
                href="/dashboard"
                className={`px-3 py-2 rounded-md text-sm font-medium ${
                  isActive('/dashboard')
                    ? 'bg-gray-100 text-gray-900'
                    : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                }`}
              >
                Dashboard
              </Link>
              {userProfile && isPm && (
                <Link
                  href="/submit"
                  className={`px-3 py-2 rounded-md text-sm font-medium ${
                    isActive('/submit')
                      ? 'bg-gray-100 text-gray-900'
                      : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                  }`}
                >
                  Submit Contract
                </Link>
              )}
              {userProfile && isPm && (
                <Link
                  href="/submissions"
                  className={`px-3 py-2 rounded-md text-sm font-medium ${
                    isActive('/submissions')
                      ? 'bg-gray-100 text-gray-900'
                      : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                  }`}
                >
                  My Submissions
                </Link>
              )}
              {userProfile && isExecOrAdmin && (
                <Link
                  href="/review"
                  className={`px-3 py-2 rounded-md text-sm font-medium ${
                    isActive('/review') || pathname?.startsWith('/review/')
                      ? 'bg-gray-100 text-gray-900'
                      : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                  }`}
                >
                  Executive Review
                </Link>
              )}
              {userProfile && isAdmin && (
                <Link
                  href="/admin/cleanup"
                  className={`px-3 py-2 rounded-md text-sm font-medium ${
                    pathname?.startsWith('/admin')
                      ? 'bg-gray-100 text-gray-900'
                      : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                  }`}
                >
                  Admin
                </Link>
              )}
            </nav>
          </div>
          <div className="flex items-center space-x-4">
            {userProfile && (
              <div className="flex items-center space-x-2 text-sm">
                <span className="font-medium text-gray-900">{userProfile.full_name}</span>
                <span className="text-gray-400">|</span>
                <span className={`px-2 py-1 rounded-md text-xs font-medium ${
                  role === 'executive'
                    ? 'bg-purple-100 text-purple-800'
                    : role === 'admin'
                    ? 'bg-red-100 text-red-800'
                    : 'bg-blue-100 text-blue-800'
                }`}>
                  {role === 'executive' ? 'Executive' : role === 'admin' ? 'Admin' : 'Project Manager'}
                </span>
              </div>
            )}
            <span className="text-gray-400">|</span>
            <button
              onClick={handleSignOut}
              disabled={isLoading}
              className="px-4 py-2 text-sm font-medium text-gray-700 hover:text-gray-900 hover:bg-gray-50 rounded-md disabled:opacity-50"
            >
              {isLoading ? 'Signing out...' : 'Sign Out'}
            </button>
          </div>
        </div>
      </div>
    </header>
  );
}
