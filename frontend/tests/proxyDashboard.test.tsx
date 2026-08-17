import { screen, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { beforeEach, describe, expect, it } from 'vitest';

import {
  devicesFixture,
  exploreFixture,
  overviewFixture,
  replayDeviceDetailFixture,
  replayMeasurementsFixture,
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
  unit_confirmation_summary:
    index === 2 || index === 5 ? ('no_active_channels' as const) : ('pending' as const),
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
        total_matching: 0,
        points_returned: 0,
        downsampling_applied: false,
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
      expect(screen.getByText(deviceId)).toBeInTheDocument();
    }
    expect(within(screen.getByRole('table')).getAllByRole('row')).toHaveLength(9);
    expect(screen.getByRole('option', { name: 'Proxy sensors' })).toBeInTheDocument();
    expect(screen.queryByRole('option', { name: 'Swale' })).not.toBeInTheDocument();
    expect(screen.queryByText('Orchard Park monitoring site')).not.toBeInTheDocument();
    expect(screen.getAllByText('Never received')).toHaveLength(7);
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

  it('separates valid observations from pending channel metadata', async () => {
    const outflow = proxyDevices[0];
    if (!outflow) throw new Error('outflow-a fixture is required');
    server.use(
      http.get('*/api/v1/devices/:deviceId', () =>
        HttpResponse.json({
          ...replayDeviceDetailFixture,
          ...outflow,
          ingestion_mode: 'live_mqtt',
          provenance: 'proxy',
        }),
      ),
      http.get('*/api/v1/devices/:deviceId/measurements/chart', () =>
        HttpResponse.json({
          ...replayMeasurementsFixture,
          provenance: 'proxy',
        }),
      ),
    );

    renderRoute(`/devices/${outflow.id}`);

    expect(await screen.findByRole('heading', { name: 'outflow-a' })).toBeInTheDocument();
    expect(screen.getAllByText('Metadata pending').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Unit unverified').length).toBeGreaterThan(0);
    expect(screen.queryByText(/flagged observations/iu)).not.toBeInTheDocument();
  });

  it('shows basic unverified summaries without treating points as quality warnings', async () => {
    const baseSeries = exploreFixture.series[0];
    if (!baseSeries) throw new Error('explore series fixture is required');
    const channel = {
      ...baseSeries.channel,
      channel_name: 'Measurement 1',
      metric_code: 'unverified_numeric_output',
      metric_name: 'Unverified numeric output',
      metric_group: 'operational',
      unit_code: null,
      unit_symbol: null,
      unit_confirmation_status: 'pending',
      verification_status: 'unverified',
      expected_reporting_interval_seconds: null,
      reporting_schedule_anchor_at: null,
      reporting_jitter_tolerance_seconds: null,
    };
    server.use(
      http.get('*/api/v1/explore', () =>
        HttpResponse.json({
          ...exploreFixture,
          site_id: proxySiteId,
          site_name: 'TTN proxy network',
          metric_group: 'operational',
          available_channels: [channel],
          selected_channel_ids: [channel.channel_id],
          series: [
            {
              ...baseSeries,
              channel,
              points: baseSeries.points.slice(0, 2).map((point) => ({
                ...point,
                quality_flag: 'valid',
                included_in_summary: true,
                expected_slot_at: null,
                timing_status: 'schedule_unavailable',
              })),
              total_matching: 2,
              points_returned: 2,
              downsampling_applied: false,
              summary: {
                status: 'available',
                status_detail: 'Basic valid observations; metadata remains unverified.',
                statistics: [
                  { code: 'latest', label: 'Latest', value: 1.4, observed_at: null },
                  { code: 'count', label: 'Count', value: 2, observed_at: null },
                  { code: 'minimum', label: 'Minimum', value: 0, observed_at: null },
                  { code: 'median', label: 'Median', value: 0.7, observed_at: null },
                  { code: 'maximum', label: 'Maximum', value: 1.4, observed_at: null },
                ],
              },
              coverage: {
                ...baseSeries.coverage,
                status: 'unavailable',
                expected_observations: null,
                received_observations: null,
                valid_observations: null,
                flagged_observations: null,
                missing_observations: null,
                coverage_percentage: null,
              },
            },
          ],
          total_matching: 2,
          points_returned: 2,
          downsampling_applied: false,
          quality_warnings: [],
        }),
      ),
    );

    renderRoute(
      '/explore?start=2026-08-04T12%3A00%3A00Z&end=2026-08-05T12%3A00%3A00Z&preset=24h&feature=all&group=operational',
    );

    expect(await screen.findByRole('heading', { name: 'Unverified numeric output' })).toBeVisible();
    expect(screen.getByText('Metadata pending')).toBeVisible();
    expect(screen.getByText('Unit unverified')).toBeVisible();
    expect(screen.getByText('Count').nextElementSibling).toHaveTextContent('2');
    expect(screen.getByText('No flagged observations in this selected period.')).toBeVisible();
  });
});
