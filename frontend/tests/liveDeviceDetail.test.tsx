import { act, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { afterEach, describe, expect, it, vi } from 'vitest';

import {
  replayChannelOneId,
  replayChannelTwoId,
  replayDeviceDetailFixture,
  replayDeviceId,
  replayMeasurementsFixture,
} from './fixtures/api';
import { renderRoute } from './render';
import { server } from './server';

vi.mock('../src/components/TimeSeriesChart', () => ({
  TimeSeriesChart: ({ title, subtitle }: { title: string; subtitle: string }) => (
    <section data-testid="time-series-chart">
      <h2>{title}</h2>
      <p>{subtitle}</p>
    </section>
  ),
}));

afterEach(() => {
  vi.useRealTimers();
});

describe('live Outflow A device detail', () => {
  it('polls every 30 seconds, preserves selection and cached data, and shows live provenance', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    const channelOne = replayMeasurementsFixture.items[0];
    const channelTwo = replayMeasurementsFixture.items[1];
    if (!channelOne || !channelTwo) throw new Error('Live test measurements are required');

    let deviceRequests = 0;
    let selectedChannelRequests = 0;
    server.use(
      http.get('*/api/v1/devices/:deviceId', ({ params }) => {
        if (params['deviceId'] !== replayDeviceId) return HttpResponse.json(null, { status: 404 });
        deviceRequests += 1;
        return HttpResponse.json({
          ...replayDeviceDetailFixture,
          ingestion_mode: 'live_mqtt',
          provenance: 'live_ttn_mqtt',
          last_seen_at: '2026-08-04T18:38:53Z',
          freshness: {
            ...replayDeviceDetailFixture.freshness,
            reference_time: '2026-08-04T18:38:53Z',
            status_basis: 'live_mqtt_reference_time',
          },
          telemetry: replayDeviceDetailFixture.telemetry
            ? {
                ...replayDeviceDetailFixture.telemetry,
                observed_at: '2026-08-04T18:38:53Z',
                gateway: 'TTN gateway (identifier withheld)',
              }
            : null,
        });
      }),
      http.get('*/api/v1/devices/:deviceId/measurements', ({ params, request }) => {
        if (params['deviceId'] !== replayDeviceId) return HttpResponse.json(null, { status: 404 });
        const selected = new URL(request.url).searchParams.get('sensor_channel_id');
        if (selected === replayChannelTwoId) {
          selectedChannelRequests += 1;
          if (selectedChannelRequests === 2) {
            return HttpResponse.json({ detail: 'Temporary refresh failure.' }, { status: 503 });
          }
          const items =
            selectedChannelRequests >= 3
              ? [
                  channelTwo,
                  {
                    ...channelTwo,
                    numeric_value: 201,
                    measured_at: '2026-08-04T18:39:53Z',
                  },
                ]
              : [channelTwo];
          return HttpResponse.json({
            ...replayMeasurementsFixture,
            items,
            total_matching: items.length,
            provenance: 'live_ttn_mqtt',
          });
        }
        return HttpResponse.json({
          ...replayMeasurementsFixture,
          items: selected === replayChannelOneId ? [channelOne] : [],
          total_matching: selected === replayChannelOneId ? 1 : 0,
          provenance: 'live_ttn_mqtt',
        });
      }),
    );

    renderRoute(`/devices/${replayDeviceId}`);

    expect(await screen.findByRole('heading', { name: 'Outflow A' })).toBeInTheDocument();
    expect(screen.getByText('Live TTN testbed data')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Live ingestion provenance' })).toBeInTheDocument();
    expect(screen.getByText('TTN application uplink')).toBeInTheDocument();
    expect(screen.getByText('Live MQTT reference time')).toBeInTheDocument();
    expect(screen.queryByText('TTN console export')).not.toBeInTheDocument();

    const controls = screen.getByRole('region', { name: 'Chart controls' });
    const channelSelect = within(controls).getByRole('combobox');
    await user.selectOptions(channelSelect, replayChannelTwoId);
    expect(channelSelect).toHaveValue(replayChannelTwoId);
    expect(await screen.findByText(/1 raw observations/)).toBeInTheDocument();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(30_000);
    });
    await waitFor(() => {
      expect(selectedChannelRequests).toBe(2);
    });
    expect(channelSelect).toHaveValue(replayChannelTwoId);
    expect(screen.getByTestId('time-series-chart')).toBeInTheDocument();
    expect(screen.getByText(/1 raw observations/)).toBeInTheDocument();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(30_000);
    });
    await waitFor(() => {
      expect(selectedChannelRequests).toBe(3);
    });
    expect(await screen.findByText(/2 raw observations/)).toBeInTheDocument();
    expect(channelSelect).toHaveValue(replayChannelTwoId);
    expect(deviceRequests).toBeGreaterThanOrEqual(3);
  });
});
