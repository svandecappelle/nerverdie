import { Component, DestroyRef, OnInit, inject, signal } from '@angular/core';
import { MatGridListModule } from '@angular/material/grid-list';
import { interval, startWith } from 'rxjs';

import { ChartComponent, PullHandler } from '../../components/chart/chart.component';
import { ChartSeries, generateEmptyData } from '../../components/chart/charts';
import { humanToBytes } from '../../components/indicator/format';
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
  cols: number;
  rows: number;
  color: string;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  formatter?: (data: any) => string;
}

export interface LiveChart {
  series: ChartSeries[];
  onPull: PullHandler;
}

const toMegabytes = (bytes: number) => Math.round(bytes / 1024 / 1024);

const TILES: Tile[] = [
  { text: 'status', endPoint: 'metrics', cols: 1, rows: 1, color: 'lightblue', type: 'status' },
  { text: 'uptime', endPoint: 'uptime', cols: 1, rows: 1, color: 'lightgreen', type: 'duration' },
  {
    text: 'memory',
    endPoint: 'memory',
    cols: 1,
    rows: 1,
    color: 'lightblue',
    type: 'string',
    suffix: 'Mo',
    formatter: (data) => `${toMegabytes(data.virtual[3])}Mo / ${toMegabytes(data.virtual[0])}Mo`,
  },
  {
    text: 'storage',
    endPoint: 'partitions',
    cols: 1,
    rows: 1,
    color: 'lightblue',
    type: 'string',
    formatter: (data) => `${toMegabytes(data.usage[1])}Mo / ${toMegabytes(data.usage[0])}Mo`,
  },
  {
    text: 'cpu',
    endPoint: 'cpu',
    cols: 1,
    rows: 1,
    color: 'lightblue',
    type: 'string',
    formatter: (data) => `${data.info.count} cores`,
  },
  {
    text: 'system_info',
    endPoint: 'system_info',
    cols: 1,
    rows: 1,
    color: 'lightblue',
    type: 'string',
    formatter: (data) => data.hostname,
  },
];

@Component({
  selector: 'app-home',
  imports: [MatGridListModule, IndicatorComponent, ChartComponent],
  templateUrl: './home.component.html',
  styleUrl: './home.component.scss',
})
export class HomeComponent implements OnInit {
  private readonly service = inject(DataService);
  private readonly destroyRef = inject(DestroyRef);
  private cpuHistoryPending = false;

  readonly tiles = signal<Tile[]>(TILES.map((tile) => ({ ...tile })));

  /** Set once the CPU count and history are known. */
  readonly cpu = signal<LiveChart | undefined>(undefined);

  readonly memory: LiveChart = {
    onPull: (data, chart) => {
      const x = Date.now();
      chart.series[0].addPoint([x, data.virtual[3]], true, true);
      chart.series[1].addPoint([x, data.swap[0]], true, true);
    },
    series: [
      { name: 'Used', data: generateEmptyData() },
      { name: 'Swap', data: generateEmptyData() },
    ],
  };

  readonly network: LiveChart = {
    onPull: (data, chart) => {
      const x = Date.now();
      const nic = data[Object.keys(data)[0]];
      chart.series[0].addPoint([x, humanToBytes(nic.incoming.bytes)], true, true);
      chart.series[1].addPoint([x, humanToBytes(nic.outgoing.bytes)], true, true);
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
          color: 'lightgreen',
          duration: seconds(),
        });
      },
      error: () => {
        this.patchTile(index, { value: CONTACT_LOST, color: 'crimson', duration: seconds() });
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
    this.service.get<Record<string, number | string>[]>('history/cpu/load').subscribe({
      next: (history) => this.setCpuChart(cpuCount, history),
      // No history yet (empty database): start the chart from scratch.
      error: () => this.setCpuChart(cpuCount, []),
    });
  }

  private setCpuChart(cpuCount: number, history: Record<string, number | string>[]): void {
    const series: ChartSeries[] = Array.from({ length: cpuCount }, (_, i) => {
      const data = history.map((entry) => ({
        // "YYYY-MM-DD HH:MM:SS", server local time.
        x: new Date(String(entry['date']).replace(' ', 'T')).getTime(),
        y: (entry[`cpu${i}`] as number | undefined) ?? null,
      }));
      return { name: `Cpu load ${i}`, data: data.length ? data : generateEmptyData() };
    });

    this.cpu.set({
      series,
      onPull: (data, chart) => {
        const x = Date.now();
        (data.usage as number[]).forEach((load, i) =>
          chart.series[i]?.addPoint([x, load], true, true),
        );
      },
    });
    this.cpuHistoryPending = false;
  }
}
