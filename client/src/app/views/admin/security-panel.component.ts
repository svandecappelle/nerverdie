import { DatePipe } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed, toObservable } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { EMPTY, Observable, catchError, combineLatest, forkJoin, interval, map, startWith, switchMap } from 'rxjs';

import { ChartComponent } from '../../components/chart/chart.component';
import { ChartSeries, historyToSeries } from '../../components/chart/charts';
import { AccountStatus, LoginHistory, LoginOutcome, SecurityService, SecurityStatus } from '../../services/security.service';
import { AbsoluteRange } from '../../time-range/time-range';

/** Refresh period of the security status and of the connection chart. */
export const SECURITY_REFRESH = 10_000;
const LOAD_ERROR = 'The login security status could not be loaded.';
const HOUR = 3600_000;
const DAY = 24 * HOUR;

export const CONNECTION_RANGES = [
  { label: '24 h', ms: DAY },
  { label: '7 days', ms: 7 * DAY },
  { label: '30 days', ms: 30 * DAY },
];

/** Connection chart series: key in the history samples -> legend. */
const SERIES = { success: 'Successful', failure: 'Failed', refused: 'Refused' };

export const OUTCOME_LABELS: Record<LoginOutcome, string> = {
  success: 'Success',
  failure: 'Failed',
  locked: 'Refused: account locked',
  throttled: 'Refused: address throttled',
};

/** Connection chart series from the login history (every bucket is present, empty ones as 0). */
export function connectionSeries(history: LoginHistory): ChartSeries[] {
  const keys = Object.keys(SERIES) as (keyof typeof SERIES)[];
  // No gap between buckets: a bucket without attempt is a 0, not missing data.
  return historyToSeries(history.samples, keys, Infinity).map((data, i) => ({ name: SERIES[keys[i]], data }));
}

/** Login security of the administration screen: connections, lock policy, locked accounts. */
@Component({
  selector: 'app-security-panel',
  imports: [
    DatePipe,
    ReactiveFormsModule,
    MatButtonModule,
    MatButtonToggleModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatProgressBarModule,
    MatSlideToggleModule,
    ChartComponent,
  ],
  templateUrl: './security-panel.component.html',
  styleUrl: './security-panel.component.scss',
})
export class SecurityPanelComponent {
  private readonly security = inject(SecurityService);
  private readonly destroyRef = inject(DestroyRef);

  protected readonly ranges = CONNECTION_RANGES;
  protected readonly outcomes = OUTCOME_LABELS;

  readonly status = signal<SecurityStatus | undefined>(undefined);
  readonly series = signal<ChartSeries[]>([]);
  readonly chartRange = signal<AbsoluteRange | undefined>(undefined);
  /** Span of the connection chart, in milliseconds up to now. */
  readonly rangeMs = signal(DAY);
  readonly busy = signal(false);
  readonly message = signal('');
  readonly error = signal('');

  readonly form = inject(FormBuilder).nonNullable.group({
    locking: true,
    maxAttempts: [5, [Validators.required, Validators.min(1), Validators.pattern(/^\d+$/)]],
    untilUnlocked: false,
    lockMinutes: [15, [Validators.required, Validators.min(1), Validators.pattern(/^\d+$/)]],
  });

  readonly lockedAccounts = computed(() => this.status()?.accounts.filter((account) => account.locked).length ?? 0);

  /** Figures of the last 24 hours, and the accounts locked now. */
  readonly stats = computed(() => {
    const day = this.status()?.last_day;
    if (!day) {
      return [];
    }
    return [
      { label: 'Successful logins', value: day.success, icon: 'login', tone: 'ok', lastDay: true },
      { label: 'Failed logins', value: day.failure, icon: 'password', tone: day.failure ? 'warn' : '', lastDay: true },
      {
        label: 'Refused attempts',
        value: day.locked + day.throttled,
        icon: 'block',
        tone: day.locked + day.throttled ? 'warn' : '',
        lastDay: true,
      },
      { label: 'Locked accounts', value: this.lockedAccounts(), icon: 'lock', tone: this.lockedAccounts() ? 'ko' : '', lastDay: false },
    ];
  });

