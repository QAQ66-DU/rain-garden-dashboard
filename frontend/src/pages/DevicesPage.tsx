import { useState } from 'react';
import { Link } from 'react-router-dom';

import { useDevices, useSites } from '../api/queries';
import type { ConnectivityStatus } from '../api/types';
import { EmptyState, ErrorState, LoadingState } from '../components/DataState';
import { MeasurementDisplay } from '../components/MeasurementDisplay';
import { StatusBadge } from '../components/StatusBadge';
import { SyntheticBanner } from '../components/SyntheticBanner';
import { formatDateTime, humanizeCode } from '../utils/format';

export function DevicesPage() {
  const [search, setSearch] = useState('');
  const [siteId, setSiteId] = useState('');
  const [deviceType, setDeviceType] = useState('');
  const [status, setStatus] = useState<ConnectivityStatus | ''>('');
  const [cursor, setCursor] = useState<string | undefined>();
  const sites = useSites();
  const devices = useDevices({
    ...(search.trim() ? { search: search.trim() } : {}),
    ...(siteId ? { siteId } : {}),
    ...(deviceType ? { deviceType } : {}),
    ...(status ? { status } : {}),
    ...(cursor ? { cursor } : {}),
  });

  const resetCursor = () => {
    setCursor(undefined);
  };
  return (
    <div className="page-stack">
      <SyntheticBanner />
      <header className="page-hero">
        <div>
          <p className="eyebrow">Technical inventory</p>
          <h1>Devices</h1>
          <p>
            Search the public device inventory and review freshness, channels, and battery data.
          </p>
        </div>
      </header>

      <section className="filter-bar" aria-label="Device filters">
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
          <div className="device-list" aria-label="Devices">
            {devices.data.items.map((device) => (
              <article className="device-card" key={device.id}>
                <div className="device-card__identity">
                  <div className="device-icon" aria-hidden="true">
                    {device.device_type === 'weather_station'
                      ? 'WS'
                      : device.device_type === 'soil_moisture_sensor'
                        ? 'SM'
                        : 'WL'}
                  </div>
                  <div>
                    <p>{humanizeCode(device.device_type)}</p>
                    <h2>{device.display_name}</h2>
                    <span>{device.site_name}</span>
                  </div>
                </div>
                <div className="device-card__status">
                  <StatusBadge status={device.freshness.calculated_status} />
                  <small>As of {formatDateTime(device.freshness.reference_time)}</small>
                </div>
                <dl className="device-facts">
                  <div>
                    <dt>Last seen</dt>
                    <dd>{formatDateTime(device.last_seen_at)}</dd>
                  </div>
                  <div>
                    <dt>Latest battery</dt>
                    <dd>
                      <MeasurementDisplay
                        value={device.latest_battery?.numeric_value}
                        unit={device.latest_battery?.unit_symbol}
                        compact
                      />
                    </dd>
                  </div>
                  <div>
                    <dt>Status basis</dt>
                    <dd>{humanizeCode(device.freshness.status_basis)}</dd>
                  </div>
                </dl>
                <Link className="button-link" to={`/devices/${device.id}`}>
                  View device details <span aria-hidden="true">→</span>
                </Link>
              </article>
            ))}
          </div>
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
