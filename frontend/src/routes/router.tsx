import { createBrowserRouter } from 'react-router-dom';

import { App } from '../App';
import { NotFoundPage } from '../pages/NotFoundPage';
import { DeviceDetailPage, DevicesPage, OverviewPage } from './lazyPages';

export const router = createBrowserRouter([
  {
    path: '/',
    element: <App />,
    children: [
      { index: true, element: <OverviewPage /> },
      { path: 'devices', element: <DevicesPage /> },
      { path: 'devices/:deviceId', element: <DeviceDetailPage /> },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
]);
