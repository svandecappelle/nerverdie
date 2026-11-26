import {
  describeRange,
  formatAbsolute,
  parseTime,
  refreshMs,
  resolveRange,
  shiftRange,
  zoomOut,
} from './time-range';

const NOW = new Date(2026, 10, 25, 12, 0, 0).getTime();
const MIN = 60 * 1000;
const HOUR = 60 * MIN;

describe('parseTime', () => {
  it('reads relative times', () => {
    expect(parseTime('now', NOW)).toBe(NOW);
    expect(parseTime('now-15m', NOW)).toBe(NOW - 15 * MIN);
    expect(parseTime(' now - 2d ', NOW)).toBe(NOW - 48 * HOUR);
    expect(parseTime('now-1w', NOW)).toBe(NOW - 7 * 24 * HOUR);
  });

  it('reads absolute local times and epoch milliseconds', () => {
    expect(parseTime('2026-11-25 10:30:00', NOW)).toBe(new Date(2026, 10, 25, 10, 30).getTime());
    expect(parseTime('2026-11-25', NOW)).toBe(new Date(2026, 10, 25).getTime());
    expect(parseTime(String(NOW), NOW)).toBe(NOW);
  });

  it('rejects anything else', () => {
    for (const value of ['', 'yesterday', 'now+1h', 'now-5x', '2026-02-31 10:00:00', '2026-13-01']) {
      expect(parseTime(value, NOW)).toBeNaN();
    }
  });
});

describe('resolveRange', () => {
  it('returns the bounds, or an error message', () => {
    expect(resolveRange({ from: 'now-1h', to: 'now' }, NOW)).toEqual({ from: NOW - HOUR, to: NOW });
    expect(resolveRange({ from: 'later', to: 'now' }, NOW)).toContain('From');
    expect(resolveRange({ from: 'now', to: 'now-1h' }, NOW)).toContain('before');
  });
});

describe('describeRange', () => {
  it('names relative ranges like Grafana', () => {
    expect(describeRange({ from: 'now-5m', to: 'now' })).toBe('Last 5 minutes');
    expect(describeRange({ from: 'now-1h', to: 'now' })).toBe('Last hour');
    expect(describeRange({ from: 'now-7d', to: 'now' })).toBe('Last 7 days');
    expect(describeRange({ from: '2026-11-25 10:00:00', to: '2026-11-25 11:00:00' })).toBe(
      '2026-11-25 10:00:00 to 2026-11-25 11:00:00',
    );
  });
});

describe('zoomOut', () => {
  it('doubles a range ending now and keeps it relative', () => {
    expect(zoomOut({ from: 'now-5m', to: 'now' }, NOW)).toEqual({ from: 'now-10m', to: 'now' });
    expect(zoomOut({ from: 'now-12h', to: 'now' }, NOW)).toEqual({ from: 'now-1d', to: 'now' });
  });

  it('widens an absolute range around its center, never past now', () => {
    const range = { from: formatAbsolute(NOW - 4 * HOUR), to: formatAbsolute(NOW - 3 * HOUR) };
    expect(zoomOut(range, NOW)).toEqual({
      from: formatAbsolute(NOW - 4.5 * HOUR),
      to: formatAbsolute(NOW - 2.5 * HOUR),
    });
    const recent = { from: formatAbsolute(NOW - HOUR), to: formatAbsolute(NOW - 10 * MIN) };
    expect(zoomOut(recent, NOW).to).toBe(formatAbsolute(NOW));
  });
});

describe('shiftRange', () => {
  it('moves by half the span, and not beyond now', () => {
    expect(shiftRange({ from: 'now-1h', to: 'now' }, -1, NOW)).toEqual({
      from: formatAbsolute(NOW - 1.5 * HOUR),
      to: formatAbsolute(NOW - 0.5 * HOUR),
    });
    const past = { from: formatAbsolute(NOW - 2 * HOUR), to: formatAbsolute(NOW - 0.25 * HOUR) };
    expect(shiftRange(past, 1, NOW).to).toBe(formatAbsolute(NOW));
  });
});

describe('refreshMs', () => {
  it('converts the intervals', () => {
    expect(refreshMs('5s')).toBe(5000);
    expect(refreshMs('1m')).toBe(60000);
    expect(refreshMs('')).toBe(0);
  });
});
