import { useEffect, useMemo, useRef, useState } from 'react';
import { Link, useLocation, useParams, useSearchParams } from 'react-router-dom';

import { useDevice, useMeasurementExport, useMeasurements } from '../api/queries';
import { ConfigurationStatus } from '../components/ConfigurationStatus';
import { EmptyState, ErrorState, LoadingState } from '../components/DataState';
import { EnglishDateTimeInput } from '../components/EnglishDateTimeInput';
import { IngestionSource } from '../components/IngestionSource';
import { MetadataStatusNote } from '../components/MetadataStatusNote';
import { MeasurementDisplay } from '../components/MeasurementDisplay';
import { PageHeader } from '../components/PageHeader';
import { StatusBadge } from '../components/StatusBadge';
import { SyntheticBanner } from '../components/SyntheticBanner';
import { TimeSeriesChart, type ChartPoint } from '../components/TimeSeriesChart';
import { UnitStatusNote } from '../components/UnitStatusNote';
import {
  formatDateTime,
  formatNumber,
  formatStatusBasis,
  fromDateTimeLocalInput,
  humanizeCode,
  presetWindow,
  SITE_TIME_ZONE,
  toDateTimeLocalInput,
} from '../utils/format';

const PRESET_HOURS = { '24h': 24, '7d': 7 * 24, '30d': 30 * 24 } as const;
type TimePreset = keyof typeof PRESET_HOURS | 'custom';

function isPreset(value: string | null): value is TimePreset {
  return value === '24h' || value === '7d' || value === '30d' || value === 'custom';
}

function presetLabel(preset: TimePreset): string {
  if (preset === '24h') return 'Last 24 hours';
  if (preset === '7d') return 'Last 7 days';
  if (preset === '30d') return 'Last 30 days';
  return 'Custom range';
}

function utcTimestamp(value: string): string {
  return /z$/i.test(value) ? value : new Date(value).toISOString();
}

