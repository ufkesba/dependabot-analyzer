'use client';

import { useState } from 'react';
import { useAuthStore } from '@/lib/store';
import { Settings, User, Key, Github, LogOut, Loader2 } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { api } from '@/lib/api';

export default function SettingsPage() {
  const { user, logout } = useAuthStore();
  const router = useRouter();
  const [isConnecting, setIsConnecting] = useState(false);
  const [error, setError] = useState('');

  const handleLogout = () => {
    logout();
    router.push('/');
  };

  const handleGitHubConnect = async () => {
    setIsConnecting(true);
    setError('');
    
    try {
      const { data } = await api.get('/api/auth/github/login');
      // Redirect to GitHub OAuth
      window.location.href = data.auth_url;
    } catch (err) {
      setError('Failed to initiate GitHub connection');
      console.error(err);
      setIsConnecting(false);
    }
  };

  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">Settings</h1>
        <p className="text-[var(--muted)]">Manage your account and preferences</p>
      </div>

      <div className="max-w-3xl space-y-6">
        {/* Profile Section */}
        <div className="card">
          <div className="flex items-center gap-3 mb-6">
            <User className="w-5 h-5 text-primary-500" />
            <h2 className="text-xl font-semibold">Profile</h2>
          </div>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-2">Email</label>
              <input
                type="email"
                value={user?.email || ''}
                disabled
                className="input w-full bg-[var(--border)] cursor-not-allowed"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">Full Name</label>
              <input
                type="text"
                value={user?.full_name || ''}
                disabled
                className="input w-full bg-[var(--border)] cursor-not-allowed"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-2">Account Status</label>
                <div className="px-3 py-2 bg-[var(--border)] rounded-lg text-sm">
                  {user?.is_active ? '✓ Active' : '✗ Inactive'}
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">Subscription</label>
                <div className="px-3 py-2 bg-[var(--border)] rounded-lg text-sm capitalize">
                  {user?.subscription_tier || 'Free'}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* API Keys Section */}
        <div className="card">
          <div className="flex items-center gap-3 mb-6">
            <Key className="w-5 h-5 text-primary-500" />
            <h2 className="text-xl font-semibold">API Keys</h2>
          </div>
          <p className="text-[var(--muted)] mb-4">
            Configure your LLM provider API keys for alert analysis.
          </p>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-2">OpenAI API Key</label>
              <input
                type="password"
                placeholder="sk-..."
                className="input w-full"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">Anthropic API Key</label>
              <input
                type="password"
                placeholder="sk-ant-..."
                className="input w-full"
              />
            </div>
          </div>
        </div>

        {/* GitHub Connection */}
        <div className="card">
          <div className="flex items-center gap-3 mb-6">
            <Github className="w-5 h-5 text-primary-500" />
            <h2 className="text-xl font-semibold">GitHub Connection</h2>
          </div>
          <p className="text-[var(--muted)] mb-4">
            Connect your GitHub account to sync repositories and alerts.
          </p>
          {error && (
            <div className="bg-red-500/10 border border-red-500/20 text-red-500 px-4 py-3 rounded-lg text-sm mb-4">
              {error}
            </div>
          )}
          <button 
            onClick={handleGitHubConnect}
            disabled={isConnecting}
            className="btn-primary flex items-center gap-2"
          >
            {isConnecting ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Connecting...
              </>
            ) : (
              <>
                <Github className="w-4 h-4" />
                Connect GitHub Account
              </>
            )}
          </button>
        </div>

        {/* Danger Zone */}
        <div className="card border-red-500/20">
          <div className="flex items-center gap-3 mb-6">
            <LogOut className="w-5 h-5 text-red-500" />
            <h2 className="text-xl font-semibold text-red-500">Danger Zone</h2>
          </div>
          <div className="space-y-4">
            <button
              onClick={handleLogout}
              className="px-4 py-2 bg-red-500/10 hover:bg-red-500/20 text-red-500 rounded-lg transition-colors"
            >
              Sign Out
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
