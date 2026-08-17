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
    const initialObservedAt = '2026-08-04T18:38:53Z';
    const nextObservedAt = '2026-08-04T18:39:53.442Z';
    const initialStart = '2026-07-28T18:38:54Z';
    const initialEnd = '2026-08-04T18:38:54Z';

    let deviceRequests = 0;
    let selectedChannelRequests = 0;
    let failNextSelectedChannelRequest = false;
    server.use(
      http.get('*/api/v1/devices/:deviceId', ({ params }) => {
        if (params['deviceId'] !== replayDeviceId) return HttpResponse.json(null, { status: 404 });
        deviceRequests += 1;
        const observedAt = deviceRequests >= 3 ? nextObservedAt : initialObservedAt;
        return HttpResponse.json({
          ...replayDeviceDetailFixture,
          ingestion_mode: 'live_mqtt',
          provenance: 'live_ttn_mqtt',
          last_seen_at: observedAt,
          freshness: {
            ...replayDeviceDetailFixture.freshness,
            reference_time: observedAt,
            status_basis: 'live_mqtt_reference_time',
          },
          telemetry: replayDeviceDetailFixture.telemetry
            ? {
                ...replayDeviceDetailFixture.telemetry,
                observed_at: observedAt,
                gateway: 'TTN gateway (identifier withheld)',
              }
            : null,
        });
      }),
      http.get('*/api/v1/devices/:deviceId/measurements/chart', ({ params, request }) => {
        if (params['deviceId'] !== replayDeviceId) return HttpResponse.json(null, { status: 404 });
        const query = new URL(request.url).searchParams;
        const selected = query.get('sensor_channel_id');
        const start = query.get('start') ?? initialStart;
        const end = query.get('end') ?? initialEnd;
        const includesNextObservation = Date.parse(end) > Date.parse(nextObservedAt);
        if (selected === replayChannelTwoId) {
          selectedChannelRequests += 1;
          if (failNextSelectedChannelRequest) {
            failNextSelectedChannelRequest = false;
            return HttpResponse.json({ detail: 'Temporary refresh failure.' }, { status: 503 });
          }
          const items = includesNextObservation
            ? [
                channelTwo,
                {
                  ...channelTwo,
                  numeric_value: 201,
                  measured_at: nextObservedAt,
                },
              ]
            : [channelTwo];
          return HttpResponse.json({
            ...replayMeasurementsFixture,
            items,
            total_matching: items.length,
            points_returned: items.length,
            start,
            end,
            provenance: 'live_ttn_mqtt',
          });
        }
        return HttpResponse.json({
          ...replayMeasurementsFixture,
          items: selected === replayChannelOneId ? [channelOne] : [],
          total_matching: selected === replayChannelOneId ? 1 : 0,
          points_returned: selected === replayChannelOneId ? 1 : 0,
          start,
          end,
          provenance: 'live_ttn_mqtt',
        });
      }),
    );

    const { router } = renderRoute(`/devices/${replayDeviceId}`);

    expect(await screen.findByRole('heading', { name: 'Outflow A' })).toBeInTheDocument();
    expect(screen.getByText('Live TTN testbed data')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Live ingestion provenance' })).toBeInTheDocument();
    expect(screen.getAllByText('Live MQTT').length).toBeGreaterThan(0);
    expect(screen.getByText('Live MQTT reference time')).toBeInTheDocument();
    expect(screen.queryByText('Offline replay')).not.toBeInTheDocument();
    await waitFor(() => {
      expect(new URLSearchParams(router.state.location.search).get('preset')).toBe('7d');
    });

    const controls = screen.getByRole('region', { name: 'Chart controls' });
    const channelSelect = within(controls).getByRole('combobox', { name: 'Sensor channel' });
    const rangeSelect = within(controls).getByRole('combobox', { name: 'Time range' });
    await user.selectOptions(channelSelect, replayChannelTwoId);
    expect(channelSelect).toHaveValue(replayChannelTwoId);
    expect(rangeSelect).toHaveValue('7d');
    expect(await screen.findByText(/1 raw observations/)).toBeInTheDocument();
    failNextSelectedChannelRequest = true;

    await act(async () => {
      await vi.advanceTimersByTimeAsync(30_000);
    });
    await waitFor(() => {
      expect(selectedChannelRequests).toBeGreaterThanOrEqual(2);
    });
    expect(channelSelect).toHaveValue(replayChannelTwoId);
    expect(rangeSelect).toHaveValue('7d');
    expect(screen.getByTestId('time-series-chart')).toBeInTheDocument();
    expect(screen.getByText(/1 raw observations/)).toBeInTheDocument();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(30_000);
    });
    await waitFor(() => {
      expect(selectedChannelRequests).toBeGreaterThanOrEqual(3);
    });
    expect(await screen.findByText(/2 raw observations/)).toBeInTheDocument();
    expect(channelSelect).toHaveValue(replayChannelTwoId);
    expect(rangeSelect).toHaveValue('7d');
    expect(screen.getByTestId('time-series-chart')).toBeInTheDocument();
    expect(new URLSearchParams(router.state.location.search).get('end')).toBe(
      '2026-08-04T18:39:53.443Z',
    );
    expect(deviceRequests).toBeGreaterThanOrEqual(3);
  });
});
