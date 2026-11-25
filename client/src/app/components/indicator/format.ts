/**
 * Human readable duration ("3 days", "5 minutes"), with the same thresholds as
 * moment's `humanize()`, built on Intl instead of moment.
 */
export function humanizeDuration(seconds: number, locale = 'en'): string {
  const abs = Math.abs(seconds);
  const steps: [Intl.NumberFormatOptions['unit'], number, number][] = [
    // unit, size in seconds, switch to next unit when value reaches
    ['second', 1, 45],
    ['minute', 60, 45],
    ['hour', 3600, 22],
    ['day', 86400, 26],
    ['month', 2629800, 11],
    ['year', 31557600, Infinity],
  ];
  for (const [unit, size, limit] of steps) {
    const value = Math.round(abs / size);
    if (value < limit) {
      return new Intl.NumberFormat(locale, { style: 'unit', unit, unitDisplay: 'long' }).format(
        Math.max(value, 1),
      );
    }
  }
  return '';
}

const BYTE_UNITS = ['K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y'];

/** Parses the server's `bytes2human` output ("9.77K", "95.37M", "512.00B") back to bytes. */
export function humanToBytes(value: string | number): number {
  if (typeof value === 'number') {
    return value;
  }
  const match = /^\s*([\d.]+)\s*([A-Z])?/i.exec(value);
  if (!match) {
    return NaN;
  }
  const amount = parseFloat(match[1]);
  const exponent = BYTE_UNITS.indexOf((match[2] ?? 'B').toUpperCase()) + 1;
  return amount * Math.pow(1024, exponent);
}

/** Human readable size in binary units ("1.5 MB", "512 B"). */
export function formatBytes(bytes: number, locale = 'en'): string {
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  let value = bytes;
  let unit = 0;
  while (Math.abs(value) >= 1024 && unit < units.length - 1) {
    value /= 1024;
    unit++;
  }
  const digits = unit === 0 || value >= 100 ? 0 : 1;
  return `${new Intl.NumberFormat(locale, { maximumFractionDigits: digits }).format(value)} ${units[unit]}`;
}
