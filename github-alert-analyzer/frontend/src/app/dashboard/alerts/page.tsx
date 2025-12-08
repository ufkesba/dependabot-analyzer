'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { AlertTriangle, Loader2, Search, Filter } from 'lucide-react';
import { alertsApi, Alert } from '@/lib/api';
import { cn, getSeverityColor } from '@/lib/utils';

export default function AlertsPage() {
  const router = useRouter();
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [severityFilter, setSeverityFilter] = useState<string>('all');

  useEffect(() => {
    fetchAlerts();
  }, []);

  const fetchAlerts = async () => {
    try {
      setIsLoading(true);
      const data = await alertsApi.list();
      setAlerts(data.items || []);
    } catch (err) {
      setError('Failed to load alerts');
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  const filteredAlerts = alerts.filter((alert) => {
    const matchesSearch = searchTerm === '' || 
      alert.package_name.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesSeverity = severityFilter === 'all' || alert.severity === severityFilter;
    return matchesSearch && matchesSeverity;
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

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-4 mb-6">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-[var(--muted)]" />
          <input
            type="text"
            placeholder="Search by package name..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="input w-full pl-10"
          />
        </div>
        <div className="flex items-center gap-2">
          <Filter className="w-5 h-5 text-[var(--muted)]" />
          <select
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
            className="input"
          >
            <option value="all">All Severities</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
        </div>
      </div>

      {filteredAlerts.length === 0 ? (
        <div className="card text-center py-12">
          <AlertTriangle className="w-16 h-16 mx-auto mb-4 text-[var(--muted)]" />
          <h3 className="text-xl font-semibold mb-2">No alerts found</h3>
          <p className="text-[var(--muted)]">
            {searchTerm || severityFilter !== 'all'
              ? 'Try adjusting your filters'
              : 'Your repositories have no security alerts'}
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {filteredAlerts.map((alert) => (
            <div 
              key={alert.id} 
              className="card hover:border-primary-500 transition-colors cursor-pointer"
              onClick={() => router.push(`/dashboard/alerts/${alert.id}`)}
            >
              <div className="flex items-start gap-4">
                <div className={cn(
                  "w-2 h-2 rounded-full mt-2",
                  getSeverityColor(alert.severity).replace('text-', 'bg-')
                )}>
                </div>
                <div className="flex-1">
                  <div className="flex items-start justify-between mb-2">
                    <div>
                      <h3 className="font-semibold text-lg">
                        {alert.package_name}
                        <span className="text-[var(--muted)] font-normal text-sm ml-2">
                          ({alert.package_ecosystem})
                        </span>
                      </h3>
                      {alert.vulnerability?.summary && (
                        <p className="text-[var(--muted)] text-sm mt-1">
                          {alert.vulnerability.summary}
                        </p>
                      )}
                    </div>
                    <span className={cn(
                      "px-3 py-1 rounded-full text-xs font-medium uppercase",
                      getSeverityColor(alert.severity).replace('text-', 'bg-') + '/10',
                      getSeverityColor(alert.severity)
                    )}>
                      {alert.severity}
                    </span>
                  </div>
                  
                  <div className="flex items-center gap-4 text-sm text-[var(--muted)]">
                    {alert.vulnerable_version_range && (
                      <span>Vulnerable: {alert.vulnerable_version_range}</span>
                    )}
                    {alert.patched_version && (
                      <span className="text-green-500">Patched: {alert.patched_version}</span>
                    )}
                    <span className={cn(
                      "px-2 py-1 rounded text-xs font-medium",
                      alert.state === 'open' && "bg-red-500/10 text-red-500",
                      alert.state === 'fixed' && "bg-green-500/10 text-green-500",
                      alert.state === 'dismissed' && "bg-gray-500/10 text-gray-500"
                    )}>
                      {alert.state}
                    </span>
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
