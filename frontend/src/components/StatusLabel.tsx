import type { ReactNode } from 'react';

type StatusTone = 'neutral' | 'info' | 'success' | 'warning' | 'danger';

interface StatusLabelProps {
  children: ReactNode;
  compact?: boolean;
  tone?: StatusTone;
}

export function StatusLabel({ children, compact = false, tone = 'neutral' }: StatusLabelProps) {
  return (
    <span
      className={`status-label status-label--${tone}${compact ? ' status-label--compact' : ''}`}
    >
      {children}
    </span>
  );
}
