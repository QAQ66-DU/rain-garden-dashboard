import { StatusLabel } from './StatusLabel';

interface MetadataStatusNoteProps {
  status: string;
}

export function MetadataStatusNote({ status }: MetadataStatusNoteProps) {
  if (status === 'unverified') {
    return <StatusLabel tone="warning">Metadata pending</StatusLabel>;
  }
  return <StatusLabel tone="success">Metadata catalogued</StatusLabel>;
}
