import { humanizeCode } from '../utils/format';

interface IngestionSourceProps {
  compact?: boolean;
  ingestionMode: string | null;
  provenance?: string | null;
  sourceSystem?: string | null;
}

const ingestionLabels: Record<string, string> = {
  live_mqtt: 'Live MQTT',
  offline_replay: 'Offline replay',
};

const provenanceLabels: Record<string, string> = {
  exported_live_data: 'Exported test data',
  proxy: 'Proxy sensor',
};

function sourceLabel(value: string): string {
  return value.toLowerCase() === 'ttn' ? 'TTN' : humanizeCode(value);
}

export function IngestionSource({
  compact = false,
  ingestionMode,
  provenance,
  sourceSystem,
}: IngestionSourceProps) {
  const primary = ingestionMode
    ? (ingestionLabels[ingestionMode] ?? humanizeCode(ingestionMode))
    : sourceSystem
      ? sourceLabel(sourceSystem)
      : 'Not reported';
  const secondary = provenance
    ? (provenanceLabels[provenance] ?? humanizeCode(provenance))
    : ingestionMode && sourceSystem
      ? sourceLabel(sourceSystem)
      : null;

  return (
    <span className={`source-summary${compact ? ' source-summary--compact' : ''}`}>
      <strong>{primary}</strong>
      {secondary ? <small>{secondary}</small> : null}
    </span>
  );
}
