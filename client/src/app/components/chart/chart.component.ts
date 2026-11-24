import {
  Component,
  DestroyRef,
  ElementRef,
  afterRenderEffect,
  computed,
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
import {
  ChartPoint,
  ChartSeries,
  ChartType,
  UPDATE_TIME,
  appendPoints,
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
    .chart {
      position: relative;
      width: 100%;
      height: 100%;
    }
  `,
})
export class ChartComponent {
  private readonly service = inject(DataService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly canvas = viewChild.required<ElementRef<HTMLCanvasElement>>('canvas');
  private chart?: Chart<'line', ChartPoint[]>;
  private polling?: Subscription;

  readonly series = input.required<ChartSeries[]>();
  readonly title = input('');
  readonly type = input<ChartType>('areaspline');
  readonly endPoint = input.required<string>();
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
      const config = buildChartConfig(series, this.title(), this.type());
      const canvas = this.canvas().nativeElement;
      untracked(() => {
        this.chart?.destroy();
        this.chart = new Chart(canvas, config);
        this.startPolling(windowFor(series));
      });
    });
    this.destroyRef.onDestroy(() => {
      this.polling?.unsubscribe();
      this.chart?.destroy();
    });
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
