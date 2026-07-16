export function SyntheticBanner() {
  return (
    <aside className="synthetic-banner" aria-label="Synthetic data notice">
      <span aria-hidden="true">◆</span>
      <div>
        <strong>Synthetic demonstration data</strong>
        <p>Illustrative test observations — not live sensor readings or performance evidence.</p>
      </div>
    </aside>
  );
}
