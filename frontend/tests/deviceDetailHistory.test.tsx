import { fireEvent, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { measurementsFixture, rainfallChannelId, weatherDeviceId } from './fixtures/api';
import { renderRoute } from './render';
import { server } from './server';

vi.mock('../src/components/TimeSeriesChart', () => ({
  TimeSeriesChart: ({
    title,
    subtitle,
    rangePreset,
    downsamplingApplied,
  }: {
    title: string;
    subtitle: string;
    rangePreset: string;
    downsamplingApplied: boolean;
  }) => (
    <section data-testid="time-series-chart" data-range-preset={rangePreset}>
      <h2>{title}</h2>
      <p>{subtitle}</p>
      {downsamplingApplied ? (
        <p>
          Chart downsampled for display. The full observation series remains available for export.
        </p>
      ) : null}
    </section>
  ),
}));

afterEach(() => {
  vi.restoreAllMocks();
});

function periodUrl(start: string, end: string, preset = 'custom') {
  const params = new URLSearchParams({ start, end, preset });
  return `/devices/${weatherDeviceId}?${params.toString()}`;
}

describe('Device Detail history controls and CSV export', () => {
  it('persists the default range and updates 24-hour, 7-day and 30-day URLs and counts', async () => {
    const user = userEvent.setup();
    server.use(
      http.get('*/api/v1/devices/:deviceId/measurements/chart', ({ request }) => {
        const params = new URL(request.url).searchParams;
        const start = params.get('start');
        const items = start?.startsWith('2026-05-31T12:00:00')
          ? measurementsFixture.items.slice(0, 1)
          : start?.startsWith('2026-05-02T12:00:00')
            ? measurementsFixture.items
            : measurementsFixture.items.slice(0, 2);
        return HttpResponse.json({
          ...measurementsFixture,
          items,
          total_matching: items.length,
          points_returned: items.length,
          start: start ?? measurementsFixture.start,
          end: params.get('end') ?? measurementsFixture.end,
        });
      }),
    );
    const { router } = renderRoute(`/devices/${weatherDeviceId}`);

    await waitFor(() => {
      const params = new URLSearchParams(router.state.location.search);
      expect(params.get('preset')).toBe('7d');
      expect(params.get('start')).toBe(measurementsFixture.start);
      expect(params.get('end')).toBe(measurementsFixture.end);
    });
    const rangeSelect = screen.getByRole('combobox', { name: 'Time range' });
    const channelSelect = screen.getByRole('combobox', { name: 'Sensor channel' });
    const selectedChannel = (channelSelect as HTMLSelectElement).value;
    expect(rangeSelect).toHaveValue('7d');

    await user.selectOptions(rangeSelect, '24h');
    await waitFor(() => {
      const params = new URLSearchParams(router.state.location.search);
      expect(params.get('preset')).toBe('24h');
      expect(params.get('start')).toBe('2026-05-31T12:00:00.000Z');
      expect(params.get('end')).toBe('2026-06-01T12:00:00.000Z');
    });
    expect(
      await screen.findByRole('heading', { name: 'Rainfall intensity · Last 24 hours' }),
    ).toBeVisible();
    expect(screen.getByText(/1 observations/)).toBeVisible();
    expect(screen.getByTestId('time-series-chart')).toHaveAttribute('data-range-preset', '24h');
    expect(channelSelect).toHaveValue(selectedChannel);

    await user.selectOptions(rangeSelect, '30d');
    await waitFor(() => {
      const params = new URLSearchParams(router.state.location.search);
      expect(params.get('preset')).toBe('30d');
      expect(params.get('start')).toBe('2026-05-02T12:00:00.000Z');
    });
    expect(
      await screen.findByRole('heading', { name: 'Rainfall intensity · Last 30 days' }),
    ).toBeVisible();
    expect(screen.getByText(/3 observations/)).toBeVisible();
    expect(screen.getByTestId('time-series-chart')).toHaveAttribute('data-range-preset', '30d');
    expect(channelSelect).toHaveValue(selectedChannel);

    await user.selectOptions(rangeSelect, '7d');
    await waitFor(() => {
      expect(new URLSearchParams(router.state.location.search).get('preset')).toBe('7d');
    });
    expect(
      await screen.findByRole('heading', { name: 'Rainfall intensity · Last 7 days' }),
    ).toBeVisible();
    expect(screen.getByTestId('time-series-chart')).toHaveAttribute('data-range-preset', '7d');
    expect(channelSelect).toHaveValue(selectedChannel);
  });

  it('displays large-range sampling metadata without showing the raw-result limit error', async () => {
    server.use(
      http.get('*/api/v1/devices/:deviceId/measurements/chart', () =>
        HttpResponse.json({
          ...measurementsFixture,
          total_matching: 9_614,
          points_returned: 2_000,
          downsampling_applied: true,
        }),
      ),
    );
    renderRoute(periodUrl('2026-07-13T12:00:00Z', '2026-08-12T12:00:00Z', '30d'));

    expect(await screen.findByText(/9,614 observations · 2,000 displayed/)).toBeVisible();
    expect(
      screen.getByText(
        'Chart downsampled for display. The full observation series remains available for export.',
      ),
    ).toBeVisible();
    expect(screen.queryByText(/maximum raw result size is 5000/i)).not.toBeInTheDocument();
  });

  it('reproduces and applies a custom Europe/London range as UTC URL parameters', async () => {
    const user = userEvent.setup();
    let requestedStart: string | null = null;
    let requestedEnd: string | null = null;
    server.use(
      http.get('*/api/v1/devices/:deviceId/measurements/chart', ({ request }) => {
        const params = new URL(request.url).searchParams;
        requestedStart = params.get('start');
        requestedEnd = params.get('end');
        return HttpResponse.json({
          ...measurementsFixture,
          start: requestedStart ?? measurementsFixture.start,
          end: requestedEnd ?? measurementsFixture.end,
        });
      }),
    );
    const { router } = renderRoute(periodUrl('2026-05-31T12:00:00Z', '2026-05-31T14:00:00Z'));

    expect(await screen.findByLabelText('Custom start (Europe/London)')).toHaveValue(
      '31/05/2026 13:00',
    );
    expect(screen.getByLabelText('Custom end (Europe/London)')).toHaveValue('31/05/2026 15:00');
    expect(screen.getByLabelText('Custom start (Europe/London)')).toHaveAttribute('lang', 'en-GB');
    expect(screen.queryByText('Format: DD/MM/YYYY HH:mm · 24-hour time')).not.toBeInTheDocument();
    expect(
      screen.getByText('Selected period: Custom range · Times shown in Europe/London.'),
    ).toBeInTheDocument();
    await user.click(
      screen.getByRole('button', {
        name: 'Custom start (Europe/London): open English calendar',
      }),
    );
    const picker = screen.getByRole('dialog', { name: 'Custom start (Europe/London) picker' });
    expect(picker).toHaveTextContent('May 2026');
    expect(picker).toHaveTextContent('MonTueWedThuFriSatSun');
    expect(picker).toHaveTextContent('Hour');
    expect(picker).toHaveTextContent('Minute');
    await user.click(screen.getByRole('button', { name: 'Cancel' }));
    await waitFor(() => {
      expect(requestedStart).toBe('2026-05-31T12:00:00Z');
      expect(requestedEnd).toBe('2026-05-31T14:00:00Z');
    });

    fireEvent.change(screen.getByLabelText('Custom start (Europe/London)'), {
      target: { value: '31/05/2026 10:00' },
    });
    fireEvent.change(screen.getByLabelText('Custom end (Europe/London)'), {
      target: { value: '31/05/2026 12:30' },
    });
    await user.click(screen.getByRole('button', { name: 'Apply custom range' }));

    await waitFor(() => {
      const params = new URLSearchParams(router.state.location.search);
      expect(params.get('start')).toBe('2026-05-31T09:00:00.000Z');
      expect(params.get('end')).toBe('2026-05-31T11:30:00.000Z');
      expect(params.get('preset')).toBe('custom');
    });
    expect(
      await screen.findByRole('heading', { name: 'Rainfall intensity · Custom range' }),
    ).toBeVisible();
  });

  it('blocks incomplete, malformed and reversed ranges before querying or exporting', async () => {
    const user = userEvent.setup();
    let measurementRequests = 0;
    server.use(
      http.get('*/api/v1/devices/:deviceId/measurements/chart', () => {
        measurementRequests += 1;
        return HttpResponse.json(measurementsFixture);
      }),
    );
    const { unmount } = renderRoute(
      `/devices/${weatherDeviceId}?start=2026-05-31T12%3A00%3A00Z&preset=custom`,
    );

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Both start and end timestamps are required.',
    );
    expect(screen.getByRole('button', { name: 'Export CSV' })).toBeDisabled();
    expect(measurementRequests).toBe(0);
    unmount();

    renderRoute(periodUrl('malformed', '2026-05-31T12:00:00Z'));
    expect(await screen.findByRole('alert')).toHaveTextContent('malformed start or end timestamp');
    expect(screen.getByRole('button', { name: 'Export CSV' })).toBeDisabled();
    expect(measurementRequests).toBe(0);

    await user.selectOptions(screen.getByRole('combobox', { name: 'Time range' }), 'custom');
    fireEvent.change(screen.getByLabelText('Custom start (Europe/London)'), {
      target: { value: '31/05/2026 14:00' },
    });
    fireEvent.change(screen.getByLabelText('Custom end (Europe/London)'), {
      target: { value: '31/05/2026 13:00' },
    });
    await user.click(screen.getByRole('button', { name: 'Apply custom range' }));
    expect(screen.getByRole('alert')).toHaveTextContent('Start must be earlier than end.');
  });

  it('downloads the selected device, channel and time range without navigating away', async () => {
    const user = userEvent.setup();
    let exportParams: URLSearchParams | undefined;
    server.use(
      http.get('*/api/v1/devices/:deviceId/measurements/export.csv', ({ params, request }) => {
        expect(params['deviceId']).toBe(weatherDeviceId);
        exportParams = new URL(request.url).searchParams;
        return new HttpResponse(
          'observed_at,measurement_value\r\n2026-05-31T12:00:00Z,1.200000\r\n',
          {
            headers: {
              'Content-Type': 'text/csv; charset=utf-8',
              'Content-Disposition':
                'attachment; filename="swale-weather-station_rainfall-intensity_2026-05-31_2026-06-01.csv"',
            },
          },
        );
      }),
    );
    const createObjectUrl = vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:test-export');
    const revokeObjectUrl = vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => undefined);
    let downloadedFilename = '';
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(function (
      this: HTMLAnchorElement,
    ) {
      downloadedFilename = this.download;
    });
    const { router } = renderRoute(
      periodUrl('2026-05-31T12:00:00Z', '2026-06-01T12:00:00Z', '24h'),
    );

    const exportButton = await screen.findByRole('button', { name: 'Export CSV' });
    expect(exportButton).toBeEnabled();
    const pathBeforeExport = router.state.location.pathname;
    await user.click(exportButton);

    await waitFor(() => {
      expect(createObjectUrl).toHaveBeenCalledOnce();
    });
    expect(exportParams?.get('sensor_channel_id')).toBe(rainfallChannelId);
    expect(exportParams?.get('start')).toBe('2026-05-31T12:00:00Z');
    expect(exportParams?.get('end')).toBe('2026-06-01T12:00:00Z');
    expect(downloadedFilename).toBe(
      'swale-weather-station_rainfall-intensity_2026-05-31_2026-06-01.csv',
    );
    expect(revokeObjectUrl).toHaveBeenCalledWith('blob:test-export');
    expect(router.state.location.pathname).toBe(pathBeforeExport);
  });

  it('shows a clear export failure without leaving Device Detail', async () => {
    const user = userEvent.setup();
    server.use(
      http.get('*/api/v1/devices/:deviceId/measurements/export.csv', () =>
        HttpResponse.json({ detail: 'CSV export is temporarily unavailable.' }, { status: 503 }),
      ),
    );
    renderRoute(periodUrl('2026-05-31T12:00:00Z', '2026-06-01T12:00:00Z', '24h'));

    await user.click(await screen.findByRole('button', { name: 'Export CSV' }));

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'CSV export is temporarily unavailable.',
    );
    expect(screen.getByRole('heading', { name: 'Swale weather station' })).toBeVisible();
  });
});
