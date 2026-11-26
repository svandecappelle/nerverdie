import { CdkConnectedOverlay, CdkOverlayOrigin, ConnectedPosition } from '@angular/cdk/overlay';
import { Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatMenuModule } from '@angular/material/menu';
import { MatTooltipModule } from '@angular/material/tooltip';

import { QUICK_RANGES, REFRESH_INTERVALS, TimeRange, describeRange, resolveRange } from './time-range';
import { TimeRangeService } from './time-range.service';

/**
 * Grafana-like time controls: shift back / forward, range picker (quick
 * ranges and absolute range), zoom out, refresh and auto-refresh interval.
 */
@Component({
  selector: 'app-time-range-picker',
  imports: [
    CdkConnectedOverlay,
    CdkOverlayOrigin,
    FormsModule,
    MatButtonModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatMenuModule,
    MatTooltipModule,
  ],
  templateUrl: './time-range-picker.component.html',
  styleUrl: './time-range-picker.component.scss',
})
export class TimeRangePickerComponent {
  protected readonly time = inject(TimeRangeService);

  protected readonly open = signal(false);
  protected readonly from = signal('');
  protected readonly to = signal('');
  protected readonly error = signal('');
  protected readonly search = signal('');

  protected readonly label = computed(() => describeRange(this.time.range()));
  protected readonly quickRanges = computed(() => {
    const term = this.search().trim().toLowerCase();
    return QUICK_RANGES.map((range) => ({ range, label: describeRange(range) })).filter(
      (quick) => !term || quick.label.toLowerCase().includes(term) || quick.range.from.includes(term),
    );
  });
  protected readonly refreshIntervals = REFRESH_INTERVALS;
  protected readonly describe = describeRange;

  protected readonly positions: ConnectedPosition[] = [
    { originX: 'end', originY: 'bottom', overlayX: 'end', overlayY: 'top', offsetY: 8 },
    { originX: 'start', originY: 'bottom', overlayX: 'start', overlayY: 'top', offsetY: 8 },
  ];

  toggle(): void {
    if (this.open()) {
      this.open.set(false);
      return;
    }
    const { from, to } = this.time.range();
    this.from.set(from);
    this.to.set(to);
    this.error.set('');
    this.search.set('');
    this.open.set(true);
  }

  isCurrent(range: TimeRange): boolean {
    const current = this.time.range();
    return current.from === range.from && current.to === range.to;
  }

  choose(range: TimeRange): void {
    this.time.setRange(range);
    this.open.set(false);
  }

  apply(): void {
    const range = { from: this.from(), to: this.to() };
    const resolved = resolveRange(range, Date.now());
    if (typeof resolved === 'string') {
      this.error.set(resolved);
      return;
    }
    this.choose(range);
  }
}