  private formReady = false;

  constructor() {
    const controls = this.form.controls;
    const updateControls = () => {
      const { locking, untilUnlocked } = this.form.getRawValue();
      for (const control of [controls.maxAttempts, controls.untilUnlocked]) {
        if (locking) {
          control.enable({ emitEvent: false });
        } else {
          control.disable({ emitEvent: false });
        }
      }
      if (locking && !untilUnlocked) {
        controls.lockMinutes.enable({ emitEvent: false });
      } else {
        controls.lockMinutes.disable({ emitEvent: false });
      }
    };
    this.form.valueChanges.pipe(takeUntilDestroyed()).subscribe(updateControls);

    combineLatest([toObservable(this.rangeMs), interval(SECURITY_REFRESH).pipe(startWith(0))])
      .pipe(
        switchMap(([span]) => {
          const to = Date.now();
          const range = { from: to - span, to };
          return forkJoin({ status: this.security.status(), history: this.security.history(range.from, range.to) }).pipe(
            catchError((error) => {
              this.fail(error, LOAD_ERROR);
              return EMPTY;
            }),
            map((result) => ({ ...result, range })),
          );
        }),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe(({ status, history, range }) => {
        this.show(status);
        this.series.set(connectionSeries(history));
        this.chartRange.set(range);
      });
  }

  save(): void {
    this.form.markAllAsTouched();
    if (this.form.invalid) {
      return;
    }
    const { locking, maxAttempts, untilUnlocked, lockMinutes } = this.form.getRawValue();
    const current = this.status()?.policy.lock_minutes ?? 15;
    const policy = {
      max_attempts: locking ? Number(maxAttempts) : null,
      lock_minutes: untilUnlocked ? 0 : locking ? Number(lockMinutes) : current,
    };
    this.run(this.security.setPolicy(policy), () =>
      this.message.set(locking ? 'Lock policy saved.' : 'Accounts are no longer locked after failed logins.'),
    );
  }

  unlock(account: AccountStatus): void {
    this.run(this.security.unlock(account.username), () =>
      this.message.set(account.locked ? `${account.username} is unlocked.` : `Failed logins of ${account.username} are reset.`),
    );
  }

  describeAccount(account: AccountStatus): string {
    if (account.locked) {
      return account.locked_until ? 'Locked until' : 'Locked until unlocked';
    }
    return account.failed_logins ? `${account.failed_logins} failed login${account.failed_logins > 1 ? 's' : ''}` : 'Active';
  }

  private run(request: Observable<SecurityStatus>, done: () => void): void {
    this.busy.set(true);
    this.message.set('');
    this.error.set('');
    request.pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (status) => {
        this.busy.set(false);
        this.show(status, true);
        done();
      },
      error: (error) => {
        this.busy.set(false);
        this.fail(error, 'The request failed.');
      },
    });
  }

  private show(status: SecurityStatus, resetForm = false): void {
    this.status.set(status);
    if (this.error() === LOAD_ERROR) {
      this.error.set('');
    }
    // Fill the form from the server once, then only after a save, so that a
    // refresh does not overwrite what is being typed.
    if (!this.formReady || resetForm) {
      this.formReady = true;
      const { limits, policy } = status;
      this.form.controls.maxAttempts.setValidators([
        Validators.required,
        Validators.min(limits.min_attempts),
        Validators.max(limits.max_attempts),
        Validators.pattern(/^\d+$/),
      ]);
      this.form.controls.lockMinutes.setValidators([
        Validators.required,
        Validators.min(1),
        Validators.max(limits.max_lock_minutes),
        Validators.pattern(/^\d+$/),
      ]);
      this.form.setValue({
        locking: policy.max_attempts !== null,
        maxAttempts: policy.max_attempts ?? this.form.controls.maxAttempts.value,
        untilUnlocked: policy.lock_minutes === 0,
        lockMinutes: policy.lock_minutes || this.form.controls.lockMinutes.value,
      });
    }
  }

  private fail(error: unknown, fallback: string): void {
    const message =
      error instanceof HttpErrorResponse && typeof error.error?.error === 'string' ? error.error.error : fallback;
    this.error.set(message);
  }
}
