import { formatNumber } from '../utils/format';

interface MeasurementDisplayProps {
  value: number | null | undefined;
  unit: string | null | undefined;
  compact?: boolean;
}

export function MeasurementDisplay({ value, unit, compact = false }: MeasurementDisplayProps) {
  if (value === null || value === undefined) {
    return <span className="missing-value">Not available</span>;
  }
  return (
    <span className={compact ? 'measurement measurement--compact' : 'measurement'}>
      <strong className="measurement__value">{formatNumber(value)}</strong>
      <span className="measurement__unit" aria-label={unit ? undefined : 'Unit not verified'}>
        {unit ?? '—'}
      </span>
    </span>
  );
}
