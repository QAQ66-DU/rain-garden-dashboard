import { describe, expect, it } from 'vitest';

import { fromDateTimeLocalInput, presetWindow, toDateTimeLocalInput } from '../src/utils/format';

describe('Europe/London time handling', () => {
  it('displays UTC instants on the correct side of the spring DST transition', () => {
    expect(toDateTimeLocalInput('2026-03-29T00:30:00Z')).toBe('2026-03-29T00:30');
    expect(toDateTimeLocalInput('2026-03-29T01:30:00Z')).toBe('2026-03-29T02:30');
  });

  it('rejects a local wall-clock time skipped by the spring transition', () => {
    expect(fromDateTimeLocalInput('2026-03-29T01:30')).toBeNull();
    expect(fromDateTimeLocalInput('2026-03-29T02:30')).toBe('2026-03-29T01:30:00.000Z');
  });

  it('rejects a local wall-clock time repeated by the autumn transition', () => {
    expect(fromDateTimeLocalInput('2026-10-25T01:30')).toBeNull();
  });

  it('builds presets as exact UTC durations ending at the dataset reference', () => {
    expect(presetWindow('2026-06-01T12:00:00Z', 24)).toEqual([
      '2026-05-31T12:00:00.000Z',
      '2026-06-01T12:00:00.000Z',
    ]);
  });
});
