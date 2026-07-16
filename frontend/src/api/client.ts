import createClient from 'openapi-fetch';

import type { paths } from './generated';
import type { DeviceDetail, DeviceList, MeasurementPage, Overview, SiteList } from './types';

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
  deviceType?: string;
  status?: 'unknown' | 'online' | 'stale' | 'offline';
  cursor?: string;
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
): Promise<MeasurementPage> {
  async function fetchPage(cursor?: string): Promise<MeasurementPage> {
    const query = {
      sensor_channel_id: channelId,
      page_size: 500,
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
