interface StateProps {
  title: string;
  message: string;
}

interface OptionalStateProps {
  title?: string | undefined;
  message?: string | undefined;
}

export function LoadingState({
  title = 'Loading dashboard data',
  message = 'Reading the bounded local dataset…',
}: OptionalStateProps) {
  return (
    <section className="state-panel" aria-live="polite">
      <span className="loading-pulse" aria-hidden="true" />
      <h2>{title}</h2>
      <p>{message}</p>
    </section>
  );
}

export function ErrorState({
  title = 'Data could not be loaded',
  message = 'Check that the API and database are available, then try again.',
}: OptionalStateProps) {
  return (
    <section className="state-panel state-panel--error" role="alert">
      <p className="eyebrow">Request failed</p>
      <h2>{title}</h2>
      <p>{message}</p>
    </section>
  );
}

export function EmptyState({ title, message }: StateProps) {
  return (
    <section className="state-panel">
      <p className="eyebrow">No observations</p>
      <h2>{title}</h2>
      <p>{message}</p>
    </section>
  );
}
