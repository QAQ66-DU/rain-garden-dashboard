import { useQuery } from '@tanstack/react-query';

import {
  fetchDevice,
  fetchDevices,
  fetchMeasurements,
  fetchOverview,
  fetchSites,
  type DeviceFilters,
} from './client';

export function useOverview(siteId?: string) {
  return useQuery({
    queryKey: ['overview', siteId ?? 'default'],
    queryFn: () => fetchOverview(siteId),
  });
}

export function useSites() {
  return useQuery({ queryKey: ['sites'], queryFn: fetchSites });
}

export function useDevices(filters: DeviceFilters) {
  return useQuery({
    queryKey: ['devices', filters],
    queryFn: () => fetchDevices(filters),
  });
}

export function useDevice(deviceId: string | undefined) {
  return useQuery({
    queryKey: ['device', deviceId],
    queryFn: () => fetchDevice(deviceId ?? ''),
    enabled: Boolean(deviceId),
  });
}

export function useMeasurements(deviceId: string | undefined, channelId: string | undefined) {
  return useQuery({
    queryKey: ['measurements', deviceId, channelId],
    queryFn: () => fetchMeasurements(deviceId ?? '', channelId ?? ''),
    enabled: Boolean(deviceId && channelId),
  });
}
