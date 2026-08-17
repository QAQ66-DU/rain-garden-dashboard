import { fireEvent, render, screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { OrchardParkMap } from '../src/components/OrchardParkMap';
import { ORCHARD_PARK_SENSORS, ORCHARD_PARK_SENSOR_TYPES } from '../src/data/orchardParkSensors';

describe('Orchard Park monitoring map', () => {
  it('keeps the confirmed eight-location reference inventory separate from device status', () => {
    expect(ORCHARD_PARK_SENSORS).toHaveLength(8);
    expect(new Set(ORCHARD_PARK_SENSORS.map(({ id }) => id)).size).toBe(8);
    expect(new Set(ORCHARD_PARK_SENSORS.map(({ sensorType }) => sensorType))).toEqual(
      new Set(ORCHARD_PARK_SENSOR_TYPES),
    );
    expect(ORCHARD_PARK_SENSORS.map(({ latitude, longitude }) => [latitude, longitude])).toEqual([
      [55.955391, -3.238305],
      [55.95547, -3.237539],
      [55.955613, -3.236647],
      [55.955383, -3.238577],
      [55.955405, -3.237983],
      [55.955528, -3.237223],
      [55.955312, -3.238602],
      [55.955466, -3.23919],
    ]);

    const serializedInventory = JSON.stringify(ORCHARD_PARK_SENSORS).toLowerCase();
    expect(serializedInventory).not.toMatch(/planned|online|offline|stale|gateway|ttn|device id/);
  });

  it('renders a four-type legend and concise marker details', () => {
    render(<OrchardParkMap />);

    const map = screen.getByRole('region', {
      name: 'Interactive map of Orchard Park monitoring locations',
    });
    const legend = within(map.parentElement ?? map).getByRole('complementary', {
      name: 'Sensor type legend',
    });
    expect(within(legend).getByText('Soil moisture')).toBeInTheDocument();
    expect(within(legend).getByText('Water level')).toBeInTheDocument();
    expect(within(legend).getByText('Weather station')).toBeInTheDocument();
    expect(within(legend).getByText('Tree-pit sensor')).toBeInTheDocument();

    const weatherMarker = screen.getByTitle('Weather station');
    fireEvent.click(weatherMarker);

    const popup = screen.getByRole('heading', { name: 'Weather station' }).closest('article');
    expect(popup).not.toBeNull();
    expect(popup).toHaveTextContent('55.955312, -3.238602');
    expect(popup).toHaveTextContent('Air temperature');
    expect(popup).toHaveTextContent('Barometric pressure');
    expect(popup).not.toHaveTextContent(/online|offline|stale|planned/i);
  });
});
