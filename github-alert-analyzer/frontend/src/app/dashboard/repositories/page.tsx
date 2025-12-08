'use client';

import { useEffect, useState } from 'react';
import { FolderGit2, RefreshCw, Loader2, AlertTriangle, Plus, Check, X } from 'lucide-react';
import { repositoriesApi, Repository } from '@/lib/api';
import { cn } from '@/lib/utils';

interface AvailableRepo {
  github_repo_id: string;
  full_name: string;
  name: string;
  description: string | null;
  is_private: boolean;
  primary_language: string | null;
  html_url: string;
  is_synced: boolean;
}

export default function RepositoriesPage() {
  const [repositories, setRepositories] = useState<Repository[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSyncing, setIsSyncing] = useState(false);
  const [error, setError] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  
  // Selection dialog state
  const [showSelectDialog, setShowSelectDialog] = useState(false);
  const [availableRepos, setAvailableRepos] = useState<AvailableRepo[]>([]);
  const [selectedRepoIds, setSelectedRepoIds] = useState<number[]>([]);
  const [isLoadingAvailable, setIsLoadingAvailable] = useState(false);

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

  const fetchAvailableRepos = async () => {
    try {
      setIsLoadingAvailable(true);
      setError('');
      const result = await repositoriesApi.getAvailable();
      setAvailableRepos(result.repositories || []);
      setShowSelectDialog(true);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to fetch available repositories');
      console.error(err);
    } finally {
      setIsLoadingAvailable(false);
    }
  };

  const handleSync = async () => {
    if (selectedRepoIds.length === 0) {
      setError('Please select at least one repository');
      return;
    }

    try {
      setIsSyncing(true);
      setError('');
      setSuccessMessage('');
      const result = await repositoriesApi.sync(selectedRepoIds);
      setSuccessMessage(result.message || 'Repositories synced successfully');
      setShowSelectDialog(false);
      setSelectedRepoIds([]);
      // Refresh the list after syncing
      await fetchRepositories();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to sync repositories');
      console.error(err);
    } finally {
      setIsSyncing(false);
    }
  };

  const toggleRepoSelection = (repoId: string) => {
    const id = parseInt(repoId);
    setSelectedRepoIds(prev =>
      prev.includes(id) ? prev.filter(i => i !== id) : [...prev, id]
    );
  };

  const handleUnlink = async (repoId: string, repoName: string) => {
    if (!confirm(`Are you sure you want to unlink ${repoName}? This will remove it from monitoring and delete all associated alerts.`)) {
      return;
    }

    try {
      setError('');
      setSuccessMessage('');
      await repositoriesApi.delete(repoId);
      setSuccessMessage(`Successfully unlinked ${repoName}`);
      await fetchRepositories();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to unlink repository');
      console.error(err);
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
        <div className="flex gap-2">
          <button
            onClick={fetchAvailableRepos}
            disabled={isLoadingAvailable}
            className="btn-primary flex items-center gap-2"
          >
            <Plus className={cn("w-4 h-4", isLoadingAvailable && "animate-spin")} />
            {isLoadingAvailable ? 'Loading...' : 'Add Repositories'}
          </button>
          <button
            onClick={fetchRepositories}
            className="btn-secondary flex items-center gap-2"
          >
            <RefreshCw className="w-4 h-4" />
            Refresh
          </button>
        </div>
      </div>

      {successMessage && (
        <div className="bg-green-500/10 border border-green-500/20 text-green-500 px-4 py-3 rounded-lg mb-6">
          {successMessage}
        </div>
      )}

      {error && (
        <div className="bg-red-500/10 border border-red-500/20 text-red-500 px-4 py-3 rounded-lg mb-6">
          {error}
        </div>
      )}

      {/* Repository Selection Dialog */}
      {showSelectDialog && (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4 backdrop-blur-sm">
          <div className="bg-[var(--card-bg)] rounded-lg shadow-xl max-w-3xl w-full max-h-[80vh] flex flex-col border border-[var(--border)]">
            <div className="p-6 border-b border-[var(--border)]">
              <h2 className="text-2xl font-bold mb-2">Select Repositories</h2>
              <p className="text-[var(--muted)]">
                Choose which repositories you want to monitor for Dependabot alerts
              </p>
            </div>
            
            <div className="flex-1 overflow-y-auto p-6">
              {availableRepos.length === 0 ? (
                <p className="text-center text-[var(--muted)] py-8">No repositories found</p>
              ) : (
                <div className="space-y-2">
                  {availableRepos.map((repo) => (
                    <button
                      key={repo.github_repo_id}
                      onClick={() => !repo.is_synced && toggleRepoSelection(repo.github_repo_id)}
                      disabled={repo.is_synced}
                      className={cn(
                        "w-full text-left p-4 rounded-lg border transition-all",
                        repo.is_synced
                          ? "border-green-500/30 bg-green-500/5 cursor-not-allowed"
                          : selectedRepoIds.includes(parseInt(repo.github_repo_id))
                          ? "border-primary-500 bg-primary-500/10"
                          : "border-[var(--border)] hover:border-primary-500/50"
                      )}
                    >
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <h3 className="font-semibold">{repo.full_name}</h3>
                            {repo.is_private && (
                              <span className="px-2 py-0.5 rounded text-xs bg-yellow-500/10 text-yellow-500">
                                Private
                              </span>
                            )}
                            {repo.is_synced && (
                              <span className="px-2 py-0.5 rounded text-xs bg-green-500/10 text-green-500">
                                Already Added
                              </span>
                            )}
                          </div>
                          {repo.description && (
                            <p className="text-sm text-[var(--muted)] mb-2">{repo.description}</p>
                          )}
                          {repo.primary_language && (
                            <span className="text-xs text-[var(--muted)]">
                              {repo.primary_language}
                            </span>
                          )}
                        </div>
                        <div>
                          {repo.is_synced ? (
                            <Check className="w-5 h-5 text-green-500" />
                          ) : selectedRepoIds.includes(parseInt(repo.github_repo_id)) ? (
                            <div className="w-5 h-5 rounded bg-primary-500 flex items-center justify-center">
                              <Check className="w-4 h-4 text-white" />
                            </div>
                          ) : (
                            <div className="w-5 h-5 rounded border-2 border-[var(--border)]" />
                          )}
                        </div>
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>
            
            <div className="p-6 border-t border-[var(--border)] flex justify-between items-center">
              <p className="text-sm text-[var(--muted)]">
                {selectedRepoIds.length} {selectedRepoIds.length === 1 ? 'repository' : 'repositories'} selected
              </p>
              <div className="flex gap-2">
                <button
                  onClick={() => {
                    setShowSelectDialog(false);
                    setSelectedRepoIds([]);
                  }}
                  className="btn-secondary"
                >
                  Cancel
                </button>
                <button
                  onClick={handleSync}
                  disabled={isSyncing || selectedRepoIds.length === 0}
                  className="btn-primary flex items-center gap-2"
                >
                  {isSyncing ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Syncing...
                    </>
                  ) : (
                    <>
                      <Plus className="w-4 h-4" />
                      Add Selected
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
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
                <div className="flex flex-col items-end gap-2">
                  <button
                    onClick={() => handleUnlink(repo.id, repo.full_name)}
                    className="p-1.5 rounded hover:bg-red-500/10 text-red-500 transition-colors"
                    title="Unlink repository"
                  >
                    <X className="w-4 h-4" />
                  </button>
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
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
