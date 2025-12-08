'use client';

import { AnalysisWorkflow } from '@/lib/api';
import { Clock, CheckCircle, XCircle, RefreshCw, Target, Code } from 'lucide-react';
import { cn } from '@/lib/utils';

interface WorkflowStatsProps {
  workflow: AnalysisWorkflow;
}

export function WorkflowStats({ workflow }: WorkflowStatsProps) {
  const successRate = workflow.total_agents_executed > 0
    ? (workflow.successful_executions / workflow.total_agents_executed) * 100
    : 0;

  const formatDuration = (seconds: number | null) => {
    if (!seconds) return 'N/A';
    if (seconds < 60) return `${seconds.toFixed(1)}s`;
    const minutes = Math.floor(seconds / 60);
    const secs = (seconds % 60).toFixed(0);
    return `${minutes}m ${secs}s`;
  };

  const getStatusBadge = () => {
    const statusColors = {
      completed: 'bg-green-100 text-green-800 border-green-300',
      running: 'bg-blue-100 text-blue-800 border-blue-300',
      pending: 'bg-gray-100 text-gray-800 border-gray-300',
      failed: 'bg-red-100 text-red-800 border-red-300',
    };

    return (
      <span className={cn(
        'px-3 py-1 rounded-full text-sm font-medium border',
        statusColors[workflow.status as keyof typeof statusColors] || statusColors.pending
      )}>
        {workflow.status.charAt(0).toUpperCase() + workflow.status.slice(1)}
      </span>
    );
  };

  const getVerdictBadge = () => {
    if (!workflow.final_verdict) return null;

    const verdictColors = {
      false_positive: 'bg-green-100 text-green-800',
      true_positive: 'bg-red-100 text-red-800',
      needs_review: 'bg-yellow-100 text-yellow-800',
    };

    return (
      <span className={cn(
        'px-3 py-1 rounded-full text-sm font-medium',
        verdictColors[workflow.final_verdict as keyof typeof verdictColors] || 'bg-gray-100 text-gray-800'
      )}>
        {workflow.final_verdict.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')}
      </span>
    );
  };

  const stats = [
    {
      label: 'Total Agents',
      value: workflow.total_agents_executed,
      icon: Target,
      color: 'text-blue-600',
    },
    {
      label: 'Successful',
      value: workflow.successful_executions,
      icon: CheckCircle,
      color: 'text-green-600',
    },
    {
      label: 'Failed',
      value: workflow.failed_executions,
      icon: XCircle,
      color: 'text-red-600',
    },
    {
      label: 'Retries',
      value: workflow.total_retries,
      icon: RefreshCw,
      color: 'text-orange-600',
    },
    {
      label: 'Refinements',
      value: workflow.total_refinements,
      icon: Target,
      color: 'text-purple-600',
    },
    {
      label: 'Code Matches',
      value: workflow.code_matches_found,
      icon: Code,
      color: 'text-indigo-600',
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">Workflow Analysis</h2>
          <p className="text-sm text-[var(--muted)] mt-1">
            {workflow.current_phase && (
              <span className="capitalize">Current Phase: {workflow.current_phase.replace('_', ' ')}</span>
            )}
          </p>
        </div>
        <div className="flex items-center gap-3">
          {getStatusBadge()}
          {getVerdictBadge()}
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        {stats.map((stat) => {
          const Icon = stat.icon;
          return (
            <div key={stat.label} className="card">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-medium text-[var(--muted)] uppercase">
                  {stat.label}
                </span>
                <Icon className={cn('w-4 h-4', stat.color)} />
              </div>
              <div className="text-2xl font-bold">
                {stat.value}
              </div>
            </div>
          );
        })}
      </div>

      {/* Duration and Success Rate */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="card">
          <div className="flex items-center gap-2 mb-2">
            <Clock className="w-4 h-4 text-[var(--muted)]" />
            <span className="text-xs font-medium text-[var(--muted)] uppercase">
              Total Duration
            </span>
          </div>
          <div className="text-2xl font-bold">
            {formatDuration(workflow.total_duration_seconds)}
          </div>
          {workflow.started_at && (
            <div className="text-xs text-[var(--muted)] mt-1">
              Started: {new Date(workflow.started_at).toLocaleString()}
            </div>
          )}
        </div>

        <div className="card">
          <div className="flex items-center gap-2 mb-2">
            <Target className="w-4 h-4 text-[var(--muted)]" />
            <span className="text-xs font-medium text-[var(--muted)] uppercase">
              Success Rate
            </span>
          </div>
          <div className="text-2xl font-bold">
            {successRate.toFixed(1)}%
          </div>
          <div className="text-xs text-[var(--muted)] mt-1">
            {workflow.successful_executions} / {workflow.total_agents_executed} executions
          </div>
        </div>

        {workflow.final_confidence_score !== null && (
          <div className="card">
            <div className="flex items-center gap-2 mb-2">
              <CheckCircle className="w-4 h-4 text-[var(--muted)]" />
              <span className="text-xs font-medium text-[var(--muted)] uppercase">
                Confidence Score
              </span>
            </div>
            <div className="text-2xl font-bold">
              {(workflow.final_confidence_score * 100).toFixed(1)}%
            </div>
          </div>
        )}
      </div>

      {/* Context */}
      {workflow.accumulated_context && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
          <h3 className="font-semibold text-amber-900 mb-2">Accumulated Context</h3>
          <p className="text-sm text-amber-800 whitespace-pre-wrap">
            {workflow.accumulated_context}
          </p>
        </div>
      )}
    </div>
  );
}
