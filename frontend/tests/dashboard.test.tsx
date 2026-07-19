import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';

import { MeasurementDisplay } from '../src/components/MeasurementDisplay';
import { treeProbeId, weatherDeviceId } from './fixtures/api';
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
