import type { ReactNode } from 'react';

interface MetricCardProps {
  label: string;
  value: ReactNode;
  note?: string;
  tone?: 'default' | 'warning';
}

export function MetricCard({ label, value, note, tone = 'default' }: MetricCardProps) {
  return (
    <article className={`metric-card metric-card--${tone}`}>
      <p>{label}</p>
      <div className="metric-card__value">{value}</div>
      {note ? <small>{note}</small> : null}
    </article>
  );
}
