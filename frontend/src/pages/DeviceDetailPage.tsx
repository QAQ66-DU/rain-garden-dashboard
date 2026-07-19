import { useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';

import { useDevice, useMeasurements } from '../api/queries';
import { EmptyState, ErrorState, LoadingState } from '../components/DataState';
import { MeasurementDisplay } from '../components/MeasurementDisplay';
import { StatusBadge } from '../components/StatusBadge';
import { SyntheticBanner } from '../components/SyntheticBanner';
import { TimeSeriesChart, type ChartPoint } from '../components/TimeSeriesChart';
import { UnitStatusNote } from '../components/UnitStatusNote';
import { formatDateTime, humanizeCode } from '../utils/format';

export function DeviceDetailPage() {
  const { deviceId } = useParams();
  const device = useDevice(deviceId);
  const [channelId, setChannelId] = useState<string>();
  const selectedChannelId = channelId ?? device.data?.channels[0]?.id;
  const measurements = useMeasurements(deviceId, selectedChannelId);
  const selectedChannel = device.data?.channels.find((channel) => channel.id === selectedChannelId);
  const points = useMemo<ChartPoint[]>(
    () =>
      measurements.data?.items.map((item) => ({
        measuredAt: item.measured_at,
        value: item.numeric_value,
        qualityFlag: item.quality_flag,
      })) ?? [],
    [measurements.data],
  );

  if (device.isLoading) {
    return <LoadingState title="Loading device detail" />;
  }
  if (device.isError || !device.data) {
    return <ErrorState message={device.error?.message} />;
  }

  const data = device.data;
  const status = data.freshness.calculated_status;
  const hasChannels = data.channels.length > 0;
  return (
    <div className="page-stack">
      <SyntheticBanner />
      <Link className="back-link" to="/devices">
        ← Back to devices
      </Link>
      <header className="device-hero">
        <div>
          <div className="hero-status-row">
            <p className="eyebrow">{humanizeCode(data.device_type)}</p>
            <StatusBadge status={status} />
          </div>
          <h1>{data.display_name}</h1>
          <p>
            {data.monitoring_feature?.display_name ?? 'Monitoring feature not assigned'} ·{' '}
            {data.site_name}
          </p>
        </div>
        <dl className="hero-facts">
          <div>
            <dt>Last seen</dt>
            <dd>{formatDateTime(data.last_seen_at)}</dd>
          </div>
          <div>
            <dt>Configuration</dt>
            <dd>{humanizeCode(data.sensor_configuration_status)}</dd>
          </div>
          <div>
            <dt>Reference time</dt>
            <dd>{formatDateTime(data.freshness.reference_time)}</dd>
          </div>
        </dl>
      </header>

      {status !== 'online' ? (
        <aside className={`freshness-warning freshness-warning--${status}`} role="status">
          <strong>{humanizeCode(status)} data status</strong>
          <span>
            Calculated against the dataset reference time using{' '}
            {String(data.freshness.stale_after_minutes)}
            -minute stale and {String(data.freshness.offline_after_minutes)}-minute offline
            thresholds.
          </span>
        </aside>
      ) : null}

      {!hasChannels ? (
        <EmptyState
          title="Sensor configuration pending"
          message="This confirmed inventory item has no configured public channels or observations yet. Metric, payload, depth, and unit mappings must be verified before real data can be accepted."
        />
      ) : (
        <>
          <section className="latest-section">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Per-channel snapshot</p>
                <h2>Latest measurements</h2>
              </div>
              <span className="count-chip">{String(data.latest_measurements.length)} channels</span>
            </div>
            <div className="latest-grid">
              {data.latest_measurements.map((item) => (
                <article key={item.channel_id} className="latest-card">
                  <p>{item.channel_name}</p>
                  <MeasurementDisplay value={item.numeric_value} unit={item.unit_symbol} />
                  <UnitStatusNote status={item.unit_confirmation_status} />
                  <small>
                    {item.installation_depth_cm === null
                      ? ''
                      : `${String(item.installation_depth_cm)} cm · `}
                    {formatDateTime(item.measured_at)}
                  </small>
                </article>
              ))}
            </div>
          </section>

          <section className="chart-controls" aria-label="Chart controls">
            <label>
              <span>Sensor channel</span>
              <select
                value={selectedChannelId ?? ''}
                onChange={(event) => {
                  setChannelId(event.target.value);
                }}
              >
                {data.channels.map((channel) => (
                  <option value={channel.id} key={channel.id}>
                    {channel.display_name}
                    {channel.installation_depth_cm === null
                      ? ''
                      : ` · ${String(channel.installation_depth_cm)} cm`}{' '}
                    · {channel.unit_symbol ?? 'unit pending'}
                  </option>
                ))}
              </select>
            </label>
            <div>
              <p>
                Each selection plots one channel only. Depth and position are not merged or assumed
                comparable.
              </p>
              {selectedChannel ? (
                <UnitStatusNote status={selectedChannel.unit_confirmation_status} />
              ) : null}
            </div>
          </section>

          {measurements.isLoading ? <LoadingState title="Loading time series" /> : null}
          {measurements.isError ? <ErrorState message={measurements.error.message} /> : null}
          {measurements.data && measurements.data.items.length === 0 ? (
            <EmptyState
              title="No measurements in this range"
              message="The channel has no observations in the default seven-day window. Missing values are not shown as zero."
            />
          ) : null}
          {selectedChannel && measurements.data && points.length > 0 ? (
            <TimeSeriesChart
              title={`${selectedChannel.display_name} over time`}
              subtitle={`${String(points.length)} raw observations · ${formatDateTime(measurements.data.start)} to ${formatDateTime(measurements.data.end)}`}
              unit={selectedChannel.unit_symbol ?? 'unit pending'}
              points={points}
            />
          ) : null}
        </>
      )}
    </div>
  );
}
