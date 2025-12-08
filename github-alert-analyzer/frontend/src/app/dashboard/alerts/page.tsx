'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { AlertTriangle, Loader2, Search, Filter, ArrowUpDown, X } from 'lucide-react';
import { alertsApi, Alert } from '@/lib/api';
import { cn, getSeverityColor } from '@/lib/utils';
import StatusBadge from '@/components/StatusBadge';

type SortField = 'severity' | 'created_at' | 'priority' | 'confidence' | 'package_name' | 'repository';
type SortOrder = 'asc' | 'desc';

export default function AlertsPage() {
  const router = useRouter();
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [totalAlerts, setTotalAlerts] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [severityFilter, setSeverityFilter] = useState<string>('all');
  const [riskFilter, setRiskFilter] = useState<string>('all');
  const [priorityFilter, setPriorityFilter] = useState<string>('all');
  const [stateFilter, setStateFilter] = useState<string>('all');
  const [repositoryFilter, setRepositoryFilter] = useState<string>('all');
  const [sortField, setSortField] = useState<SortField>('created_at');
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc');

  // Get unique repositories from alerts
  const uniqueRepositories = Array.from(new Set(alerts.map(a => a.repository_full_name).filter(Boolean)))
    .sort() as string[];

  useEffect(() => {
    fetchAlerts();
  }, []);

  const fetchAlerts = async () => {
    try {
      setIsLoading(true);
      // Fetch all alerts by setting a high per_page limit
      const data = await alertsApi.list({ per_page: 1000 });
      setAlerts(data.items || []);
      setTotalAlerts(data.total);
    } catch (err) {
      setError('Failed to load alerts');
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortOrder('desc');
    }
  };

  const clearFilters = () => {
    setSearchTerm('');
    setSeverityFilter('all');
    setRiskFilter('all');
    setPriorityFilter('all');
    setStateFilter('all');
    setRepositoryFilter('all');
  };

  const activeFilterCount = [
    searchTerm !== '',
    severityFilter !== 'all',
    riskFilter !== 'all',
    priorityFilter !== 'all',
    stateFilter !== 'all',
    repositoryFilter !== 'all',
  ].filter(Boolean).length;

  const filteredAndSortedAlerts = alerts
    .filter((alert) => {
      const matchesSearch = searchTerm === '' || 
        alert.package_name.toLowerCase().includes(searchTerm.toLowerCase());
      const matchesSeverity = severityFilter === 'all' || alert.severity === severityFilter;
      const matchesRisk = riskFilter === 'all' || alert.risk_status === riskFilter;
      const matchesPriority = priorityFilter === 'all' || alert.action_priority === priorityFilter;
      const matchesState = stateFilter === 'all' || alert.state === stateFilter;
      const matchesRepository = repositoryFilter === 'all' || alert.repository_full_name === repositoryFilter;
      return matchesSearch && matchesSeverity && matchesRisk && matchesPriority && matchesState && matchesRepository;
    })
    .sort((a, b) => {
      let comparison = 0;
      
      switch (sortField) {
        case 'severity':
          const severityOrder = { critical: 4, high: 3, medium: 2, low: 1 };
          comparison = (severityOrder[a.severity] || 0) - (severityOrder[b.severity] || 0);
          break;
        case 'priority':
          const priorityOrder = { critical: 5, high: 4, medium: 3, low: 2, no_action: 1 };
          comparison = (priorityOrder[a.action_priority as keyof typeof priorityOrder] || 0) - 
                      (priorityOrder[b.action_priority as keyof typeof priorityOrder] || 0);
          break;
        case 'confidence':
          comparison = (a.analysis_confidence || 0) - (b.analysis_confidence || 0);
          break;
        case 'package_name':
          comparison = a.package_name.localeCompare(b.package_name);
          break;
        case 'repository':
          const repoA = a.repository_full_name || '';
          const repoB = b.repository_full_name || '';
          comparison = repoA.localeCompare(repoB);
          break;
        case 'created_at':
        default:
          comparison = new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
          break;
      }
      
      return sortOrder === 'asc' ? comparison : -comparison;
    });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="w-8 h-8 animate-spin text-primary-500" />
      </div>
    );
  }

  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">Security Alerts</h1>
        <p className="text-[var(--muted)]">View and manage Dependabot security alerts</p>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/20 text-red-500 px-4 py-3 rounded-lg mb-6">
          {error}
        </div>
      )}

      {/* Filters and Sort */}
      <div className="card mb-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-semibold flex items-center gap-2">
            <Filter className="w-4 h-4" />
            Filters & Sort
          </h3>
          {activeFilterCount > 0 && (
            <button
              onClick={clearFilters}
              className="text-sm text-[var(--muted)] hover:text-[var(--foreground)] flex items-center gap-1"
            >
              <X className="w-3 h-3" />
              Clear {activeFilterCount} filter{activeFilterCount > 1 ? 's' : ''}
            </button>
          )}
        </div>

        {/* Search */}
        <div className="relative mb-4">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-[var(--muted)]" />
          <input
            type="text"
            placeholder="Search by package name..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="input w-full pl-10"
          />
        </div>

        {/* Filter Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4 mb-4">
          <div>
            <label className="block text-xs font-medium text-[var(--muted)] mb-1">Severity</label>
            <select
              value={severityFilter}
              onChange={(e) => setSeverityFilter(e.target.value)}
              className="input w-full"
            >
              <option value="all">All Severities</option>
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-[var(--muted)] mb-1">Risk Status</label>
            <select
              value={riskFilter}
              onChange={(e) => setRiskFilter(e.target.value)}
              className="input w-full"
            >
              <option value="all">All Risk Levels</option>
              <option value="true_positive">True Positive</option>
              <option value="false_positive">False Positive</option>
              <option value="needs_review">Needs Review</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-[var(--muted)] mb-1">Action Priority</label>
            <select
              value={priorityFilter}
              onChange={(e) => setPriorityFilter(e.target.value)}
              className="input w-full"
            >
              <option value="all">All Priorities</option>
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
              <option value="no_action">No Action</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-[var(--muted)] mb-1">Repository</label>
            <select
              value={repositoryFilter}
              onChange={(e) => setRepositoryFilter(e.target.value)}
              className="input w-full"
            >
              <option value="all">All Repositories</option>
              {uniqueRepositories.map((repo) => (
                <option key={repo} value={repo}>{repo}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-[var(--muted)] mb-1">State</label>
            <select
              value={stateFilter}
              onChange={(e) => setStateFilter(e.target.value)}
              className="input w-full"
            >
              <option value="all">All States</option>
              <option value="open">Open</option>
              <option value="fixed">Fixed</option>
              <option value="dismissed">Dismissed</option>
            </select>
          </div>
        </div>

        {/* Sort Options */}
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs font-medium text-[var(--muted)]">Sort by:</span>
          <button
            onClick={() => handleSort('created_at')}
            className={cn(
              "text-xs px-2 py-1 rounded flex items-center gap-1",
              sortField === 'created_at' 
                ? "bg-primary-500 text-white" 
                : "bg-[var(--border)] hover:bg-[var(--border)]/80"
            )}
          >
            Date {sortField === 'created_at' && (sortOrder === 'asc' ? '↑' : '↓')}
          </button>
          <button
            onClick={() => handleSort('repository')}
            className={cn(
              "text-xs px-2 py-1 rounded flex items-center gap-1",
              sortField === 'repository' 
                ? "bg-primary-500 text-white" 
                : "bg-[var(--border)] hover:bg-[var(--border)]/80"
            )}
          >
            Repository {sortField === 'repository' && (sortOrder === 'asc' ? '↑' : '↓')}
          </button>
          <button
            onClick={() => handleSort('severity')}
            className={cn(
              "text-xs px-2 py-1 rounded flex items-center gap-1",
              sortField === 'severity' 
                ? "bg-primary-500 text-white" 
                : "bg-[var(--border)] hover:bg-[var(--border)]/80"
            )}
          >
            Severity {sortField === 'severity' && (sortOrder === 'asc' ? '↑' : '↓')}
          </button>
          <button
            onClick={() => handleSort('priority')}
            className={cn(
              "text-xs px-2 py-1 rounded flex items-center gap-1",
              sortField === 'priority' 
                ? "bg-primary-500 text-white" 
                : "bg-[var(--border)] hover:bg-[var(--border)]/80"
            )}
          >
            Priority {sortField === 'priority' && (sortOrder === 'asc' ? '↑' : '↓')}
          </button>
          <button
            onClick={() => handleSort('confidence')}
            className={cn(
              "text-xs px-2 py-1 rounded flex items-center gap-1",
              sortField === 'confidence' 
                ? "bg-primary-500 text-white" 
                : "bg-[var(--border)] hover:bg-[var(--border)]/80"
            )}
          >
            Confidence {sortField === 'confidence' && (sortOrder === 'asc' ? '↑' : '↓')}
          </button>
          <button
            onClick={() => handleSort('package_name')}
            className={cn(
              "text-xs px-2 py-1 rounded flex items-center gap-1",
              sortField === 'package_name' 
                ? "bg-primary-500 text-white" 
                : "bg-[var(--border)] hover:bg-[var(--border)]/80"
            )}
          >
            Name {sortField === 'package_name' && (sortOrder === 'asc' ? '↑' : '↓')}
          </button>
        </div>
      </div>

      {/* Results */}
      <div className="mb-4 text-sm text-[var(--muted)]">
        Showing {filteredAndSortedAlerts.length} of {totalAlerts} alert{totalAlerts !== 1 ? 's' : ''}
      </div>

      {filteredAndSortedAlerts.length === 0 ? (
        <div className="card text-center py-12">
          <AlertTriangle className="w-16 h-16 mx-auto mb-4 text-[var(--muted)]" />
          <h3 className="text-xl font-semibold mb-2">No alerts found</h3>
          <p className="text-[var(--muted)]">
            {activeFilterCount > 0
              ? 'Try adjusting your filters'
              : 'Your repositories have no security alerts'}
          </p>
        </div>
      ) : (
        <div className="space-y-6">
          {filteredAndSortedAlerts.map((alert) => (
            <div 
              key={alert.id} 
              className="card hover:border-primary-500 transition-all cursor-pointer"
              onClick={() => router.push(`/dashboard/alerts/${alert.id}`)}
            >
              {/* Header Section */}
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-start gap-3 flex-1">
                  {/* Severity Badge - Left aligned as visual anchor */}
                  <span className={cn(
                    "px-2.5 py-1 rounded text-xs font-bold uppercase shrink-0 mt-0.5",
                    alert.severity === 'critical' && "bg-purple-500/10 text-purple-500 border border-purple-500/20",
                    alert.severity === 'high' && "bg-red-500/10 text-red-500 border border-red-500/20",
                    alert.severity === 'medium' && "bg-yellow-500/10 text-yellow-500 border border-yellow-500/20",
                    alert.severity === 'low' && "bg-blue-500/10 text-blue-500 border border-blue-500/20"
                  )}>
                    {alert.severity}
                  </span>

                  {/* Package Info */}
                  <div className="flex-1 min-w-0">
                    <h3 className="font-semibold text-lg mb-1 truncate">
                      {alert.package_name}
                      <span className="text-[var(--muted)] font-normal text-sm ml-2">
                        ({alert.package_ecosystem})
                      </span>
                    </h3>
                    
                    {/* Metadata badges */}
                    <div className="flex items-center gap-2 flex-wrap text-xs mb-2">
                      {alert.repository_full_name && (
                        <span className="font-mono bg-[var(--border)] px-2 py-0.5 rounded">
                          {alert.repository_full_name}
                        </span>
                      )}
                      {alert.repository_full_name && (
                        <a
                          href={`https://github.com/${alert.repository_full_name}/security/dependabot/${alert.github_alert_number}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          onClick={(e) => e.stopPropagation()}
                          className="font-mono bg-blue-500/10 text-blue-500 hover:bg-blue-500/20 px-2 py-0.5 rounded transition-colors"
                          title="View on GitHub"
                        >
                          #{alert.github_alert_number} ↗
                        </a>
                      )}
                      {!alert.repository_full_name && (
                        <span className="font-mono bg-[var(--border)] px-2 py-0.5 rounded">
                          #{alert.github_alert_number}
                        </span>
                      )}
                      {alert.manifest_path && (
                        <span className="font-mono bg-blue-500/10 text-blue-500 px-2 py-0.5 rounded" title={`Impacted file: ${alert.manifest_path}`}>
                          📄 {alert.manifest_path}
                        </span>
                      )}
                      <span className={cn(
                        "px-2 py-0.5 rounded text-xs font-medium",
                        alert.state === 'open' && "bg-red-500/10 text-red-500",
                        alert.state === 'fixed' && "bg-green-500/10 text-green-500",
                        alert.state === 'dismissed' && "bg-gray-500/10 text-gray-500"
                      )}>
                        {alert.state}
                      </span>
                    </div>
                    
                    {/* Vulnerability Summary */}
                    {alert.vulnerability?.summary && (
                      <p className="text-[var(--muted)] text-sm leading-relaxed line-clamp-2">
                        {alert.vulnerability.summary}
                      </p>
                    )}
                  </div>
                </div>
              </div>

              {/* Version Info */}
              {(alert.vulnerable_version_range || alert.patched_version) && (
                <div className="flex items-center gap-6 text-sm mb-4 pb-4 border-b border-[var(--border)]">
                  {alert.vulnerable_version_range && (
                    <div className="flex items-center gap-2">
                      <span className="text-[var(--muted)] text-xs">Vulnerable:</span>
                      <span className="font-mono text-xs bg-red-500/10 text-red-500 px-2 py-0.5 rounded">
                        {alert.vulnerable_version_range}
                      </span>
                    </div>
                  )}
                  {alert.patched_version && (
                    <div className="flex items-center gap-2">
                      <span className="text-[var(--muted)] text-xs">Patched:</span>
                      <span className="font-mono text-xs bg-green-500/10 text-green-500 px-2 py-0.5 rounded">
                        {alert.patched_version}
                      </span>
                    </div>
                  )}
                </div>
              )}

              {/* Analysis Status Section */}
              {(alert.risk_status || alert.exploitability_level || alert.action_priority) && (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
                  {alert.risk_status && (
                    <div>
                      <div className="text-xs text-[var(--muted)] mb-1">Risk Assessment</div>
                      <StatusBadge type="risk" value={alert.risk_status} size="sm" />
                    </div>
                  )}
                  {alert.exploitability_level && (
                    <div>
                      <div className="text-xs text-[var(--muted)] mb-1">Exploitability</div>
                      <StatusBadge type="exploitability" value={alert.exploitability_level} size="sm" />
                    </div>
                  )}
                  {alert.action_priority && (
                    <div>
                      <div className="text-xs text-[var(--muted)] mb-1">Priority</div>
                      <StatusBadge type="priority" value={alert.action_priority} size="sm" />
                    </div>
                  )}
                  {alert.analysis_confidence !== null && alert.analysis_confidence !== undefined && (
                    <div>
                      <div className="text-xs text-[var(--muted)] mb-1">Confidence</div>
                      <span className={cn(
                        "text-xs font-semibold",
                        alert.analysis_confidence >= 0.8 ? "text-green-600 dark:text-green-400" :
                        alert.analysis_confidence >= 0.6 ? "text-yellow-600 dark:text-yellow-400" :
                        "text-red-600 dark:text-red-400"
                      )}>
                        {Math.round(alert.analysis_confidence * 100)}%
                      </span>
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
