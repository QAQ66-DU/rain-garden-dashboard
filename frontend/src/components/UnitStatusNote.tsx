import { StatusLabel } from './StatusLabel';
import { unitStatusPresentation } from '../utils/unitStatus';

interface UnitStatusNoteProps {
  compact?: boolean;
  status: string;
}

export function UnitStatusNote({ compact = false, status }: UnitStatusNoteProps) {
  if (status === 'confirmed') return null;
  const presentation = unitStatusPresentation(status);
  return (
    <StatusLabel compact={compact} tone={presentation.tone}>
      {compact ? presentation.compactLabel : presentation.detailedLabel}
    </StatusLabel>
  );
}
