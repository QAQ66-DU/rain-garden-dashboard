import { http, HttpResponse } from 'msw';
import { setupServer } from 'msw/node';

import {
  deviceDetailFixture,
  devicesFixture,
  exploreFixture,
  measurementsFixture,
  overviewFixture,
  sitesFixture,
  treeDetailFixture,
  treeProbeId,
  replayDeviceDetailFixture,
  replayDeviceId,
  replayMeasurementsFixture,
} from './fixtures/api';

export const handlers = [
  http.get('*/api/v1/overview', () => HttpResponse.json(overviewFixture)),
  http.get('*/api/v1/sites', () => HttpResponse.json(sitesFixture)),
  http.get('*/api/v1/explore', ({ request }) => {
    const params = new URL(request.url).searchParams;
    const feature = params.get('feature');
    const group = params.get('metric_group') ?? 'hydrology';
    const channelParam = params.get('channels');
    const availableDevices = exploreFixture.available_devices.filter(
      (device) => !feature || device.feature_slug === feature,
    );
    const availableChannels = exploreFixture.available_channels.filter(
      (channel) => group === channel.metric_group && (!feature || channel.feature_slug === feature),
    );
    const selected =
      channelParam === null
        ? availableChannels.map((channel) => channel.channel_id)
        : channelParam.split(',').filter(Boolean);
    return HttpResponse.json({
      ...exploreFixture,
      start: params.get('start') ?? exploreFixture.start,
      end: params.get('end') ?? exploreFixture.end,
      feature,
      metric_group: group,
      available_devices: availableDevices,
      available_channels: availableChannels,
      selected_channel_ids: selected,
      series: exploreFixture.series.filter((series) =>
        selected.includes(series.channel.channel_id),
      ),
      quality_warnings: feature === 'tree-pit' ? [] : exploreFixture.quality_warnings,
    });
  }),
  http.get('*/api/v1/devices', ({ request }) => {
    const params = new URL(request.url).searchParams;
    const search = params.get('search')?.toLowerCase();
    const feature = params.get('feature');
    const deviceType = params.get('device_type');
    const siteId = params.get('site_id');
    const status = params.get('status');
    const items = devicesFixture.items.filter(
      (device) =>
        (!search || device.display_name.toLowerCase().includes(search)) &&
        (!feature || device.monitoring_feature?.public_slug === feature) &&
        (!deviceType || device.device_type === deviceType) &&
        (!siteId || device.site_id === siteId) &&
        (!status || device.freshness.calculated_status === status),
    );
    return HttpResponse.json({ ...devicesFixture, items });
  }),
  http.get('*/api/v1/devices/:deviceId', ({ params }) => {
    if (params['deviceId'] === treeProbeId) return HttpResponse.json(treeDetailFixture);
    if (params['deviceId'] === replayDeviceId) return HttpResponse.json(replayDeviceDetailFixture);
    return HttpResponse.json(deviceDetailFixture);
  }),
  http.get('*/api/v1/devices/:deviceId/measurements', ({ params }) =>
    HttpResponse.json(
      params['deviceId'] === replayDeviceId ? replayMeasurementsFixture : measurementsFixture,
    ),
  ),
];

export const server = setupServer(...handlers);
