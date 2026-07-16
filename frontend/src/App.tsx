import { Suspense } from 'react';
import { Outlet } from 'react-router-dom';

import { AppLayout } from './components/AppLayout';
import { LoadingState } from './components/DataState';
import { ErrorBoundary } from './components/ErrorBoundary';

export function App() {
  return (
    <ErrorBoundary>
      <AppLayout>
        <Suspense fallback={<LoadingState title="Loading dashboard view" />}>
          <Outlet />
        </Suspense>
      </AppLayout>
    </ErrorBoundary>
  );
}
