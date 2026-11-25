import { Component, DestroyRef, OnInit, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed, toObservable } from '@angular/core/rxjs-interop';
import { catchError, forkJoin, interval, map, of, startWith, switchMap, tap } from 'rxjs';

import { ChartComponent } from '../../components/chart/chart.component';
import { ChartSeries, HISTORY_GAP, historyToSeries } from '../../components/chart/charts';
import { formatBytes } from '../../components/indicator/format';
import {
  CONTACT_LOST,
  IndicatorComponent,
  IndicatorTile,
} from '../../components/indicator/indicator.component';
import { DataService } from '../../services/data.service';
import { AbsoluteRange, formatAbsolute } from '../../time-range/time-range';
import { TimeRangePickerComponent } from '../../time-range/time-range-picker.component';
import { TimeRangeService } from '../../time-range/time-range.service';

/** Delay between two refreshes of the status tiles. */
const REFRESH_TIME = 3000;

export interface Tile extends IndicatorTile {
  endPoint: string;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  formatter?: (data: any) => string;
  /** Used share (0..1) shown as a gauge. */
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  ratioOf?: (data: any) => number;
}

/** `/api/history/<metric>` response. */
export interface MetricHistory {
  step: number;
  samples: Record<string, number | string | null>[];
}

export interface DashboardCharts {
  cpu: ChartSeries[];
  memory: ChartSeries[];
  network: ChartSeries[];
}

const EMPTY_CHARTS: DashboardCharts = { cpu: [], memory: [], network: [] };

/** Series of each chart: key in the history entries -> legend. */
const MEMORY_SERIES = { used: 'Used', swap: 'Swap' };
const NETWORK_SERIES = { incoming: 'Received', outgoing: 'Sent' };

/** CPU keys found in the samples, in core order (cpu0, cpu1, ..., cpu10). */
function cpuKeys(samples: MetricHistory['samples']): string[] {
  const keys = new Set<string>();
  samples.forEach((sample) => Object.keys(sample).forEach((key) => /^cpu\d+$/.test(key) && keys.add(key)));
  return [...keys].sort((a, b) => Number(a.slice(3)) - Number(b.slice(3)));
}

function toSeries(history: MetricHistory, legends: Record<string, string>): ChartSeries[] {
  const keys = Object.keys(legends);
  // Buckets are `step` seconds apart: a missing one or more means no data.
  const gap = Math.max(HISTORY_GAP, 2.5 * history.step * 1000);
  return historyToSeries(history.samples, keys, gap).map((data, i) => ({ name: legends[keys[i]], data }));
}

/** Data points requested per chart: about one per horizontal pixel. */
function pointsWanted(): number {
  return Math.round(Math.min(Math.max(window.innerWidth, 300), 1500));
}

const used = (usedBytes: number, totalBytes: number) =>
  `${formatBytes(usedBytes)} / ${formatBytes(totalBytes)}`;

const TILES: Tile[] = [
  { text: 'Status', icon: 'monitor_heart', endPoint: 'metrics', type: 'status' },
  { text: 'Uptime', icon: 'schedule', endPoint: 'uptime', type: 'duration' },
  {
    text: 'Memory',
    icon: 'memory',
    endPoint: 'memory',
    type: 'string',
    // psutil.virtual_memory(): total, available, percent, used, free
    formatter: (data) => used(data.virtual[3], data.virtual[0]),
    ratioOf: (data) => data.virtual[2] / 100,
  },
  {
    text: 'Storage',
    icon: 'save',
    endPoint: 'partitions',
    type: 'string',
    // psutil.disk_usage('/'): total, used, free, percent
    formatter: (data) => used(data.usage[1], data.usage[0]),
    ratioOf: (data) => data.usage[3] / 100,
  },
  {
    text: 'CPU',
    icon: 'developer_board',
    endPoint: 'cpu',
    type: 'string',
    formatter: (data) => `${data.info.count} cores`,
  },
  {
    text: 'Host',
    icon: 'dns',
    endPoint: 'system_info',
    type: 'string',
    formatter: (data) => data.hostname,
  },
];

const clampRatio = (ratio: number) => (Number.isFinite(ratio) ? Math.min(Math.max(ratio, 0), 1) : undefined);

@Component({
  selector: 'app-home',
  providers: [TimeRangeService],
  imports: [IndicatorComponent, ChartComponent, TimeRangePickerComponent],
  templateUrl: './home.component.html',
  styleUrl: './home.component.scss',
})
export class HomeComponent implements OnInit {
  private readonly service = inject(DataService);
  private readonly destroyRef = inject(DestroyRef);

