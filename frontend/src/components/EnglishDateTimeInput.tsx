import { useId, useMemo, useState } from 'react';

import { toDateTimeLocalInput } from '../utils/format';

interface EnglishDateTimeInputProps {
  label: string;
  timeZone: string;
  value: string;
  onChange: (value: string) => void;
}

interface LocalDateTimeParts {
  year: number;
  month: number;
  day: number;
  hour: number;
  minute: number;
}

const MONTHS = [
  'January',
  'February',
  'March',
  'April',
  'May',
  'June',
  'July',
  'August',
  'September',
  'October',
  'November',
  'December',
] as const;
const WEEKDAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'] as const;

function pad(value: number): string {
  return String(value).padStart(2, '0');
}

function parseLocalValue(value: string): LocalDateTimeParts | null {
  const match = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})$/.exec(value);
  if (!match) return null;
  const parts = {
    year: Number(match[1]),
    month: Number(match[2]),
    day: Number(match[3]),
    hour: Number(match[4]),
    minute: Number(match[5]),
  };
  const date = new Date(Date.UTC(parts.year, parts.month - 1, parts.day));
  if (
    date.getUTCFullYear() !== parts.year ||
    date.getUTCMonth() !== parts.month - 1 ||
    date.getUTCDate() !== parts.day ||
    parts.hour > 23 ||
    parts.minute > 59
  ) {
    return null;
  }
  return parts;
}

function parseEnglishValue(value: string): LocalDateTimeParts | null {
  const match = /^(\d{2})\/(\d{2})\/(\d{4}) (\d{2}):(\d{2})$/.exec(value.trim());
  if (!match) return null;
  return parseLocalValue(
    `${String(match[3])}-${String(match[2])}-${String(match[1])}T${String(match[4])}:${String(match[5])}`,
  );
}

function localValue(parts: LocalDateTimeParts): string {
  return `${String(parts.year)}-${pad(parts.month)}-${pad(parts.day)}T${pad(parts.hour)}:${pad(parts.minute)}`;
}

function englishValue(value: string): string {
  const parts = parseLocalValue(value);
  if (!parts) return value;
  return `${pad(parts.day)}/${pad(parts.month)}/${String(parts.year)} ${pad(parts.hour)}:${pad(parts.minute)}`;
}

function defaultParts(timeZone: string): LocalDateTimeParts {
  return (
    parseLocalValue(toDateTimeLocalInput(new Date().toISOString(), timeZone)) ?? {
      year: 2000,
      month: 1,
      day: 1,
      hour: 0,
      minute: 0,
    }
  );
}

function calendarDays(year: number, month: number): Array<number | null> {
  const firstDay = new Date(Date.UTC(year, month - 1, 1)).getUTCDay();
  const mondayOffset = (firstDay + 6) % 7;
  const dayCount = new Date(Date.UTC(year, month, 0)).getUTCDate();
  return [
    ...Array.from<null>({ length: mondayOffset }).fill(null),
    ...Array.from({ length: dayCount }, (_, index) => index + 1),
  ];
}

export function EnglishDateTimeInput({
  label,
  timeZone,
  value,
  onChange,
}: EnglishDateTimeInputProps) {
  const inputId = useId();
  const dialogId = useId();
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState<LocalDateTimeParts>(
    () => parseLocalValue(value) ?? defaultParts(timeZone),
  );
  const days = useMemo(() => calendarDays(draft.year, draft.month), [draft.month, draft.year]);
  const monthName = MONTHS[draft.month - 1] ?? 'January';

  const openPicker = () => {
    setDraft(parseLocalValue(value) ?? defaultParts(timeZone));
    setOpen(true);
  };

  const changeMonth = (offset: number) => {
    setDraft((current) => {
      const date = new Date(Date.UTC(current.year, current.month - 1 + offset, 1));
      const nextYear = date.getUTCFullYear();
      const nextMonth = date.getUTCMonth() + 1;
      const maximumDay = new Date(Date.UTC(nextYear, nextMonth, 0)).getUTCDate();
      return {
        ...current,
        year: nextYear,
        month: nextMonth,
        day: Math.min(current.day, maximumDay),
      };
    });
  };

  return (
    <div className="english-date-time-field">
      <label htmlFor={inputId}>{label}</label>
      <div className="english-date-time-field__input-row">
        <input
          id={inputId}
          type="text"
          lang="en-GB"
          inputMode="numeric"
          autoComplete="off"
          placeholder="DD/MM/YYYY HH:mm"
          value={englishValue(value)}
          onChange={(event) => {
            const parsed = parseEnglishValue(event.target.value);
            onChange(parsed ? localValue(parsed) : event.target.value);
          }}
        />
        <button
          className="date-time-picker-button"
          type="button"
          aria-label={`${label}: open English calendar`}
          aria-haspopup="dialog"
          aria-expanded={open}
          aria-controls={dialogId}
          onClick={() => {
            if (open) setOpen(false);
            else openPicker();
          }}
        >
          <span aria-hidden="true">▦</span>
        </button>
      </div>
      <small>Format: DD/MM/YYYY HH:mm · 24-hour time</small>
      {open ? (
        <div
          className="date-time-picker"
          id={dialogId}
          role="dialog"
          aria-label={`${label} picker`}
        >
          <div className="date-time-picker__month">
            <button
              type="button"
              aria-label="Previous month"
              onClick={() => {
                changeMonth(-1);
              }}
            >
              ‹
            </button>
            <strong>{`${monthName} ${String(draft.year)}`}</strong>
            <button
              type="button"
              aria-label="Next month"
              onClick={() => {
                changeMonth(1);
              }}
            >
              ›
            </button>
          </div>
          <div className="date-time-picker__calendar" role="grid">
            {WEEKDAYS.map((weekday) => (
              <span className="date-time-picker__weekday" key={weekday} role="columnheader">
                {weekday}
              </span>
            ))}
            {days.map((day, index) =>
              day === null ? (
                <span key={`empty-${String(index)}`} />
              ) : (
                <button
                  type="button"
                  key={day}
                  aria-label={`${String(day)} ${monthName} ${String(draft.year)}`}
                  aria-pressed={day === draft.day}
                  onClick={() => {
                    setDraft((current) => ({ ...current, day }));
                  }}
                >
                  {String(day)}
                </button>
              ),
            )}
          </div>
          <div className="date-time-picker__time">
            <label>
              <span>Hour</span>
              <select
                value={pad(draft.hour)}
                onChange={(event) => {
                  setDraft((current) => ({ ...current, hour: Number(event.target.value) }));
                }}
              >
                {Array.from({ length: 24 }, (_, hour) => (
                  <option value={pad(hour)} key={hour}>
                    {pad(hour)}
                  </option>
                ))}
              </select>
            </label>
            <span aria-hidden="true">:</span>
            <label>
              <span>Minute</span>
              <select
                value={pad(draft.minute)}
                onChange={(event) => {
                  setDraft((current) => ({ ...current, minute: Number(event.target.value) }));
                }}
              >
                {Array.from({ length: 60 }, (_, minute) => (
                  <option value={pad(minute)} key={minute}>
                    {pad(minute)}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <div className="date-time-picker__actions">
            <button
              className="text-button"
              type="button"
              onClick={() => {
                setOpen(false);
              }}
            >
              Cancel
            </button>
            <button
              className="secondary-button"
              type="button"
              onClick={() => {
                onChange(localValue(draft));
                setOpen(false);
              }}
            >
              Use date and time
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
