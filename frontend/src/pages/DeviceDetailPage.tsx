import { useMemo, useState } from 'react';
import { Link, useLocation, useParams } from 'react-router-dom';

import { useDevice, useMeasurements } from '../api/queries';
import { EmptyState, ErrorState, LoadingState } from '../components/DataState';
import { MetadataStatusNote } from '../components/MetadataStatusNote';
import { MeasurementDisplay } from '../components/MeasurementDisplay';
import { StatusBadge } from '../components/StatusBadge';
import { SyntheticBanner } from '../components/SyntheticBanner';
import { TimeSeriesChart, type ChartPoint } from '../components/TimeSeriesChart';
import { UnitStatusNote } from '../components/UnitStatusNote';
import { formatDateTime, formatNumber, formatStatusBasis, humanizeCode } from '../utils/format';

export function DeviceDetailPage() {
  const { deviceId } = useParams();
  const location = useLocation();
  const periodParams = new URLSearchParams(location.search);
  const periodStart = periodParams.get('start') ?? undefined;
  const periodEnd = periodParams.get('end') ?? undefined;
  const device = useDevice(deviceId);
  const [channelId, setChannelId] = useState<string>();
  const selectedChannelId = channelId ?? device.data?.channels[0]?.id;
  const measurements = useMeasurements(deviceId, selectedChannelId, periodStart, periodEnd);
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
  if (!device.data) {
    return <ErrorState message={device.error?.message} />;
  }

  const data = device.data;
  const isLiveMqtt = data.ingestion_mode === 'live_mqtt';
  const isProxy = data.provenance === 'proxy';
  const status = data.freshness.calculated_status;
  const hasChannels = data.channels.length > 0;
  return (
    <div className="page-stack">
      <SyntheticBanner
        mode={
          isProxy ? 'proxy' : data.is_test_device ? (isLiveMqtt ? 'live' : 'replay') : 'synthetic'
        }
      />
      <Link className="back-link" to={{ pathname: '/devices', search: location.search }}>
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
          {data.is_test_device ? (
            <div className="provenance-tags" aria-label="Data provenance">
              <span className="provenance-tag">{isProxy ? 'Proxy sensor' : 'Testbed'}</span>
              <span className="provenance-tag">{isLiveMqtt ? 'Live MQTT' : 'Replay data'}</span>
              <span className="provenance-tag provenance-tag--warning">Metadata pending</span>
              <span className="provenance-tag provenance-tag--warning">Unit unverified</span>
            </div>
          ) : null}
        </div>
        <dl className="hero-facts">
          <div>
            <dt>Last seen</dt>
            <dd>
              {data.last_seen_at === null
                ? 'Never seen / No data'
                : formatDateTime(data.last_seen_at)}
            </dd>
          </div>
          <div>
            <dt>Configuration</dt>
            <dd>{humanizeCode(data.sensor_configuration_status)}</dd>
          </div>
          <div>
            <dt>Reference time</dt>
            <dd>{formatDateTime(data.freshness.reference_time)}</dd>
          </div>
          <div>
            <dt>Status basis</dt>
            <dd>{formatStatusBasis(data.freshness.status_basis)}</dd>
          </div>
        </dl>
      </header>

      {data.is_test_device ? (
        <section className="panel" aria-labelledby="ingestion-provenance-heading">
          <div className="section-heading">
            <div>
              <p className="eyebrow">
                {isLiveMqtt ? 'Private-source live ingestion' : 'Private-source replay'}
              </p>
              <h2 id="ingestion-provenance-heading">
                {isLiveMqtt ? 'Live ingestion provenance' : 'Replay provenance'}
              </h2>
              <p>
                Raw events are preserved privately. Public views expose only selected normalised
                fields and never expose network identifiers, session material, tokens, or raw JSON.
              </p>
            </div>
          </div>
          <dl className="telemetry-grid">
            <div>
              <dt>Source</dt>
              <dd>{isLiveMqtt ? 'TTN application uplink' : 'TTN console export'}</dd>
            </div>
            <div>
              <dt>Ingestion</dt>
              <dd>{humanizeCode(data.ingestion_mode ?? 'offline_replay')}</dd>
            </div>
            <div>
              <dt>Environment</dt>
              <dd>{humanizeCode(data.environment ?? 'test')}</dd>
            </div>
            <div>
              <dt>Latest observation</dt>
              <dd>{formatDateTime(data.last_seen_at)}</dd>
            </div>
          </dl>
        </section>
      ) : null}

      {data.is_test_device && data.telemetry ? (
        <section className="panel" aria-labelledby="operational-status-heading">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Decoder status and network context</p>
              <h2 id="operational-status-heading">Latest operational status</h2>
              <p>Status values are kept separate from scientific measurement channels.</p>
            </div>
          </div>
          <dl className="telemetry-grid">
            <div>
              <dt>Battery</dt>
              <dd>
                {data.telemetry.battery_percent === null
                  ? 'Not available'
                  : `${formatNumber(data.telemetry.battery_percent)}%`}
              </dd>
            </div>
            <div>
              <dt>Firmware</dt>
              <dd>{data.telemetry.firmware_version ?? 'Not available'}</dd>
            </div>
            <div>
              <dt>Hardware</dt>
              <dd>{data.telemetry.hardware_version ?? 'Not available'}</dd>
            </div>
            <div>
              <dt>Measurement interval</dt>
              <dd>
                {data.telemetry.measurement_interval_value === null
                  ? 'Not available'
                  : `${formatNumber(data.telemetry.measurement_interval_value)} · unit not verified`}
              </dd>
            </div>
            <div>
              <dt>Latest RSSI</dt>
              <dd>
                {data.telemetry.latest_rssi_dbm === null
                  ? 'Not available'
                  : `${formatNumber(data.telemetry.latest_rssi_dbm)} dBm`}
              </dd>
            </div>
            <div>
              <dt>Latest SNR</dt>
              <dd>
                {data.telemetry.latest_snr_db === null
                  ? 'Not available'
                  : `${formatNumber(data.telemetry.latest_snr_db)} dB`}
              </dd>
            </div>
            <div>
              <dt>Gateway</dt>
              <dd>{data.telemetry.gateway ?? 'Not available'}</dd>
            </div>
            <div>
              <dt>Status observed</dt>
              <dd>{formatDateTime(data.telemetry.observed_at)}</dd>
            </div>
          </dl>
        </section>
      ) : null}

      {status !== 'online' ? (
        <aside className={`freshness-warning freshness-warning--${status}`} role="status">
          <strong>{humanizeCode(status)} data status</strong>
          <span>
            Calculated against {isProxy ? 'current UTC time' : 'the dataset reference time'} using{' '}
            {String(data.freshness.stale_after_minutes)}
            -minute stale and {String(data.freshness.offline_after_minutes)}-minute offline
            thresholds.
          </span>
        </aside>
      ) : null}

      {!hasChannels ? (
        <EmptyState
          title={
            isProxy && data.last_seen_at === null
              ? 'Never seen / No data'
              : 'Sensor configuration pending'
          }
          message="No observed uplink establishes public measurement channels for this device. Metric, payload, and unit mappings will not be inferred."
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
                  <MetadataStatusNote status={item.verification_status} />
                  <UnitStatusNote status={item.unit_confirmation_status} />
                  <small>
                    {item.installation_depth_cm === null
                      ? ''
                      : `${String(item.installation_depth_cm)} cm · `}
                    {formatDateTime(item.measured_at)}
                    {item.timestamp_basis === 'ttn_received_at' ? ' · TTN received timestamp' : ''}
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
                    · {channel.unit_symbol ?? 'unit not verified'}
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
                <>
                  <MetadataStatusNote status={selectedChannel.verification_status} />
                  <UnitStatusNote status={selectedChannel.unit_confirmation_status} />
                </>
              ) : null}
            </div>
          </section>

          {measurements.isLoading ? <LoadingState title="Loading time series" /> : null}
          {measurements.isError && !measurements.data ? (
            <ErrorState message={measurements.error.message} />
          ) : null}
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
              unit={selectedChannel.unit_symbol ?? 'Unit not verified'}
              points={points}
            />
          ) : null}
        </>
      )}
    </div>
  );
}
