import { useState } from 'react';

import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

import type { ExploreResponse } from '../api/types';
import {
  buildChartTimeAxis,
  formatChartAxisTick,
  type ChartRangePreset,
} from '../utils/chartTimeAxis';
import { formatDateTime, formatNumber } from '../utils/format';

type ExploreSeries = ExploreResponse['series'][number];

interface ExploreSeriesChartProps {
  series: ExploreSeries;
  start: string;
  end: string;
  timeZone: string;
  rangePreset: ChartRangePreset;
}

export function ExploreSeriesChart({
  series,
  start,
  end,
  timeZone,
  rangePreset,
}: ExploreSeriesChartProps) {
  const [tooltipPortal, setTooltipPortal] = useState<HTMLDivElement | null>(null);
  const unit = series.channel.unit_symbol ?? 'unit pending';
  const axis = buildChartTimeAxis(start, end, rangePreset, timeZone);
  const data = series.points.map((point) => ({
    timestamp: Date.parse(point.measured_at),
    measuredAt: point.measured_at,
    receivedAt: point.received_at,
    value: point.numeric_value,
    validValue: point.included_in_summary ? point.numeric_value : null,
    flaggedValue: point.included_in_summary ? null : point.numeric_value,
    qualityFlag: point.quality_flag,
    timingStatus: point.timing_status,
    transmissionDelaySeconds: point.transmission_delay_seconds,
  }));
  return (
    <div className="explore-chart-shell">
      <div
        className="explore-chart"
        data-testid="explore-series-chart"
        aria-label={`${series.channel.device_name}, ${series.channel.channel_name}, measured in ${unit}`}
      >
        <ResponsiveContainer width="100%" height="100%">
          <LineChart
            data={data}
            syncId="site-time-explorer"
            syncMethod="value"
            margin={{ top: 12, right: 18, bottom: 8, left: 8 }}
          >
            <CartesianGrid stroke="#dbe4e7" strokeDasharray="3 5" vertical={false} />
            <XAxis
              type="number"
              dataKey="timestamp"
              domain={axis.domain}
              scale="time"
              ticks={axis.ticks}
              tickFormatter={(value) =>
                formatChartAxisTick(Number(value), axis.granularity, timeZone)
              }
              minTickGap={48}
              allowDataOverflow
              stroke="#72817c"
              tick={{ fontSize: 11 }}
            />
            <YAxis
              stroke="#72817c"
              tick={{ fontSize: 11 }}
              width={62}
              label={{ value: unit, angle: -90, position: 'insideLeft', fill: '#52645f' }}
            />
            <Tooltip
              portal={tooltipPortal}
              wrapperStyle={{ position: 'relative', zIndex: 1 }}
              content={({ active, payload }) => {
                const point = payload[0]?.payload as (typeof data)[number] | undefined;
                if (!active || !point) return null;
                return (
                  <div className="explore-tooltip">
                    <strong>
                      {formatNumber(point.value)} {unit}
                    </strong>
                    <span>Measured {formatDateTime(point.measuredAt, timeZone)}</span>
                    <span>Received {formatDateTime(point.receivedAt, timeZone)}</span>
                    <span>
                      {point.qualityFlag.replaceAll('_', ' ')} ·{' '}
                      {point.timingStatus.replaceAll('_', ' ')} · delay{' '}
                      {formatNumber(point.transmissionDelaySeconds)} s
                    </span>
                  </div>
                );
              }}
            />
            <Line
              type="monotone"
              dataKey="validValue"
              stroke="#1f657f"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4, fill: '#ffffff', stroke: '#1f657f', strokeWidth: 2 }}
              connectNulls={false}
              isAnimationActive={false}
            />
            <Line
              type="linear"
              dataKey="flaggedValue"
              stroke="transparent"
              strokeWidth={0}
              dot={{ r: 4, fill: '#9a483f', stroke: '#ffffff', strokeWidth: 1 }}
              activeDot={{ r: 5, fill: '#9a483f', stroke: '#ffffff', strokeWidth: 2 }}
              connectNulls={false}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <div
        ref={setTooltipPortal}
        className="explore-tooltip-slot"
        data-testid="explore-tooltip-slot"
        aria-live="polite"
      />
    </div>
  );
}
