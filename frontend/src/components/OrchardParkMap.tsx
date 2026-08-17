import L, { latLngBounds } from 'leaflet';
import { useEffect, useRef } from 'react';

import {
  ORCHARD_PARK_SENSORS,
  ORCHARD_PARK_SENSOR_TYPES,
  ORCHARD_PARK_SENSOR_TYPE_LABELS,
  type OrchardParkSensorLocation,
  type OrchardParkSensorType,
} from '../data/orchardParkSensors';

const INITIAL_CENTER: [number, number] = [55.95545, -3.23792];

function createSensorIcon(sensorType: OrchardParkSensorType) {
  return L.divIcon({
    className: 'sensor-marker-host',
    html: `<span class="sensor-marker sensor-marker--${sensorType}" aria-hidden="true"></span>`,
    iconAnchor: [14, 14],
    iconSize: [28, 28],
    popupAnchor: [0, -14],
  });
}

function createPopupContent(sensor: OrchardParkSensorLocation) {
  const article = document.createElement('article');
  const heading = document.createElement('h3');
  heading.textContent = sensor.displayName;
  article.appendChild(heading);

  const details = document.createElement('dl');
  const location = document.createElement('div');
  const locationTerm = document.createElement('dt');
  const locationValue = document.createElement('dd');
  locationTerm.textContent = 'Location';
  locationValue.textContent = `${sensor.latitude.toFixed(6)}, ${sensor.longitude.toFixed(6)}`;
  location.append(locationTerm, locationValue);

  const measurements = document.createElement('div');
  const measurementsTerm = document.createElement('dt');
  const measurementsValue = document.createElement('dd');
  const measurementList = document.createElement('ul');
  measurementsTerm.textContent = 'Measurements';
  sensor.measurements.forEach((measurement) => {
    const item = document.createElement('li');
    item.textContent = measurement;
    measurementList.appendChild(item);
  });
  measurementsValue.appendChild(measurementList);
  measurements.append(measurementsTerm, measurementsValue);

  details.append(location, measurements);
  article.appendChild(details);
  return article;
}

export function OrchardParkMap() {
  const mapContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const container = mapContainerRef.current;
    if (container === null) return;

    const map = L.map(container, {
      center: INITIAL_CENTER,
      maxZoom: 19,
      scrollWheelZoom: true,
      zoom: 17,
      zoomControl: false,
    });
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    }).addTo(map);
    L.control.zoom({ position: 'bottomleft' }).addTo(map);

    ORCHARD_PARK_SENSORS.forEach((sensor) => {
      L.marker([sensor.latitude, sensor.longitude], {
        alt: sensor.displayName,
        icon: createSensorIcon(sensor.sensorType),
        keyboard: true,
        riseOnHover: true,
        title: sensor.displayName,
      })
        .bindPopup(createPopupContent(sensor), {
          className: 'sensor-popup',
          maxWidth: 250,
          minWidth: 210,
        })
        .addTo(map);
    });

    const bounds = latLngBounds(
      ORCHARD_PARK_SENSORS.map(({ latitude, longitude }) => [latitude, longitude]),
    );
    const refreshMapSize = () => {
      map.invalidateSize({ pan: false });
      map.fitBounds(bounds, { animate: false, maxZoom: 18, padding: [42, 42] });
    };
    refreshMapSize();

    const resizeObserver = new ResizeObserver(refreshMapSize);
    resizeObserver.observe(container);

    return () => {
      resizeObserver.disconnect();
      map.remove();
    };
  }, []);

  return (
    <section className="panel sensor-map-section" aria-labelledby="orchard-park-map-title">
      <div className="section-heading sensor-map-heading">
        <div>
          <p className="eyebrow">Site reference</p>
          <h2 id="orchard-park-map-title">Orchard Park monitoring layout</h2>
          <p>Sensor locations across the swale and tree-pit monitoring network.</p>
        </div>
        <span className="sensor-map-count">8 locations</span>
      </div>

      <div className="sensor-map-frame">
        <div
          ref={mapContainerRef}
          className="sensor-map-canvas sensor-map"
          role="region"
          aria-label="Interactive map of Orchard Park monitoring locations"
        />

        <aside className="sensor-map-legend" aria-label="Sensor type legend">
          <strong>Sensor type</strong>
          <ul>
            {ORCHARD_PARK_SENSOR_TYPES.map((sensorType) => (
              <li key={sensorType}>
                <span
                  className={`sensor-legend-symbol sensor-legend-symbol--${sensorType}`}
                  aria-hidden="true"
                />
                {ORCHARD_PARK_SENSOR_TYPE_LABELS[sensorType]}
              </li>
            ))}
          </ul>
        </aside>
      </div>
    </section>
  );
}
