import { screen } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { beforeEach, describe, expect, it } from 'vitest';

import {
  devicesFixture,
  exploreFixture,
  overviewFixture,
  replayDeviceDetailFixture,
} from './fixtures/api';
import { renderRoute } from './render';
import { server } from './server';

const proxySiteId = '00000000-0000-4000-8000-000000000099';
const proxyFeature = {
  id: '00000000-0000-4000-8000-000000000009',
  public_slug: 'proxy-sensors',
  display_name: 'Proxy sensors',
  feature_type: 'testbed',
};
const proxyIds = [
  'outflow-a',
  'soil-moisture-1',
  'prototype-board-1',
  'weather-station-2',
  'weather-station',
  'vision-ai',
  'ph-sensor',
  'soilmoisture-temp-sensor',
];
const proxyDevices = devicesFixture.items.slice(0, 8).map((device, index) => ({
  ...device,
  site_id: proxySiteId,
  site_name: 'TTN proxy network',
  monitoring_feature: proxyFeature,
  display_name: proxyIds[index] ?? 'missing-proxy-id',
  sensor_configuration_status: 'pending',
  environment: 'proxy',
  source_system: 'ttn',
  ingestion_mode: index === 0 ? 'live_mqtt' : null,
  provenance: 'proxy',
  is_test_device: true,
  last_seen_at: index === 0 ? '2026-08-05T12:00:00Z' : null,
  freshness: {
    ...device.freshness,
    calculated_status: index === 0 ? ('online' as const) : ('unknown' as const),
    age_seconds: index === 0 ? 0 : null,
    reference_time: '2026-08-05T12:00:00Z',
    status_basis: index === 0 ? 'live_mqtt_reference_time' : 'never_seen',
  },
}));

beforeEach(() => {
  server.use(
    http.get('*/api/v1/overview', () =>
      HttpResponse.json({
        ...overviewFixture,
        site_id: proxySiteId,
        site_name: 'TTN proxy network',
        public_location_label: 'Proxy network; not Orchard Park',
        synthetic: false,
        synthetic_notice:
          'Live proxy sensor data — these devices are not deployed at Orchard Park; physical units remain unverified.',
        reference_time: '2026-08-05T12:00:00Z',
        last_data_update: '2026-08-05T12:00:00Z',
        devices: { total: 8, online: 1, stale: 0, offline: 0, unknown: 7 },
        latest_rainfall_intensity: null,
        soil_moisture: null,
      }),
    ),
    http.get('*/api/v1/sites', () =>
      HttpResponse.json({
        next_cursor: null,
        items: [
          {
            id: proxySiteId,
            name: 'TTN proxy network',
            description: 'Live proxy sensor data.',
            public_location_label: 'Proxy network; not Orchard Park',
            location_disclosure: 'withheld',
            display_timezone: 'Europe/London',
            active: true,
          },
        ],
      }),
    ),
    http.get('*/api/v1/devices', () =>
      HttpResponse.json({
        synthetic: false,
        contains_replay_data: true,
        reference_time: '2026-08-05T12:00:00Z',
        next_cursor: null,
        items: proxyDevices,
      }),
    ),
    http.get('*/api/v1/devices/:deviceId', ({ params }) => {
      const selected = proxyDevices.find((device) => device.id === params['deviceId']);
      return HttpResponse.json({
        ...replayDeviceDetailFixture,
        ...selected,
        channels: [],
        latest_measurements: [],
        telemetry: null,
      });
    }),
    http.get('*/api/v1/explore', () =>
      HttpResponse.json({
        ...exploreFixture,
        site_id: proxySiteId,
        site_name: 'TTN proxy network',
        synthetic: false,
        available_devices: [],
        available_channels: [],
        selected_channel_ids: [],
        series: [],
        quality_warnings: [],
      }),
    ),
  );
});

describe('proxy TTN dashboard', () => {
  it('shows exactly the eight public TTN IDs and hides synthetic site filters', async () => {
    renderRoute('/devices');

    expect(await screen.findByText('Live proxy sensor data')).toBeInTheDocument();
    for (const deviceId of proxyIds) {
      expect(screen.getByRole('heading', { name: deviceId })).toBeInTheDocument();
    }
    expect(screen.getAllByRole('article')).toHaveLength(8);
    expect(screen.getByRole('option', { name: 'Proxy sensors' })).toBeInTheDocument();
    expect(screen.queryByRole('option', { name: 'Swale' })).not.toBeInTheDocument();
    expect(screen.queryByText('Orchard Park monitoring site')).not.toBeInTheDocument();
    expect(screen.getAllByText('Never seen / No data')).toHaveLength(7);
  });

  it('shows the required no-data state for vision-ai without channels', async () => {
    const vision = proxyDevices[5];
    if (!vision) throw new Error('vision-ai fixture is required');

    renderRoute(`/devices/${vision.id}`);

    expect(await screen.findByRole('heading', { name: 'vision-ai' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Never seen / No data' })).toBeInTheDocument();
    expect(screen.queryByRole('region', { name: 'Chart controls' })).not.toBeInTheDocument();
  });

  it('uses proxy provenance on Overview and Explore', async () => {
    const { router } = renderRoute('/');

    expect(await screen.findByRole('heading', { name: 'TTN proxy network' })).toBeInTheDocument();
    expect(screen.getByText('Live proxy sensor data')).toBeInTheDocument();

    await router.navigate(
      '/explore?start=2026-08-04T12%3A00%3A00Z&end=2026-08-05T12%3A00%3A00Z&preset=24h&feature=all&group=weather',
    );
    expect(await screen.findByRole('heading', { name: 'Explore' })).toBeInTheDocument();
    expect(screen.getByRole('option', { name: 'Proxy sensors' })).toBeInTheDocument();
    expect(screen.queryByRole('option', { name: 'Swale' })).not.toBeInTheDocument();
  });
});
