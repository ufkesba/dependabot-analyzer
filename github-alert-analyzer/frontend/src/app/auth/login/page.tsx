'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { Shield, Mail, Lock, Loader2 } from 'lucide-react';
import { useAuthStore } from '@/lib/store';

export default function LoginPage() {
  const router = useRouter();
  const { login, mockLogin } = useAuthStore();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isDemoMode, setIsDemoMode] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      if (isDemoMode) {
        await mockLogin();
      } else {
        await login(email, password);
      }
      router.push('/dashboard');
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Invalid email or password';
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-6 bg-[var(--background)]">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <Link href="/" className="inline-flex items-center gap-2 mb-6">
            <Shield className="w-10 h-10 text-primary-500" />
            <span className="text-2xl font-bold">Alert Analyzer</span>
          </Link>
          <h1 className="text-3xl font-bold mb-2">Welcome back</h1>
          <p className="text-[var(--muted)]">Sign in to your account to continue</p>
        </div>

        <form onSubmit={handleSubmit} className="card space-y-6">
          {error && (
            <div className="bg-red-500/10 border border-red-500/20 text-red-500 px-4 py-3 rounded-lg text-sm">
              {error}
            </div>
          )}

          <div className="bg-blue-500/10 border border-blue-500/20 px-4 py-3 rounded-lg">
            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={isDemoMode}
                onChange={(e) => setIsDemoMode(e.target.checked)}
                className="w-4 h-4 text-blue-500 rounded focus:ring-2 focus:ring-blue-500"
              />
              <div>
                <span className="text-sm font-medium text-blue-400">Demo Mode</span>
                <p className="text-xs text-blue-300/70 mt-0.5">
                  Login with mock data (no credentials required)
                </p>
              </div>
            </label>
          </div>

          <div>
            <label htmlFor="email" className="block text-sm font-medium mb-2">
              Email address
            </label>
            <div className="relative" suppressHydrationWarning>
              <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-[var(--muted)]" />
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="input w-full pl-10"
                placeholder="you@example.com"
                required={!isDemoMode}
                disabled={isDemoMode}
                suppressHydrationWarning
              />
            </div>
          </div>

          <div>
            <label htmlFor="password" className="block text-sm font-medium mb-2">
              Password
            </label>
            <div className="relative" suppressHydrationWarning>
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-[var(--muted)]" />
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="input w-full pl-10"
                placeholder="••••••••"
                required={!isDemoMode}
                disabled={isDemoMode}
                minLength={8}
                suppressHydrationWarning
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="btn-primary w-full py-3 flex items-center justify-center gap-2"
          >
            {isLoading ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                {isDemoMode ? 'Loading demo...' : 'Signing in...'}
              </>
            ) : (
              isDemoMode ? 'Enter Demo' : 'Sign in'
            )}
          </button>
        </form>

        <p className="text-center mt-6 text-[var(--muted)]">
          Don&apos;t have an account?{' '}
          <Link href="/auth/register" className="text-primary-500 hover:text-primary-400">
            Sign up
          </Link>
        </p>
      </div>
    </div>
  );
}
