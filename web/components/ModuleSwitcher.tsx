'use client';

import { useState, useEffect } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import { authAPI } from '@/lib/api';
import type { Module } from '@/types';

/**
 * Derive the active module key from the current URL path.
 * - /labor/* → 'labor'
 * - everything else → 'contracts'
 */
function deriveModuleFromPathname(pathname: string): string {
  if (pathname.startsWith('/labor')) return 'labor';
  return 'contracts';
}

/**
 * Map a module key to its root route.
 */
function moduleRootRoute(key: string): string {
  switch (key) {
    case 'labor':
      return '/labor';
    case 'contracts':
    default:
      return '/dashboard';
  }
}

export default function ModuleSwitcher() {
  const pathname = usePathname();
  const router = useRouter();
  const [modules, setModules] = useState<Module[]>([]);

  useEffect(() => {
    authAPI.getMyModules()
      .then(setModules)
      .catch((err) => {
        console.error('[ModuleSwitcher] Error fetching modules:', err);
      });
  }, []);

  // Render nothing if user has 0 or 1 module — no switcher needed
  if (modules.length <= 1) {
    return null;
  }

  const activeKey = deriveModuleFromPathname(pathname);

  return (
    <div className="flex items-center bg-gray-100 rounded-full p-0.5">
      {modules.map((mod) => {
        const isActive = mod.key === activeKey;
        return (
          <button
            key={mod.key}
            onClick={() => {
              if (!isActive) {
                router.push(moduleRootRoute(mod.key));
              }
            }}
            className={`px-3 py-1 text-xs font-medium rounded-full transition-colors ${
              isActive
                ? 'bg-white text-gray-900 shadow-sm'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            {mod.name}
          </button>
        );
      })}
    </div>
  );
}
