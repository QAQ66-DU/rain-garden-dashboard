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
      <aside className="site-sidebar">
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
            <small>Operations workspace</small>
          </span>
        </NavLink>
        <nav aria-label="Primary navigation">
          <NavLink to={{ pathname: '/', search: preservedSearch }} end>
            Overview
          </NavLink>
          <NavLink to={{ pathname: '/explore', search: preservedSearch }}>Explore</NavLink>
          <NavLink to={{ pathname: '/devices', search: preservedSearch }}>Devices</NavLink>
        </nav>
        <div className="site-sidebar__context">
          <span>Monitoring system</span>
          <small>Europe/London display</small>
        </div>
      </aside>
      <main className="page-shell">{children}</main>
      <footer className="site-footer">
        Rain Garden Monitoring · provenance-labelled data · UTC storage
      </footer>
    </div>
  );
}
