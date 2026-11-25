import { Component, DestroyRef, OnInit, computed, inject, signal } from '@angular/core';
import { interval, startWith } from 'rxjs';

import { ChartComponent, PullHandler } from '../../components/chart/chart.component';
import { ChartSeries, generateEmptyData, historyToSeries } from '../../components/chart/charts';
import { formatBytes, humanToBytes } from '../../components/indicator/format';
import {
  CONTACT_LOST,
  IndicatorComponent,
  IndicatorTile,
} from '../../components/indicator/indicator.component';
import { DataService } from '../../services/data.service';

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

export interface LiveChart {
  series: ChartSeries[];
  onPull: PullHandler;
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
  imports: [IndicatorComponent, ChartComponent],
  templateUrl: './home.component.html',
  styleUrl: './home.component.scss',
})
export class HomeComponent implements OnInit {
  private readonly service = inject(DataService);
  private readonly destroyRef = inject(DestroyRef);
  private cpuHistoryPending = false;

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

  /** Set once the CPU count and history are known. */
  readonly cpu = signal<LiveChart | undefined>(undefined);

  readonly memory: LiveChart = {
    onPull: (data) => [data.virtual[3], data.swap[0]],
    series: [
      { name: 'Used', data: generateEmptyData() },
      { name: 'Swap', data: generateEmptyData() },
    ],
  };

  readonly network: LiveChart = {
    onPull: (data) => {
      const nic = data[Object.keys(data)[0]];
      return [humanToBytes(nic.incoming.bytes), humanToBytes(nic.outgoing.bytes)];
    },
    series: [
      { name: 'Incoming', data: generateEmptyData() },
      { name: 'Outgoing', data: generateEmptyData() },
    ],
  };

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
        if (tile.endPoint === 'cpu') {
          this.initCpuChart(data.usage.length);
        }
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

  /** Builds the CPU chart once, seeded with the server-side load history. */
  private initCpuChart(cpuCount: number): void {
    if (this.cpu() || this.cpuHistoryPending) {
      return;
    }
    this.cpuHistoryPending = true;
    this.service.get<Record<string, number | string | null>[]>('history/cpu/load').subscribe({
      next: (history) => this.setCpuChart(cpuCount, history),
      // No history yet (empty database): start the chart from scratch.
      error: () => this.setCpuChart(cpuCount, []),
    });
  }

  private setCpuChart(cpuCount: number, history: Record<string, number | string | null>[]): void {
    const keys = Array.from({ length: cpuCount }, (_, i) => `cpu${i}`);
    const series: ChartSeries[] = historyToSeries(history, keys).map((data, i) => ({
      name: `Cpu load ${i}`,
      data: data.length ? data : generateEmptyData(),
    }));

    this.cpu.set({
      series,
      onPull: (data) => data.usage as number[],
    });
    this.cpuHistoryPending = false;
  }
}
