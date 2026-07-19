import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';

import { MeasurementDisplay } from '../src/components/MeasurementDisplay';
import { exploreFixture, treeProbeId, weatherDeviceId } from './fixtures/api';
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
    expect(screen.getByText('Demo-normalised unit · not deployment-confirmed')).toBeInTheDocument();
    expect(screen.queryByText('Average')).not.toBeInTheDocument();
    expect(
      screen.getByRole('link', { name: /Review quality warnings in Time Explorer/ }),
    ).toHaveAttribute('href', expect.stringContaining('/explore?'));
  });

  it('lists all status states and filters devices by public display name', async () => {
    const user = userEvent.setup();
    renderRoute('/devices');

    expect(
      await screen.findByRole('heading', { name: 'Swale weather station' }),
    ).toBeInTheDocument();
    expect(screen.getAllByText('Online')).not.toHaveLength(0);
    expect(screen.getAllByText('Stale')).not.toHaveLength(0);
    expect(screen.getAllByText('Offline')).not.toHaveLength(0);

    await user.type(screen.getByRole('searchbox', { name: 'Search devices' }), 'soil');

    expect(await screen.findByRole('heading', { name: 'Swale soil sensor 1' })).toBeInTheDocument();
    expect(
      screen.queryByRole('heading', { name: 'Swale weather station' }),
    ).not.toBeInTheDocument();
    expect(document.body).not.toHaveTextContent('DevEUI');
  });

  it('renders one explicitly selected sensor channel as a raw seven-day series', async () => {
    renderRoute(`/devices/${weatherDeviceId}`);

    expect(
      await screen.findByRole('heading', { name: 'Swale weather station' }),
    ).toBeInTheDocument();
    expect(await screen.findByTestId('time-series-chart')).toBeInTheDocument();
    expect(
      screen.getByRole('heading', { name: 'Rainfall intensity over time' }),
    ).toBeInTheDocument();
    const controls = screen.getByRole('region', { name: 'Chart controls' });
    expect(within(controls).getByRole('combobox')).toHaveValue(
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
      target: { value: '2026-06-01T13:00' },
    });
    fireEvent.change(screen.getByLabelText('Custom end (Europe/London)'), {
      target: { value: '2026-06-01T12:00' },
    });
    await user.click(screen.getByRole('button', { name: 'Apply custom range' }));
    expect(screen.getByRole('alert')).toHaveTextContent('Start must be earlier than end.');

    fireEvent.change(screen.getByLabelText('Custom start (Europe/London)'), {
      target: { value: '2026-03-29T01:30' },
    });
    fireEvent.change(screen.getByLabelText('Custom end (Europe/London)'), {
      target: { value: '2026-03-29T03:00' },
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
});
