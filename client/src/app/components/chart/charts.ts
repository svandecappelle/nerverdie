import type { ChartConfiguration, ChartDataset } from 'chart.js';

/** Delay between two polls of a chart endpoint. */
export const UPDATE_TIME = 3 * 1000;

export interface ChartPoint {
  x: number;
  y: number | null;
}

export interface ChartSeries {
  name: string;
  data: ChartPoint[];
}

export type ChartType = 'spline' | 'areaspline' | 'area' | 'line';

/** Line colours, one per series (cycled). */
export const SERIES_COLORS = [
  '#2f7ed8',
  '#0d233a',
  '#8bbc21',
  '#910000',
  '#1aadce',
  '#492970',
  '#f28f43',
  '#77a1e5',
];

const timeFormat = new Intl.DateTimeFormat(undefined, {
  hour: '2-digit',
  minute: '2-digit',
  second: '2-digit',
});
const dateTimeFormat = new Intl.DateTimeFormat(undefined, {
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
  hour: '2-digit',
  minute: '2-digit',
  second: '2-digit',
});

/** Time of day in the browser's time zone, for the x axis. */
export function formatTime(timestamp: number): string {
  return timeFormat.format(timestamp);
}

/** Full date and time in the browser's time zone, for tooltips. */
export function formatDateTime(timestamp: number): string {
  return dateTimeFormat.format(timestamp);
}

function withAlpha(hex: string, alpha: number): string {
  const value = parseInt(hex.slice(1), 16);
  return `rgba(${(value >> 16) & 255}, ${(value >> 8) & 255}, ${value & 255}, ${alpha})`;
}

function dataset(serie: ChartSeries, index: number, type: ChartType): ChartDataset<'line', ChartPoint[]> {
  const color = SERIES_COLORS[index % SERIES_COLORS.length];
  const filled = type === 'area' || type === 'areaspline';
  return {
    label: serie.name,
    // Copy: the chart mutates its data when points are appended.
    data: serie.data.map((point) => ({ ...point })),
    borderColor: color,
    backgroundColor: filled ? withAlpha(color, 0.25) : color,
    borderWidth: 2,
    fill: type === 'area' ? (index === 0 ? 'origin' : '-1') : filled ? 'origin' : false,
    tension: type === 'spline' || type === 'areaspline' ? 0.4 : 0,
    pointRadius: 0,
    pointHoverRadius: 4,
    // A null value (contact lost) is drawn as a gap.
    spanGaps: false,
  };
}

/** Builds the Chart.js configuration shared by every live chart of the dashboard. */
export function buildChartConfig(
  series: ChartSeries[],
  title: string,
  type: ChartType,
): ChartConfiguration<'line', ChartPoint[]> {
  const stacked = type === 'area';
  // Explicit bounds: Chart.js would otherwise round them to "nice" numbers,
  // which stretches a timestamp axis far beyond the data.
  const bounds = xBounds(series);
  return {
    type: 'line',
    data: { datasets: series.map((serie, index) => dataset(serie, index, type)) },
    options: {
      animation: false,
      responsive: true,
      maintainAspectRatio: false,
      parsing: false,
      normalized: true,
      interaction: { mode: 'nearest', axis: 'x', intersect: false },
      scales: {
        x: {
          type: 'linear',
          min: bounds?.min,
          max: bounds?.max,
          ticks: { maxTicksLimit: 8, callback: (value) => formatTime(Number(value)) },
        },
        y: {
          stacked,
          title: { display: true, text: 'Value' },
          grid: { color: (ctx) => (ctx.tick.value === 0 ? '#808080' : 'rgba(0, 0, 0, 0.1)') },
        },
      },
      plugins: {
        title: { display: !!title, text: title },
        legend: { display: true, position: 'bottom' },
        tooltip: {
          callbacks: {
            title: (items) => (items.length ? formatDateTime(items[0].parsed.x ?? 0) : ''),
            label: (item) => `${item.dataset.label}: ${(item.parsed.y ?? 0).toFixed(2)}`,
          },
        },
      },
    },
  };
}

/** Shortest time span shown by a live chart. */
export const MIN_WINDOW = 10 * 60 * 1000;

/** Smallest and largest x of all the points, or undefined when there is none. */
export function xBounds(datasets: { data: ChartPoint[] }[]): { min: number; max: number } | undefined {
  let min = Infinity;
  let max = -Infinity;
  for (const set of datasets) {
    for (const point of set.data) {
      min = Math.min(min, point.x);
      max = Math.max(max, point.x);
    }
  }
  return min <= max ? { min, max } : undefined;
}

/** Time span a chart keeps on screen: its initial span, at least MIN_WINDOW. */
export function windowFor(series: ChartSeries[]): number {
  const bounds = xBounds(series);
  return Math.max(MIN_WINDOW, bounds ? bounds.max - bounds.min : 0);
}

/**
 * Appends one point per series at time `x` and drops the points older than
 * `windowMs`, so that the chart keeps a sliding time window. Missing values
 * are drawn as gaps.
 */
export function appendPoints(
  datasets: { data: ChartPoint[] }[],
  x: number,
  values: (number | null | undefined)[],
  windowMs = MIN_WINDOW,
): void {
  const oldest = x - windowMs;
  datasets.forEach((set, index) => {
    set.data.push({ x, y: values[index] ?? null });
    const firstKept = set.data.findIndex((point) => point.x >= oldest);
    if (firstKept > 0) {
      set.data.splice(0, firstKept);
    }
  });
}

/** One point per second for the last `minutes` minutes, all at zero. */
export function generateEmptyData(minutes = 10, now = Date.now()): ChartPoint[] {
  const data: ChartPoint[] = [];
  for (let i = -minutes * 60; i <= 0; i += 1) {
    data.push({ x: now + (i + 3) * 1000, y: 0 });
  }
  return data;
}
