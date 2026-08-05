import type {
  DeviceDetail,
  DeviceList,
  DevicePublic,
  ExploreResponse,
  MeasurementPage,
  MeasurementValue,
  Overview,
  SiteList,
} from '../../src/api/types';

export const siteId = '00000000-0000-4000-8000-000000000001';
export const swaleFeatureId = '00000000-0000-4000-8000-000000000002';
export const treeFeatureId = '00000000-0000-4000-8000-000000000003';
export const weatherDeviceId = '00000000-0000-4000-8000-000000000011';
export const treeProbeId = '00000000-0000-4000-8000-000000000018';
export const rainfallChannelId = '00000000-0000-4000-8000-000000000021';
export const replayDeviceId = '00000000-0000-4000-8000-000000000019';
export const replayChannelOneId = '00000000-0000-4000-8000-000000000091';
export const replayChannelTwoId = '00000000-0000-4000-8000-000000000092';

const referenceTime = '2026-06-01T12:00:00Z';
const demoUnitStatus = 'synthetic_demo_only';
const swaleFeature = {
  id: swaleFeatureId,
  public_slug: 'swale',
  display_name: 'Swale',
  feature_type: 'swale',
};
const treeFeature = {
  id: treeFeatureId,
  public_slug: 'tree-pit',
  display_name: 'Tree pit',
  feature_type: 'tree_pit',
};
const replayFeature = {
  id: '00000000-0000-4000-8000-000000000009',
  public_slug: 'ttn-testbed',
  display_name: 'TTN Testbed',
  feature_type: 'testbed',
};

export const rainfallMeasurement: MeasurementValue = {
  channel_id: rainfallChannelId,
  channel_code: 'rainfall_intensity',
  channel_name: 'Rainfall intensity',
  metric_code: 'rainfall_intensity',
  metric_name: 'Rainfall intensity',
  numeric_value: 0,
  unit_code: 'mm_h',
  unit_symbol: 'mm/h',
  unit_confirmation_status: demoUnitStatus,
  verification_status: 'catalogued',
  timestamp_basis: null,
  measured_at: referenceTime,
  quality_flag: 'valid',
  quality_notes: null,
  installation_depth_cm: null,
  depth_cm: null,
  position_label: null,
};

const soilObservation = (index: number, value: number): MeasurementValue => ({
  channel_id: `00000000-0000-4000-8000-00000000003${String(index)}`,
  channel_code: 'soil_moisture',
  channel_name: `Soil moisture sensor ${String(index)}`,
  metric_code: 'soil_moisture',
  metric_name: 'Soil moisture',
  numeric_value: value,
  unit_code: 'vwc_pct',
  unit_symbol: '% VWC',
  unit_confirmation_status: demoUnitStatus,
  verification_status: 'catalogued',
  timestamp_basis: null,
  measured_at: '2026-06-01T10:00:00Z',
  quality_flag: 'valid',
  quality_notes: null,
  installation_depth_cm: null,
  depth_cm: null,
  position_label: null,
});

