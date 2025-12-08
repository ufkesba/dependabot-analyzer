'use client';

import { useState } from 'react';
import { 
  CheckCircle, 
  XCircle, 
  Clock, 
  Play, 
  AlertCircle,
  ChevronDown,
  ChevronRight,
  Loader2
} from 'lucide-react';
import { AgentExecution } from '@/lib/api';
import { cn } from '@/lib/utils';

interface AgentExecutionCardProps {
  execution: AgentExecution;
}

export function AgentExecutionCard({ execution }: AgentExecutionCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  const getStatusIcon = () => {
    switch (execution.status) {
      case 'completed':
        return execution.success ? (
          <CheckCircle className="w-5 h-5 text-green-500" />
        ) : (
          <XCircle className="w-5 h-5 text-red-500" />
        );
      case 'running':
        return <Loader2 className="w-5 h-5 text-blue-500 animate-spin" />;
      case 'pending':
        return <Clock className="w-5 h-5 text-gray-400" />;
      case 'failed':
        return <XCircle className="w-5 h-5 text-red-500" />;
      default:
        return <AlertCircle className="w-5 h-5 text-yellow-500" />;
    }
  };

  const getStatusColor = () => {
    switch (execution.status) {
      case 'completed':
        return execution.success ? 'border-green-500 bg-green-50' : 'border-red-500 bg-red-50';
      case 'running':
        return 'border-blue-500 bg-blue-50';
      case 'pending':
        return 'border-gray-300 bg-gray-50';
      case 'failed':
        return 'border-red-500 bg-red-50';
      default:
        return 'border-yellow-500 bg-yellow-50';
    }
  };

  const formatDuration = (seconds: number | null) => {
    if (!seconds) return 'N/A';
    if (seconds < 1) return `${(seconds * 1000).toFixed(0)}ms`;
    if (seconds < 60) return `${seconds.toFixed(2)}s`;
    return `${(seconds / 60).toFixed(2)}m`;
  };

  const formatAgentName = (name: string) => {
    return name
      .split('_')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  };

  return (
    <div className={cn('border-l-4 p-4 rounded-lg shadow-sm', getStatusColor())}>
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3 flex-1">
          {getStatusIcon()}
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <h4 className="font-semibold">
                {formatAgentName(execution.agent_name)}
              </h4>
              {execution.attempt_number > 1 && (
                <span className="px-2 py-0.5 text-xs bg-orange-100 text-orange-700 rounded-full">
                  Attempt {execution.attempt_number}
                </span>
              )}
            </div>
            <div className="flex items-center gap-4 mt-1 text-sm text-gray-600">
              <span className="capitalize">{execution.phase.replace('_', ' ')}</span>
              <span>•</span>
              <span>Order: {execution.execution_order}</span>
              {execution.duration_seconds !== null && (
                <>
                  <span>•</span>
                  <span>{formatDuration(execution.duration_seconds)}</span>
                </>
              )}
            </div>
          </div>
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="p-1 hover:bg-gray-200 rounded"
            aria-label="Toggle details"
          >
            {isExpanded ? (
              <ChevronDown className="w-5 h-5" />
            ) : (
              <ChevronRight className="w-5 h-5" />
            )}
          </button>
        </div>
      </div>

      {isExpanded && (
        <div className="mt-4 space-y-3 pl-8">
          {execution.output_summary && (
            <div>
              <h5 className="font-medium text-sm text-gray-700 mb-1">Summary</h5>
              <p className="text-sm text-gray-600 bg-white p-3 rounded border">
                {execution.output_summary}
              </p>
            </div>
          )}

          {execution.output_data && Object.keys(execution.output_data).length > 0 && (
            <div>
              <h5 className="font-medium text-sm text-gray-700 mb-1">Output Data</h5>
              <pre className="text-xs text-gray-600 bg-white p-3 rounded border overflow-x-auto">
                {JSON.stringify(execution.output_data, null, 2)}
              </pre>
            </div>
          )}

          {execution.error_message && (
            <div>
              <h5 className="font-medium text-sm text-red-700 mb-1">Error</h5>
              <p className="text-sm text-red-600 bg-red-50 p-3 rounded border border-red-200">
                {execution.error_message}
              </p>
            </div>
          )}

          {execution.extra_data && Object.keys(execution.extra_data).length > 0 && (
            <div>
              <h5 className="font-medium text-sm text-gray-700 mb-1">Additional Data</h5>
              <pre className="text-xs text-gray-600 bg-white p-3 rounded border overflow-x-auto">
                {JSON.stringify(execution.extra_data, null, 2)}
              </pre>
            </div>
          )}

          <div className="flex gap-4 text-xs text-gray-500 pt-2 border-t">
            {execution.started_at && (
              <div>
                <span className="font-medium">Started:</span>{' '}
                {new Date(execution.started_at).toLocaleString()}
              </div>
            )}
            {execution.completed_at && (
              <div>
                <span className="font-medium">Completed:</span>{' '}
                {new Date(execution.completed_at).toLocaleString()}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
