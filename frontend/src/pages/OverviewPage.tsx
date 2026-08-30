import { Link, useLocation } from 'react-router-dom';

import { useExplorer, useOverview } from '../api/queries';
import { ErrorState, LoadingState } from '../components/DataState';
import { MeasurementDisplay } from '../components/MeasurementDisplay';
import { MetricCard } from '../components/MetricCard';
import { OrchardParkMap } from '../components/OrchardParkMap';
import { PageHeader } from '../components/PageHeader';
import { SyntheticBanner } from '../components/SyntheticBanner';
import { formatDateTime } from '../utils/format';

const MAX_VISIBLE_WARNINGS = 3;

export function OverviewPage() {
  const overview = useOverview();
  const warningWindow = overview.data?.data_quality;
  const warningDetails = useExplorer(
    warningWindow?.start && warningWindow.end && warningWindow.warning_count > 0
      ? {
          start: warningWindow.start,
          end: warningWindow.end,
          metricGroup: 'hydrology',
        }
      : undefined,
  );
  const location = useLocation();

  if (overview.isLoading) {
    return <LoadingState title="Loading site overview" />;
  }
  if (overview.isError || !overview.data) {
    return <ErrorState message={overview.error?.message} />;
  }

  const data = overview.data;
  const isProxy = !data.synthetic && data.synthetic_notice?.startsWith('Live proxy') === true;
  const visibleWarnings = (warningDetails.data?.quality_warnings ?? []).slice(
    0,
    Math.min(MAX_VISIBLE_WARNINGS, data.data_quality.warning_count),
  );
  const additionalWarningCount = Math.max(
    0,
    data.data_quality.warning_count - visibleWarnings.length,
  );
  return (
    <div className="page-stack">
      {isProxy ? <SyntheticBanner mode="proxy" /> : data.synthetic ? <SyntheticBanner /> : null}
      <PageHeader
        eyebrow="Site overview"
        title={isProxy ? 'Overview' : data.site_name}
        description={isProxy ? undefined : data.public_location_label}
        meta={
          <div className="page-header__facts">
            <div>
              <span className="page-header__fact-value">{formatDateTime(data.reference_time)}</span>
              <small>{isProxy ? 'Current UTC time' : 'Deterministic dataset reference'}</small>
            </div>
          </div>
        }
      />

      <section className="metric-grid" aria-label="Overview metrics">
        <MetricCard
          label="Monitored devices"
          value={data.devices.total}
          note={`${String(data.devices.online)} online · ${String(data.devices.stale)} stale · ${String(data.devices.offline)} offline`}
        />
        <MetricCard
          label="Latest rainfall intensity"
          value={
            <MeasurementDisplay
              value={data.latest_rainfall_intensity?.numeric_value}
              unit={data.latest_rainfall_intensity?.unit_symbol}
            />
          }
          note={
            data.latest_rainfall_intensity
              ? `${isProxy ? 'Latest valid reading' : 'Synthetic demo reading'} · ${formatDateTime(data.latest_rainfall_intensity.measured_at)}`
              : 'No valid rainfall observation'
          }
        />
        <MetricCard
          label="Data-quality flags"
          value={data.data_quality.warning_count}
          note={
            isProxy
              ? 'Non-valid observations in the 24 hours before the latest uplink'
              : 'Non-valid observations in the final 24 dataset hours'
          }
          tone={data.data_quality.warning_count > 0 ? 'warning' : 'default'}
        />
        <MetricCard
          label="Last data update"
          value={<span className="date-value">{formatDateTime(data.last_data_update)}</span>}
          note={isProxy ? 'Latest proxy uplink receipt' : 'Latest synthetic uplink receipt'}
        />
      </section>
      <OrchardParkMap />

      <section className="overview-grid">
        <article className="panel status-panel">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Network status</p>
              <h2>Device freshness</h2>
            </div>
            <Link className="text-link" to={{ pathname: '/devices', search: location.search }}>
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
        </article>

        <article className="panel quality-panel">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Data quality</p>
              <h2>Flagged observations</h2>
            </div>
          </div>
          <strong className="metric-card__value">{data.data_quality.warning_count}</strong>
          {data.data_quality.warning_count === 0 ? (
            <p className="missing-value">No flagged observations</p>
          ) : warningDetails.isLoading ? (
            <p className="missing-value">Loading flagged observations…</p>
          ) : warningDetails.isError || visibleWarnings.length === 0 ? (
            <p className="missing-value">Flagged observations unavailable.</p>
          ) : (
            <>
              <div className="channel-list" aria-label="Flagged observations">
                {visibleWarnings.map((warning) => (
                  <div key={warning.measurement_id} className="channel-row">
                    <div>
                      <strong>{warning.device_name}</strong>
                      <span>
                        {warning.channel_name} · {warning.quality_flag.replaceAll('_', ' ')}
                      </span>
                      <span>{warning.explanation}</span>
                      <span>{formatDateTime(warning.observation_time, data.display_timezone)}</span>
                    </div>
                  </div>
                ))}
              </div>
              {additionalWarningCount > 0 ? (
                <p className="panel-note">
                  + {additionalWarningCount} more flagged{' '}
                  {additionalWarningCount === 1 ? 'observation' : 'observations'}
                </p>
              ) : null}
            </>
          )}
        </article>
      </section>
    </div>
  );
}
