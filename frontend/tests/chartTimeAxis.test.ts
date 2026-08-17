import { describe, expect, it } from 'vitest';

import {
  buildChartTimeAxis,
  formatChartAxisTick,
  formatChartTooltipTimestamp,
} from '../src/utils/chartTimeAxis';

describe('Device Detail chart time axis', () => {
  it('uses readable hour ticks for 24 hours and marks the local midnight transition', () => {
    const axis = buildChartTimeAxis('2026-08-11T17:00:00Z', '2026-08-12T17:00:00Z', '24h');
    const labels = axis.ticks.map((tick) => formatChartAxisTick(tick, axis.granularity));

    expect(axis.domain).toEqual([
      Date.parse('2026-08-11T17:00:00Z'),
      Date.parse('2026-08-12T17:00:00Z'),
    ]);
    expect(axis.granularity).toBe('hour');
    expect(axis.ticks.length).toBeLessThanOrEqual(8);
    expect(labels).toContain('12 Aug, 00:00');
    expect(labels.every((label) => label.includes(':'))).toBe(true);
  });

  it('uses day-level labels for seven days without hourly clutter', () => {
    const axis = buildChartTimeAxis('2026-08-05T12:00:00Z', '2026-08-12T12:00:00Z', '7d');
    const labels = axis.ticks.map((tick) => formatChartAxisTick(tick, axis.granularity));

    expect(axis.granularity).toBe('day');
    expect(axis.ticks.length).toBeGreaterThanOrEqual(6);
    expect(axis.ticks.length).toBeLessThanOrEqual(8);
    expect(labels.every((label) => !label.includes(':'))).toBe(true);
  });

  it('spaces date-level ticks across 30 days', () => {
    const axis = buildChartTimeAxis('2026-07-13T12:00:00Z', '2026-08-12T12:00:00Z', '30d');
    const gaps = axis.ticks.slice(1).map((tick, index) => tick - (axis.ticks[index] ?? tick));

    expect(axis.granularity).toBe('day');
    expect(axis.ticks.length).toBeLessThanOrEqual(8);
    expect(Math.min(...gaps)).toBeGreaterThanOrEqual(4 * 24 * 60 * 60 * 1000);
  });

  it('formats tooltip timestamps with local date, year and seconds', () => {
    expect(formatChartTooltipTimestamp(Date.parse('2026-08-12T16:21:34Z'))).toBe(
      '12 Aug 2026, 17:21:34',
    );
  });
});
