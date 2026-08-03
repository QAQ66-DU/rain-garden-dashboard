interface UnitStatusNoteProps {
  status: string;
}

export function UnitStatusNote({ status }: UnitStatusNoteProps) {
  if (status === 'synthetic_demo_only') {
    return (
      <span className="unit-status unit-status--demo">
        Demo-normalised unit · not deployment-confirmed
      </span>
    );
  }
  if (status === 'confirmed') {
    return <span className="unit-status unit-status--confirmed">Deployment unit confirmed</span>;
  }
  return <span className="unit-status unit-status--pending">Unit not verified</span>;
}
