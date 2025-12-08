'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { ArrowLeft, Loader2, AlertTriangle, ExternalLink, Clock, PlayCircle } from 'lucide-react';
import { alertsApi, workflowApi, Alert, AnalysisWorkflow } from '@/lib/api';
import { getSeverityColor, cn } from '@/lib/utils';

export default function AlertDetailPage() {
  const params = useParams();
  const router = useRouter();
  const alertId = params.id as string;

  const [alert, setAlert] = useState<Alert | null>(null);
  const [workflows, setWorkflows] = useState<AnalysisWorkflow[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (alertId) {
      fetchAlertData();
    }
  }, [alertId]);

  const fetchAlertData = async () => {
    try {
      setIsLoading(true);
      const [alertData, workflowsData] = await Promise.all([
        alertsApi.get(alertId),
        workflowApi.getByAlert(alertId),
      ]);
      setAlert(alertData);
      setWorkflows(workflowsData);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load alert');
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  const formatDuration = (seconds: number | null) => {
    if (!seconds) return 'N/A';
    if (seconds < 60) return `${seconds.toFixed(1)}s`;
    const minutes = Math.floor(seconds / 60);
    const secs = (seconds % 60).toFixed(0);
    return `${minutes}m ${secs}s`;
  };

  const getStatusBadge = (status: string) => {
    const statusColors = {
      completed: 'bg-green-100 text-green-800',
      running: 'bg-blue-100 text-blue-800',
      pending: 'bg-gray-100 text-gray-800',
      failed: 'bg-red-100 text-red-800',
    };

    return (
      <span className={cn(
        'px-2 py-1 rounded text-xs font-medium',
        statusColors[status as keyof typeof statusColors] || statusColors.pending
      )}>
        {status.charAt(0).toUpperCase() + status.slice(1)}
      </span>
    );
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <Loader2 className="w-8 h-8 animate-spin text-primary-500" />
      </div>
    );
  }

  if (error || !alert) {
    return (
      <div className="p-8">
        <div className="flex items-center gap-2 text-red-600 mb-4">
          <AlertTriangle className="w-5 h-5" />
          <span>{error || 'Alert not found'}</span>
        </div>
        <button
          onClick={() => router.back()}
          className="px-4 py-2 bg-gray-200 hover:bg-gray-300 rounded-lg"
        >
          Go Back
        </button>
      </div>
    );
  }

  return (
    <div className="p-8 max-w-7xl mx-auto">
      {/* Back button */}
      <button
        onClick={() => router.back()}
        className="flex items-center gap-2 text-[var(--muted)] hover:text-[var(--foreground)] mb-6"
      >
        <ArrowLeft className="w-4 h-4" />
        Back to Alerts
      </button>

      {/* Alert Header */}
      <div className="card mb-6">
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-center gap-3">
              <AlertTriangle className={`w-8 h-8 ${getSeverityColor(alert.severity)}`} />
            <div>
              <h1 className="text-3xl font-bold">
                {alert.package_name}
              </h1>
              <div className="flex items-center gap-3 mt-2">
                <span className={`px-3 py-1 rounded-full text-sm font-medium ${getSeverityColor(alert.severity)} bg-opacity-20`}>
                  {alert.severity.toUpperCase()}
                </span>
                <span className="px-3 py-1 rounded-full text-sm font-medium bg-gray-100 text-gray-800">
                  {alert.package_ecosystem}
                </span>
                <span className={`px-3 py-1 rounded-full text-sm font-medium capitalize ${
                  alert.state === 'open' ? 'bg-red-100 text-red-800' :
                  alert.state === 'fixed' ? 'bg-green-100 text-green-800' :
                  'bg-gray-100 text-gray-800'
                }`}>
                  {alert.state}
                </span>
              </div>
            </div>
          </div>
          <div className="text-sm text-gray-600">
            <div>Alert #{alert.github_alert_number}</div>
            <div className="mt-1">
              Created: {new Date(alert.created_at).toLocaleDateString()}
            </div>
          </div>
        </div>

        {/* Vulnerability Details */}
        {alert.vulnerability && (
          <div className="border-t pt-4 mt-4">
            <h2 className="font-semibold text-lg mb-2">
              Vulnerability Details
            </h2>
            {alert.vulnerability.summary && (
              <p className="text-gray-700 mb-3">{alert.vulnerability.summary}</p>
            )}
            {alert.vulnerability.description && (
              <p className="text-sm text-gray-600 mb-3">{alert.vulnerability.description}</p>
            )}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              {alert.vulnerability.cve_id && (
                <div>
                  <span className="font-medium text-gray-700">CVE ID:</span>
                  <div className="text-gray-600">{alert.vulnerability.cve_id}</div>
                </div>
              )}
              {alert.vulnerability.ghsa_id && (
                <div>
                  <span className="font-medium text-gray-700">GHSA ID:</span>
                  <div className="text-gray-600">{alert.vulnerability.ghsa_id}</div>
                </div>
              )}
              {alert.vulnerability.cvss_score && (
                <div>
                  <span className="font-medium text-gray-700">CVSS Score:</span>
                  <div className="text-gray-600">{alert.vulnerability.cvss_score}</div>
                </div>
              )}
              {alert.vulnerable_version_range && (
                <div>
                  <span className="font-medium text-gray-700">Vulnerable Range:</span>
                  <div className="text-gray-600">{alert.vulnerable_version_range}</div>
                </div>
              )}
            </div>
            {alert.patched_version && (
              <div className="mt-3 p-3 bg-green-50 border border-green-200 rounded">
                <span className="font-medium text-green-900">Patched Version: </span>
                <span className="text-green-800">{alert.patched_version}</span>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Agentic Analysis Workflows */}
      <div className="card">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold">
            Agentic Analysis Workflows
          </h2>
          {workflows.length === 0 && (
            <button
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg flex items-center gap-2"
              onClick={() => {/* TODO: Trigger analysis */}}
            >
              <PlayCircle className="w-4 h-4" />
              Start Analysis
            </button>
          )}
        </div>

        {workflows.length === 0 ? (
          <div className="text-center py-12 text-gray-500">
            <AlertTriangle className="w-12 h-12 mx-auto mb-3 text-gray-400" />
            <p>No agentic analysis workflows have been run for this alert yet.</p>
            <p className="text-sm mt-1">Start an analysis to see detailed agent execution.</p>
          </div>
        ) : (
          <div className="space-y-4">
            {workflows.map((workflow) => (
              <div
                key={workflow.id}
                className="card hover:shadow-md transition-shadow cursor-pointer"
                onClick={() => router.push(`/dashboard/workflows/${workflow.id}`)}
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <h3 className="font-semibold">
                        Workflow Analysis
                      </h3>
                      {getStatusBadge(workflow.status)}
                      {workflow.final_verdict && (
                        <span className={cn(
                          'px-2 py-1 rounded text-xs font-medium',
                          workflow.final_verdict === 'false_positive' ? 'bg-green-100 text-green-800' :
                          workflow.final_verdict === 'true_positive' ? 'bg-red-100 text-red-800' :
                          'bg-yellow-100 text-yellow-800'
                        )}>
                          {workflow.final_verdict.split('_').map(w => 
                            w.charAt(0).toUpperCase() + w.slice(1)
                          ).join(' ')}
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-4 text-sm text-gray-600">
                      <div className="flex items-center gap-1">
                        <Clock className="w-4 h-4" />
                        {formatDuration(workflow.total_duration_seconds)}
                      </div>
                      <span>•</span>
                      <span>{workflow.total_agents_executed} agents executed</span>
                      <span>•</span>
                      <span className="text-green-600">{workflow.successful_executions} successful</span>
                      {workflow.failed_executions > 0 && (
                        <>
                          <span>•</span>
                          <span className="text-red-600">{workflow.failed_executions} failed</span>
                        </>
                      )}
                    </div>
                  </div>
                  <ExternalLink className="w-5 h-5 text-gray-400" />
                </div>

                {/* Progress bar */}
                <div className="w-full bg-gray-200 rounded-full h-2 mb-2">
                  <div
                    className={cn(
                      'h-2 rounded-full transition-all',
                      workflow.status === 'completed' ? 'bg-green-500' :
                      workflow.status === 'failed' ? 'bg-red-500' :
                      workflow.status === 'running' ? 'bg-blue-500' :
                      'bg-gray-400'
                    )}
                    style={{
                      width: workflow.total_agents_executed > 0
                        ? `${(workflow.successful_executions / workflow.total_agents_executed) * 100}%`
                        : '0%'
                    }}
                  />
                </div>

                <div className="flex items-center justify-between text-xs text-gray-500">
                  <span>
                    Started: {workflow.started_at ? new Date(workflow.started_at).toLocaleString() : 'N/A'}
                  </span>
                  {workflow.final_confidence_score !== null && (
                    <span>
                      Confidence: {(workflow.final_confidence_score * 100).toFixed(1)}%
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
