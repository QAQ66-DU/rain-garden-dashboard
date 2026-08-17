import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

import {
  buildChartTimeAxis,
  formatChartAxisTick,
  formatChartTooltipTimestamp,
  type ChartRangePreset,
} from '../utils/chartTimeAxis';
import { formatNumber } from '../utils/format';

export interface ChartPoint {
  measuredAt: string;
  value: number;
  qualityFlag: string;
}

interface TimeSeriesChartProps {
  title: string;
  subtitle: string;
  unit: string;
  points: ChartPoint[];
  rangeStart: string;
  rangeEnd: string;
  rangePreset: ChartRangePreset;
  downsamplingApplied: boolean;
}

export function TimeSeriesChart({
  title,
  subtitle,
  unit,
  points,
  rangeStart,
  rangeEnd,
  rangePreset,
  downsamplingApplied,
}: TimeSeriesChartProps) {
  const flagged = points.filter((point) => point.qualityFlag !== 'valid').length;
  const axis = buildChartTimeAxis(rangeStart, rangeEnd, rangePreset);
  const chartPoints = points.map((point) => ({
    ...point,
    timestamp: Date.parse(point.measuredAt),
  }));
  return (
    <section className="chart-card" data-testid="time-series-chart">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Selected-period series</p>
          <h2>{title}</h2>
          <p>{subtitle}</p>
        </div>
        <span className="unit-chip">Unit · {unit}</span>
      </div>
      {flagged > 0 ? (
        <p className="quality-callout" role="status">
          {flagged} displayed flagged observation{flagged === 1 ? '' : 's'} identified in the source
          data.
        </p>
      ) : null}
      <div className="chart-frame" aria-label={`${title}, measured in ${unit}`}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartPoints} margin={{ top: 16, right: 20, bottom: 12, left: 8 }}>
            <CartesianGrid stroke="#dbe4e7" strokeDasharray="3 5" vertical={false} />
            <XAxis
              dataKey="timestamp"
              type="number"
              scale="time"
              domain={axis.domain}
              ticks={axis.ticks}
              tickFormatter={(value) => formatChartAxisTick(Number(value), axis.granularity)}
              minTickGap={48}
              allowDataOverflow
              stroke="#72817c"
              tick={{ fontSize: 12 }}
            />
            <YAxis
              stroke="#72817c"
              tick={{ fontSize: 12 }}
              width={68}
              label={{ value: unit, angle: -90, position: 'insideLeft', fill: '#52645f' }}
            />
            <Tooltip
              labelFormatter={(label) => formatChartTooltipTimestamp(Number(label))}
              formatter={(value) => [`${formatNumber(Number(value))} ${unit}`, 'Observed value']}
            />
            <Line
              type="monotone"
              dataKey="value"
              name="Observed value"
              stroke="#1f657f"
              strokeWidth={2.4}
              dot={false}
              activeDot={{ r: 5, fill: '#ffffff', stroke: '#1f657f', strokeWidth: 3 }}
              connectNulls={false}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <p className="chart-note">
        Missing records are not converted to zero.{' '}
        {downsamplingApplied
          ? 'Chart downsampled for display. Full raw data remains available for export.'
          : 'All matching raw observations are displayed.'}
      </p>
    </section>
  );
}
