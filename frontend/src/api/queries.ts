import { useMutation, useQuery } from '@tanstack/react-query';

import {
  fetchDevice,
  fetchDevices,
  fetchExplorer,
  fetchMeasurementCsv,
  fetchMeasurements,
  fetchOverview,
  fetchSites,
  type DeviceFilters,
  type ExplorerFilters,
} from './client';

const DEVICE_DETAIL_POLL_INTERVAL_MS = 30_000;

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

export function useExplorer(filters: ExplorerFilters | undefined) {
  return useQuery({
    queryKey: ['explorer', filters],
    queryFn: () => fetchExplorer(filters as ExplorerFilters),
    enabled: Boolean(filters),
  });
}

export function useDevice(deviceId: string | undefined) {
  return useQuery({
    queryKey: ['device', deviceId],
    queryFn: () => fetchDevice(deviceId ?? ''),
    enabled: Boolean(deviceId),
    refetchInterval: DEVICE_DETAIL_POLL_INTERVAL_MS,
    refetchIntervalInBackground: false,
  });
}

export function useMeasurements(
  deviceId: string | undefined,
  channelId: string | undefined,
  start?: string,
  end?: string,
  enabled = true,
) {
  return useQuery({
    queryKey: ['measurements', deviceId, channelId, start, end],
    queryFn: () => fetchMeasurements(deviceId ?? '', channelId ?? '', start, end),
    enabled: Boolean(deviceId && channelId && enabled),
    refetchInterval: DEVICE_DETAIL_POLL_INTERVAL_MS,
    refetchIntervalInBackground: false,
  });
}

export function useMeasurementExport() {
  return useMutation({ mutationFn: fetchMeasurementCsv });
}
