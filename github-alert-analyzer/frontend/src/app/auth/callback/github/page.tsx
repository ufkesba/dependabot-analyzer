'use client';

import { useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Loader2, CheckCircle, XCircle } from 'lucide-react';
import { api } from '@/lib/api';
import { useAuthStore } from '@/lib/store';

export default function GitHubCallbackPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
  const [message, setMessage] = useState('Completing GitHub authentication...');
  const { login } = useAuthStore();

  useEffect(() => {
    const handleCallback = async () => {
      const code = searchParams.get('code');
      const error = searchParams.get('error');

      if (error) {
        setStatus('error');
        setMessage('GitHub authentication was cancelled or failed');
        setTimeout(() => router.push('/dashboard/settings'), 3000);
        return;
      }

      if (!code) {
        setStatus('error');
        setMessage('No authorization code received from GitHub');
        setTimeout(() => router.push('/dashboard/settings'), 3000);
        return;
      }

      try {
        // Exchange code for token with backend
        const { data } = await api.get(`/api/auth/github/callback?code=${code}`);
        
        // Store the token
        localStorage.setItem('access_token', data.access_token);
        
        setStatus('success');
        setMessage('Successfully connected to GitHub!');
        
        // Redirect to dashboard after success
        setTimeout(() => router.push('/dashboard'), 2000);
      } catch (err) {
        console.error('GitHub callback error:', err);
        setStatus('error');
        setMessage('Failed to complete GitHub authentication');
        setTimeout(() => router.push('/dashboard/settings'), 3000);
      }
    };

    handleCallback();
  }, [searchParams, router]);

  return (
    <div className="min-h-screen flex items-center justify-center px-6 bg-[var(--background)]">
      <div className="w-full max-w-md text-center">
        <div className="card">
          {status === 'loading' && (
            <>
              <Loader2 className="w-16 h-16 mx-auto mb-4 animate-spin text-primary-500" />
              <h2 className="text-xl font-semibold mb-2">Connecting to GitHub</h2>
              <p className="text-[var(--muted)]">{message}</p>
            </>
          )}
          
          {status === 'success' && (
            <>
              <CheckCircle className="w-16 h-16 mx-auto mb-4 text-green-500" />
              <h2 className="text-xl font-semibold mb-2 text-green-500">Success!</h2>
              <p className="text-[var(--muted)]">{message}</p>
              <p className="text-sm text-[var(--muted)] mt-2">Redirecting...</p>
            </>
          )}
          
          {status === 'error' && (
            <>
              <XCircle className="w-16 h-16 mx-auto mb-4 text-red-500" />
              <h2 className="text-xl font-semibold mb-2 text-red-500">Error</h2>
              <p className="text-[var(--muted)]">{message}</p>
              <p className="text-sm text-[var(--muted)] mt-2">Redirecting back...</p>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
