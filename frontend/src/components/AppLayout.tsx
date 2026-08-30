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
          aria-label="Orchard Park Monitor home"
        >
          <strong>Orchard Park Monitor</strong>
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
        </div>
      </aside>
      <main className="page-shell">{children}</main>
    </div>
  );
}
