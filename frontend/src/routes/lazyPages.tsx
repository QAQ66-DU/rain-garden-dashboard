import { lazy } from 'react';

export const OverviewPage = lazy(() =>
  import('../pages/OverviewPage').then((module) => ({ default: module.OverviewPage })),
);

export const DevicesPage = lazy(() =>
  import('../pages/DevicesPage').then((module) => ({ default: module.DevicesPage })),
);

export const DeviceDetailPage = lazy(() =>
  import('../pages/DeviceDetailPage').then((module) => ({ default: module.DeviceDetailPage })),
);
