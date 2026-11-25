import {
  Component,
  DestroyRef,
  ElementRef,
  afterRenderEffect,
  computed,
  effect,
  inject,
  input,
  output,
  signal,
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

import { ThemeService } from '../../services/theme.service';
import { AbsoluteRange } from '../../time-range/time-range';
import { formatBytes } from '../indicator/format';
import {
  ChartPoint,
  ChartSeries,
  ChartTheme,
  ChartType,
  DEFAULT_CHART_THEME,
  applyChartTheme,
  buildChartConfig,
} from './charts';

// Only the Chart.js parts used by the dashboard are bundled.
Chart.register(LineController, LineElement, PointElement, LinearScale, Filler, Legend, Title, Tooltip);

export type ChartUnit = 'bytes' | 'bytes/s' | 'percent' | 'number';

/** Narrowest drag (px) taken as a zoom selection rather than a click. */
const MIN_SELECTION = 6;

/**
 * Time series chart. Shows `series` over `range`; dragging over it selects
 * a new range (`rangeSelected`), double-clicking asks to zoom out.
 */
@Component({
  selector: 'app-chart',
  host: {
    '[style.width]': 'width()',
    '[style.height]': 'height()',
  },
  // The canvas fallback content describes the chart to assistive technologies.
  template: `
    <div
      class="chart"
      (pointerdown)="startSelection($event)"
      (pointermove)="moveSelection($event)"
      (pointerup)="endSelection($event)"
      (pointercancel)="selection.set(undefined)"
      (dblclick)="zoomOut.emit()"
    >
      <canvas #canvas [attr.aria-label]="title()" role="img">{{ title() }}: {{ seriesNames() }}</canvas>
      @if (selectionBox(); as box) {
        <div class="selection" [style.left.px]="box.left" [style.width.px]="box.width"></div>
      }
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
      cursor: crosshair;
      touch-action: pan-y;
      user-select: none;
    }
    .selection {
      position: absolute;
      top: 0;
      bottom: 0;
      background: color-mix(in srgb, var(--mat-sys-primary) 18%, transparent);
      border-inline: 1px solid var(--mat-sys-primary);
      pointer-events: none;
    }
  `,
})
export class ChartComponent {
  private readonly destroyRef = inject(DestroyRef);
  private readonly theme = inject(ThemeService);
  private readonly canvas = viewChild.required<ElementRef<HTMLCanvasElement>>('canvas');
  private chart?: Chart<'line', ChartPoint[]>;

  readonly series = input.required<ChartSeries[]>();
  /** Time span of the x axis; defaults to the span of the data. */
  readonly range = input<AbsoluteRange>();
  readonly title = input('');
  /** Draw the title in the chart (it always names the canvas for assistive technologies). */
  readonly showTitle = input(true);
  readonly type = input<ChartType>('areaspline');
  /** Unit of the values, used on the y axis and in tooltips. */
  readonly unit = input<ChartUnit>('number');
  readonly width = input('50%');
  readonly height = input('300px');

  /** A time span selected by dragging over the chart. */
  readonly rangeSelected = output<AbsoluteRange>();
  readonly zoomOut = output<void>();

  protected readonly selection = signal<{ start: number; end: number } | undefined>(undefined);
  protected readonly selectionBox = computed(() => {
    const selection = this.selection();
    if (!selection) {
      return undefined;
    }
    const left = Math.min(selection.start, selection.end);
    return { left, width: Math.abs(selection.end - selection.start) };
  });

  protected readonly seriesNames = computed(() =>
    this.series()
      .map((serie) => serie.name)
      .join(', '),
  );

  constructor() {
    // (Re)build the chart when its look changes.
    afterRenderEffect(() => {
      const title = this.showTitle() ? this.title() : '';
      const type = this.type();
      const unit = this.unit();
      const canvas = this.canvas().nativeElement;
      untracked(() => {
        const config = buildChartConfig(this.series(), title, type, this.readTheme());
        applyUnit(config.options, unit);
        this.chart?.destroy();
        this.chart = new Chart(canvas, config);
        this.update(this.series(), this.range());
      });
    });
    // New data or range: update the existing chart in place.
    effect(() => {
      const series = this.series();
      const range = this.range();
      untracked(() => this.update(series, range));
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
    this.destroyRef.onDestroy(() => this.chart?.destroy());
  }

  protected startSelection(event: PointerEvent): void {
    if (event.button !== 0 || !this.chart) {
      return;
    }
    const x = this.offsetX(event);
    this.selection.set({ start: x, end: x });
    (event.currentTarget as HTMLElement).setPointerCapture?.(event.pointerId);
  }

  protected moveSelection(event: PointerEvent): void {
    const selection = this.selection();
    if (selection) {
      this.selection.set({ ...selection, end: this.offsetX(event) });
    }
  }

  protected endSelection(event: PointerEvent): void {
    const selection = this.selection();
    this.selection.set(undefined);
    const scale = this.chart?.scales['x'];
    if (!selection || !scale || Math.abs(this.offsetX(event) - selection.start) < MIN_SELECTION) {
      return;
    }
    const [a, b] = [selection.start, this.offsetX(event)].map((x) => scale.getValueForPixel(x) ?? NaN);
    if (Number.isFinite(a) && Number.isFinite(b)) {
      this.rangeSelected.emit({ from: Math.round(Math.min(a, b)), to: Math.round(Math.max(a, b)) });
    }
  }

  /** Pointer x within the chart area (the plot, not the axes). */
  private offsetX(event: PointerEvent): number {
    const element = event.currentTarget as HTMLElement;
    const x = event.clientX - element.getBoundingClientRect().left;
    const area = this.chart?.chartArea;
    return area ? Math.min(Math.max(x, area.left), area.right) : x;
  }

  private update(series: ChartSeries[], range: AbsoluteRange | undefined): void {
    const chart = this.chart;
    if (!chart) {
      return;
    }
    const datasets = chart.data.datasets;
    if (datasets.length !== series.length || datasets.some((set, i) => set.label !== series[i].name)) {
      // Different series (e.g. the CPU count is now known): rebuild them.
      const fresh = buildChartConfig(series, '', this.type(), this.readTheme());
      chart.data.datasets = fresh.data.datasets;
    } else {
      datasets.forEach((set, i) => (set.data = series[i].data.map((point) => ({ ...point }))));
    }
    const x = chart.options.scales?.['x'];
    if (x) {
      x.min = range?.from;
      x.max = range?.to;
    }
    chart.update('none');
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
}

type ChartOptions = ReturnType<typeof buildChartConfig>['options'];

/** Y axis ticks and tooltip values in the given unit. */
function applyUnit(options: ChartOptions, unit: ChartUnit): void {
  const y = options?.scales?.['y'];
  const tooltip = options?.plugins?.tooltip?.callbacks;
  const format =
    unit === 'percent'
      ? (value: number) => `${Math.round(value * 10) / 10} %`
      : unit === 'bytes'
        ? (value: number) => formatBytes(value)
        : unit === 'bytes/s'
          ? (value: number) => `${formatBytes(value)}/s`
          : undefined;
  if (!format || !y?.ticks || !tooltip) {
    return;
  }
  if (unit === 'percent') {
    y.max = 100;
  }
  // Loads and sizes are never negative, even when every value is zero.
  y.min = 0;
  y.ticks.callback = (value) => format(Number(value));
  tooltip.label = (item) => `${item.dataset.label}: ${format(item.parsed.y ?? 0)}`;
}
