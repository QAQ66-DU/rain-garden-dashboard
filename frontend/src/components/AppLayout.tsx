import type { ReactNode } from 'react';
import { NavLink, useLocation } from 'react-router-dom';

interface AppLayoutProps {
  children: ReactNode;
}

export function AppLayout({ children }: AppLayoutProps) {
  const location = useLocation();
  const preservedSearch = location.search;
  return (
    <div className="app-shell">
      <header className="site-header">
        <NavLink
          className="brand"
          to={{ pathname: '/', search: preservedSearch }}
          aria-label="Rain Garden Dashboard home"
        >
          <span className="brand-mark" aria-hidden="true">
            RG
          </span>
          <span>
            <strong>Rain Garden</strong>
            <small>Monitoring dashboard</small>
          </span>
        </NavLink>
        <nav aria-label="Primary navigation">
          <NavLink to={{ pathname: '/', search: preservedSearch }} end>
            Overview
          </NavLink>
          <NavLink to={{ pathname: '/explore', search: preservedSearch }}>Explore</NavLink>
          <NavLink to={{ pathname: '/devices', search: preservedSearch }}>Devices</NavLink>
        </nav>
        <span className="research-tag">MSc research</span>
      </header>
      <main className="page-shell">{children}</main>
      <footer className="site-footer">
        Synthetic research interface · UTC storage · Europe/London display
      </footer>
    </div>
  );
}
