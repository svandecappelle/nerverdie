/**
 * Time ranges in the Grafana syntax: `now`, `now-15m`, `now-7d`, or an
 * absolute local time `YYYY-MM-DD HH:mm:ss`.
 */

/** A range as typed or chosen by the user (kept relative to "now" when it is). */
export interface TimeRange {
  from: string;
  to: string;
}

/** A range resolved to epoch milliseconds. */
export interface AbsoluteRange {
  from: number;
  to: number;
}

const UNITS: Record<string, number> = {
  s: 1000,
  m: 60 * 1000,
  h: 60 * 60 * 1000,
  d: 24 * 60 * 60 * 1000,
  w: 7 * 24 * 60 * 60 * 1000,
};

const UNIT_NAMES: Record<string, [string, string]> = {
  s: ['second', 'seconds'],
  m: ['minute', 'minutes'],
  h: ['hour', 'hours'],
  d: ['day', 'days'],
  w: ['week', 'weeks'],
};

export const DEFAULT_RANGE: TimeRange = { from: 'now-1h', to: 'now' };

export const QUICK_RANGES: TimeRange[] = [
  'now-5m',
  'now-15m',
  'now-30m',
  'now-1h',
  'now-3h',
  'now-6h',
  'now-12h',
  'now-24h',
  'now-2d',
  'now-7d',
  'now-30d',
].map((from) => ({ from, to: 'now' }));

/** Auto-refresh choices; '' turns it off. */
export const REFRESH_INTERVALS = ['', '3s', '5s', '10s', '30s', '1m', '5m'];
export const DEFAULT_REFRESH = '5s';

const RELATIVE = /^now(?:\s*-\s*(\d+)\s*([smhdw]))?$/;
const ABSOLUTE = /^(\d{4})-(\d{2})-(\d{2})(?:[ T](\d{2}):(\d{2})(?::(\d{2}))?)?$/;

/** Epoch milliseconds of `value` (relative to `now`), or NaN when it is not valid. */
export function parseTime(value: string, now: number): number {
  const text = value.trim();
  const relative = RELATIVE.exec(text);
  if (relative) {
    return relative[1] ? now - Number(relative[1]) * UNITS[relative[2]] : now;
  }
  const absolute = ABSOLUTE.exec(text);
  if (absolute) {
    const [, year, month, day, hours = '0', minutes = '0', seconds = '0'] = absolute;
    const date = new Date(+year, +month - 1, +day, +hours, +minutes, +seconds);
    // Reject overflowing dates such as 2026-02-31.
    return date.getMonth() === +month - 1 && date.getDate() === +day ? date.getTime() : NaN;
  }
  if (/^\d{10,}$/.test(text)) {
    return Number(text); // epoch milliseconds (shared URLs)
  }
  return NaN;
}

export function isRelative(value: string): boolean {
  return RELATIVE.test(value.trim());
}

/** Resolves a range, or returns an error message. */
export function resolveRange(range: TimeRange, now: number): AbsoluteRange | string {
  const from = parseTime(range.from, now);
  const to = parseTime(range.to, now);
  if (Number.isNaN(from)) {
    return 'Invalid "From": use now-6h or 2026-11-25 10:00:00';
  }
  if (Number.isNaN(to)) {
    return 'Invalid "To": use now or 2026-11-25 11:00:00';
  }
  if (from >= to) {
    return '"From" must be before "To"';
  }
  return { from, to };
}

const pad = (value: number) => String(value).padStart(2, '0');

/** Local `YYYY-MM-DD HH:mm:ss`, the absolute syntax accepted by parseTime. */
export function formatAbsolute(time: number): string {
  const d = new Date(time);
  return (
    `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ` +
    `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
  );
}

/** "Last 15 minutes", or the two dates of an absolute range. */
export function describeRange(range: TimeRange): string {
  const relative = RELATIVE.exec(range.from.trim());
  if (relative?.[1] && range.to.trim() === 'now') {
    const count = Number(relative[1]);
    const [one, many] = UNIT_NAMES[relative[2]];
    return `Last ${count === 1 ? one : `${count} ${many}`}`;
  }
  return `${range.from} to ${range.to}`;
}

/** Shortest form of a duration for relative ranges ("90m" -> "now-90m"). */
function relativeFrom(spanMs: number): string {
  for (const unit of ['w', 'd', 'h', 'm']) {
    if (spanMs % UNITS[unit] === 0) {
      return `now-${spanMs / UNITS[unit]}${unit}`;
    }
  }
  return `now-${Math.max(1, Math.round(spanMs / 1000))}s`;
}

function absolute(from: number, to: number): TimeRange {
  return { from: formatAbsolute(from), to: formatAbsolute(to) };
}

/** Doubles the span. A range ending now stays relative; others widen around their center. */
export function zoomOut(range: TimeRange, now: number): TimeRange {
  const resolved = resolveRange(range, now);
  if (typeof resolved === 'string') {
    return range;
  }
  const span = resolved.to - resolved.from;
  if (range.to.trim() === 'now') {
    return { from: relativeFrom(span * 2), to: 'now' };
  }
  const to = Math.min(resolved.to + span / 2, now);
  return absolute(to - span * 2, to);
}

/** Moves the range by half its span, back (-1) or forward (+1), never past now. */
export function shiftRange(range: TimeRange, direction: -1 | 1, now: number): TimeRange {
  const resolved = resolveRange(range, now);
  if (typeof resolved === 'string') {
    return range;
  }
  const span = resolved.to - resolved.from;
  const to = Math.min(resolved.to + (direction * span) / 2, now);
  return absolute(to - span, to);
}

/** Milliseconds of a refresh interval ('5s', '1m'), 0 when off or invalid. */
export function refreshMs(interval: string): number {
  const match = /^(\d+)([smh])$/.exec(interval);
  return match ? Number(match[1]) * UNITS[match[2]] : 0;
}
