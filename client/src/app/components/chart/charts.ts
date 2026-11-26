import type { ChartConfiguration, ChartDataset } from 'chart.js';

export interface ChartPoint {
  x: number;
  y: number | null;
}

export interface ChartSeries {
  name: string;
  data: ChartPoint[];
}

export type ChartType = 'spline' | 'areaspline' | 'area' | 'line';

/** Line colours, one per series (cycled); mid tones readable on light and dark backgrounds. */
export const SERIES_COLORS = [
  '#3b82f6',
  '#10b981',
  '#f59e0b',
  '#ef4444',
  '#8b5cf6',
  '#06b6d4',
  '#ec4899',
  '#84cc16',
];

/** Text and grid colours of a chart, taken from the page theme. */
export interface ChartTheme {
  text: string;
  grid: string;
  /** Line of the zero value. */
  axis: string;
}

export const DEFAULT_CHART_THEME: ChartTheme = {
  text: '#5f6368',
  grid: 'rgba(128, 128, 128, 0.18)',
  axis: 'rgba(128, 128, 128, 0.6)',
};

const timeFormat = new Intl.DateTimeFormat(undefined, {
  hour: '2-digit',
  minute: '2-digit',
  second: '2-digit',
});
const dayTimeFormat = new Intl.DateTimeFormat(undefined, {
  month: '2-digit',
  day: '2-digit',
  hour: '2-digit',
  minute: '2-digit',
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

/** Day and time, for the x axis of ranges longer than a day. */
export function formatDayTime(timestamp: number): string {
  return dayTimeFormat.format(timestamp);
}

const DAY = 24 * 60 * 60 * 1000;

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
    // Copy: the chart keeps its own data.
    data: serie.data.map((point) => ({ ...point })),
    borderColor: color,
    backgroundColor: filled ? withAlpha(color, 0.18) : color,
    borderWidth: 2,
    fill: type === 'area' ? (index === 0 ? 'origin' : '-1') : filled ? 'origin' : false,
    tension: type === 'spline' || type === 'areaspline' ? 0.4 : 0,
    pointRadius: 0,
    pointHoverRadius: 4,
    // A null value (contact lost) is drawn as a gap.
    spanGaps: false,
  };
}

/** Builds the Chart.js configuration shared by every chart of the dashboard. */
export function buildChartConfig(
  series: ChartSeries[],
  title: string,
  type: ChartType,
  theme: ChartTheme = DEFAULT_CHART_THEME,
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
      color: theme.text,
      scales: {
        x: {
          type: 'linear',
          min: bounds?.min,
          max: bounds?.max,
          border: { display: false },
          grid: { display: false },
          ticks: {
            color: theme.text,
            maxTicksLimit: 8,
            // Show the day too when the range spans more than a day.
            callback(value) {
              const span = Number(this.max) - Number(this.min);
              return span > DAY ? formatDayTime(Number(value)) : formatTime(Number(value));
            },
          },
        },
        y: {
          stacked,
          border: { display: false },
          ticks: { color: theme.text, maxTicksLimit: 6 },
          grid: { color: (ctx) => (ctx.tick.value === 0 ? theme.axis : theme.grid) },
        },
      },
      plugins: {
        title: { display: !!title, text: title, color: theme.text },
        legend: {
          display: true,
          position: 'bottom',
          labels: { color: theme.text, usePointStyle: true, pointStyle: 'circle', boxWidth: 8, boxHeight: 8 },
        },
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

/** Applies new theme colours to an existing chart configuration (theme switch). */
export function applyChartTheme(options: ChartConfiguration<'line', ChartPoint[]>['options'], theme: ChartTheme): void {
  if (!options) {
    return;
  }
  options.color = theme.text;
  const { x, y } = options.scales ?? {};
  for (const scale of [x, y]) {
    if (scale?.ticks) {
      scale.ticks.color = theme.text;
    }
  }
  if (y?.grid) {
    y.grid.color = (ctx) => (ctx.tick.value === 0 ? theme.axis : theme.grid);
  }
  const plugins = options.plugins;
  if (plugins?.title) {
    plugins.title.color = theme.text;
  }
  if (plugins?.legend?.labels) {
    plugins.legend.labels.color = theme.text;
  }
}

/** Samples further apart than this are not linked: the server was not collecting. */
export const HISTORY_GAP = 10 * 1000;

/**
 * Turns the stored history (`[{ date: 'YYYY-MM-DD HH:MM:SS', cpu0: 12.5, ... }]`,
 * server local time) into one series per key, sorted by time, with a gap where
 * consecutive samples are more than `gap` ms apart (the collection stopped).
 */
export function historyToSeries(
  history: Record<string, number | string | null>[],
  keys: string[],
  gap = HISTORY_GAP,
): ChartPoint[][] {
  const samples = history
    .map((entry) => ({ x: new Date(String(entry['date']).replace(' ', 'T')).getTime(), entry }))
    .filter((sample) => Number.isFinite(sample.x))
    .sort((a, b) => a.x - b.x);
  return keys.map((key) => {
    const points: ChartPoint[] = [];
    samples.forEach(({ x, entry }, index) => {
      if (index > 0 && x - samples[index - 1].x > gap) {
        points.push({ x: samples[index - 1].x + 1, y: null });
      }
      const value = entry[key];
      points.push({ x, y: typeof value === 'number' ? value : null });
    });
    return points;
  });
}