export const overviewFixture: Overview = {
  site_id: siteId,
  site_name: 'Orchard Park monitoring site',
  public_location_label: 'Orchard Park, Edinburgh; exact sensor locations withheld.',
  display_timezone: 'Europe/London',
  synthetic: true,
  synthetic_notice: 'Synthetic demonstration data — not live observations.',
  reference_time: referenceTime,
  last_data_update: referenceTime,
  devices: { total: 8, online: 3, stale: 2, offline: 2, unknown: 1 },
  latest_rainfall_intensity: rainfallMeasurement,
  soil_moisture: {
    metric_code: 'soil_moisture',
    unit_code: 'vwc_pct',
    unit_symbol: '% VWC',
    unit_confirmation_status: demoUnitStatus,
    minimum: 24.8,
    median: 27.2,
    maximum: 29.6,
    contributing_channel_count: 3,
    timestamp_start: '2026-06-01T10:00:00Z',
    timestamp_end: '2026-06-01T10:00:00Z',
    contributing_channels: [
      soilObservation(1, 24.8),
      soilObservation(2, 27.2),
      soilObservation(3, 29.6),
    ],
    comparability_note:
      'Latest valid observations are shown as a spread; channels are not averaged or assumed comparable across depth, position, or time.',
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

function device(
  suffix: number,
  displayName: string,
  deviceType: string,
  status: 'online' | 'stale' | 'offline' | 'unknown',
  feature: typeof swaleFeature | typeof treeFeature = swaleFeature,
): DevicePublic {
  const ageByStatus = { online: 0, stale: 7200, offline: 14_400, unknown: null };
  return {
    id: `00000000-0000-4000-8000-0000000000${String(suffix)}`,
    site_id: siteId,
    site_name: 'Orchard Park monitoring site',
    monitoring_feature: feature,
    display_name: displayName,
    device_type: deviceType,
    sensor_configuration_status: status === 'unknown' ? 'pending' : 'configured',
    operational_override: null,
    last_seen_at: status === 'unknown' ? null : referenceTime,
    location_disclosure: 'private',
    environment: null,
    source_system: null,
    ingestion_mode: null,
    provenance: null,
    is_test_device: false,
    freshness: {
      ...baseFreshness,
      calculated_status: status,
      age_seconds: ageByStatus[status],
      status_basis: status === 'unknown' ? 'never_seen' : baseFreshness.status_basis,
    },
    latest_battery: null,
  };
}

export const devicesFixture: DeviceList = {
  synthetic: false,
  contains_replay_data: true,
  reference_time: referenceTime,
  next_cursor: null,
  items: [
    device(11, 'Swale weather station', 'weather_station', 'online'),
    device(12, 'Swale soil sensor 1', 'soil_moisture_sensor', 'online'),
    device(13, 'Swale soil sensor 2', 'soil_moisture_sensor', 'online'),
    device(14, 'Swale soil sensor 3', 'soil_moisture_sensor', 'stale'),
    device(15, 'Swale water-level sensor 1', 'water_level_sensor', 'stale'),
    device(16, 'Swale water-level sensor 2', 'water_level_sensor', 'offline'),
    device(17, 'Swale water-level sensor 3', 'water_level_sensor', 'offline'),
    device(18, 'Tree-pit multi-depth probe', 'multi_depth_soil_probe', 'unknown', treeFeature),
    {
      ...device(19, 'Outflow A', 'test_telemetry_device', 'online', replayFeature),
      site_id: '00000000-0000-4000-8000-000000000099',
      site_name: 'TTN Testbed',
      sensor_configuration_status: 'pending',
      environment: 'test',
      source_system: 'ttn',
      ingestion_mode: 'offline_replay',
      provenance: 'exported_live_data',
      is_test_device: true,
      last_seen_at: '2026-08-03T16:11:01Z',
      freshness: {
        ...baseFreshness,
        calculated_status: 'online',
        age_seconds: 0,
        reference_time: '2026-08-03T16:11:01Z',
        status_basis: 'replay_dataset_reference_time',
      },
    },
  ],
};

export const sitesFixture: SiteList = {
  next_cursor: null,
  items: [
    {
      id: siteId,
      name: 'Orchard Park monitoring site',
      description:
        'Confirmed monitoring inventory with deterministic synthetic demonstration data.',
      public_location_label: 'Orchard Park, Edinburgh; exact sensor locations withheld.',
      location_disclosure: 'private',
      display_timezone: 'Europe/London',
      active: true,
    },
    {
      id: '00000000-0000-4000-8000-000000000099',
      name: 'TTN Testbed',
      description: 'Isolated local replay testbed.',
      public_location_label: 'Local replay testbed; location withheld',
      location_disclosure: 'withheld',
      display_timezone: 'Europe/London',
      active: true,
    },
  ],
};

const weatherDevice = devicesFixture.items[0];
const treeDevice = devicesFixture.items[7];
if (!weatherDevice || !treeDevice) {
  throw new Error('The device fixtures are required');
}

export const deviceDetailFixture: DeviceDetail = {
  ...weatherDevice,
  channels: [
    {
      id: rainfallChannelId,
      channel_code: 'rainfall_intensity',
      display_name: 'Rainfall intensity',
      metric_code: 'rainfall_intensity',
      metric_name: 'Rainfall intensity',
      unit_code: 'mm_h',
      unit_symbol: 'mm/h',
      unit_confirmation_status: demoUnitStatus,
      installation_depth_cm: null,
      depth_cm: null,
      position_label: null,
      expected_reporting_interval_seconds: 3600,
      reporting_schedule_anchor_at: '2026-05-25T12:00:00Z',
      reporting_jitter_tolerance_seconds: 300,
      water_level_reference_or_datum: null,
      scientific_meaning: 'Rainfall intensity measurement.',
      verification_status: 'catalogued',
      timestamp_basis: null,
      active: true,
    },
  ],
  latest_measurements: [rainfallMeasurement],
  telemetry: null,
};

export const treeDetailFixture: DeviceDetail = {
  ...treeDevice,
  channels: [],
  latest_measurements: [],
  telemetry: null,
};

const replayMeasurement: MeasurementValue = {
  channel_id: replayChannelOneId,
  channel_code: 'outflow_measurement_1',
  channel_name: 'Measurement 1',
  metric_code: 'unverified_numeric_output',
  metric_name: 'Unverified numeric output',
  numeric_value: 840,
  unit_code: null,
  unit_symbol: null,
  unit_confirmation_status: 'pending',
  verification_status: 'unverified',
  timestamp_basis: 'ttn_received_at',
  measured_at: '2026-08-03T16:10:00Z',
  quality_flag: 'valid',
  quality_notes: null,
  installation_depth_cm: null,
  depth_cm: null,
  position_label: null,
};

const replayMeasurementTwo: MeasurementValue = {
  ...replayMeasurement,
  channel_id: replayChannelTwoId,
  channel_code: 'outflow_measurement_2',
  channel_name: 'Measurement 2',
  numeric_value: 200,
};

const replayDevice = devicesFixture.items[8];
if (!replayDevice) throw new Error('Replay device fixture is required');

export const replayDeviceDetailFixture: DeviceDetail = {
  ...replayDevice,
  channels: [
    {
      id: replayChannelOneId,
      channel_code: 'outflow_measurement_1',
      display_name: 'Measurement 1',
      metric_code: 'unverified_numeric_output',
      metric_name: 'Unverified numeric output',
      unit_code: null,
      unit_symbol: null,
      unit_confirmation_status: 'pending',
      installation_depth_cm: null,
      depth_cm: null,
      position_label: null,
      expected_reporting_interval_seconds: null,
      reporting_schedule_anchor_at: null,
      reporting_jitter_tolerance_seconds: null,
      water_level_reference_or_datum: null,
      scientific_meaning: null,
      verification_status: 'unverified',
      timestamp_basis: 'ttn_received_at',
      active: true,
    },
    {
      id: replayChannelTwoId,
      channel_code: 'outflow_measurement_2',
      display_name: 'Measurement 2',
      metric_code: 'unverified_numeric_output',
      metric_name: 'Unverified numeric output',
      unit_code: null,
      unit_symbol: null,
      unit_confirmation_status: 'pending',
      installation_depth_cm: null,
      depth_cm: null,
      position_label: null,
      expected_reporting_interval_seconds: null,
      reporting_schedule_anchor_at: null,
      reporting_jitter_tolerance_seconds: null,
      water_level_reference_or_datum: null,
      scientific_meaning: null,
      verification_status: 'unverified',
      timestamp_basis: 'ttn_received_at',
      active: true,
    },
  ],
  latest_measurements: [replayMeasurement, replayMeasurementTwo],
  telemetry: {
    observed_at: '2026-08-03T16:11:01Z',
    battery_percent: 100,
    firmware_version: '3.0',
    hardware_version: '1.1',
    measurement_interval_value: 60,
    measurement_interval_unit: null,
    latest_rssi_dbm: -81,
    latest_snr_db: 8.5,
    gateway: 'Replay gateway (identifier withheld)',
  },
};

export const replayMeasurementsFixture: MeasurementPage = {
  items: [replayMeasurement, replayMeasurementTwo],
  next_cursor: null,
  total_matching: 2,
  start: '2026-07-27T16:11:01Z',
  end: '2026-08-03T16:11:01Z',
  reference_time: '2026-08-03T16:11:01Z',
  default_range_applied: true,
  synthetic: false,
  provenance: 'exported_live_data',
};

export const measurementsFixture: MeasurementPage = {
  items: [
    { ...rainfallMeasurement, measured_at: '2026-05-30T12:00:00Z', numeric_value: 1.2 },
    { ...rainfallMeasurement, measured_at: '2026-05-31T12:00:00Z', numeric_value: 0 },
    { ...rainfallMeasurement, measured_at: referenceTime, numeric_value: 3.4 },
  ],
  next_cursor: null,
  total_matching: 3,
  start: '2026-05-25T12:00:00Z',
  end: referenceTime,
  reference_time: referenceTime,
  default_range_applied: true,
  synthetic: true,
  provenance: null,
};

const waterExploreChannel: ExploreResponse['available_channels'][number] = {
  channel_id: '00000000-0000-4000-8000-000000000022',
  device_id: '00000000-0000-4000-8000-000000000015',
  device_name: 'Swale water-level sensor 1',
  feature_id: swaleFeatureId,
  feature_slug: 'swale',
  feature_name: 'Swale',
  channel_name: 'Water level',
  metric_code: 'water_level',
  metric_name: 'Water level',
  metric_group: 'hydrology',
  unit_code: 'mm',
  unit_symbol: 'mm',
  unit_confirmation_status: demoUnitStatus,
  verification_status: 'catalogued',
  installation_depth_cm: null,
  position_label: null,
  expected_reporting_interval_seconds: 3600,
  reporting_schedule_anchor_at: '2026-05-25T12:00:00Z',
  reporting_jitter_tolerance_seconds: 300,
  water_level_reference_or_datum: null,
};

const rainfallExploreChannel: ExploreResponse['available_channels'][number] = {
  ...waterExploreChannel,
  channel_id: rainfallChannelId,
  device_id: weatherDeviceId,
  device_name: 'Swale weather station',
  channel_name: 'Rainfall intensity',
  metric_code: 'rainfall_intensity',
  metric_name: 'Rainfall intensity',
  unit_code: 'mm_h',
  unit_symbol: 'mm/h',
};

const exploreCoverage: ExploreResponse['series'][number]['coverage'] = {
  status: 'available',
  status_detail:
    'Coverage counts unique schedule-aligned slots in the half-open UTC window [start, end); flagged slots are received but not valid. Late means received more than one reporting interval after measured_at.',
  expected_observations: 168,
  received_observations: 166,
  valid_observations: 166,
  flagged_observations: 0,
  missing_observations: 2,
  coverage_percentage: 98.81,
  late_observations: 0,
  out_of_tolerance_observations: 0,
  duplicate_slot_observations: 0,
  missing_intervals: [
    {
      start: '2026-05-28T12:00:00Z',
      end: '2026-05-28T13:00:00Z',
      expected_slots: 1,
    },
  ],
};

const explorePoint = (
  measurementId: string,
  measuredAt: string,
  value: number,
): ExploreResponse['series'][number]['points'][number] => ({
  measurement_id: measurementId,
  measured_at: measuredAt,
  received_at: measuredAt,
  numeric_value: value,
  quality_flag: 'valid',
  included_in_summary: true,
  expected_slot_at: measuredAt,
  timing_status: 'on_schedule',
  transmission_delay_seconds: 0,
});

const availableExploreDevices: ExploreResponse['available_devices'] = devicesFixture.items.map(
  (device) => ({
    device_id: device.id,
    device_name: device.display_name,
    device_type: device.device_type,
    sensor_configuration_status: device.sensor_configuration_status,
    feature_id: device.monitoring_feature?.id ?? swaleFeatureId,
    feature_slug: device.monitoring_feature?.public_slug ?? 'swale',
    feature_name: device.monitoring_feature?.display_name ?? 'Swale',
    current_freshness: device.freshness,
  }),
);

export const exploreFixture: ExploreResponse = {
  site_id: siteId,
  site_name: 'Orchard Park monitoring site',
  display_timezone: 'Europe/London',
  start: '2026-05-25T12:00:00Z',
  end: referenceTime,
  time_window_semantics: 'Half-open UTC interval [start, end); scientific axis is measured_at.',
  feature: null,
  metric_group: 'hydrology',
  selected_channel_ids: [rainfallChannelId, waterExploreChannel.channel_id],
  available_devices: availableExploreDevices,
  available_channels: [rainfallExploreChannel, waterExploreChannel],
  series: [
    {
      channel: rainfallExploreChannel,
      points: [
        explorePoint('00000000-0000-4000-8000-000000000061', '2026-05-30T12:00:00Z', 0),
        explorePoint('00000000-0000-4000-8000-000000000062', '2026-05-31T12:00:00Z', 1.4),
        explorePoint('00000000-0000-4000-8000-000000000063', '2026-06-01T11:00:00Z', 0),
      ],
      summary: {
        status: 'available',
        status_detail: 'Valid unique schedule slots only.',
        statistics: [
          {
            code: 'latest',
            label: 'Latest valid',
            value: 0,
            observed_at: '2026-06-01T11:00:00Z',
          },
          {
            code: 'maximum',
            label: 'Maximum intensity',
            value: 1.4,
            observed_at: '2026-05-31T12:00:00Z',
          },
          {
            code: 'duration_above_zero_seconds',
            label: 'Duration above zero',
            value: 3600,
            observed_at: null,
          },
        ],
      },
      coverage: {
        ...exploreCoverage,
        received_observations: 168,
        valid_observations: 168,
        missing_observations: 0,
        coverage_percentage: 100,
        missing_intervals: [],
      },
    },
    {
      channel: waterExploreChannel,
      points: [
        explorePoint('00000000-0000-4000-8000-000000000071', '2026-05-30T12:00:00Z', 74),
        explorePoint('00000000-0000-4000-8000-000000000072', '2026-06-01T11:00:00Z', 78),
      ],
      summary: {
        status: 'available',
        status_detail: 'Valid unique schedule slots only.',
        statistics: [
          { code: 'first', label: 'First valid', value: 74, observed_at: '2026-05-30T12:00:00Z' },
          {
            code: 'latest',
            label: 'Latest valid',
            value: 78,
            observed_at: '2026-06-01T11:00:00Z',
          },
          { code: 'minimum', label: 'Minimum', value: 74, observed_at: '2026-05-30T12:00:00Z' },
          {
            code: 'maximum',
            label: 'Maximum / peak',
            value: 78,
            observed_at: '2026-06-01T11:00:00Z',
          },
          {
            code: 'change',
            label: 'Change',
            value: 4,
            observed_at: '2026-06-01T11:00:00Z',
          },
        ],
      },
      coverage: exploreCoverage,
    },
  ],
  quality_warnings: [
    {
      measurement_id: '00000000-0000-4000-8000-000000000081',
      device_name: 'Swale weather station',
      channel_name: 'Relative humidity',
      observation_time: '2026-06-01T06:00:00Z',
      received_at: '2026-06-01T06:00:00Z',
      quality_flag: 'out_of_range',
      explanation: 'Observation falls outside a controlled definition-level validity bound.',
      excluded_from_summaries: true,
    },
  ],
  reference_time: referenceTime,
  synthetic: true,
};
