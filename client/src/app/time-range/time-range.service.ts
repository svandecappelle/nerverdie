import { DestroyRef, Injectable, computed, inject, signal } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';

import {
  AbsoluteRange,
  DEFAULT_RANGE,
  DEFAULT_REFRESH,
  REFRESH_INTERVALS,
  TimeRange,
  isRelative,
  refreshMs,
  resolveRange,
  shiftRange,
  zoomOut,
} from './time-range';

const RECENT_KEY = 'neverdie.recentRanges';
const MAX_RECENT = 4;

/**
 * Time range and auto-refresh of a dashboard, kept in the URL
 * (`?from=now-6h&to=now&refresh=5s`) like Grafana, so that a view can be
 * bookmarked or shared. Provided by the dashboard component.
 */
@Injectable()
export class TimeRangeService {
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);

  readonly range = signal<TimeRange>(DEFAULT_RANGE);
  readonly refresh = signal(DEFAULT_REFRESH);
  /** Absolute ranges applied recently, newest first. */
  readonly recent = signal<TimeRange[]>(loadRecent());
  /** Bumped by every refresh (automatic or manual): the range is resolved again. */
  private readonly tick = signal(0);

  /** The range in epoch milliseconds, recomputed on each refresh for relative ranges. */
  readonly resolved = computed<AbsoluteRange>(() => {
    this.tick();
    const resolved = resolveRange(this.range(), Date.now());
    return typeof resolved === 'string'
      ? (resolveRange(DEFAULT_RANGE, Date.now()) as AbsoluteRange)
      : resolved;
  });

  /** Moving forward is pointless when the range already ends now. */
  readonly endsNow = computed(() => isRelative(this.range().to));

  constructor() {
    const params = this.route.snapshot.queryParamMap;
    const range = { from: params.get('from') ?? DEFAULT_RANGE.from, to: params.get('to') ?? DEFAULT_RANGE.to };
    if (typeof resolveRange(range, Date.now()) !== 'string') {
      this.range.set(range);
    }
    const refresh = params.get('refresh');
    if (refresh !== null && REFRESH_INTERVALS.includes(refresh)) {
      this.refresh.set(refresh);
    }

    // Auto-refresh timer, restarted when the interval changes.
    let timer: ReturnType<typeof setInterval> | undefined;
    const schedule = () => {
      clearInterval(timer);
      const ms = refreshMs(this.refresh());
      timer = ms ? setInterval(() => this.reload(), ms) : undefined;
    };
    schedule();
    this.rescheduleTimer = schedule;
    inject(DestroyRef).onDestroy(() => clearInterval(timer));
  }

  private rescheduleTimer: () => void = () => undefined;

  setRange(range: TimeRange): void {
    const clean = { from: range.from.trim(), to: range.to.trim() };
    this.range.set(clean);
    if (!isRelative(clean.from) || !isRelative(clean.to)) {
      this.remember(clean);
    }
    this.updateUrl();
    this.reload();
  }

  setRefresh(interval: string): void {
    this.refresh.set(interval);
    this.rescheduleTimer();
    this.updateUrl();
  }

  reload(): void {
    this.tick.update((value) => value + 1);
  }

  zoomOut(): void {
    this.setRange(zoomOut(this.range(), Date.now()));
  }

  shift(direction: -1 | 1): void {
    this.setRange(shiftRange(this.range(), direction, Date.now()));
  }

  private updateUrl(): void {
    const { from, to } = this.range();
    void this.router.navigate([], {
      relativeTo: this.route,
      queryParams: { from, to, refresh: this.refresh() || null },
      queryParamsHandling: 'merge',
      replaceUrl: true,
    });
  }

  private remember(range: TimeRange): void {
    const recent = [range, ...this.recent().filter((r) => r.from !== range.from || r.to !== range.to)];
    this.recent.set(recent.slice(0, MAX_RECENT));
    try {
      localStorage.setItem(RECENT_KEY, JSON.stringify(this.recent()));
    } catch {
      // Storage unavailable: the list lasts for this page only.
    }
  }
}

function loadRecent(): TimeRange[] {
  try {
    const stored = JSON.parse(localStorage.getItem(RECENT_KEY) ?? '[]');
    return Array.isArray(stored)
      ? stored.filter((r) => typeof r?.from === 'string' && typeof r?.to === 'string').slice(0, MAX_RECENT)
      : [];
  } catch {
    return [];
  }
}
