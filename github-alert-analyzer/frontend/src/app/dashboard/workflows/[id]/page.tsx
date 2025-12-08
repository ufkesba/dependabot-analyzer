'use client';

import { useEffect, useState, useRef } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { ArrowLeft, Loader2, AlertTriangle, XCircle } from 'lucide-react';
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
  const [polling, setPolling] = useState(false);
  const [isTerminating, setIsTerminating] = useState(false);
  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    if (workflowId) {
      fetchWorkflow();
    }
  }, [workflowId]);

  // Poll for updates while workflow is running
  useEffect(() => {
    // Clear any existing interval first
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
      pollingIntervalRef.current = null;
    }

    if (!workflow) return;
    
    const isRunning = workflow.status === 'running' || workflow.status === 'pending';
    if (!isRunning) {
      setPolling(false);
      return;
    }

    setPolling(true);
    
    const pollWorkflow = async () => {
      try {
        const response = await fetch(`http://localhost:8000/api/analysis/workflows/${workflowId}/status`, {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
          },
        });
        
        if (response.ok) {
          const data = await response.json();
          if (data.status !== 'running' && data.status !== 'pending') {
            // Workflow completed - stop polling and fetch full data
            if (pollingIntervalRef.current) {
              clearInterval(pollingIntervalRef.current);
              pollingIntervalRef.current = null;
            }
            setPolling(false);
            fetchWorkflow();
          } else {
            // Update workflow with progress
            setWorkflow(prev => prev ? { ...prev, ...data } : null);
          }
        }
      } catch (err) {
        console.error('Polling error:', err);
      }
    };

    pollingIntervalRef.current = setInterval(pollWorkflow, 3000);

    return () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
        pollingIntervalRef.current = null;
      }
      setPolling(false);
    };
  }, [workflow?.status, workflowId]);

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

  const handleTerminate = async (status: 'failed' | 'cancelled') => {
    if (!confirm(`Are you sure you want to mark this workflow as ${status}? This action cannot be undone.`)) {
      return;
    }

    try {
      setIsTerminating(true);
      const token = localStorage.getItem('access_token');
      const response = await fetch(`http://localhost:8000/api/workflows/${workflowId}/status`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          status,
          error_message: `Workflow manually terminated by user`
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to terminate workflow');
      }

      const updatedWorkflow = await response.json();
      setWorkflow(updatedWorkflow);
      setPolling(false);
    } catch (err: any) {
      setError(err.message || 'Failed to terminate workflow');
      console.error(err);
    } finally {
      setIsTerminating(false);
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
      {/* Back button and status indicator */}
      <div className="flex items-center justify-between mb-6">
        <button
          onClick={() => router.back()}
          className="flex items-center gap-2 text-[var(--muted)] hover:text-[var(--foreground)]"
        >
          <ArrowLeft className="w-4 h-4" />
          Back
        </button>
        
        <div className="flex items-center gap-4">
          {polling && (
            <div className="flex items-center gap-2 text-blue-600">
              <Loader2 className="w-4 h-4 animate-spin" />
              <span className="text-sm">Live updating...</span>
            </div>
          )}
          
          {(workflow.status === 'running' || workflow.status === 'pending') && (
            <button
              onClick={() => handleTerminate('failed')}
              disabled={isTerminating}
              className="flex items-center gap-2 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-sm disabled:opacity-50"
            >
              {isTerminating ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Terminating...
                </>
              ) : (
                <>
                  <XCircle className="w-4 h-4" />
                  Terminate Workflow
                </>
              )}
            </button>
          )}
          
          {(workflow.status === 'completed' || workflow.status === 'failed') && (
            <button
              onClick={() => router.push(`/dashboard/alerts/${alert.id}`)}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm"
            >
              Start New Analysis
            </button>
          )}
        </div>
      </div>

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

      {/* Error Message */}
      {workflow.status === 'failed' && workflow.error_message && (
        <div className="card mb-8 bg-red-50 border border-red-200">
          <div className="flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <h3 className="font-semibold text-red-900 mb-1">Analysis Failed</h3>
              <p className="text-red-800 text-sm">{workflow.error_message}</p>
            </div>
          </div>
        </div>
      )}

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
