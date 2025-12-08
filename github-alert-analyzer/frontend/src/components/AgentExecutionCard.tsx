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
  Loader2,
  Info
} from 'lucide-react';
import { AgentExecution } from '@/lib/api';
import { cn } from '@/lib/utils';

interface AgentExecutionCardProps {
  execution: AgentExecution;
}

export function AgentExecutionCard({ execution }: AgentExecutionCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [showTooltip, setShowTooltip] = useState(false);

  const getAgentDescription = (agentName: string): string => {
    const descriptions: Record<string, string> = {
      'code_analyzer': 'Searches the codebase for actual usage of vulnerable functions. Uses pattern matching and optionally LLM to identify where the vulnerable package functions are called in your code.',
      'alert_fetcher': 'Fetches additional context about the dependency, including manifest files (package.json, requirements.txt) and how the package is configured in your project.',
      'deep_analyzer': 'Performs comprehensive security analysis using LLM reasoning. Examines code context, usage patterns, and determines if the vulnerability is actually exploitable in your specific codebase.',
      'reflection_agent': 'Meta-analysis agent that reviews the quality and confidence of the analysis. Detects patterns like unused packages, test-only usage, or contradictions, and decides if refinement is needed.',
      'false_positive_checker': 'Critical validation step that examines the findings to identify false positives. Validates whether flagged vulnerabilities are actually exploitable given your specific usage patterns.'
    };
    return descriptions[agentName] || 'Performs analysis on the security alert.';
  };

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
      <div 
        className="flex items-start justify-between cursor-pointer hover:opacity-80 transition-opacity"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center gap-3 flex-1">
          {getStatusIcon()}
          <div className="flex-1">
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2">
                <h4 className="text-xl font-bold text-gray-900">
                  {formatAgentName(execution.agent_name)}
                </h4>
                <div className="relative">
                  <button
                    onMouseEnter={() => setShowTooltip(true)}
                    onMouseLeave={() => setShowTooltip(false)}
                    onClick={(e) => e.stopPropagation()}
                    className="text-gray-400 hover:text-gray-600 transition-colors"
                    aria-label="Agent information"
                  >
                    <Info className="w-4 h-4" />
                  </button>
                  {showTooltip && (
                    <div className="absolute left-0 top-6 z-50 w-80 p-3 bg-gray-900 text-white text-xs rounded-lg shadow-lg">
                      <div className="absolute -top-1 left-4 w-2 h-2 bg-gray-900 transform rotate-45"></div>
                      {getAgentDescription(execution.agent_name)}
                    </div>
                  )}
                </div>
              </div>
              {execution.attempt_number > 1 && (
                <span className="px-2 py-0.5 text-xs bg-orange-100 text-orange-700 rounded-full font-medium">
                  Attempt {execution.attempt_number}
                </span>
              )}
              <span className="px-2 py-0.5 text-xs bg-blue-100 text-blue-700 rounded-full font-medium">
                {execution.phase.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')}
              </span>
              {execution.output_data?.llm_model_used && (
                <span className="px-2 py-0.5 text-xs bg-purple-100 text-purple-700 rounded-full font-medium">
                  🤖 {execution.output_data.llm_model_used.provider} / {execution.output_data.llm_model_used.model}
                </span>
              )}
            </div>
            <div className="flex items-center gap-4 mt-2 text-sm text-gray-600">
              <span className="font-medium">Order: {execution.execution_order}</span>
              {execution.duration_seconds !== null && (
                <>
                  <span>•</span>
                  <span className="font-medium">{formatDuration(execution.duration_seconds)}</span>
                </>
              )}
            </div>
          </div>
          <div className="flex-shrink-0 p-2 bg-white/80 rounded-full shadow-sm border border-gray-300">
            {isExpanded ? (
              <ChevronDown className="w-5 h-5 text-gray-700" />
            ) : (
              <ChevronRight className="w-5 h-5 text-gray-700" />
            )}
          </div>
        </div>
      </div>

      {isExpanded && (
        <div className="mt-4 space-y-4 pl-8">
          {execution.output_summary && (
            <div>
              <h5 className="font-semibold text-sm text-gray-900 mb-2 uppercase tracking-wide">Agent Response</h5>
              <div className="text-sm text-gray-700 bg-white p-4 rounded-lg border border-gray-200 shadow-sm leading-relaxed whitespace-pre-wrap">
                {execution.output_summary}
              </div>
            </div>
          )}

          {execution.output_data && Object.keys(execution.output_data).length > 0 && (
            <div>
              <h5 className="font-semibold text-sm text-gray-900 mb-2 uppercase tracking-wide">Detailed Output</h5>
              <div className="bg-white p-4 rounded-lg border border-gray-200 shadow-sm">
                {Object.entries(execution.output_data).map(([key, value]) => (
                  <div key={key} className="mb-3 last:mb-0">
                    <span className="font-semibold text-xs text-gray-600 uppercase tracking-wider">{key.replace(/_/g, ' ')}:</span>
                    <div className="mt-1 text-sm text-gray-800">
                      {typeof value === 'object' ? (
                        <pre className="text-xs bg-gray-50 p-2 rounded overflow-x-auto">
                          {JSON.stringify(value, null, 2)}
                        </pre>
                      ) : (
                        <span className="whitespace-pre-wrap">{String(value)}</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
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
            {execution.output_data?.llm_model_used && (
              <div>
                <span className="font-medium">LLM:</span>{' '}
                {execution.output_data.llm_model_used.provider} / {execution.output_data.llm_model_used.model}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