  readonly tiles = signal<Tile[]>(TILES.map((tile) => ({ ...tile })));

  /** Server reachability, from the last answer of every tile. */
  readonly health = computed(() => {
    const answered = this.tiles().filter((tile) => tile.value !== undefined);
    const lost = answered.filter((tile) => tile.value === CONTACT_LOST).length;
    if (!answered.length) {
      return { label: 'Connecting', css: '' };
    }
    if (lost === answered.length) {
      return { label: 'Offline', css: 'ko' };
    }
    return lost ? { label: 'Degraded', css: 'ko' } : { label: 'Live', css: 'ok' };
  });

  readonly hostname = computed(() => {
    const host = this.tiles().find((tile) => tile.endPoint === 'system_info')?.value;
    return host && host !== CONTACT_LOST ? String(host) : undefined;
  });

  protected readonly time = inject(TimeRangeService);

  /** Series shown by the charts, for `chartsRange`. */
  readonly charts = signal<DashboardCharts>(EMPTY_CHARTS);
  readonly chartsRange = signal<AbsoluteRange | undefined>(undefined);
  readonly chartsError = signal(false);

  constructor() {
    // Load the history of every chart for the time range, again on each refresh.
    toObservable(this.time.resolved)
      .pipe(
        switchMap((range) => {
          const query = `?from=${range.from}&to=${range.to}&points=${pointsWanted()}`;
          const get = (metric: string) => this.service.get<MetricHistory>(`history/${metric}${query}`);
          return forkJoin({ cpu: get('cpu'), memory: get('memory'), network: get('network') }).pipe(
            map((history) => ({ range, history })),
            catchError(() => of({ range, history: undefined })),
          );
        }),
        tap(({ range, history }) => {
          this.chartsError.set(!history);
          if (!history) {
            return;
          }
          const legends = Object.fromEntries(
            cpuKeys(history.cpu.samples).map((key) => [key, `Cpu load ${key.slice(3)}`]),
          );
          this.charts.set({
            cpu: toSeries(history.cpu, legends),
            memory: toSeries(history.memory, MEMORY_SERIES),
            network: toSeries(history.network, NETWORK_SERIES),
          });
          this.chartsRange.set(range);
        }),
        takeUntilDestroyed(),
      )
      .subscribe();
  }

  readonly chartList = computed(() => {
    const charts = this.charts();
    return [
      { title: 'CPU', subtitle: 'Load per core', series: charts.cpu, type: 'spline' as const, unit: 'percent' as const, wide: false },
      { title: 'Memory', subtitle: 'Used memory and swap', series: charts.memory, type: 'areaspline' as const, unit: 'bytes' as const, wide: false },
      { title: 'Network', subtitle: 'Data received and sent, all interfaces', series: charts.network, type: 'areaspline' as const, unit: 'bytes/s' as const, wide: true },
    ];
  });

  /** Whether a chart has no point at all in the time range. */
  isEmpty(series: ChartSeries[]): boolean {
    return series.every((serie) => serie.data.every((point) => point.y === null));
  }

  /** Drag over a chart: show that span. */
  zoomTo(range: AbsoluteRange): void {
    this.time.setRange({ from: formatAbsolute(range.from), to: formatAbsolute(range.to) });
  }

  ngOnInit(): void {
    const sub = interval(REFRESH_TIME)
      .pipe(startWith(0))
      .subscribe(() => this.tiles().forEach((_, index) => this.refreshTile(index)));
    this.destroyRef.onDestroy(() => sub.unsubscribe());
  }

  private refreshTile(index: number): void {
    const startedAt = Date.now();
    const tile = this.tiles()[index];
    const seconds = () => (Date.now() - startedAt) / 1000;

    this.service.get(tile.endPoint).subscribe({
      next: (data) => {
        this.patchTile(index, {
          value: tile.formatter ? tile.formatter(data) : data,
          ratio: tile.ratioOf ? clampRatio(tile.ratioOf(data)) : undefined,
          duration: seconds(),
        });
      },
      error: () => {
        this.patchTile(index, { value: CONTACT_LOST, ratio: undefined, duration: seconds() });
      },
    });
  }

  private patchTile(index: number, patch: Partial<Tile>): void {
    this.tiles.update((tiles) => tiles.map((t, i) => (i === index ? { ...t, ...patch } : t)));
  }
}
