import { Link } from 'react-router-dom';

export function NotFoundPage() {
  return (
    <section className="state-panel">
      <p className="eyebrow">404</p>
      <h1>Page not found</h1>
      <p>The requested dashboard view does not exist.</p>
      <Link className="button-link" to="/">
        Return to overview
      </Link>
    </section>
  );
}
