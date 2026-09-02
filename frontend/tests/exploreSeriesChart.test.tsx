import type { CSSProperties, ReactNode } from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ExploreSeriesChart } from '../src/components/ExploreSeriesChart';
import { exploreFixture } from './fixtures/api';

const chartProbe = vi.hoisted(() => ({
  portalTestId: null as string | null,
  syncId: null as string | null,
  syncMethod: null as string | null,
  tooltipPosition: null as string | null,
}));

vi.mock('recharts', () => ({
  CartesianGrid: () => null,
  Line: () => null,
  LineChart: ({
    children,
    syncId,
    syncMethod,
  }: {
    children: ReactNode;
    syncId?: string;
    syncMethod?: string;
  }) => {
    chartProbe.syncId = syncId ?? null;
    chartProbe.syncMethod = syncMethod ?? null;
    return <div>{children}</div>;
  },
  ResponsiveContainer: ({ children }: { children: ReactNode }) => <>{children}</>,
  Tooltip: ({
    portal,
    wrapperStyle,
  }: {
    portal?: HTMLElement | null;
    wrapperStyle?: CSSProperties;
  }) => {
    chartProbe.portalTestId = portal?.dataset.testid ?? null;
    chartProbe.tooltipPosition = wrapperStyle?.position ?? null;
    return null;
  },
  XAxis: () => null,
  YAxis: () => null,
}));

describe('ExploreSeriesChart', () => {
  beforeEach(() => {
    chartProbe.portalTestId = null;
    chartProbe.syncId = null;
    chartProbe.syncMethod = null;
    chartProbe.tooltipPosition = null;
  });

  it('synchronises matching timestamps and keeps tooltip content outside the plot', async () => {
    const series = exploreFixture.series[0];
    if (!series) throw new Error('Explore fixture must include a chart series.');

    render(
      <ExploreSeriesChart
        series={series}
        start={exploreFixture.start}
        end={exploreFixture.end}
        timeZone={exploreFixture.display_timezone}
        rangePreset="7d"
      />,
    );

    const plot = screen.getByTestId('explore-series-chart');
    const tooltipSlot = screen.getByTestId('explore-tooltip-slot');

    expect(plot).not.toContainElement(tooltipSlot);
    expect(chartProbe.syncId).toBe('site-time-explorer');
    expect(chartProbe.syncMethod).toBe('value');
    expect(chartProbe.tooltipPosition).toBe('relative');
    expect(
      screen.queryByText('Hover or focus the chart to inspect a point.'),
    ).not.toBeInTheDocument();
    await waitFor(() => {
      expect(chartProbe.portalTestId).toBe('explore-tooltip-slot');
    });
  });
});