export function DeviceDetailPage() {
  const { deviceId } = useParams();
  const location = useLocation();
  const [periodParams, setPeriodParams] = useSearchParams();
  const periodStart = periodParams.get('start');
  const periodEnd = periodParams.get('end');
  const hasNoRange = periodStart === null && periodEnd === null;
  const hasIncompleteRange = (periodStart === null) !== (periodEnd === null);
  const startMilliseconds = periodStart === null ? Number.NaN : Date.parse(periodStart);
  const endMilliseconds = periodEnd === null ? Number.NaN : Date.parse(periodEnd);
  const hasMalformedRange =
    !hasNoRange &&
    !hasIncompleteRange &&
    (Number.isNaN(startMilliseconds) || Number.isNaN(endMilliseconds));
  const hasReversedRange =
    !hasNoRange &&
    !hasIncompleteRange &&
    !hasMalformedRange &&
    startMilliseconds >= endMilliseconds;
  const rangeError = hasIncompleteRange
    ? 'Both start and end timestamps are required.'
    : hasMalformedRange
      ? 'The selected URL contains a malformed start or end timestamp.'
      : hasReversedRange
        ? 'Start must be earlier than end.'
        : undefined;
  const resolvedStart = periodStart && !rangeError ? utcTimestamp(periodStart) : undefined;
  const resolvedEnd = periodEnd && !rangeError ? utcTimestamp(periodEnd) : undefined;
  const presetParam = periodParams.get('preset');
  const selectedPreset: TimePreset = rangeError
    ? 'custom'
    : isPreset(presetParam)
      ? presetParam
      : hasNoRange
        ? '7d'
        : 'custom';
  const device = useDevice(deviceId);
  const [channelId, setChannelId] = useState<string>();
  const [customStart, setCustomStart] = useState<string | null>(null);
  const [customEnd, setCustomEnd] = useState<string | null>(null);
  const [customError, setCustomError] = useState<string>();
  const [rollingLivePreset, setRollingLivePreset] = useState(hasNoRange);
  const lastLiveObservation = useRef<string | null>(null);
  const selectedChannelId = channelId ?? device.data?.channels[0]?.id;
  const measurements = useMeasurements(
    deviceId,
    selectedChannelId,
    resolvedStart,
    resolvedEnd,
    hasNoRange || !rangeError,
  );
  const measurementExport = useMeasurementExport();
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

  useEffect(() => {
    if (!hasNoRange || !measurements.data) return;
    const next = new URLSearchParams(periodParams);
    next.set('start', measurements.data.start);
    next.set('end', measurements.data.end);
    next.set('preset', '7d');
    setPeriodParams(next, { replace: true });
  }, [hasNoRange, measurements.data, periodParams, setPeriodParams]);

  useEffect(() => {
    const observedAt = device.data?.last_seen_at;
    if (
      !rollingLivePreset ||
      selectedPreset === 'custom' ||
      device.data?.ingestion_mode !== 'live_mqtt' ||
      !observedAt
    ) {
      return;
    }
    if (lastLiveObservation.current === null) {
      lastLiveObservation.current = observedAt;
      return;
    }
    const observedMilliseconds = Date.parse(observedAt);
    if (observedMilliseconds <= Date.parse(lastLiveObservation.current)) return;
    lastLiveObservation.current = observedAt;
    if (hasNoRange || (resolvedEnd && observedMilliseconds < Date.parse(resolvedEnd))) return;

    const exclusiveEnd = new Date(observedMilliseconds + 1).toISOString();
    const [nextStart, nextEnd] = presetWindow(exclusiveEnd, PRESET_HOURS[selectedPreset]);
    const next = new URLSearchParams(periodParams);
    next.set('start', nextStart);
    next.set('end', nextEnd);
    next.set('preset', selectedPreset);
    setPeriodParams(next, { replace: true });
  }, [
    device.data?.ingestion_mode,
    device.data?.last_seen_at,
    hasNoRange,
    periodParams,
    resolvedEnd,
    rollingLivePreset,
    selectedPreset,
    setPeriodParams,
  ]);

  const updateRange = (start: string, end: string, preset: TimePreset) => {
    const next = new URLSearchParams(periodParams);
    next.set('start', start);
    next.set('end', end);
    next.set('preset', preset);
    setPeriodParams(next);
    setCustomStart(null);
    setCustomEnd(null);
    setCustomError(undefined);
    measurementExport.reset();
  };

  const applyPreset = (preset: TimePreset) => {
    if (preset === 'custom') {
      setRollingLivePreset(false);
      const next = new URLSearchParams(periodParams);
      next.set('preset', 'custom');
      setPeriodParams(next);
      setCustomError(undefined);
      measurementExport.reset();
      return;
    }
    if (!device.data) return;
    setRollingLivePreset(device.data.ingestion_mode === 'live_mqtt');
    lastLiveObservation.current = device.data.last_seen_at;
    const [start, end] = presetWindow(device.data.freshness.reference_time, PRESET_HOURS[preset]);
    updateRange(start, end, preset);
  };

  const customStartValue =
    customStart ??
    (periodStart && !Number.isNaN(startMilliseconds)
      ? toDateTimeLocalInput(periodStart, SITE_TIME_ZONE)
      : '');
  const customEndValue =
    customEnd ??
    (periodEnd && !Number.isNaN(endMilliseconds)
      ? toDateTimeLocalInput(periodEnd, SITE_TIME_ZONE)
      : '');

  const applyCustomRange = () => {
    if (!customStartValue || !customEndValue) {
      setCustomError('Enter both start and end date-times.');
      return;
    }
    const start = fromDateTimeLocalInput(customStartValue, SITE_TIME_ZONE);
    const end = fromDateTimeLocalInput(customEndValue, SITE_TIME_ZONE);
    if (!start || !end) {
      setCustomError(
        'Enter valid Europe/London date-times. Times skipped or repeated by a daylight-saving transition are invalid.',
      );
      return;
    }
    if (Date.parse(start) >= Date.parse(end)) {
      setCustomError('Start must be earlier than end.');
      return;
    }
    updateRange(start, end, 'custom');
  };

  const exportCsv = () => {
    if (!deviceId || !selectedChannelId || !resolvedStart || !resolvedEnd || rangeError) return;
    measurementExport.mutate(
      { deviceId, channelId: selectedChannelId, start: resolvedStart, end: resolvedEnd },
      {
        onSuccess: ({ blob, filename }) => {
          const downloadUrl = URL.createObjectURL(blob);
          const link = document.createElement('a');
          link.href = downloadUrl;
          link.download = filename;
          document.body.append(link);
          link.click();
          link.remove();
          URL.revokeObjectURL(downloadUrl);
        },
      },
    );
  };

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
      <PageHeader
        eyebrow={humanizeCode(data.device_type)}
        title={data.display_name}
        description={`${data.monitoring_feature?.display_name ?? 'Monitoring feature not assigned'} · ${data.site_name}`}
        meta={
          <dl className="page-header__facts page-header__facts--device">
            <div>
              <dt>Operational status</dt>
              <dd>
                <StatusBadge status={status} />
              </dd>
            </div>
            <div>
              <dt>Source</dt>
              <dd>
                <IngestionSource
                  compact
                  ingestionMode={data.ingestion_mode}
                  provenance={data.provenance}
                  sourceSystem={data.source_system}
                />
              </dd>
            </div>
            <div>
              <dt>Last received</dt>
              <dd>
                {data.last_seen_at === null ? 'Never received' : formatDateTime(data.last_seen_at)}
              </dd>
            </div>
            <div>
              <dt>Configuration</dt>
              <dd>
                <ConfigurationStatus compact status={data.sensor_configuration_status} />
              </dd>
            </div>
            <div>
              <dt>Units</dt>
              <dd>
                <UnitStatusNote compact status={data.unit_confirmation_summary} />
              </dd>
            </div>
            <div>
              <dt>Status basis</dt>
              <dd>{formatStatusBasis(data.freshness.status_basis)}</dd>
              <small>Reference {formatDateTime(data.freshness.reference_time)}</small>
            </div>
          </dl>
        }
      />

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
              <dt>Ingestion source</dt>
              <dd>
                <IngestionSource
                  ingestionMode={data.ingestion_mode}
                  provenance={data.provenance}
                  sourceSystem={data.source_system}
                />
              </dd>
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
          <section className="panel latest-section">
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

          <section className="toolbar chart-controls" aria-label="Chart controls">
            <div className="device-chart-filters">
              <label>
                <span>Sensor channel</span>
                <select
                  value={selectedChannelId ?? ''}
                  onChange={(event) => {
                    setChannelId(event.target.value);
                    measurementExport.reset();
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
              <p className="device-control-helper">
                Each selection plots one channel only. Depth and position are not merged or assumed
                comparable.
              </p>
              {selectedChannel ? (
                <div className="device-control-badges" aria-label="Selected channel metadata">
                  <MetadataStatusNote status={selectedChannel.verification_status} />
                  <UnitStatusNote status={selectedChannel.unit_confirmation_status} />
                </div>
              ) : null}
              <label>
                <span>Time range</span>
                <select
                  value={selectedPreset}
                  onChange={(event) => {
                    applyPreset(event.target.value as TimePreset);
                  }}
                >
                  <option value="24h">Last 24 hours</option>
                  <option value="7d">Last 7 days</option>
                  <option value="30d">Last 30 days</option>
                  <option value="custom">Custom range</option>
                </select>
              </label>
              <p className="device-control-helper">
                Selected period: {presetLabel(selectedPreset)} · [start, end) in UTC · displayed in{' '}
                {SITE_TIME_ZONE}.
              </p>
              {selectedPreset === 'custom' ? (
                <div className="device-custom-time-fields">
                  <EnglishDateTimeInput
                    label={`Custom start (${SITE_TIME_ZONE})`}
                    timeZone={SITE_TIME_ZONE}
                    value={customStartValue}
                    onChange={setCustomStart}
                  />
                  <EnglishDateTimeInput
                    label={`Custom end (${SITE_TIME_ZONE})`}
                    timeZone={SITE_TIME_ZONE}
                    value={customEndValue}
                    onChange={setCustomEnd}
                  />
                  <button className="secondary-button" type="button" onClick={applyCustomRange}>
                    Apply custom range
                  </button>
                </div>
              ) : null}
              {rangeError || customError ? (
                <p className="control-error" role="alert">
                  {customError ?? rangeError}
                </p>
              ) : null}
              <div className="device-export-control">
                <button
                  className="secondary-button"
                  type="button"
                  disabled={
                    measurementExport.isPending ||
                    !deviceId ||
                    !selectedChannelId ||
                    !resolvedStart ||
                    !resolvedEnd ||
                    Boolean(rangeError)
                  }
                  onClick={exportCsv}
                >
                  {measurementExport.isPending ? 'Preparing CSV…' : 'Export CSV'}
                </button>
                <p>The CSV contains the selected device, channel and time range only.</p>
              </div>
              {measurementExport.isError ? (
                <p className="control-error" role="alert">
                  {measurementExport.error.message}
                </p>
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
              message="The selected channel has no observations in this period. Missing values are not shown as zero."
            />
          ) : null}
          {selectedChannel && measurements.data && points.length > 0 ? (
            <TimeSeriesChart
              title={`${selectedChannel.display_name} · ${presetLabel(selectedPreset)}`}
              subtitle={`${
                measurements.data.downsampling_applied
                  ? `${formatNumber(measurements.data.total_matching)} observations · ${formatNumber(measurements.data.points_returned)} displayed`
                  : `${formatNumber(measurements.data.total_matching)} raw observations`
              } · ${formatDateTime(measurements.data.start)} to ${formatDateTime(measurements.data.end)}`}
              unit={selectedChannel.unit_symbol ?? 'Unit not verified'}
              points={points}
              rangeStart={measurements.data.start}
              rangeEnd={measurements.data.end}
              rangePreset={selectedPreset}
              downsamplingApplied={measurements.data.downsampling_applied}
            />
          ) : null}
        </>
      )}
    </div>
  );
}
