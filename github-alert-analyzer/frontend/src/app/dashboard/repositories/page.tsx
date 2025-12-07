'use client';

import { useEffect, useState } from 'react';
import { FolderGit2, RefreshCw, Loader2, AlertTriangle } from 'lucide-react';
import { repositoriesApi, Repository } from '@/lib/api';
import { cn } from '@/lib/utils';

export default function RepositoriesPage() {
  const [repositories, setRepositories] = useState<Repository[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    fetchRepositories();
  }, []);

  const fetchRepositories = async () => {
    try {
      setIsLoading(true);
      const data = await repositoriesApi.list();
      setRepositories(data.items || []);
    } catch (err) {
      setError('Failed to load repositories');
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="w-8 h-8 animate-spin text-primary-500" />
      </div>
    );
  }

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold mb-2">Repositories</h1>
          <p className="text-[var(--muted)]">Manage your monitored repositories</p>
        </div>
        <button
          onClick={fetchRepositories}
          className="btn-primary flex items-center gap-2"
        >
          <RefreshCw className="w-4 h-4" />
          Refresh
        </button>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/20 text-red-500 px-4 py-3 rounded-lg mb-6">
          {error}
        </div>
      )}

      {repositories.length === 0 ? (
        <div className="card text-center py-12">
          <FolderGit2 className="w-16 h-16 mx-auto mb-4 text-[var(--muted)]" />
          <h3 className="text-xl font-semibold mb-2">No repositories found</h3>
          <p className="text-[var(--muted)] mb-4">
            Connect your GitHub account to start monitoring repositories
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4">
          {repositories.map((repo) => (
            <div key={repo.id} className="card">
              <div className="flex items-start justify-between">
                <div className="flex items-start gap-4 flex-1">
                  <FolderGit2 className="w-6 h-6 text-primary-500 mt-1" />
                  <div className="flex-1">
                    <h3 className="font-semibold text-lg mb-1">{repo.full_name}</h3>
                    {repo.description && (
                      <p className="text-[var(--muted)] text-sm mb-3">{repo.description}</p>
                    )}
                    <div className="flex items-center gap-4 text-sm">
                      {repo.primary_language && (
                        <span className="text-[var(--muted)]">
                          Language: {repo.primary_language}
                        </span>
                      )}
                      <span className={cn(
                        "px-2 py-1 rounded text-xs font-medium",
                        repo.is_monitored
                          ? "bg-green-500/10 text-green-500"
                          : "bg-gray-500/10 text-gray-500"
                      )}>
                        {repo.is_monitored ? 'Monitored' : 'Not Monitored'}
                      </span>
                      {repo.is_private && (
                        <span className="px-2 py-1 rounded text-xs font-medium bg-yellow-500/10 text-yellow-500">
                          Private
                        </span>
                      )}
                    </div>
                  </div>
                </div>
                <div className="text-right">
                  <div className="flex items-center gap-2 text-sm mb-2">
                    <AlertTriangle className="w-4 h-4 text-red-500" />
                    <span className="font-semibold">{repo.alert_count || 0}</span>
                    <span className="text-[var(--muted)]">alerts</span>
                  </div>
                  {repo.last_synced_at && (
                    <p className="text-xs text-[var(--muted)]">
                      Last synced: {new Date(repo.last_synced_at).toLocaleDateString()}
                    </p>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
