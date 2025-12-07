'use client';

import { useEffect } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import Link from 'next/link';
import { Shield, LayoutDashboard, FolderGit2, AlertTriangle, Settings, LogOut, Loader2 } from 'lucide-react';
import { useAuthStore } from '@/lib/store';
import { cn } from '@/lib/utils';

const navigation = [
  { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { name: 'Repositories', href: '/dashboard/repositories', icon: FolderGit2 },
  { name: 'Alerts', href: '/dashboard/alerts', icon: AlertTriangle },
  { name: 'Settings', href: '/dashboard/settings', icon: Settings },
];

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { user, isAuthenticated, isLoading, checkAuth, logout } = useAuthStore();

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push('/auth/login');
    }
  }, [isLoading, isAuthenticated, router]);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[var(--background)]">
        <Loader2 className="w-8 h-8 animate-spin text-primary-500" />
      </div>
    );
  }

  if (!isAuthenticated) return null;

  return (
    <div className="min-h-screen bg-[var(--background)] flex">
      <aside className="w-64 border-r border-[var(--border)] flex flex-col">
        <div className="p-6 border-b border-[var(--border)]">
          <Link href="/dashboard" className="flex items-center gap-2">
            <Shield className="w-8 h-8 text-primary-500" />
            <span className="text-lg font-bold">Alert Analyzer</span>
          </Link>
        </div>
        <nav className="flex-1 p-4 space-y-1">
          {navigation.map((item) => {
            const isActive = pathname === item.href || (item.href !== '/dashboard' && pathname.startsWith(item.href));
            return (
              <Link key={item.name} href={item.href}
                className={cn('flex items-center gap-3 px-4 py-3 rounded-lg transition-colors',
                  isActive ? 'bg-primary-500/10 text-primary-500' : 'text-[var(--muted)] hover:text-[var(--foreground)] hover:bg-[var(--card)]'
                )}>
                <item.icon className="w-5 h-5" />
                {item.name}
              </Link>
            );
          })}
        </nav>
        <div className="p-4 border-t border-[var(--border)]">
          <div className="flex items-center gap-3 px-4 py-3 mb-2">
            <div className="w-8 h-8 rounded-full bg-primary-500/20 flex items-center justify-center">
              <span className="text-sm font-medium text-primary-500">{user?.email?.charAt(0).toUpperCase()}</span>
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium truncate">{user?.full_name || 'User'}</p>
              <p className="text-xs text-[var(--muted)] truncate">{user?.email}</p>
            </div>
          </div>
          <button onClick={() => { logout(); router.push('/'); }}
            className="flex items-center gap-3 w-full px-4 py-3 rounded-lg text-[var(--muted)] hover:text-red-500 hover:bg-red-500/10 transition-colors">
            <LogOut className="w-5 h-5" />
            Sign out
          </button>
        </div>
      </aside>
      <main className="flex-1 overflow-auto">{children}</main>
    </div>
  );
}
