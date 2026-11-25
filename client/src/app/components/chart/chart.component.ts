import {
  Component,
  DestroyRef,
  ElementRef,
  afterRenderEffect,
  computed,
  effect,
  inject,
  input,
  untracked,
  viewChild,
} from '@angular/core';
import {
  Chart,
  Filler,
  Legend,
  LineController,
  LineElement,
  LinearScale,
  PointElement,
  Title,
  Tooltip,
} from 'chart.js';
import { Subscription, catchError, exhaustMap, interval, map, of } from 'rxjs';

import { DataService } from '../../services/data.service';
import { formatBytes } from '../indicator/format';
import { ThemeService } from '../../services/theme.service';
import {
  ChartPoint,
  ChartSeries,
  ChartTheme,
  ChartType,
  DEFAULT_CHART_THEME,
  UPDATE_TIME,
  appendPoints,
  applyChartTheme,
  buildChartConfig,
  windowFor,
  xBounds,
} from './charts';

// Only the Chart.js parts used by the dashboard are bundled.
Chart.register(LineController, LineElement, PointElement, LinearScale, Filler, Legend, Title, Tooltip);

/**
 * Turns the response of the chart endpoint into the new value of each
 * series, in order. `null` or a missing value is drawn as a gap.
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export type PullHandler = (data: any) => (number | null | undefined)[];

/** A live chart that polls `/api/<endPoint>` and appends the values returned by `onPull`. */
@Component({
  selector: 'app-chart',
  host: {
    '[style.width]': 'width()',
    '[style.height]': 'height()',
  },
  // The canvas fallback content describes the chart to assistive technologies.
  template: `
    <div class="chart">
      <canvas #canvas [attr.aria-label]="title()" role="img">{{ title() }}: {{ seriesNames() }}</canvas>
    </div>
  `,
  styles: `
    :host {
      display: inline-block;
      vertical-align: top;
    }
    /* The colours below are read back to theme the canvas. */
    .chart {
      position: relative;
      width: 100%;
      height: 100%;
      color: var(--mat-sys-on-surface-variant);
      border-top-color: var(--mat-sys-outline-variant);
      outline-color: var(--mat-sys-outline);
    }
  `,
})
export class ChartComponent {
  private readonly service = inject(DataService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly theme = inject(ThemeService);
  private readonly canvas = viewChild.required<ElementRef<HTMLCanvasElement>>('canvas');
  private chart?: Chart<'line', ChartPoint[]>;
  private polling?: Subscription;

  readonly series = input.required<ChartSeries[]>();
  readonly title = input('');
  /** Draw the title in the chart (it always names the canvas for assistive technologies). */
  readonly showTitle = input(true);
  readonly type = input<ChartType>('areaspline');
  readonly endPoint = input.required<string>();
  /**
   * Unit of the values: 'bytes' shows "1.5 GB", 'percent' a fixed 0-100 % axis,
   * on the axis and in tooltips.
   */
  readonly unit = input<'bytes' | 'percent' | 'number'>('number');
  readonly onPull = input.required<PullHandler>();
  readonly width = input('50%');
  readonly height = input('300px');

  protected readonly seriesNames = computed(() =>
    this.series()
      .map((serie) => serie.name)
      .join(', '),
  );

  constructor() {
    // (Re)build the chart once rendered, and whenever its series, title or type change.
    afterRenderEffect(() => {
      const series = this.series();
      const title = this.showTitle() ? this.title() : '';
      const type = this.type();
      const unit = this.unit();
      const canvas = this.canvas().nativeElement;
      untracked(() => {
        const config = buildChartConfig(series, title, type, this.readTheme());
        if (unit === 'percent') {
          const y = config.options?.scales?.['y'];
          if (y?.ticks) {
            y.min = 0;
            y.max = 100;
            y.ticks.callback = (value) => `${value} %`;
          }
          const tooltip = config.options?.plugins?.tooltip?.callbacks;
          if (tooltip) {
            tooltip.label = (item) => `${item.dataset.label}: ${(item.parsed.y ?? 0).toFixed(1)} %`;
          }
        }
        if (unit === 'bytes') {
          const y = config.options?.scales?.['y'];
          if (y?.ticks) {
            // Sizes are never negative, even when every value is zero.
            y.min = 0;
            y.ticks.callback = (value) => formatBytes(Number(value));
          }
          const tooltip = config.options?.plugins?.tooltip?.callbacks;
          if (tooltip) {
            tooltip.label = (item) => `${item.dataset.label}: ${formatBytes(item.parsed.y ?? 0)}`;
          }
        }
        this.chart?.destroy();
        this.chart = new Chart(canvas, config);
        this.startPolling(windowFor(series));
      });
    });
    // Theme switch: recolour the chart in place, keeping its points.
    effect(() => {
      this.theme.dark();
      untracked(() => {
        const chart = this.chart;
        if (chart) {
          applyChartTheme(chart.options, this.readTheme());
          chart.update('none');
        }
      });
    });
    this.destroyRef.onDestroy(() => {
      this.polling?.unsubscribe();
      this.chart?.destroy();
    });
  }

  /** Resolved theme colours of the chart container (see the styles above). */
  private readTheme(): ChartTheme {
    const element = this.canvas().nativeElement.parentElement;
    const style = element ? getComputedStyle(element) : undefined;
    const color = (value: string | undefined, fallback: string) =>
      value && /^(rgb|#|color\()/.test(value) ? value : fallback;
    return {
      text: color(style?.color, DEFAULT_CHART_THEME.text),
      grid: color(style?.borderTopColor, DEFAULT_CHART_THEME.grid),
      axis: color(style?.outlineColor, DEFAULT_CHART_THEME.axis),
    };
  }

  private startPolling(windowMs: number): void {
    this.polling?.unsubscribe();
    this.polling = interval(UPDATE_TIME)
      .pipe(
        // Skip a tick while the previous request is still pending.
        exhaustMap(() =>
          this.service.get(this.endPoint()).pipe(
            map((data) => ({ ok: true as const, data })),
            catchError(() => of({ ok: false as const, data: null })),
          ),
        ),
      )
      .subscribe((result) => {
        const chart = this.chart;
        if (!chart) {
          return;
        }
        // Contact lost: draw a gap in every series.
        const values = result.ok ? this.onPull()(result.data) : [];
        appendPoints(chart.data.datasets, Date.now(), values, windowMs);
        const bounds = xBounds(chart.data.datasets);
        const x = chart.options.scales?.['x'];
        if (bounds && x) {
          x.min = bounds.min;
          x.max = bounds.max;
        }
        chart.update('none');
      });
  }
}
