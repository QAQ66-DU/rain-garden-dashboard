import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

import { formatCompactDate, formatDateTime, formatNumber } from '../utils/format';

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
}

export function TimeSeriesChart({ title, subtitle, unit, points }: TimeSeriesChartProps) {
  const flagged = points.filter((point) => point.qualityFlag !== 'valid').length;
  return (
    <section className="chart-card" data-testid="time-series-chart">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Selected-period raw series</p>
          <h2>{title}</h2>
          <p>{subtitle}</p>
        </div>
        <span className="unit-chip">Unit · {unit}</span>
      </div>
      {flagged > 0 ? (
        <p className="quality-callout" role="status">
          {flagged} flagged observation{flagged === 1 ? '' : 's'} included and identified in the
          source data.
        </p>
      ) : null}
      <div className="chart-frame" aria-label={`${title}, measured in ${unit}`}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={points} margin={{ top: 16, right: 20, bottom: 12, left: 8 }}>
            <CartesianGrid stroke="#dbe4e7" strokeDasharray="3 5" vertical={false} />
            <XAxis
              dataKey="measuredAt"
              tickFormatter={(value) => formatCompactDate(String(value))}
              minTickGap={42}
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
              labelFormatter={(label) => formatDateTime(String(label))}
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
        Missing records are not converted to zero. No aggregation or downsampling is applied.
      </p>
    </section>
  );
}
