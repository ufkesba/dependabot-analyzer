import React from 'react';
import { AlertTriangle, CheckCircle, HelpCircle, Shield, Ban, Package, TestTube } from 'lucide-react';

interface StatusBadgeProps {
  type: 'risk' | 'exploitability' | 'priority';
  value: string | null | undefined;
  size?: 'sm' | 'md' | 'lg';
  showIcon?: boolean;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ 
  type, 
  value, 
  size = 'md',
  showIcon = true 
}) => {
  if (!value) return null;

  const sizeClasses = {
    sm: 'px-2 py-0.5 text-xs',
    md: 'px-2.5 py-1 text-sm',
    lg: 'px-3 py-1.5 text-base',
  };

  const iconSizes = {
    sm: 12,
    md: 14,
    lg: 16,
  };

  const iconSize = iconSizes[size];

  // Risk Status Badges
  if (type === 'risk') {
    const riskConfig = {
      true_positive: {
        label: 'True Positive',
        bg: 'bg-red-100 dark:bg-red-900/30',
        text: 'text-red-800 dark:text-red-200',
        border: 'border-red-300 dark:border-red-700',
        icon: AlertTriangle,
      },
      false_positive: {
        label: 'False Positive',
        bg: 'bg-green-100 dark:bg-green-900/30',
        text: 'text-green-800 dark:text-green-200',
        border: 'border-green-300 dark:border-green-700',
        icon: CheckCircle,
      },
      needs_review: {
        label: 'Needs Review',
        bg: 'bg-yellow-100 dark:bg-yellow-900/30',
        text: 'text-yellow-800 dark:text-yellow-200',
        border: 'border-yellow-300 dark:border-yellow-700',
        icon: HelpCircle,
      },
    };

    const config = riskConfig[value as keyof typeof riskConfig];
    if (!config) return null;

    const Icon = config.icon;

    return (
      <span className={`inline-flex items-center gap-1 ${sizeClasses[size]} font-medium rounded-md border ${config.bg} ${config.text} ${config.border}`}>
        {showIcon && <Icon size={iconSize} />}
        {config.label}
      </span>
    );
  }

  // Exploitability Level Badges
  if (type === 'exploitability') {
    const exploitConfig = {
      exploitable: {
        label: 'Exploitable',
        bg: 'bg-red-100 dark:bg-red-900/30',
        text: 'text-red-800 dark:text-red-200',
        border: 'border-red-300 dark:border-red-700',
        icon: Shield,
      },
      not_exploitable: {
        label: 'Not Exploitable',
        bg: 'bg-green-100 dark:bg-green-900/30',
        text: 'text-green-800 dark:text-green-200',
        border: 'border-green-300 dark:border-green-700',
        icon: Shield,
      },
      package_unused: {
        label: 'Package Unused',
        bg: 'bg-blue-100 dark:bg-blue-900/30',
        text: 'text-blue-800 dark:text-blue-200',
        border: 'border-blue-300 dark:border-blue-700',
        icon: Package,
      },
      test_only: {
        label: 'Test Only',
        bg: 'bg-purple-100 dark:bg-purple-900/30',
        text: 'text-purple-800 dark:text-purple-200',
        border: 'border-purple-300 dark:border-purple-700',
        icon: TestTube,
      },
    };

    const config = exploitConfig[value as keyof typeof exploitConfig];
    if (!config) return null;

    const Icon = config.icon;

    return (
      <span className={`inline-flex items-center gap-1 ${sizeClasses[size]} font-medium rounded-md border ${config.bg} ${config.text} ${config.border}`}>
        {showIcon && <Icon size={iconSize} />}
        {config.label}
      </span>
    );
  }

  // Action Priority Badges
  if (type === 'priority') {
    const priorityConfig = {
      critical: {
        label: 'Critical',
        bg: 'bg-red-100 dark:bg-red-900/30',
        text: 'text-red-800 dark:text-red-200',
        border: 'border-red-300 dark:border-red-700',
      },
      high: {
        label: 'High',
        bg: 'bg-orange-100 dark:bg-orange-900/30',
        text: 'text-orange-800 dark:text-orange-200',
        border: 'border-orange-300 dark:border-orange-700',
      },
      medium: {
        label: 'Medium',
        bg: 'bg-yellow-100 dark:bg-yellow-900/30',
        text: 'text-yellow-800 dark:text-yellow-200',
        border: 'border-yellow-300 dark:border-yellow-700',
      },
      low: {
        label: 'Low',
        bg: 'bg-blue-100 dark:bg-blue-900/30',
        text: 'text-blue-800 dark:text-blue-200',
        border: 'border-blue-300 dark:border-blue-700',
      },
      no_action: {
        label: 'No Action',
        bg: 'bg-gray-100 dark:bg-gray-900/30',
        text: 'text-gray-800 dark:text-gray-200',
        border: 'border-gray-300 dark:border-gray-700',
        icon: Ban,
      },
    };

    const config = priorityConfig[value as keyof typeof priorityConfig];
    if (!config) return null;

    const Icon = config.icon;

    return (
      <span className={`inline-flex items-center gap-1 ${sizeClasses[size]} font-medium rounded-md border ${config.bg} ${config.text} ${config.border}`}>
        {showIcon && Icon && <Icon size={iconSize} />}
        {config.label}
      </span>
    );
  }

  return null;
};

export default StatusBadge;
