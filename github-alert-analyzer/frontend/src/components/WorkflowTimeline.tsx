'use client';

import { AnalysisWorkflow, AgentExecution } from '@/lib/api';
import { AgentExecutionCard } from './AgentExecutionCard';
import { cn } from '@/lib/utils';

interface WorkflowTimelineProps {
  workflow: AnalysisWorkflow;
}

export function WorkflowTimeline({ workflow }: WorkflowTimelineProps) {
  const executions = workflow.agent_executions || [];
  
  // Group executions by phase
  const phases = executions.reduce((acc, execution) => {
    if (!acc[execution.phase]) {
      acc[execution.phase] = [];
    }
    acc[execution.phase].push(execution);
    return acc;
  }, {} as Record<string, AgentExecution[]>);

  const phaseOrder = [
    'initial',
    'code_analysis',
    'deep_analysis',
    'reflection',
    'fp_check',
    'completed',
    'failed'
  ];

  const sortedPhases = Object.keys(phases).sort((a, b) => {
    const aIndex = phaseOrder.indexOf(a);
    const bIndex = phaseOrder.indexOf(b);
    if (aIndex === -1) return 1;
    if (bIndex === -1) return -1;
    return aIndex - bIndex;
  });

  const getPhaseColor = (phase: string) => {
    switch (phase) {
      case 'initial':
        return 'bg-gray-100 text-gray-700 border-gray-300';
      case 'code_analysis':
        return 'bg-blue-100 text-blue-700 border-blue-300';
      case 'deep_analysis':
        return 'bg-purple-100 text-purple-700 border-purple-300';
      case 'reflection':
        return 'bg-yellow-100 text-yellow-700 border-yellow-300';
      case 'fp_check':
        return 'bg-green-100 text-green-700 border-green-300';
      case 'completed':
        return 'bg-emerald-100 text-emerald-700 border-emerald-300';
      case 'failed':
        return 'bg-red-100 text-red-700 border-red-300';
      default:
        return 'bg-gray-100 text-gray-700 border-gray-300';
    }
  };

  const formatPhaseName = (phase: string) => {
    return phase
      .split('_')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  };

  return (
    <div className="space-y-6">
      {sortedPhases.map((phase, phaseIndex) => {
        const phaseExecutions = phases[phase];
        const phaseSuccess = phaseExecutions.every(e => e.success);
        const phaseComplete = phaseExecutions.every(e => e.status === 'completed');
        
        return (
          <div key={phase} className="relative">
            {/* Phase connector line */}
            {phaseIndex < sortedPhases.length - 1 && (
              <div className="absolute left-6 top-12 bottom-0 w-0.5 bg-gray-300" />
            )}
            
            {/* Phase header */}
            <div className="flex items-center gap-3 mb-4">
              <div
                className={cn(
                  'w-12 h-12 rounded-full flex items-center justify-center font-bold text-lg border-2 z-10',
                  getPhaseColor(phase)
                )}
              >
                {phaseIndex + 1}
              </div>
              <div className="flex-1">
                <h3 className="text-lg font-semibold">
                  {formatPhaseName(phase)}
                </h3>
                <div className="flex items-center gap-3 text-sm text-gray-600">
                  <span>{phaseExecutions.length} execution{phaseExecutions.length !== 1 ? 's' : ''}</span>
                  {phaseComplete && (
                    <>
                      <span>•</span>
                      <span className={phaseSuccess ? 'text-green-600 font-medium' : 'text-red-600 font-medium'}>
                        {phaseSuccess ? 'Success' : 'Failed'}
                      </span>
                    </>
                  )}
                </div>
              </div>
            </div>

            {/* Executions in this phase */}
            <div className="ml-16 space-y-3">
              {phaseExecutions
                .sort((a, b) => a.execution_order - b.execution_order)
                .map((execution) => (
                  <AgentExecutionCard key={execution.id} execution={execution} />
                ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}
