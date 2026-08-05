interface MetadataStatusNoteProps {
  status: string;
}

export function MetadataStatusNote({ status }: MetadataStatusNoteProps) {
  if (status === 'unverified') {
    return <span className="unit-status unit-status--pending">Metadata pending</span>;
  }
  return <span className="unit-status unit-status--confirmed">Metadata catalogued</span>;
}
