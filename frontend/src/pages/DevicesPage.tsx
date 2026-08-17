import { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';

import { useDevices, useSites } from '../api/queries';
import type { ConnectivityStatus } from '../api/types';
import { ConfigurationStatus } from '../components/ConfigurationStatus';
import { EmptyState, ErrorState, LoadingState } from '../components/DataState';
import { IngestionSource } from '../components/IngestionSource';
import { PageHeader } from '../components/PageHeader';
import { StatusBadge } from '../components/StatusBadge';
import { SyntheticBanner } from '../components/SyntheticBanner';
import { UnitStatusNote } from '../components/UnitStatusNote';
import { formatDateTime, humanizeCode } from '../utils/format';

export function DevicesPage() {
  const location = useLocation();
  const [search, setSearch] = useState('');
  const [siteId, setSiteId] = useState('');
  const [feature, setFeature] = useState('');
  const [deviceType, setDeviceType] = useState('');
  const [status, setStatus] = useState<ConnectivityStatus | ''>('');
  const [cursor, setCursor] = useState<string | undefined>();
  const sites = useSites();
  const devices = useDevices({
    ...(search.trim() ? { search: search.trim() } : {}),
    ...(siteId ? { siteId } : {}),
    ...(feature ? { feature } : {}),
    ...(deviceType ? { deviceType } : {}),
    ...(status ? { status } : {}),
    ...(cursor ? { cursor } : {}),
  });
  const containsLiveMqtt = devices.data?.items.some(
    (device) => device.is_test_device && device.ingestion_mode === 'live_mqtt',
  );
  const containsProxy = devices.data?.items.some((device) => device.provenance === 'proxy');

  const resetCursor = () => {
    setCursor(undefined);
  };
  return (
    <div className="page-stack">
      <SyntheticBanner
        mode={
          containsProxy
            ? 'proxy'
            : containsLiveMqtt
              ? 'live-mixed'
              : devices.data?.contains_replay_data
                ? 'mixed'
                : 'synthetic'
        }
      />
      <PageHeader
        eyebrow="Technical inventory"
        title="Devices"
        description="Review device source, operational freshness, configuration completeness and unit interpretation as separate system properties."
      />

      <section className="toolbar filter-bar" aria-label="Device filters">
        <label className="filter-field filter-field--search">
          <span>Search devices</span>
          <input
            type="search"
            value={search}
            placeholder="e.g. weather"
            onChange={(event) => {
              setSearch(event.target.value);
              resetCursor();
            }}
          />
        </label>
        <label className="filter-field">
          <span>Monitoring feature</span>
          <select
            value={feature}
            onChange={(event) => {
              setFeature(event.target.value);
              resetCursor();
            }}
          >
            <option value="">All features</option>
            {containsProxy ? (
              <option value="proxy-sensors">Proxy sensors</option>
            ) : (
              <>
                <option value="swale">Swale</option>
                <option value="tree-pit">Tree pit</option>
              </>
            )}
          </select>
        </label>
        <label className="filter-field">
          <span>Site</span>
          <select
            value={siteId}
            onChange={(event) => {
              setSiteId(event.target.value);
              resetCursor();
            }}
          >
            <option value="">All sites</option>
            {sites.data?.items.map((site) => (
              <option key={site.id} value={site.id}>
                {site.name}
              </option>
            ))}
          </select>
        </label>
        <label className="filter-field">
          <span>Device type</span>
          <select
            value={deviceType}
            onChange={(event) => {
              setDeviceType(event.target.value);
              resetCursor();
            }}
          >
            <option value="">All types</option>
            <option value="weather_station">Weather station</option>
            <option value="soil_moisture_sensor">Soil-moisture sensor</option>
            <option value="water_level_sensor">Water-level sensor</option>
            <option value="multi_depth_soil_probe">Multi-depth soil probe</option>
            <option value="test_telemetry_device">Test telemetry device</option>
          </select>
        </label>
        <label className="filter-field">
          <span>Status</span>
          <select
            value={status}
            onChange={(event) => {
              setStatus(event.target.value as ConnectivityStatus | '');
              resetCursor();
            }}
          >
            <option value="">All statuses</option>
            <option value="online">Online</option>
            <option value="stale">Stale</option>
            <option value="offline">Offline</option>
            <option value="unknown">Unknown</option>
          </select>
        </label>
      </section>

      {devices.isLoading ? <LoadingState title="Loading device inventory" /> : null}
      {devices.isError ? <ErrorState message={devices.error.message} /> : null}
      {devices.data && devices.data.items.length === 0 ? (
        <EmptyState
          title="No devices match these filters"
          message="Adjust the search or filters. Missing devices are not inferred from measurements."
        />
      ) : null}
      {devices.data && devices.data.items.length > 0 ? (
        <>
          <section className="panel inventory-panel" aria-labelledby="device-inventory-title">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Current result set</p>
                <h2 id="device-inventory-title">Device inventory</h2>
              </div>
              <span className="count-chip">{devices.data.items.length} devices</span>
            </div>
            <div className="table-scroll">
              <table className="data-table data-table--responsive">
                <thead>
                  <tr>
                    <th>Device</th>
                    <th>Type / location</th>
                    <th>Source</th>
                    <th>Operational status</th>
                    <th>Last received</th>
                    <th>Configuration</th>
                    <th>Units</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {devices.data.items.map((device) => (
                    <tr key={device.id}>
                      <td data-label="Device">
                        <strong className="data-table__primary">{device.display_name}</strong>
                      </td>
                      <td data-label="Type / location">
                        <span className="data-table__primary">
                          {humanizeCode(device.device_type)}
                        </span>
                        <small className="data-table__secondary">
                          {device.monitoring_feature?.display_name ?? 'Feature not assigned'} ·{' '}
                          {device.site_name}
                        </small>
                      </td>
                      <td data-label="Source">
                        <IngestionSource
                          compact
                          ingestionMode={device.ingestion_mode}
                          provenance={device.provenance}
                          sourceSystem={device.source_system}
                        />
                      </td>
                      <td data-label="Operational status">
                        <StatusBadge status={device.freshness.calculated_status} />
                      </td>
                      <td data-label="Last received">
                        {device.last_seen_at === null
                          ? 'Never received'
                          : formatDateTime(device.last_seen_at)}
                      </td>
                      <td data-label="Configuration">
                        <ConfigurationStatus compact status={device.sensor_configuration_status} />
                      </td>
                      <td data-label="Units">
                        <UnitStatusNote compact status={device.unit_confirmation_summary} />
                      </td>
                      <td data-label="Action">
                        <Link
                          className="text-link"
                          to={{ pathname: `/devices/${device.id}`, search: location.search }}
                        >
                          View details <span aria-hidden="true">→</span>
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
          {devices.data.next_cursor ? (
            <button
              className="secondary-button"
              type="button"
              onClick={() => {
                setCursor(devices.data.next_cursor ?? undefined);
              }}
            >
              Next page
            </button>
          ) : null}
        </>
      ) : null}
    </div>
  );
}
