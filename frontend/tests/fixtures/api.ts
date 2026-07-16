import type {
  DeviceDetail,
  DeviceList,
  MeasurementPage,
  MeasurementValue,
  Overview,
  SiteList,
} from '../../src/api/types';

export const siteId = '00000000-0000-4000-8000-000000000001';
export const weatherDeviceId = '00000000-0000-4000-8000-000000000011';
export const soilDeviceId = '00000000-0000-4000-8000-000000000012';
export const waterDeviceId = '00000000-0000-4000-8000-000000000013';
export const rainfallChannelId = '00000000-0000-4000-8000-000000000021';

const referenceTime = '2026-06-01T12:00:00Z';

export const rainfallMeasurement: MeasurementValue = {
  channel_id: rainfallChannelId,
  channel_code: 'rainfall_hourly',
  channel_name: 'Rainfall gauge',
  metric_code: 'rainfall',
  metric_name: 'Rainfall',
  numeric_value: 0,
  unit_code: 'millimetre',
  unit_symbol: 'mm',
  measured_at: '2026-06-01T12:00:00Z',
  quality_flag: 'valid',
  quality_notes: null,
  depth_cm: null,
  position_label: 'Weather mast',
};

const battery = (channelId: string, value: number): MeasurementValue => ({
  channel_id: channelId,
  channel_code: 'battery_voltage',
  channel_name: 'Battery voltage',
  metric_code: 'battery_voltage',
  metric_name: 'Battery voltage',
  numeric_value: value,
  unit_code: 'volt',
  unit_symbol: 'V',
  measured_at: referenceTime,
  quality_flag: 'valid',
  quality_notes: null,
  depth_cm: null,
  position_label: null,
});

export const overviewFixture: Overview = {
  site_id: siteId,
  site_name: 'North Campus Rain Garden',
  public_location_label: 'University north campus',
  display_timezone: 'Europe/London',
  synthetic: true,
  synthetic_notice: 'Synthetic data for Phase 1 development and demonstration.',
  reference_time: referenceTime,
  last_data_update: referenceTime,
  devices: { total: 3, online: 1, stale: 1, offline: 1, unknown: 0 },
  latest_rainfall: rainfallMeasurement,
  soil_moisture: {
    metric_code: 'soil_moisture_vwc',
    unit_code: 'percent',
    unit_symbol: '%',
    minimum: 24.8,
    median: 27.2,
    maximum: 29.6,
    contributing_channel_count: 2,
    timestamp_start: '2026-06-01T10:00:00Z',
    timestamp_end: '2026-06-01T10:00:00Z',
    contributing_channels: [
      {
        channel_id: '00000000-0000-4000-8000-000000000031',
        channel_code: 'soil_moisture_10cm',
        channel_name: 'Soil moisture at 10 cm',
        metric_code: 'soil_moisture_vwc',
        metric_name: 'Volumetric soil moisture',
        numeric_value: 24.8,
        unit_code: 'percent',
        unit_symbol: '%',
        measured_at: '2026-06-01T10:00:00Z',
        quality_flag: 'valid',
        quality_notes: null,
        depth_cm: 10,
        position_label: 'Inlet bed',
      },
      {
        channel_id: '00000000-0000-4000-8000-000000000032',
        channel_code: 'soil_moisture_30cm',
        channel_name: 'Soil moisture at 30 cm',
        metric_code: 'soil_moisture_vwc',
        metric_name: 'Volumetric soil moisture',
        numeric_value: 29.6,
        unit_code: 'percent',
        unit_symbol: '%',
        measured_at: '2026-06-01T10:00:00Z',
        quality_flag: 'valid',
        quality_notes: null,
        depth_cm: 30,
        position_label: 'Inlet bed',
      },
    ],
    comparability_note:
      'Summary reports the spread across named channels; depth and position remain explicit.',
  },
  data_quality: {
    start: '2026-05-31T12:00:00Z',
    end: referenceTime,
    warning_count: 1,
  },
};

const baseFreshness = {
  reference_time: referenceTime,
  stale_after_minutes: 90,
  offline_after_minutes: 180,
  status_basis: 'last_seen_at',
};

export const devicesFixture: DeviceList = {
  synthetic: true,
  reference_time: referenceTime,
  next_cursor: null,
  items: [
    {
      id: weatherDeviceId,
      site_id: siteId,
      site_name: 'North Campus Rain Garden',
      display_name: 'Weather Station',
      device_type: 'weather_station',
      operational_override: null,
      last_seen_at: referenceTime,
      location_disclosure: 'public_label_only',
      freshness: {
        ...baseFreshness,
        calculated_status: 'online',
        age_seconds: 0,
      },
      latest_battery: battery('00000000-0000-4000-8000-000000000041', 3.7),
    },
    {
      id: soilDeviceId,
      site_id: siteId,
      site_name: 'North Campus Rain Garden',
      display_name: 'Soil Profile Sensor',
      device_type: 'soil_moisture_sensor',
      operational_override: null,
      last_seen_at: '2026-06-01T10:00:00Z',
      location_disclosure: 'public_label_only',
      freshness: {
        ...baseFreshness,
        calculated_status: 'stale',
        age_seconds: 7200,
      },
      latest_battery: battery('00000000-0000-4000-8000-000000000042', 3.5),
    },
    {
      id: waterDeviceId,
      site_id: siteId,
      site_name: 'North Campus Rain Garden',
      display_name: 'Outlet Level Sensor',
      device_type: 'water_level_sensor',
      operational_override: null,
      last_seen_at: '2026-06-01T08:00:00Z',
      location_disclosure: 'public_label_only',
      freshness: {
        ...baseFreshness,
        calculated_status: 'offline',
        age_seconds: 14_400,
      },
      latest_battery: battery('00000000-0000-4000-8000-000000000043', 3.4),
    },
  ],
};

export const sitesFixture: SiteList = {
  next_cursor: null,
  items: [
    {
      id: siteId,
      name: 'North Campus Rain Garden',
      description: 'Synthetic monitoring site for reproducible development.',
      public_location_label: 'University north campus',
      location_disclosure: 'public_label_only',
      display_timezone: 'Europe/London',
      active: true,
    },
  ],
};

const weatherDevice = devicesFixture.items[0];
if (!weatherDevice) {
  throw new Error('The weather-device fixture is required');
}

export const deviceDetailFixture: DeviceDetail = {
  ...weatherDevice,
  channels: [
    {
      id: rainfallChannelId,
      channel_code: 'rainfall_hourly',
      display_name: 'Rainfall gauge',
      metric_code: 'rainfall',
      metric_name: 'Rainfall',
      unit_code: 'millimetre',
      unit_symbol: 'mm',
      depth_cm: null,
      position_label: 'Weather mast',
      active: true,
    },
  ],
  latest_measurements: [rainfallMeasurement],
};

export const measurementsFixture: MeasurementPage = {
  items: [
    { ...rainfallMeasurement, measured_at: '2026-05-30T12:00:00Z', numeric_value: 1.2 },
    { ...rainfallMeasurement, measured_at: '2026-05-31T12:00:00Z', numeric_value: 0 },
    { ...rainfallMeasurement, measured_at: '2026-06-01T12:00:00Z', numeric_value: 3.4 },
  ],
  next_cursor: null,
  total_matching: 3,
  start: '2026-05-25T12:00:00Z',
  end: referenceTime,
  reference_time: referenceTime,
  default_range_applied: true,
  synthetic: true,
};
