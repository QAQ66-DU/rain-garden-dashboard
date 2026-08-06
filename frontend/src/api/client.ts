import createClient from 'openapi-fetch';

import type { components, paths } from './generated';
import type {
  DeviceDetail,
  DeviceList,
  ExploreResponse,
  MeasurementPage,
  Overview,
  SiteList,
} from './types';

const browserOrigin = typeof window === 'undefined' ? 'http://localhost' : window.location.origin;
const configuredBaseUrl: unknown = import.meta.env['VITE_API_BASE_URL'];
const client = createClient<paths>({
  baseUrl:
    typeof configuredBaseUrl === 'string' && configuredBaseUrl.length > 0
      ? configuredBaseUrl
      : browserOrigin,
  fetch: (request) => globalThis.fetch(request),
});

export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

function errorMessage(error: unknown): string {
  if (typeof error === 'object' && error !== null && 'detail' in error) {
    const detail = error.detail;
    if (typeof detail === 'string') {
      return detail;
    }
  }
  return 'The dashboard could not load this data. Please try again.';
}

export interface DeviceFilters {
  search?: string;
  siteId?: string;
  feature?: string;
  deviceType?: string;
  status?: 'unknown' | 'online' | 'stale' | 'offline';
  cursor?: string;
}

export interface ExplorerFilters {
  start: string;
  end: string;
  siteId?: string;
  feature?: string;
  metricGroup: components['schemas']['MetricGroup'];
  channels?: string;
}

export interface MeasurementExportFilters {
  deviceId: string;
  channelId: string;
  start: string;
  end: string;
}

export interface MeasurementCsvDownload {
  blob: Blob;
  filename: string;
}

export async function fetchOverview(siteId?: string): Promise<Overview> {
  const { data, error, response } = await client.GET('/api/v1/overview', {
    params: { query: siteId ? { site_id: siteId } : {} },
  });
  if (!data) {
    throw new ApiError(response.status, errorMessage(error));
  }
  return data;
}

export async function fetchSites(): Promise<SiteList> {
  const { data, error, response } = await client.GET('/api/v1/sites', {
    params: { query: { page_size: 100 } },
  });
  if (!data) {
    throw new ApiError(response.status, errorMessage(error));
  }
  return data;
}

export async function fetchDevices(filters: DeviceFilters): Promise<DeviceList> {
  const query = {
    page_size: 50,
    ...(filters.search ? { search: filters.search } : {}),
    ...(filters.siteId ? { site_id: filters.siteId } : {}),
    ...(filters.feature ? { feature: filters.feature } : {}),
    ...(filters.deviceType ? { device_type: filters.deviceType } : {}),
    ...(filters.status ? { status: filters.status } : {}),
    ...(filters.cursor ? { cursor: filters.cursor } : {}),
  };
  const { data, error, response } = await client.GET('/api/v1/devices', {
    params: { query },
  });
  if (!data) {
    throw new ApiError(response.status, errorMessage(error));
  }
  return data;
}

export async function fetchExplorer(filters: ExplorerFilters): Promise<ExploreResponse> {
  const query = {
    start: filters.start,
    end: filters.end,
    metric_group: filters.metricGroup,
    ...(filters.siteId ? { site_id: filters.siteId } : {}),
    ...(filters.feature ? { feature: filters.feature } : {}),
    ...(filters.channels !== undefined ? { channels: filters.channels } : {}),
  };
  const { data, error, response } = await client.GET('/api/v1/explore', {
    params: { query },
  });
  if (!data) {
    throw new ApiError(response.status, errorMessage(error));
  }
  return data;
}

export async function fetchDevice(deviceId: string): Promise<DeviceDetail> {
  const { data, error, response } = await client.GET('/api/v1/devices/{device_id}', {
    params: { path: { device_id: deviceId } },
  });
  if (!data) {
    throw new ApiError(response.status, errorMessage(error));
  }
  return data;
}

export async function fetchMeasurements(
  deviceId: string,
  channelId: string,
  start?: string,
  end?: string,
): Promise<MeasurementPage> {
  async function fetchPage(cursor?: string): Promise<MeasurementPage> {
    const query = {
      sensor_channel_id: channelId,
      page_size: 500,
      ...(start && end ? { start, end } : {}),
      ...(cursor ? { cursor } : {}),
    };
    const { data, error, response } = await client.GET('/api/v1/devices/{device_id}/measurements', {
      params: { path: { device_id: deviceId }, query },
    });
    if (!data) {
      throw new ApiError(response.status, errorMessage(error));
    }
    return data;
  }

  const firstPage = await fetchPage();
  const items = [...firstPage.items];
  let cursor = firstPage.next_cursor ?? undefined;
  while (cursor) {
    const page = await fetchPage(cursor);
    items.push(...page.items);
    cursor = page.next_cursor ?? undefined;
  }
  return { ...firstPage, items, next_cursor: null };
}

export async function fetchMeasurementCsv(
  filters: MeasurementExportFilters,
): Promise<MeasurementCsvDownload> {
  const { data, error, response } = await client.GET(
    '/api/v1/devices/{device_id}/measurements/export.csv',
    {
      params: {
        path: { device_id: filters.deviceId },
        query: {
          start: filters.start,
          end: filters.end,
          sensor_channel_id: filters.channelId,
        },
      },
      parseAs: 'text',
    },
  );
  if (!response.ok || typeof data !== 'string') {
    throw new ApiError(response.status, errorMessage(error));
  }
  const disposition = response.headers.get('content-disposition') ?? '';
  const filename = /filename="?([^";]+)"?/i.exec(disposition)?.[1] ?? 'measurements.csv';
  return {
    blob: new Blob([data], { type: response.headers.get('content-type') ?? 'text/csv' }),
    filename,
  };
}
