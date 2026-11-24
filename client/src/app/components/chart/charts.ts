import type Highcharts from 'highcharts/esm/highcharts';

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

/** Builds the Highcharts options shared by every live chart of the dashboard. */
export function buildChartOptions(
  series: ChartSeries[],
  title: string,
  type: ChartType,
): Highcharts.Options {
  return {
    chart: {
      type,
      zooming: { type: 'x' },
      animation: false,
      marginRight: 10,
    },
    title: { text: title },
    plotOptions: {
      area: {
        stacking: 'normal',
        marker: { enabled: false },
      },
      areaspline: {
        marker: { enabled: false },
      },
      spline: {
        marker: { enabled: false },
      },
    },
    xAxis: {
      type: 'datetime',
      tickPixelInterval: 150,
    },
    yAxis: {
      title: { text: 'Value' },
      plotLines: [{ value: 0, width: 1, color: '#808080' }],
    },
    tooltip: {
      headerFormat: '<b>{series.name}</b><br/>',
      pointFormat: '{point.x:%Y-%m-%d %H:%M:%S}<br/>{point.y:.2f}',
    },
    legend: { enabled: true },
    series: series.map((s) => ({ ...s, type }) as Highcharts.SeriesOptionsType),
  };
}

/** One point per second for the last `minutes` minutes, all at zero. */
export function generateEmptyData(minutes = 10, now = Date.now()): ChartPoint[] {
  const data: ChartPoint[] = [];
  for (let i = -minutes * 60; i <= 0; i += 1) {
    data.push({ x: now + (i + 3) * 1000, y: 0 });
  }
  return data;
}
