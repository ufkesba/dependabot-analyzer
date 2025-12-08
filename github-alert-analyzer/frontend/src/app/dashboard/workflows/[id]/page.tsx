'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { ArrowLeft, Loader2, AlertTriangle } from 'lucide-react';
import { workflowApi, alertsApi, AnalysisWorkflow, Alert } from '@/lib/api';
import { WorkflowStats } from '@/components/WorkflowStats';
import { WorkflowTimeline } from '@/components/WorkflowTimeline';
import { getSeverityColor } from '@/lib/utils';

export default function WorkflowDetailPage() {
  const params = useParams();
  const router = useRouter();
  const workflowId = params.id as string;

  const [workflow, setWorkflow] = useState<AnalysisWorkflow | null>(null);
  const [alert, setAlert] = useState<Alert | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (workflowId) {
      fetchWorkflow();
    }
  }, [workflowId]);

  const fetchWorkflow = async () => {
    try {
      setIsLoading(true);
      const workflowData = await workflowApi.get(workflowId);
      setWorkflow(workflowData);

      // Fetch the associated alert
      const alertData = await alertsApi.get(workflowData.alert_id);
      setAlert(alertData);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load workflow');
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <Loader2 className="w-8 h-8 animate-spin text-primary-500" />
      </div>
    );
  }

  if (error || !workflow || !alert) {
    return (
      <div className="p-8">
        <div className="flex items-center gap-2 text-red-600 mb-4">
          <AlertTriangle className="w-5 h-5" />
          <span>{error || 'Workflow not found'}</span>
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
        Back
      </button>

      {/* Alert Info */}
      <div className="card mb-6">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-center gap-3 mb-2">
              <AlertTriangle className={`w-6 h-6 ${getSeverityColor(alert.severity)}`} />
              <h1 className="text-2xl font-bold">
                {alert.package_name}
              </h1>
              <span className={`px-3 py-1 rounded-full text-sm font-medium ${getSeverityColor(alert.severity)} bg-opacity-20`}>
                {alert.severity.toUpperCase()}
              </span>
            </div>
            <div className="flex items-center gap-4 text-sm text-gray-600">
              <span>{alert.package_ecosystem}</span>
              <span>•</span>
              <span>Alert #{alert.github_alert_number}</span>
              <span>•</span>
              <span className="capitalize">{alert.state}</span>
            </div>
            {alert.vulnerability?.summary && (
              <p className="mt-3 text-gray-700">
                {alert.vulnerability.summary}
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Workflow Stats */}
      <div className="mb-8">
        <WorkflowStats workflow={workflow} />
      </div>

      {/* Workflow Timeline */}
      <div className="card">
        <h2 className="text-xl font-bold mb-6">
          Agent Execution Timeline
        </h2>
        <WorkflowTimeline workflow={workflow} />
      </div>

      {/* Code Context Section */}
      {workflow.code_context && (
        <div className="mt-8 card">
          <h2 className="text-xl font-bold mb-4">
            Code Context
          </h2>
          <pre className="text-sm text-gray-700 bg-gray-50 p-4 rounded border overflow-x-auto">
            {workflow.code_context}
          </pre>
        </div>
      )}
    </div>
  );
}
