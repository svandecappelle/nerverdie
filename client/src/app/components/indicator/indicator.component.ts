import { DatePipe, DecimalPipe } from '@angular/common';
import { Component, computed, input } from '@angular/core';

import { humanizeDuration } from './format';

export const CONTACT_LOST = 'Contact lost';

export type IndicatorType = 'date' | 'duration' | 'status' | 'string' | 'number';

export interface IndicatorTile {
  text: string;
  type: IndicatorType;
  prefix?: string;
  suffix?: string;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  value?: any;
  /** Duration of the last request, in seconds. */
  duration?: number;
}

@Component({
  selector: 'app-indicator',
  imports: [DatePipe, DecimalPipe],
  templateUrl: './indicator.component.html',
  styleUrl: './indicator.component.css',
})
export class IndicatorComponent {
  readonly tile = input.required<IndicatorTile>();

  protected readonly lost = computed(() => this.tile().value === CONTACT_LOST);
  protected readonly humanDuration = computed(() => {
    // The server sends the uptime in milliseconds.
    const ms = Number(this.tile().value);
    return Number.isFinite(ms) ? humanizeDuration(ms / 1000) : '';
  });
}
