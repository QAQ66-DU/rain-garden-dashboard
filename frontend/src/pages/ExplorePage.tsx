import { useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';

import { useExplorer, useOverview } from '../api/queries';
import type { ExploreResponse } from '../api/types';
import { EmptyState, ErrorState, LoadingState } from '../components/DataState';
import { EnglishDateTimeInput } from '../components/EnglishDateTimeInput';
import { ExploreSeriesChart } from '../components/ExploreSeriesChart';
import { MetadataStatusNote } from '../components/MetadataStatusNote';
import { PageHeader } from '../components/PageHeader';
import { StatusBadge } from '../components/StatusBadge';
import { SyntheticBanner } from '../components/SyntheticBanner';
import { UnitStatusNote } from '../components/UnitStatusNote';
import type { ChartRangePreset } from '../utils/chartTimeAxis';
import {
  formatDateTime,
  formatDurationSeconds,
  formatNumber,
  fromDateTimeLocalInput,
  presetWindow,
  toDateTimeLocalInput,
} from '../utils/format';

type MetricGroup = 'hydrology' | 'soil' | 'weather' | 'operational';
type ExploreSeries = ExploreResponse['series'][number];

const PRESET_HOURS = { '24h': 24, '7d': 7 * 24, '30d': 30 * 24 } as const;

function isMetricGroup(value: string | null): value is MetricGroup {
  return (
    value === 'hydrology' || value === 'soil' || value === 'weather' || value === 'operational'
  );
}

function statisticValue(statistic: ExploreSeries['summary']['statistics'][number], unit: string) {
  if (statistic.code === 'duration_above_zero_seconds') {
    return formatDurationSeconds(statistic.value);
  }
  if (statistic.code === 'count') {
    return formatNumber(statistic.value);
  }
  return `${formatNumber(statistic.value)} ${unit}`;
}

export function ExplorePage() {
  const overview = useOverview();
  const [searchParams, setSearchParams] = useSearchParams();
  const [customStart, setCustomStart] = useState<string | null>(null);
  const [customEnd, setCustomEnd] = useState<string | null>(null);
  const [customError, setCustomError] = useState<string>();
  const start = searchParams.get('start');
  const end = searchParams.get('end');
  const featureParam = searchParams.get('feature') ?? 'all';
  const metricGroupParam = searchParams.get('group');
  const metricGroup: MetricGroup = isMetricGroup(metricGroupParam) ? metricGroupParam : 'hydrology';
  const presetParam = searchParams.get('preset');
  const rangePreset: ChartRangePreset =
    presetParam === '24h' || presetParam === '7d' || presetParam === '30d' ? presetParam : 'custom';
  const channels = searchParams.has('channels') ? (searchParams.get('channels') ?? '') : undefined;
  const timeZone = overview.data?.display_timezone ?? 'Europe/London';

  useEffect(() => {
    if (!overview.data || (start && end)) return;
    const [defaultStart, defaultEnd] = presetWindow(
      overview.data.reference_time,
      PRESET_HOURS['7d'],
    );
    const next = new URLSearchParams(searchParams);
    next.set('start', defaultStart);
    next.set('end', defaultEnd);
    next.set('preset', '7d');
    next.set('feature', featureParam);
    next.set('group', metricGroup);
    setSearchParams(next, { replace: true });
  }, [end, featureParam, metricGroup, overview.data, searchParams, setSearchParams, start]);

  const customStartValue =
    customStart ??
    (start && !Number.isNaN(Date.parse(start)) ? toDateTimeLocalInput(start, timeZone) : '');
  const customEndValue =
    customEnd ?? (end && !Number.isNaN(Date.parse(end)) ? toDateTimeLocalInput(end, timeZone) : '');

  const explorer = useExplorer(
    start && end
      ? {
          start,
          end,
          metricGroup,
          ...(featureParam !== 'all' ? { feature: featureParam } : {}),
          ...(channels !== undefined ? { channels } : {}),
        }
      : undefined,
  );

  const updateParams = (updates: Record<string, string | undefined>) => {
    const next = new URLSearchParams(searchParams);
    for (const [key, value] of Object.entries(updates)) {
      if (value === undefined) next.delete(key);
      else next.set(key, value);
    }
    setSearchParams(next);
  };

  const applyPreset = (preset: string) => {
    if (preset === 'custom') {
      updateParams({ preset: 'custom' });
      return;
    }
    if (!overview.data || !(preset in PRESET_HOURS)) return;
    const hours = PRESET_HOURS[preset as keyof typeof PRESET_HOURS];
    const [nextStart, nextEnd] = presetWindow(overview.data.reference_time, hours);
    setCustomError(undefined);
    setCustomStart(null);
    setCustomEnd(null);
    updateParams({ start: nextStart, end: nextEnd, preset, channels: undefined });
  };

  const applyCustom = () => {
    const nextStart = fromDateTimeLocalInput(customStartValue, timeZone);
    const nextEnd = fromDateTimeLocalInput(customEndValue, timeZone);
    if (!nextStart || !nextEnd) {
      setCustomError(
        `Enter valid ${timeZone} date-times. Times skipped or repeated by a daylight-saving transition are invalid.`,
      );
      return;
    }
    if (Date.parse(nextStart) >= Date.parse(nextEnd)) {
      setCustomError('Start must be earlier than end.');
      return;
    }
    setCustomError(undefined);
    updateParams({ start: nextStart, end: nextEnd, preset: 'custom', channels: undefined });
  };

  const toggleChannel = (channelId: string, checked: boolean) => {
    if (!explorer.data) return;
    const selected = new Set(explorer.data.selected_channel_ids);
    if (checked) selected.add(channelId);
    else selected.delete(channelId);
    updateParams({ channels: [...selected].join(',') });
  };

  const unitGroups = useMemo(() => {
    const groups = new Map<string, ExploreSeries[]>();
    for (const series of explorer.data?.series ?? []) {
      const key = `${series.channel.metric_code}|${series.channel.unit_code ?? 'pending'}|${series.channel.unit_confirmation_status}`;
      const group = groups.get(key) ?? [];
      group.push(series);
      groups.set(key, group);
    }
    return [...groups.values()];
  }, [explorer.data]);
  const freshnessByDevice = new Map(
    explorer.data?.available_devices.map((device) => [device.device_id, device.current_freshness]),
  );

  if (overview.isLoading || (!start && !end)) {
    return <LoadingState title="Preparing Time Explorer" />;
  }
  if (overview.isError || !overview.data) {
    return <ErrorState message={overview.error?.message} />;
  }
  const isProxy =
    !overview.data.synthetic && overview.data.synthetic_notice?.startsWith('Live proxy') === true;

  return (
    <div className="page-stack">
      <SyntheticBanner mode={isProxy ? 'proxy' : 'synthetic'} />
      <PageHeader
        title="Explore"
        meta={
          <dl className="page-header__facts">
            <div>
              <dt>Selected period</dt>
              <dd>
                {formatDateTime(start, timeZone)} → {formatDateTime(end, timeZone)}
              </dd>
            </div>
          </dl>
        }
      />

      <section className="toolbar explore-controls" aria-label="Time Explorer controls">
        <label className="filter-field">
          <span>Time range</span>
          <select
            value={searchParams.get('preset') ?? '7d'}
            onChange={(event) => {
              applyPreset(event.target.value);
            }}
          >
            <option value="24h">Last 24 hours</option>
            <option value="7d">Last 7 days</option>
            <option value="30d">Last 30 days</option>
            <option value="custom">Custom</option>
          </select>
        </label>
        {!isProxy ? (
          <label className="filter-field">
            <span>Feature</span>
            <select
              value={featureParam}
              onChange={(event) => {
                updateParams({ feature: event.target.value, channels: undefined });
              }}
            >
              <option value="all">All features</option>
              <option value="swale">Swale</option>
              <option value="tree-pit">Tree pit</option>
            </select>
          </label>
        ) : null}
        <label className="filter-field">
          <span>Metric group</span>
          <select
            value={metricGroup}
            onChange={(event) => {
              updateParams({ group: event.target.value, channels: undefined });
            }}
          >
            <option value="hydrology">Hydrology</option>
            <option value="soil">Soil</option>
            <option value="weather">Weather</option>
            <option value="operational">Operational / unverified</option>
          </select>
        </label>
        <div className="custom-time-fields">
          <EnglishDateTimeInput
            label={`Custom start (${timeZone})`}
            timeZone={timeZone}
            value={customStartValue}
            onChange={setCustomStart}
          />
          <EnglishDateTimeInput
            label={`Custom end (${timeZone})`}
            timeZone={timeZone}
            value={customEndValue}
            onChange={setCustomEnd}
          />
          <button className="secondary-button" type="button" onClick={applyCustom}>
            Apply custom range
          </button>
        </div>
        {customError ? (
          <p className="control-error" role="alert">
            {customError}
          </p>
        ) : null}
      </section>

      {explorer.isLoading ? <LoadingState title="Loading selected period" /> : null}
      {explorer.isError ? <ErrorState message={explorer.error.message} /> : null}
      {explorer.data ? (
        <>
          <section className="panel channel-selector" aria-labelledby="channel-selector-title">
            <div className="section-heading">
              <div>
                <h2 id="channel-selector-title">Sensor channels</h2>
              </div>
              <div className="inline-actions">
                <button
                  type="button"
                  className="text-button"
                  onClick={() => {
                    updateParams({ channels: undefined });
                  }}
                >
                  Select all
                </button>
                <button
                  type="button"
                  className="text-button"
                  onClick={() => {
                    updateParams({ channels: '' });
                  }}
                >
                  Clear
                </button>
              </div>
            </div>
            {explorer.data.available_channels.length > 0 ? (
              <div className="channel-options">
                {explorer.data.available_channels.map((channel) => (
                  <label key={channel.channel_id}>
                    <input
                      type="checkbox"
                      checked={explorer.data.selected_channel_ids.includes(channel.channel_id)}
                      onChange={(event) => {
                        toggleChannel(channel.channel_id, event.target.checked);
                      }}
                    />
                    <span>
                      <strong>{channel.device_name}</strong>
                      {channel.channel_name} · {channel.unit_symbol ?? 'unit pending'}
                      {channel.installation_depth_cm === null
                        ? ''
                        : ` · ${String(channel.installation_depth_cm)} cm`}
                    </span>
                  </label>
                ))}
              </div>
            ) : (
              <p className="missing-value">
                No configured channels match this feature and metric group.
              </p>
            )}
          </section>

          {unitGroups.length === 0 ? (
            <EmptyState
              title={
                explorer.data.available_devices.some(
                  (device) => device.sensor_configuration_status === 'pending',
                )
                  ? 'Channel configuration pending'
                  : 'No channels selected'
              }
              message="Choose configured channels, or select another feature or metric group. No measurements or depths are inferred for pending devices."
            />
          ) : (
            <div className="explore-groups">
              {unitGroups.map((group) => {
                const first = group[0];
                if (!first) return null;
                return (
                  <section
                    className="panel explore-group"
                    key={`${first.channel.metric_code}-${first.channel.unit_code ?? 'pending'}`}
                  >
                    <div className="section-heading">
                      <div>
                        <h2>{first.channel.metric_name}</h2>
                      </div>
                      <span className="unit-chip">
                        Unit · {first.channel.unit_symbol ?? 'mapping pending'}
                      </span>
                    </div>
                    <UnitStatusNote status={first.channel.unit_confirmation_status} />
                    <MetadataStatusNote status={first.channel.verification_status} />
                    <div className="small-multiples">
                      {group.map((series) => {
                        const current = freshnessByDevice.get(series.channel.device_id);
                        const unit = series.channel.unit_symbol ?? 'unit pending';
                        return (
                          <article className="explore-series-card" key={series.channel.channel_id}>
                            <header>
                              <div>
                                {!isProxy ? <p>{series.channel.feature_name}</p> : null}
                                <h3>{series.channel.device_name}</h3>
                                <span>{series.channel.channel_name}</span>
                              </div>
                              {current ? <StatusBadge status={current.calculated_status} /> : null}
                            </header>
                            <p className="chart-note">
                              {formatNumber(series.total_matching)} observations
                            </p>
                            {series.points.length > 0 ? (
                              <ExploreSeriesChart
                                series={series}
                                start={explorer.data.start}
                                end={explorer.data.end}
                                timeZone={explorer.data.display_timezone}
                                rangePreset={rangePreset}
                              />
                            ) : (
                              <p className="empty-chart">
                                No observations in this period; numeric zero is not substituted.
                              </p>
                            )}
                            <div className="explore-summary" aria-label="Period summary">
                              {series.summary.statistics.map((statistic) => (
                                <div key={statistic.code}>
                                  <span>{statistic.label}</span>
                                  <strong>{statisticValue(statistic, unit)}</strong>
                                  {statistic.observed_at ? (
                                    <small>
                                      {formatDateTime(
                                        statistic.observed_at,
                                        explorer.data.display_timezone,
                                      )}
                                    </small>
                                  ) : null}
                                </div>
                              ))}
                            </div>
                            {series.summary.status !== 'available' ? (
                              <p className="coverage-note">{series.summary.status_detail}</p>
                            ) : null}
                            <div className="coverage-panel">
                              <div>
                                <span>Selected-period coverage</span>
                                <strong>
                                  {series.coverage.coverage_percentage === null
                                    ? 'Unavailable'
                                    : `${formatNumber(series.coverage.coverage_percentage)}%`}
                                </strong>
                              </div>
                              <dl>
                                <div>
                                  <dt>Expected</dt>
                                  <dd>{series.coverage.expected_observations ?? '—'}</dd>
                                </div>
                                <div>
                                  <dt>Received</dt>
                                  <dd>{series.coverage.received_observations ?? '—'}</dd>
                                </div>
                                <div>
                                  <dt>Valid</dt>
                                  <dd>{series.coverage.valid_observations ?? '—'}</dd>
                                </div>
                                <div>
                                  <dt>Flagged</dt>
                                  <dd>{series.coverage.flagged_observations ?? '—'}</dd>
                                </div>
                                <div>
                                  <dt>Missing</dt>
                                  <dd>{series.coverage.missing_observations ?? '—'}</dd>
                                </div>
                              </dl>
                              <p>{series.coverage.status_detail}</p>
                              {series.coverage.late_observations > 0 ||
                              series.coverage.out_of_tolerance_observations > 0 ||
                              series.coverage.duplicate_slot_observations > 0 ? (
                                <p>
                                  Late {series.coverage.late_observations} · out of tolerance{' '}
                                  {series.coverage.out_of_tolerance_observations} · duplicate slot{' '}
                                  {series.coverage.duplicate_slot_observations}
                                </p>
                              ) : null}
                              {series.coverage.missing_intervals.length > 0 ? (
                                <details>
                                  <summary>
                                    {series.coverage.missing_intervals.length} missing interval
                                    {series.coverage.missing_intervals.length === 1 ? '' : 's'}
                                  </summary>
                                  <ul>
                                    {series.coverage.missing_intervals.map((interval) => (
                                      <li key={`${interval.start}-${interval.end}`}>
                                        {formatDateTime(
                                          interval.start,
                                          explorer.data.display_timezone,
                                        )}{' '}
                                        to{' '}
                                        {formatDateTime(
                                          interval.end,
                                          explorer.data.display_timezone,
                                        )}{' '}
                                        · {interval.expected_slots} expected slot
                                        {interval.expected_slots === 1 ? '' : 's'}
                                      </li>
                                    ))}
                                  </ul>
                                </details>
                              ) : null}
                            </div>
                          </article>
                        );
                      })}
                    </div>
                  </section>
                );
              })}
            </div>
          )}
        </>
      ) : null}
    </div>
  );
}
