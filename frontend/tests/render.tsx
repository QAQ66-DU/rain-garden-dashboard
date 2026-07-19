import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render } from '@testing-library/react';
import type { ReactElement } from 'react';
import { createMemoryRouter, RouterProvider } from 'react-router-dom';

import { App } from '../src/App';
import { DeviceDetailPage } from '../src/pages/DeviceDetailPage';
import { DevicesPage } from '../src/pages/DevicesPage';
import { ExplorePage } from '../src/pages/ExplorePage';
import { NotFoundPage } from '../src/pages/NotFoundPage';
import { OverviewPage } from '../src/pages/OverviewPage';

export function renderRoute(path = '/') {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  const router = createMemoryRouter(
    [
      {
        path: '/',
        element: <App />,
        children: [
          { index: true, element: <OverviewPage /> },
          { path: 'explore', element: <ExplorePage /> },
          { path: 'devices', element: <DevicesPage /> },
          { path: 'devices/:deviceId', element: <DeviceDetailPage /> },
          { path: '*', element: <NotFoundPage /> },
        ],
      },
    ],
    { initialEntries: [path] },
  );

  const result = render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
  return { ...result, router };
}

export function renderWithQueryClient(element: ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return render(<QueryClientProvider client={queryClient}>{element}</QueryClientProvider>);
}
