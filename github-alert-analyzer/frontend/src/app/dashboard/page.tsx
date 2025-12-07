'use client';

import { useEffect, useState } from 'react';
import { AlertTriangle, FolderGit2, Brain, TrendingUp, Loader2 } from 'lucide-react';
import { dashboardApi, DashboardStats } from '@/lib/api';
import { cn, getSeverityColor, formatRelativeTime } from '@/lib/utils';

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const data = await dashboardApi.getStats();
        setStats(data);
      } catch (err) {
        setError('Failed to load dashboard stats');
        console.error(err);
      } finally {
        setIsLoading(false);
      }
    };
    fetchStats();
  }, []);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="w-8 h-8 animate-spin text-primary-500" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-8">
        <div className="bg-red-500/10 border border-red-500/20 text-red-500 px-4 py-3 rounded-lg">
          {error}
        </div>
      </div>
    );
  }

  const severityOrder = ['critical', 'high', 'medium', 'low'];

  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">Dashboard</h1>
        <p className="text-[var(--muted)]">Overview of your security alerts and analysis</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <StatCard
          icon={<AlertTriangle className="w-6 h-6" />}
          label="Total Alerts"
          value={stats?.total_alerts || 0}
          color="text-red-500"
          bgColor="bg-red-500/10"
        />
        <StatCard
          icon={<FolderGit2 className="w-6 h-6" />}
          label="Repositories"
          value={stats?.repositories_monitored || 0}
          color="text-blue-500"
          bgColor="bg-blue-500/10"
        />
        <StatCard
          icon={<Brain className="w-6 h-6" />}
          label="Analyses Done"
          value={stats?.total_analyses || 0}
          color="text-purple-500"
          bgColor="bg-purple-500/10"
        />
        <StatCard
          icon={<TrendingUp className="w-6 h-6" />}
          label="Open Alerts"
          value={stats?.alerts_by_state?.open || 0}
          color="text-orange-500"
          bgColor="bg-orange-500/10"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Alerts by Severity */}
        <div className="card">
          <h2 className="text-lg font-semibold mb-4">Alerts by Severity</h2>
          <div className="space-y-3">
            {severityOrder.map((severity) => {
              const count = stats?.alerts_by_severity?.[severity] || 0;
              const total = stats?.total_alerts || 1;
              const percentage = Math.round((count / total) * 100) || 0;
              
              return (
                <div key={severity} className="flex items-center gap-4">
                  <div className="w-20 capitalize font-medium">{severity}</div>
                  <div className="flex-1 h-3 bg-[var(--border)] rounded-full overflow-hidden">
                    <div
                      className={cn(
                        'h-full rounded-full transition-all duration-500',
                        severity === 'critical' && 'bg-red-500',
                        severity === 'high' && 'bg-orange-500',
                        severity === 'medium' && 'bg-yellow-500',
                        severity === 'low' && 'bg-green-500'
                      )}
                      style={{ width: `${percentage}%` }}
                    />
                  </div>
                  <div className="w-12 text-right text-[var(--muted)]">{count}</div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Alerts by Ecosystem */}
        <div className="card">
          <h2 className="text-lg font-semibold mb-4">Alerts by Ecosystem</h2>
          {Object.keys(stats?.alerts_by_ecosystem || {}).length > 0 ? (
            <div className="space-y-3">
              {Object.entries(stats?.alerts_by_ecosystem || {}).map(([ecosystem, count]) => (
                <div key={ecosystem} className="flex items-center justify-between">
                  <span className="font-medium">{ecosystem}</span>
                  <span className="px-3 py-1 rounded-full bg-[var(--border)] text-sm">
                    {count}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-[var(--muted)]">No alerts yet. Sync your repositories to get started.</p>
          )}
        </div>

        {/* Recent Alerts */}
        <div className="card lg:col-span-2">
          <h2 className="text-lg font-semibold mb-4">Recent Alerts</h2>
          {stats?.recent_alerts && stats.recent_alerts.length > 0 ? (
            <div className="space-y-3">
              {stats.recent_alerts.map((alert) => (
                <div
                  key={alert.id}
                  className="flex items-center justify-between p-3 rounded-lg bg-[var(--background)] border border-[var(--border)]"
                >
                  <div className="flex items-center gap-4">
                    <span className={cn('px-2 py-1 rounded text-xs font-medium', getSeverityColor(alert.severity))}>
                      {alert.severity}
                    </span>
                    <div>
                      <p className="font-medium">{alert.package_name}</p>
                      <p className="text-sm text-[var(--muted)]">{alert.package_ecosystem}</p>
                    </div>
                  </div>
                  <span className="text-sm text-[var(--muted)]">
                    {formatRelativeTime(alert.created_at)}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-[var(--muted)]">No recent alerts. Your repositories are looking secure!</p>
          )}
        </div>
      </div>
    </div>
  );
}

function StatCard({
  icon,
  label,
  value,
  color,
  bgColor,
}: {
  icon: React.ReactNode;
  label: string;
  value: number;
  color: string;
  bgColor: string;
}) {
  return (
    <div className="card">
      <div className="flex items-center gap-4">
        <div className={cn('p-3 rounded-lg', bgColor, color)}>{icon}</div>
        <div>
          <p className="text-2xl font-bold">{value}</p>
          <p className="text-sm text-[var(--muted)]">{label}</p>
        </div>
      </div>
    </div>
  );
}
