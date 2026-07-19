export const SITE_TIME_ZONE = 'Europe/London';

export function formatDateTime(
  value: string | null | undefined,
  timeZone = SITE_TIME_ZONE,
): string {
  if (!value) {
    return 'Not available';
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return 'Invalid timestamp';
  }
  return new Intl.DateTimeFormat('en-GB', {
    dateStyle: 'medium',
    timeStyle: 'short',
    timeZone,
  }).format(date);
}

export function formatCompactDate(value: string, timeZone = SITE_TIME_ZONE): string {
  return new Intl.DateTimeFormat('en-GB', {
    day: '2-digit',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
    timeZone,
  }).format(new Date(value));
}

export function formatNumber(value: number, maximumFractionDigits = 2): string {
  return new Intl.NumberFormat('en-GB', { maximumFractionDigits }).format(value);
}

export function humanizeCode(value: string): string {
  return value.replaceAll('_', ' ').replace(/^./, (letter) => letter.toUpperCase());
}

interface DateTimeParts {
  year: number;
  month: number;
  day: number;
  hour: number;
  minute: number;
}

function zonedParts(date: Date, timeZone: string): DateTimeParts {
  const parts = new Intl.DateTimeFormat('en-GB', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hourCycle: 'h23',
    timeZone,
  }).formatToParts(date);
  const value = (type: Intl.DateTimeFormatPartTypes) =>
    Number(parts.find((part) => part.type === type)?.value);
  return {
    year: value('year'),
    month: value('month'),
    day: value('day'),
    hour: value('hour'),
    minute: value('minute'),
  };
}

function partsAsUtc(parts: DateTimeParts): number {
  return Date.UTC(parts.year, parts.month - 1, parts.day, parts.hour, parts.minute);
}

export function toDateTimeLocalInput(value: string, timeZone = SITE_TIME_ZONE): string {
  const parts = zonedParts(new Date(value), timeZone);
  const pad = (number: number) => String(number).padStart(2, '0');
  return `${String(parts.year)}-${pad(parts.month)}-${pad(parts.day)}T${pad(parts.hour)}:${pad(parts.minute)}`;
}

export function fromDateTimeLocalInput(value: string, timeZone = SITE_TIME_ZONE): string | null {
  const match = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})$/.exec(value);
  if (!match) return null;
  const target: DateTimeParts = {
    year: Number(match[1]),
    month: Number(match[2]),
    day: Number(match[3]),
    hour: Number(match[4]),
    minute: Number(match[5]),
  };
  const targetMilliseconds = partsAsUtc(target);
  let candidate = targetMilliseconds;
  for (let attempt = 0; attempt < 4; attempt += 1) {
    const displayed = zonedParts(new Date(candidate), timeZone);
    candidate += targetMilliseconds - partsAsUtc(displayed);
  }
  const verified = zonedParts(new Date(candidate), timeZone);
  if (partsAsUtc(verified) !== targetMilliseconds) return null;
  const ambiguous = [-2, -1, 1, 2].some((offsetHours) => {
    const alternative = new Date(candidate + offsetHours * 60 * 60 * 1000);
    return partsAsUtc(zonedParts(alternative, timeZone)) === targetMilliseconds;
  });
  if (ambiguous) return null;
  return new Date(candidate).toISOString();
}

export function presetWindow(referenceTime: string, hours: number): [string, string] {
  const end = new Date(referenceTime);
  return [new Date(end.getTime() - hours * 60 * 60 * 1000).toISOString(), end.toISOString()];
}

export function formatDurationSeconds(value: number): string {
  if (value % 3600 === 0) return `${formatNumber(value / 3600)} h`;
  if (value % 60 === 0) return `${formatNumber(value / 60)} min`;
  return `${formatNumber(value)} s`;
}
