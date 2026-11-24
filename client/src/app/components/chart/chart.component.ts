import { Component, DestroyRef, computed, inject, input } from '@angular/core';
import type Highcharts from 'highcharts/esm/highcharts';
import { HighchartsChartDirective } from 'highcharts-angular';
import { Subscription, catchError, exhaustMap, interval, map, of } from 'rxjs';

import { DataService } from '../../services/data.service';
import { ChartSeries, ChartType, UPDATE_TIME, buildChartOptions } from './charts';

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export type PullHandler = (data: any, chart: Highcharts.Chart) => void;

/** A live chart that polls `/api/<endPoint>` and lets `onPull` append the new points. */
@Component({
  selector: 'app-chart',
  imports: [HighchartsChartDirective],
  host: {
    '[style.width]': 'width()',
    '[style.height]': 'height()',
  },
  template: `
    <!-- highcharts-light: keep the light theme even when the OS is in dark mode. -->
    <div
      highchartsChart
      [options]="options()"
      (chartInstance)="startPolling($event)"
      class="chart highcharts-light"
    ></div>
  `,
  styles: `
    :host {
      display: inline-block;
      vertical-align: top;
    }
    .chart {
      width: 100%;
      height: 100%;
    }
  `,
})
export class ChartComponent {
  private readonly service = inject(DataService);
  private readonly destroyRef = inject(DestroyRef);
  private polling?: Subscription;

  readonly series = input.required<ChartSeries[]>();
  readonly title = input('');
  readonly type = input<ChartType>('areaspline');
  readonly endPoint = input.required<string>();
  readonly onPull = input.required<PullHandler>();
  readonly width = input('50%');
  readonly height = input('300px');

  protected readonly options = computed(() =>
    buildChartOptions(this.series(), this.title(), this.type()),
  );

  constructor() {
    this.destroyRef.onDestroy(() => this.polling?.unsubscribe());
  }

  startPolling(chart: Highcharts.Chart): void {
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
        if (result.ok) {
          this.onPull()(result.data, chart);
        } else {
          // Contact lost: draw a gap.
          const x = Date.now();
          chart.series.forEach((serie) => serie.addPoint([x, null], true, true));
        }
      });
  }
}
