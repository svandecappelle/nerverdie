import { DatePipe, DecimalPipe, PercentPipe } from '@angular/common';
import { Component, computed, input } from '@angular/core';
import { MatIconModule } from '@angular/material/icon';

import { humanizeDuration } from './format';

export const CONTACT_LOST = 'Contact lost';

export type IndicatorType = 'date' | 'duration' | 'status' | 'string' | 'number';

export interface IndicatorTile {
  text: string;
  type: IndicatorType;
  /** Material icon name. */
  icon?: string;
  prefix?: string;
  suffix?: string;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  value?: any;
  /** Used share (0..1), drawn as a gauge under the value. */
  ratio?: number;
  /** Duration of the last request, in seconds. */
  duration?: number;
}

/** Dashboard stat card: icon, label, value and response time. */
@Component({
  selector: 'app-indicator',
  imports: [DatePipe, DecimalPipe, PercentPipe, MatIconModule],
  templateUrl: './indicator.component.html',
  styleUrl: './indicator.component.css',
  host: {
    '[class.ok]': 'state() === "ok"',
    '[class.ko]': 'state() === "ko"',
  },
})
export class IndicatorComponent {
  readonly tile = input.required<IndicatorTile>();

  protected readonly lost = computed(() => this.tile().value === CONTACT_LOST);
  /** pending until the first answer, then ok or ko (contact lost). */
  protected readonly state = computed(() =>
    this.lost() ? 'ko' : this.tile().value === undefined ? 'pending' : 'ok',
  );
  protected readonly humanDuration = computed(() => {
    // The server sends the uptime in milliseconds.
    const ms = Number(this.tile().value);
    return Number.isFinite(ms) ? humanizeDuration(ms / 1000) : '';
  });
}
