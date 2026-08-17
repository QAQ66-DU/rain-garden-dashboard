import { SITE_TIME_ZONE } from './format';

const HOUR_MS = 60 * 60 * 1000;
const MAX_TICKS = 8;

export type ChartRangePreset = '24h' | '7d' | '30d' | 'custom';
export type ChartTickGranularity = 'hour' | 'day';

export interface ChartTimeAxis {
  domain: [number, number];
  ticks: number[];
  granularity: ChartTickGranularity;
}

interface LocalClock {
  day: number;
  hour: number;
  minute: number;
}

function localClock(timestamp: number, timeZone = SITE_TIME_ZONE): LocalClock {
  const parts = new Intl.DateTimeFormat('en-GB', {
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hourCycle: 'h23',
    timeZone,
  }).formatToParts(timestamp);
  const value = (type: Intl.DateTimeFormatPartTypes) =>
    Number(parts.find((part) => part.type === type)?.value);
  return { day: value('day'), hour: value('hour'), minute: value('minute') };
}

function hourlyCandidates(start: number, end: number): number[] {
  const ticks: number[] = [];
  for (let tick = Math.ceil(start / HOUR_MS) * HOUR_MS; tick < end; tick += HOUR_MS) {
    ticks.push(tick);
  }
  return ticks;
}

function hourTicks(start: number, end: number, timeZone: string): number[] {
  const durationHours = (end - start) / HOUR_MS;
  const step = [1, 2, 3, 4, 6, 12, 24].find((candidate) => durationHours / candidate <= MAX_TICKS);
  const intervalHours = step ?? 24;
  const ticks = hourlyCandidates(start, end).filter((tick) => {
    const local = localClock(tick, timeZone);
    return local.minute === 0 && local.hour % intervalHours === 0;
  });
  return ticks.length >= 2 ? ticks : [start, end];
}

function dayTicks(start: number, end: number, timeZone: string): number[] {
  const midnights = hourlyCandidates(start, end).filter((tick) => {
    const local = localClock(tick, timeZone);
    return local.hour === 0 && local.minute === 0;
  });
  if (midnights.length <= MAX_TICKS) return midnights;
  const stride = Math.ceil(midnights.length / MAX_TICKS);
  return midnights.filter((_, index) => index % stride === 0);
}

function granularityForRange(
  preset: ChartRangePreset,
  start: number,
  end: number,
): ChartTickGranularity {
  if (preset === '24h') return 'hour';
  if (preset === '7d' || preset === '30d') return 'day';
  return end - start <= 48 * HOUR_MS ? 'hour' : 'day';
}

export function buildChartTimeAxis(
  startValue: string,
  endValue: string,
  preset: ChartRangePreset,
  timeZone = SITE_TIME_ZONE,
): ChartTimeAxis {
  const start = Date.parse(startValue);
  const end = Date.parse(endValue);
  if (!Number.isFinite(start) || !Number.isFinite(end) || start >= end) {
    throw new Error('A valid chart time range is required.');
  }
  const granularity = granularityForRange(preset, start, end);
  return {
    domain: [start, end],
    ticks:
      granularity === 'hour' ? hourTicks(start, end, timeZone) : dayTicks(start, end, timeZone),
    granularity,
  };
}

export function formatChartAxisTick(
  timestamp: number,
  granularity: ChartTickGranularity,
  timeZone = SITE_TIME_ZONE,
): string {
  if (granularity === 'day') {
    return new Intl.DateTimeFormat('en-GB', {
      day: 'numeric',
      month: 'short',
      timeZone,
    }).format(timestamp);
  }
  const local = localClock(timestamp, timeZone);
  return new Intl.DateTimeFormat('en-GB', {
    ...(local.hour === 0 && local.minute === 0 ? { day: 'numeric', month: 'short' } : {}),
    hour: '2-digit',
    minute: '2-digit',
    hourCycle: 'h23',
    timeZone,
  }).format(timestamp);
}

export function formatChartTooltipTimestamp(timestamp: number): string {
  return new Intl.DateTimeFormat('en-GB', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hourCycle: 'h23',
    timeZone: SITE_TIME_ZONE,
  }).format(timestamp);
}
