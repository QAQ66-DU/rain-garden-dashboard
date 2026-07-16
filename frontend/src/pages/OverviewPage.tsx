import { Link } from 'react-router-dom';

import { useOverview } from '../api/queries';
import { ErrorState, LoadingState } from '../components/DataState';
import { MeasurementDisplay } from '../components/MeasurementDisplay';
import { MetricCard } from '../components/MetricCard';
import { SyntheticBanner } from '../components/SyntheticBanner';
import { formatDateTime, formatNumber } from '../utils/format';

export function OverviewPage() {
  const overview = useOverview();

  if (overview.isLoading) {
    return <LoadingState title="Loading site overview" />;
  }
  if (overview.isError || !overview.data) {
    return <ErrorState message={overview.error?.message} />;
  }

  const data = overview.data;
  const soil = data.soil_moisture;
  return (
    <div className="page-stack">
      {data.synthetic ? <SyntheticBanner /> : null}
      <header className="page-hero page-hero--overview">
        <div>
          <p className="eyebrow">Site overview</p>
          <h1>{data.site_name}</h1>
          <p>{data.public_location_label}</p>
        </div>
        <div className="hero-meta">
          <span>Reference time</span>
          <strong>{formatDateTime(data.reference_time)}</strong>
          <small>Calculated from the deterministic dataset</small>
        </div>
      </header>

      <section className="metric-grid" aria-label="Overview metrics">
        <MetricCard
          label="Monitored devices"
          value={data.devices.total}
          note={`${String(data.devices.online)} online · ${String(data.devices.stale)} stale · ${String(data.devices.offline)} offline`}
        />
        <MetricCard
          label="Latest rainfall reading"
          value={
            <MeasurementDisplay
              value={data.latest_rainfall?.numeric_value}
              unit={data.latest_rainfall?.unit_symbol}
            />
          }
          note={
            data.latest_rainfall
              ? `Observed ${formatDateTime(data.latest_rainfall.measured_at)}`
              : 'No valid rainfall observation'
          }
        />
        <MetricCard
          label="Data-quality warnings"
          value={data.data_quality.warning_count}
          note="Non-valid observations in the final 24 dataset hours"
          tone={data.data_quality.warning_count > 0 ? 'warning' : 'default'}
        />
        <MetricCard
          label="Last data update"
          value={<span className="date-value">{formatDateTime(data.last_data_update)}</span>}
          note="Latest synthetic uplink receipt"
        />
      </section>

      <section className="overview-grid">
        <article className="panel status-panel">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Network status</p>
              <h2>Device freshness</h2>
            </div>
            <Link className="text-link" to="/devices">
              Review devices →
            </Link>
          </div>
          <div className="status-counts">
            {(['online', 'stale', 'offline', 'unknown'] as const).map((status) => (
              <div key={status} className={`status-count status-count--${status}`}>
                <strong>{data.devices[status]}</strong>
                <span>{status}</span>
              </div>
            ))}
          </div>
          <p className="panel-note">
            Status uses the dataset reference time. It is operational context, not a stored device
            claim.
          </p>
        </article>

        <article className="panel soil-panel">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Latest valid observations</p>
              <h2>Soil-moisture spread</h2>
            </div>
            {soil ? <span className="unit-chip">Unit · {soil.unit_symbol}</span> : null}
          </div>
          {soil ? (
            <>
              <div className="soil-summary" aria-label="Soil moisture summary">
                <div>
                  <span>Minimum</span>
                  <strong>
                    {formatNumber(soil.minimum)} <small>{soil.unit_symbol}</small>
                  </strong>
                </div>
                <div>
                  <span>Median</span>
                  <strong>
                    {formatNumber(soil.median)} <small>{soil.unit_symbol}</small>
                  </strong>
                </div>
                <div>
                  <span>Maximum</span>
                  <strong>
                    {formatNumber(soil.maximum)} <small>{soil.unit_symbol}</small>
                  </strong>
                </div>
              </div>
              <p className="comparability-note">{soil.comparability_note}</p>
              <div className="channel-list">
                {soil.contributing_channels.map((channel) => (
                  <div key={channel.channel_id} className="channel-row">
                    <div>
                      <strong>{channel.channel_name}</strong>
                      <span>
                        {channel.depth_cm === null
                          ? 'Depth not supplied'
                          : `${String(channel.depth_cm)} cm`}
                        {channel.position_label ? ` · ${channel.position_label}` : ''}
                      </span>
                    </div>
                    <MeasurementDisplay
                      value={channel.numeric_value}
                      unit={channel.unit_symbol}
                      compact
                    />
                  </div>
                ))}
              </div>
              <small className="timestamp-range">
                Contributing channels: {soil.contributing_channel_count} · timestamps{' '}
                {formatDateTime(soil.timestamp_start)} to {formatDateTime(soil.timestamp_end)}
              </small>
            </>
          ) : (
            <p className="missing-value">No valid soil-moisture observations are available.</p>
          )}
        </article>
      </section>
    </div>
  );
}
