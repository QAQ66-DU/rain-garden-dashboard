import { http, HttpResponse } from 'msw';
import { setupServer } from 'msw/node';

import {
  deviceDetailFixture,
  devicesFixture,
  measurementsFixture,
  overviewFixture,
  sitesFixture,
} from './fixtures/api';

export const handlers = [
  http.get('*/api/v1/overview', () => HttpResponse.json(overviewFixture)),
  http.get('*/api/v1/sites', () => HttpResponse.json(sitesFixture)),
  http.get('*/api/v1/devices', ({ request }) => {
    const search = new URL(request.url).searchParams.get('search')?.toLowerCase();
    const items = search
      ? devicesFixture.items.filter((device) => device.display_name.toLowerCase().includes(search))
      : devicesFixture.items;
    return HttpResponse.json({ ...devicesFixture, items });
  }),
  http.get('*/api/v1/devices/:deviceId', () => HttpResponse.json(deviceDetailFixture)),
  http.get('*/api/v1/devices/:deviceId/measurements', () => HttpResponse.json(measurementsFixture)),
];

export const server = setupServer(...handlers);
