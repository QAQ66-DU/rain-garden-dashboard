import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';

import { MeasurementDisplay } from '../src/components/MeasurementDisplay';
import {
  devicesFixture,
  exploreFixture,
  replayDeviceId,
  siteId,
  treeProbeId,
  weatherDeviceId,
} from './fixtures/api';
import { renderRoute, renderWithQueryClient } from './render';
import { server } from './server';

describe('monitoring dashboard', () => {
  it('shows a provenance-labelled, summary-first overview without hiding sensor channels', async () => {
    renderRoute();

    expect(
      await screen.findByRole('heading', { name: 'Orchard Park monitoring site' }),
    ).toBeInTheDocument();
    expect(screen.getByText('Synthetic demonstration data')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Soil-moisture spread' })).toBeInTheDocument();
    expect(screen.getByText('Soil moisture sensor 1')).toBeInTheDocument();
    expect(screen.getByText('Soil moisture sensor 3')).toBeInTheDocument();
    expect(screen.getByText('Median')).toBeInTheDocument();
    expect(
      screen.getByRole('heading', { name: 'Orchard Park monitoring layout' }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole('region', { name: 'Interactive map of Orchard Park monitoring locations' }),
    ).toBeInTheDocument();
    expect(screen.getByText('Demo-normalised unit · not deployment-confirmed')).toBeInTheDocument();
    expect(screen.queryByText('Average')).not.toBeInTheDocument();
    expect(
      screen.getByRole('link', { name: /Review quality warnings in Time Explorer/ }),
    ).toHaveAttribute('href', expect.stringContaining('/explore?'));
  });

  it('lists all status states and filters devices by public display name', async () => {
    const user = userEvent.setup();
    renderRoute('/devices');

    expect(await screen.findByText('Swale weather station')).toBeInTheDocument();
    const table = screen.getByRole('table');
    expect(within(table).getByRole('columnheader', { name: 'Source' })).toBeInTheDocument();
    expect(
      within(table).getByRole('columnheader', { name: 'Operational status' }),
    ).toBeInTheDocument();
    expect(within(table).getByRole('columnheader', { name: 'Configuration' })).toBeInTheDocument();
    expect(within(table).getByRole('columnheader', { name: 'Units' })).toBeInTheDocument();
    expect(screen.getAllByText('Online')).not.toHaveLength(0);
    expect(screen.getAllByText('Stale')).not.toHaveLength(0);
    expect(screen.getAllByText('Offline')).not.toHaveLength(0);

    await user.type(screen.getByRole('searchbox', { name: 'Search devices' }), 'soil');

    expect(await screen.findByText('Swale soil sensor 1')).toBeInTheDocument();
    expect(screen.queryByText('Swale weather station')).not.toBeInTheDocument();
    expect(document.body).not.toHaveTextContent(['Dev', 'EUI'].join(''));
  });

  it('renders inventory columns from separate source, operational, configuration and unit fields', async () => {
    const livePending = {
      ...devicesFixture.items[0],
      display_name: 'Live pending device',
      ingestion_mode: 'live_mqtt',
      provenance: 'proxy',
      source_system: 'ttn',
      sensor_configuration_status: 'pending',
      unit_confirmation_summary: 'pending',
      freshness: {
        ...devicesFixture.items[0]?.freshness,
        calculated_status: 'online',
      },
    };
    const replayMixed = {
      ...devicesFixture.items[5],
      display_name: 'Replay mixed device',
      ingestion_mode: 'offline_replay',
      provenance: 'exported_live_data',
      source_system: 'ttn',
      unit_confirmation_summary: 'mixed',
      freshness: {
        ...devicesFixture.items[5]?.freshness,
        calculated_status: 'offline',
      },
    };
    const noChannels = {
      ...devicesFixture.items[7],
      display_name: 'No-channel device',
      last_seen_at: null,
      unit_confirmation_summary: 'no_active_channels',
      freshness: {
        ...devicesFixture.items[7]?.freshness,
        calculated_status: 'unknown',
      },
    };
    server.use(
      http.get('*/api/v1/devices', () =>
        HttpResponse.json({
          ...devicesFixture,
          items: [livePending, replayMixed, noChannels],
        }),
      ),
    );

    renderRoute('/devices');

    const table = await screen.findByRole('table');
    const liveRow = within(table).getByRole('row', { name: /Live pending device/ });
    expect(within(liveRow).getByText('Live MQTT')).toBeInTheDocument();
    expect(within(liveRow).getByText('Online')).toBeInTheDocument();
    expect(within(liveRow).getByText('Configuration pending')).toBeInTheDocument();
    expect(within(liveRow).getByText('Unit unverified')).toBeInTheDocument();

    const replayRow = within(table).getByRole('row', { name: /Replay mixed device/ });
    expect(within(replayRow).getByText('Offline replay')).toBeInTheDocument();
    expect(within(replayRow).getByText('Offline')).toBeInTheDocument();
    expect(within(replayRow).getByText('Mixed unit status')).toBeInTheDocument();

    const emptyRow = within(table).getByRole('row', { name: /No-channel device/ });
    expect(within(emptyRow).getByText('Unknown')).toBeInTheDocument();
    expect(within(emptyRow).getByText('Never received')).toBeInTheDocument();
    expect(within(emptyRow).getByText('No active channels')).toBeInTheDocument();
  });

  it('keeps the eight Orchard devices isolated from the ninth TTN Testbed row', async () => {
    const user = userEvent.setup();
    renderRoute('/devices');

    expect(await screen.findByText('Outflow A')).toBeInTheDocument();
    expect(within(screen.getByRole('table')).getAllByRole('row')).toHaveLength(10);
    expect(screen.getByText(/Testbed · TTN Testbed/)).toBeInTheDocument();
    expect(screen.getByText('Offline replay')).toBeInTheDocument();
    expect(screen.getByText('Unit unverified')).toBeInTheDocument();

    await user.selectOptions(screen.getByRole('combobox', { name: 'Site' }), siteId);
    await waitFor(() => {
      expect(screen.queryByText('Outflow A')).not.toBeInTheDocument();
    });
    expect(within(screen.getByRole('table')).getAllByRole('row')).toHaveLength(9);

    await user.selectOptions(
      screen.getByRole('combobox', { name: 'Site' }),
      '00000000-0000-4000-8000-000000000099',
    );
    expect(await screen.findByText('Outflow A')).toBeInTheDocument();
    expect(within(screen.getByRole('table')).getAllByRole('row')).toHaveLength(2);
  });

  it('renders one explicitly selected sensor channel as a raw seven-day series', async () => {
    renderRoute(
      `/devices/${weatherDeviceId}?start=2026-05-25T12%3A00%3A00Z&end=2026-06-01T12%3A00%3A00Z&preset=7d`,
    );

    expect(
      await screen.findByRole('heading', { name: 'Swale weather station' }),
    ).toBeInTheDocument();
    expect(await screen.findByTestId('time-series-chart')).toBeInTheDocument();
    expect(
      screen.getByRole('heading', { name: 'Rainfall intensity · Last 7 days' }),
    ).toBeInTheDocument();
    const controls = screen.getByRole('region', { name: 'Chart controls' });
    expect(within(controls).getByRole('combobox', { name: 'Sensor channel' })).toHaveValue(
      '00000000-0000-4000-8000-000000000021',
    );
    expect(screen.getByText(/Missing records are not converted to zero/)).toBeInTheDocument();
  });

  it('shows the confirmed tree-pit inventory item as configuration pending', async () => {
    renderRoute(`/devices/${treeProbeId}`);

    expect(
      await screen.findByRole('heading', { name: 'Tree-pit multi-depth probe' }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole('heading', { name: 'Sensor configuration pending' }),
    ).toBeInTheDocument();
    expect(screen.queryByRole('region', { name: 'Chart controls' })).not.toBeInTheDocument();
  });

  it('labels the isolated TTN replay device without inventing units or exposing raw IDs', async () => {
    renderRoute(`/devices/${replayDeviceId}`);

    expect(await screen.findByRole('heading', { name: 'Outflow A' })).toBeInTheDocument();
    expect(screen.getByText('Offline TTN replay data')).toBeInTheDocument();
    expect(screen.getAllByText('Unit unverified').length).toBeGreaterThan(0);
    expect(screen.getByText('Replay dataset reference time')).toBeInTheDocument();
    expect(screen.getAllByText('Offline replay').length).toBeGreaterThan(0);
    expect(screen.getByText('Replay gateway (identifier withheld)')).toBeInTheDocument();
    expect(screen.getByText('840')).toBeInTheDocument();
    expect(screen.getByText('200')).toBeInTheDocument();
    expect(screen.getByText('Measurement 2')).toBeInTheDocument();
    expect(screen.getAllByText('Metadata pending').length).toBeGreaterThanOrEqual(2);
    expect(screen.getAllByText('Unit unverified').length).toBeGreaterThanOrEqual(2);
    expect(document.body).not.toHaveTextContent(['Dev', 'EUI'].join(''));
    expect(document.body).not.toHaveTextContent('session_key_id');
  });

  it('renders unit-separated, synchronised channel small multiples with historical coverage', async () => {
    renderRoute(
      '/explore?start=2026-05-25T12%3A00%3A00Z&end=2026-06-01T12%3A00%3A00Z&preset=7d&feature=all&group=hydrology',
    );

    expect(await screen.findByRole('heading', { name: 'Explore' })).toBeInTheDocument();
    expect(await screen.findAllByTestId('explore-series-chart')).toHaveLength(2);
    expect(screen.getByRole('heading', { name: 'Rainfall intensity' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Water level' })).toBeInTheDocument();
    expect(screen.getByText('Unit · mm/h')).toBeInTheDocument();
    expect(screen.getByText('Unit · mm')).toBeInTheDocument();
    expect(
      screen.getAllByText('Current status above · historical availability below'),
    ).toHaveLength(2);
    expect(screen.getByText('100%')).toBeInTheDocument();
    expect(screen.getByText('98.81%')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Quality warnings' })).toBeInTheDocument();
    expect(screen.getByText('Relative humidity')).toBeInTheDocument();
    expect(screen.getByText('Excluded')).toBeInTheDocument();
  });

  it('renders sampled 24-hour, 7-day, 30-day and custom Explore ranges without a raw-limit error', async () => {
    const user = userEvent.setup();
    const requestedWindows: number[] = [];
    server.use(
      http.get('*/api/v1/explore', ({ request }) => {
        const params = new URL(request.url).searchParams;
        const start = params.get('start') ?? exploreFixture.start;
        const end = params.get('end') ?? exploreFixture.end;
        requestedWindows.push(Date.parse(end) - Date.parse(start));
        return HttpResponse.json({
          ...exploreFixture,
          start,
          end,
          total_matching: 11_816,
          points_returned: 4_000,
          downsampling_applied: true,
          series: exploreFixture.series.map((series) => ({
            ...series,
            total_matching: 5_908,
            points_returned: 2_000,
            downsampling_applied: true,
          })),
        });
      }),
    );
    const { router } = renderRoute(
      '/explore?start=2026-05-31T12%3A00%3A00Z&end=2026-06-01T12%3A00%3A00Z&preset=24h&feature=all&group=hydrology',
    );

    expect(
      await screen.findByText('11,816 observations · 4,000 displayed across 2 series.'),
    ).toBeVisible();
    expect(screen.getAllByText('5,908 observations · 2,000 displayed')).toHaveLength(2);
    expect(screen.queryByText(/maximum.*5000/i)).not.toBeInTheDocument();
    const range = screen.getByRole('combobox', { name: 'Time range' });
    const feature = screen.getByRole('combobox', { name: 'Feature' });
    const group = screen.getByRole('combobox', { name: 'Metric group' });
    expect(feature).toHaveValue('all');
    expect(group).toHaveValue('hydrology');

    await user.selectOptions(range, '7d');
    await waitFor(() => {
      expect(requestedWindows).toContain(7 * 24 * 60 * 60 * 1_000);
      expect(router.state.location.search).toContain('preset=7d');
    });
    await user.selectOptions(range, '30d');
    await waitFor(() => {
      expect(requestedWindows).toContain(30 * 24 * 60 * 60 * 1_000);
      expect(router.state.location.search).toContain('preset=30d');
    });

    await user.selectOptions(range, 'custom');
    fireEvent.change(screen.getByLabelText('Custom start (Europe/London)'), {
      target: { value: '20/05/2026 13:00' },
    });
    fireEvent.change(screen.getByLabelText('Custom end (Europe/London)'), {
      target: { value: '01/06/2026 13:00' },
    });
    await user.click(screen.getByRole('button', { name: 'Apply custom range' }));
    await waitFor(() => {
      expect(router.state.location.search).toContain('preset=custom');
    });
    expect(
      await screen.findByText('11,816 observations · 4,000 displayed across 2 series.'),
    ).toBeVisible();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(feature).toHaveValue('all');
    expect(group).toHaveValue('hydrology');
  });

  it('persists the selected period and filters when navigating to Devices', async () => {
    const user = userEvent.setup();
    const { router } = renderRoute(
      '/explore?start=2026-05-25T12%3A00%3A00Z&end=2026-06-01T12%3A00%3A00Z&preset=7d&feature=swale&group=hydrology',
    );

    await screen.findByRole('heading', { name: 'Explore' });
    await user.click(screen.getByRole('link', { name: /^Devices$/ }));

    await screen.findByRole('heading', { name: 'Devices' });
    expect(router.state.location.search).toContain('start=2026-05-25T12%3A00%3A00Z');
    expect(router.state.location.search).toContain('feature=swale');
    expect(router.state.location.search).toContain('group=hydrology');
  });

  it('updates preset URLs and shows the tree-pit configuration-pending state', async () => {
    const user = userEvent.setup();
    const { router } = renderRoute(
      '/explore?start=2026-05-25T12%3A00%3A00Z&end=2026-06-01T12%3A00%3A00Z&preset=7d&feature=all&group=hydrology',
    );
    await screen.findByRole('heading', { name: 'Explore' });

    await user.selectOptions(screen.getByRole('combobox', { name: 'Time range' }), '24h');
    await waitFor(() => {
      expect(router.state.location.search).toContain('preset=24h');
      expect(router.state.location.search).toContain('start=2026-05-31T12%3A00%3A00.000Z');
    });

    await user.selectOptions(screen.getByRole('combobox', { name: 'Feature' }), 'tree-pit');
    expect(
      await screen.findByRole('heading', { name: 'Channel configuration pending' }),
    ).toBeInTheDocument();
    expect(screen.queryByTestId('explore-series-chart')).not.toBeInTheDocument();
  });

  it('validates custom order and daylight-saving gaps before querying', async () => {
    const user = userEvent.setup();
    renderRoute(
      '/explore?start=2026-05-25T12%3A00%3A00Z&end=2026-06-01T12%3A00%3A00Z&preset=custom&feature=all&group=hydrology',
    );
    await screen.findByRole('heading', { name: 'Explore' });
    fireEvent.change(screen.getByLabelText('Custom start (Europe/London)'), {
      target: { value: '01/06/2026 13:00' },
    });
    fireEvent.change(screen.getByLabelText('Custom end (Europe/London)'), {
      target: { value: '01/06/2026 12:00' },
    });
    await user.click(screen.getByRole('button', { name: 'Apply custom range' }));
    expect(screen.getByRole('alert')).toHaveTextContent('Start must be earlier than end.');

    fireEvent.change(screen.getByLabelText('Custom start (Europe/London)'), {
      target: { value: '29/03/2026 01:30' },
    });
    fireEvent.change(screen.getByLabelText('Custom end (Europe/London)'), {
      target: { value: '29/03/2026 03:00' },
    });
    await user.click(screen.getByRole('button', { name: 'Apply custom range' }));
    expect(screen.getByRole('alert')).toHaveTextContent('daylight-saving transition');
  });

  it('labels coverage unavailable instead of inferring an unknown schedule', async () => {
    server.use(
      http.get('*/api/v1/explore', () =>
        HttpResponse.json({
          ...exploreFixture,
          series: exploreFixture.series.map((series) => ({
            ...series,
            coverage: {
              ...series.coverage,
              status: 'unavailable',
              status_detail:
                'Coverage unavailable because the reporting schedule is not confirmed.',
              expected_observations: null,
              received_observations: null,
              valid_observations: null,
              flagged_observations: null,
              missing_observations: null,
              coverage_percentage: null,
              missing_intervals: [],
            },
          })),
        }),
      ),
    );
    renderRoute(
      '/explore?start=2026-05-25T12%3A00%3A00Z&end=2026-06-01T12%3A00%3A00Z&preset=7d&feature=all&group=hydrology',
    );

    expect(await screen.findAllByText('Unavailable')).toHaveLength(2);
    expect(screen.getAllByText(/reporting schedule is not confirmed/)).toHaveLength(2);
  });

  it('shows a useful standard API error without exposing internals', async () => {
    server.use(
      http.get('*/api/v1/overview', () =>
        HttpResponse.json({ detail: 'Overview is temporarily unavailable.' }, { status: 503 }),
      ),
    );
    renderRoute();

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Overview is temporarily unavailable.',
    );
    expect(document.body).not.toHaveTextContent('Traceback');
  });
});

describe('measurement semantics', () => {
  it('distinguishes a measured zero from missing data', () => {
    renderWithQueryClient(
      <div>
        <MeasurementDisplay value={0} unit="mm" />
        <MeasurementDisplay value={null} unit="mm" />
      </div>,
    );

    expect(screen.getByText('0')).toBeInTheDocument();
    expect(screen.getByText('mm')).toBeInTheDocument();
    expect(screen.getByText('Not available')).toBeInTheDocument();
  });

  it('shows an unverified numeric decoder output without assigning a unit', () => {
    renderWithQueryClient(<MeasurementDisplay value={840} unit={null} />);

    expect(screen.getByText('840')).toBeInTheDocument();
    expect(screen.getByLabelText('Unit not verified')).toHaveTextContent('—');
  });
});
