import type { ConnectivityStatus } from '../api/types';

interface StatusBadgeProps {
  status: ConnectivityStatus;
}

const labels: Record<ConnectivityStatus, string> = {
  online: 'Online',
  stale: 'Stale',
  offline: 'Offline',
  unknown: 'Unknown',
};

export function StatusBadge({ status }: StatusBadgeProps) {
  return (
    <span className={`status-badge status-badge--${status}`}>
      <span className="status-dot" aria-hidden="true" />
      {labels[status]}
    </span>
  );
}
