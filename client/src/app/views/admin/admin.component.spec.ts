import { HttpErrorResponse } from '@angular/common/http';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of, throwError } from 'rxjs';

import { StorageService, StorageStatus } from '../../services/storage.service';
import { AdminComponent } from './admin.component';

const MB = 1024 * 1024;

function storageStatus(overrides: Partial<StorageStatus> = {}): StorageStatus {
  return {
    limit_mb: null,
    limit_bytes: null,
    used_bytes: 5 * MB,
    file_bytes: 6 * MB,
    free_bytes: MB,
    samples: 1234,
    oldest: '2026-11-24 10:00:00',
    newest: '2026-11-25 10:00:00',
    min_limit_mb: 1,
    max_limit_mb: 1048576,
    ...overrides,
  };
}

describe('AdminComponent', () => {
  let fixture: ComponentFixture<AdminComponent>;
  let service: {
    status: ReturnType<typeof vi.fn>;
    setLimit: ReturnType<typeof vi.fn>;
    compact: ReturnType<typeof vi.fn>;
  };

  async function create(status: StorageStatus): Promise<void> {
    service.status.mockReturnValue(of(status));
    fixture = TestBed.createComponent(AdminComponent);
    await fixture.whenStable();
  }

  beforeEach(() => {
    service = { status: vi.fn(), setLimit: vi.fn(), compact: vi.fn() };
    TestBed.configureTestingModule({ providers: [{ provide: StorageService, useValue: service }] });
  });

  const el = () => fixture.nativeElement as HTMLElement;
  const component = () => fixture.componentInstance;

  it('shows the current size, without a gauge when unlimited', async () => {
    await create(storageStatus());

    expect(el().textContent).toContain('5 MB used, no size limit');
    expect(el().textContent).toContain('6 MB');
    expect(el().textContent).toContain('1,234');
    expect(el().querySelector('mat-progress-bar')).toBeNull();
    expect(component().form.getRawValue().limited).toBe(false);
    expect(component().form.controls.limitMb.disabled).toBe(true);
  });

  it('shows the share of the limit in use and fills the form', async () => {
    await create(storageStatus({ limit_mb: 10, limit_bytes: 10 * MB, used_bytes: 9.5 * MB }));

    expect(el().textContent).toContain('used of 10 MB (95%)');
    expect(el().querySelector('mat-progress-bar')?.getAttribute('aria-valuenow')).toBe('95');
    expect(component().form.getRawValue()).toEqual({ limited: true, limitMb: 10 });
    expect(component().form.controls.limitMb.enabled).toBe(true);
  });

  it('saves a new limit and reports the deleted samples', async () => {
    await create(storageStatus());
    service.setLimit.mockReturnValue(
      of(storageStatus({ limit_mb: 2, limit_bytes: 2 * MB, used_bytes: MB, deleted: 42 })),
    );

    component().form.setValue({ limited: true, limitMb: 2 });
    component().save();
    await fixture.whenStable();

    expect(service.setLimit).toHaveBeenCalledWith(2);
    expect(el().querySelector('[role=status]')?.textContent).toContain(
      'Limit set to 2 MB. 42 old samples were deleted.',
    );
    expect(el().textContent).toContain('used of 2 MB (50%)');
  });

  it('removes the limit when the toggle is off', async () => {
    await create(storageStatus({ limit_mb: 10, limit_bytes: 10 * MB }));
    service.setLimit.mockReturnValue(of(storageStatus()));

    component().form.controls.limited.setValue(false);
    component().save();
    await fixture.whenStable();

    expect(service.setLimit).toHaveBeenCalledWith(null);
    expect(el().textContent).toContain('Database size is now unlimited.');
  });

  it('does not send an invalid limit', async () => {
    await create(storageStatus());

    for (const limitMb of [0, 1.5, 2_000_000]) {
      component().form.setValue({ limited: true, limitMb });
      component().save();
    }
    await fixture.whenStable();

    expect(service.setLimit).not.toHaveBeenCalled();
  });

  it('shows the error returned by the API', async () => {
    await create(storageStatus());
    service.setLimit.mockReturnValue(
      throwError(
        () => new HttpErrorResponse({ status: 400, error: { error: 'limit must be between 1 and 1048576 MB' } }),
      ),
    );

    component().form.setValue({ limited: true, limitMb: 5 });
    component().save();
    await fixture.whenStable();

    expect(el().querySelector('[role=alert]')?.textContent).toContain('limit must be between');
  });

  it('compacts the database', async () => {
    await create(storageStatus());
    service.compact.mockReturnValue(of(storageStatus({ file_bytes: 5 * MB, free_bytes: 0 })));

    el().querySelector<HTMLButtonElement>('button.compact')!.click();
    await fixture.whenStable();

    expect(service.compact).toHaveBeenCalled();
    expect(el().textContent).toContain('Database compacted: 5 MB on disk.');
  });
});
