import type { ReactNode } from 'react';
import { NavLink } from 'react-router-dom';

interface AppLayoutProps {
  children: ReactNode;
}

export function AppLayout({ children }: AppLayoutProps) {
  return (
    <div className="app-shell">
      <header className="site-header">
        <NavLink className="brand" to="/" aria-label="Rain Garden Dashboard home">
          <span className="brand-mark" aria-hidden="true">
            RG
          </span>
          <span>
            <strong>Rain Garden</strong>
            <small>Monitoring dashboard</small>
          </span>
        </NavLink>
        <nav aria-label="Primary navigation">
          <NavLink to="/" end>
            Overview
          </NavLink>
          <NavLink to="/devices">Devices</NavLink>
        </nav>
        <span className="research-tag">MSc research</span>
      </header>
      <main className="page-shell">{children}</main>
      <footer className="site-footer">
        Synthetic Phase 1 research interface · Timestamps stored in UTC
      </footer>
    </div>
  );
}
