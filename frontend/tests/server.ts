import { http, HttpResponse } from 'msw';
import { setupServer } from 'msw/node';

import {
  deviceDetailFixture,
  devicesFixture,
  measurementsFixture,
  overviewFixture,
  sitesFixture,
  treeDetailFixture,
  treeProbeId,
} from './fixtures/api';

export const handlers = [
  http.get('*/api/v1/overview', () => HttpResponse.json(overviewFixture)),
  http.get('*/api/v1/sites', () => HttpResponse.json(sitesFixture)),
  http.get('*/api/v1/devices', ({ request }) => {
    const params = new URL(request.url).searchParams;
    const search = params.get('search')?.toLowerCase();
    const feature = params.get('feature');
    const deviceType = params.get('device_type');
    const status = params.get('status');
    const items = devicesFixture.items.filter(
      (device) =>
        (!search || device.display_name.toLowerCase().includes(search)) &&
        (!feature || device.monitoring_feature?.public_slug === feature) &&
        (!deviceType || device.device_type === deviceType) &&
        (!status || device.freshness.calculated_status === status),
    );
    return HttpResponse.json({ ...devicesFixture, items });
  }),
  http.get('*/api/v1/devices/:deviceId', ({ params }) =>
    HttpResponse.json(params['deviceId'] === treeProbeId ? treeDetailFixture : deviceDetailFixture),
  ),
  http.get('*/api/v1/devices/:deviceId/measurements', () => HttpResponse.json(measurementsFixture)),
];

export const server = setupServer(...handlers);
