import { StatusLabel } from './StatusLabel';

interface ConfigurationStatusProps {
  compact?: boolean;
  status: string;
}

const labels: Record<string, string> = {
  configured: 'Configured',
  pending: 'Configuration pending',
};

export function ConfigurationStatus({ compact = false, status }: ConfigurationStatusProps) {
  return (
    <StatusLabel compact={compact} tone={status === 'configured' ? 'success' : 'warning'}>
      {labels[status] ?? 'Configuration unknown'}
    </StatusLabel>
  );
}
