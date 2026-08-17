export const ORCHARD_PARK_SENSOR_TYPES = [
  'soil-moisture',
  'water-level',
  'weather-station',
  'tree-pit',
] as const;

export type OrchardParkSensorType = (typeof ORCHARD_PARK_SENSOR_TYPES)[number];

export interface OrchardParkSensorLocation {
  id: string;
  displayName: string;
  sensorType: OrchardParkSensorType;
  latitude: number;
  longitude: number;
  measurements: readonly string[];
}

export const ORCHARD_PARK_SENSOR_TYPE_LABELS: Record<OrchardParkSensorType, string> = {
  'soil-moisture': 'Soil moisture',
  'water-level': 'Water level',
  'weather-station': 'Weather station',
  'tree-pit': 'Tree-pit sensor',
};

export const ORCHARD_PARK_SENSORS = [
  {
    id: 'orchard-park-soil-moisture-1',
    displayName: 'Soil moisture sensor 1',
    sensorType: 'soil-moisture',
    latitude: 55.955391,
    longitude: -3.238305,
    measurements: ['Soil moisture', 'Temperature', 'Electrical conductivity'],
  },
  {
    id: 'orchard-park-soil-moisture-2',
    displayName: 'Soil moisture sensor 2',
    sensorType: 'soil-moisture',
    latitude: 55.95547,
    longitude: -3.237539,
    measurements: ['Soil moisture', 'Temperature', 'Electrical conductivity'],
  },
  {
    id: 'orchard-park-soil-moisture-3',
    displayName: 'Soil moisture sensor 3',
    sensorType: 'soil-moisture',
    latitude: 55.955613,
    longitude: -3.236647,
    measurements: ['Soil moisture', 'Temperature', 'Electrical conductivity'],
  },
  {
    id: 'orchard-park-water-level-1',
    displayName: 'Water level sensor 1',
    sensorType: 'water-level',
    latitude: 55.955383,
    longitude: -3.238577,
    measurements: ['Water level'],
  },
  {
    id: 'orchard-park-water-level-2',
    displayName: 'Water level sensor 2',
    sensorType: 'water-level',
    latitude: 55.955405,
    longitude: -3.237983,
    measurements: ['Water level'],
  },
  {
    id: 'orchard-park-water-level-3',
    displayName: 'Water level sensor 3',
    sensorType: 'water-level',
    latitude: 55.955528,
    longitude: -3.237223,
    measurements: ['Water level'],
  },
  {
    id: 'orchard-park-weather-station',
    displayName: 'Weather station',
    sensorType: 'weather-station',
    latitude: 55.955312,
    longitude: -3.238602,
    measurements: [
      'Air temperature',
      'Humidity',
      'Wind speed',
      'Wind direction',
      'Rainfall intensity',
      'Light intensity',
      'UV index',
      'Barometric pressure',
    ],
  },
  {
    id: 'orchard-park-tree-pit-multi-depth',
    displayName: 'Tree-pit multi-depth soil sensor',
    sensorType: 'tree-pit',
    latitude: 55.955466,
    longitude: -3.23919,
    measurements: ['Soil moisture at multiple depths', 'Soil temperature at multiple depths'],
  },
] as const satisfies readonly OrchardParkSensorLocation[];
