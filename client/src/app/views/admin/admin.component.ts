import { DatePipe, DecimalPipe, PercentPipe } from '@angular/common';
import { Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { HttpErrorResponse } from '@angular/common/http';
import { EMPTY, Observable, catchError, exhaustMap, interval, startWith } from 'rxjs';

import { formatBytes } from '../../components/indicator/format';
import { StorageService, StorageStatus } from '../../services/storage.service';

/** Refresh period of the storage status. */
export const STORAGE_REFRESH = 10_000;
const LOAD_ERROR = 'The storage status could not be loaded.';

/** Administration screen: database size, size limit and compaction. */
@Component({
  selector: 'app-admin',
  imports: [
    DatePipe,
    DecimalPipe,
    PercentPipe,
    ReactiveFormsModule,
    MatButtonModule,
    MatCardModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatProgressBarModule,
    MatSlideToggleModule,
  ],
  templateUrl: './admin.component.html',
  styleUrl: './admin.component.scss',
})
export class AdminComponent {
  private readonly storage = inject(StorageService);
  private readonly destroyRef = inject(DestroyRef);

  readonly status = signal<StorageStatus | undefined>(undefined);
  readonly busy = signal(false);
  readonly message = signal('');
  readonly error = signal('');

  readonly form = inject(FormBuilder).nonNullable.group({
    limited: false,
    limitMb: [
      { value: 100, disabled: true },
      [Validators.required, Validators.min(1), Validators.pattern(/^\d+$/)],
    ],
  });

  /** Used share of the limit (0..1), undefined when unlimited. */
  readonly usage = computed(() => {
    const status = this.status();
    return status?.limit_bytes ? Math.min(status.used_bytes / status.limit_bytes, 1) : undefined;
  });

  protected readonly formatBytes = formatBytes;
  private formReady = false;

  constructor() {
    this.form.controls.limited.valueChanges
      .pipe(takeUntilDestroyed())
      .subscribe((limited) =>
        limited ? this.form.controls.limitMb.enable() : this.form.controls.limitMb.disable(),
      );

    interval(STORAGE_REFRESH)
      .pipe(
        startWith(0),
        // Keep polling after a failed request.
        exhaustMap(() =>
          this.storage.status().pipe(
            catchError((error) => {
              this.fail(error, LOAD_ERROR);
              return EMPTY;
            }),
          ),
        ),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe((status) => this.show(status));
  }

  save(): void {
    this.form.markAllAsTouched();
    if (this.form.invalid) {
      return;
    }
    const { limited, limitMb } = this.form.getRawValue();
    this.run(this.storage.setLimit(limited ? Number(limitMb) : null), (status) => {
      const deleted = status.deleted ?? 0;
      this.message.set(
        status.limit_mb === null
          ? 'Database size is now unlimited.'
          : `Limit set to ${status.limit_mb} MB.` +
              (deleted ? ` ${deleted} old samples were deleted.` : ''),
      );
    });
  }

  compact(): void {
    this.run(this.storage.compact(), (status) =>
      this.message.set(`Database compacted: ${formatBytes(status.file_bytes)} on disk.`),
    );
  }

  private run(request: Observable<StorageStatus>, done: (status: StorageStatus) => void): void {
    this.busy.set(true);
    this.message.set('');
    this.error.set('');
    request.pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (status) => {
        this.busy.set(false);
        this.show(status, true);
        done(status);
      },
      error: (error) => {
        this.busy.set(false);
        this.fail(error, 'The request failed.');
      },
    });
  }

  private show(status: StorageStatus, resetForm = false): void {
    this.status.set(status);
    if (this.error() === LOAD_ERROR) {
      this.error.set('');
    }
    // Fill the form from the server once, then only after a save, so that a
    // refresh does not overwrite what is being typed.
    if (!this.formReady || resetForm) {
      this.formReady = true;
      this.form.controls.limitMb.setValidators([
        Validators.required,
        Validators.min(status.min_limit_mb),
        Validators.max(status.max_limit_mb),
        Validators.pattern(/^\d+$/),
      ]);
      this.form.setValue({
        limited: status.limit_mb !== null,
        limitMb: status.limit_mb ?? this.form.controls.limitMb.value,
      });
    }
  }

  private fail(error: unknown, fallback: string): void {
    // The API explains a rejected request in `{ error: "..." }`.
    const message =
      error instanceof HttpErrorResponse && typeof error.error?.error === 'string'
        ? error.error.error
        : fallback;
    this.error.set(message);
  }
}
