import { HttpErrorResponse } from '@angular/common/http';
import { Component, input } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of, throwError } from 'rxjs';

import { ChartComponent } from '../../components/chart/chart.component';
import { ChartSeries } from '../../components/chart/charts';
import { LoginHistory, SecurityService, SecurityStatus } from '../../services/security.service';
import { SecurityPanelComponent, connectionSeries } from './security-panel.component';

/** Chart.js needs a real canvas, which jsdom lacks. */
@Component({ selector: 'app-chart', template: '' })
class ChartStubComponent {
  readonly series = input<ChartSeries[]>([]);
  readonly range = input<unknown>();
  readonly title = input('');
  readonly showTitle = input(true);
  readonly type = input('');
  readonly unit = input('');
  readonly width = input('');
  readonly height = input('');
}

function securityStatus(overrides: Partial<SecurityStatus> = {}): SecurityStatus {
  return {
    policy: { max_attempts: 5, lock_minutes: 15 },
    limits: { min_attempts: 1, max_attempts: 100, max_lock_minutes: 10080 },
    throttle: { max_failures: 5, window_seconds: 300 },
    accounts: [
      { username: 'admin', failed_logins: 0, locked: false, locked_until: null },
      { username: 'bob', failed_logins: 2, locked: false, locked_until: null },
      { username: 'eve', failed_logins: 5, locked: true, locked_until: null },
    ],
    last_day: { success: 12, failure: 3, locked: 1, throttled: 1 },
    recent: [
      { time: '2026-11-25 10:00:00', username: 'eve', address: '10.0.0.9', outcome: 'locked' },
      { time: '2026-11-25 09:59:00', username: 'admin', address: '127.0.0.1', outcome: 'success' },
    ],
    ...overrides,
  };
}

const HISTORY: LoginHistory = {
  step: 1800,
  samples: [
    { date: '2026-11-25 09:00:00', success: 1, failure: 0, refused: 0 },
    { date: '2026-11-25 09:30:00', success: 0, failure: 2, refused: 1 },
  ],
};

describe('connectionSeries', () => {
  it('makes one series per outcome, zeros included', () => {
    const series = connectionSeries(HISTORY);
    expect(series.map((serie) => serie.name)).toEqual(['Successful', 'Failed', 'Refused']);
    expect(series[1].data.map((point) => point.y)).toEqual([0, 2]);
  });
});

describe('SecurityPanelComponent', () => {
  let fixture: ComponentFixture<SecurityPanelComponent>;
  let service: {
    status: ReturnType<typeof vi.fn>;
    history: ReturnType<typeof vi.fn>;
    setPolicy: ReturnType<typeof vi.fn>;
    unlock: ReturnType<typeof vi.fn>;
  };

  async function create(status = securityStatus()): Promise<void> {
    service.status.mockReturnValue(of(status));
    fixture = TestBed.createComponent(SecurityPanelComponent);
    await fixture.whenStable();
  }

  beforeEach(() => {
    service = {
      status: vi.fn(),
      history: vi.fn().mockReturnValue(of(HISTORY)),
      setPolicy: vi.fn(),
      unlock: vi.fn(),
    };
    TestBed.configureTestingModule({ providers: [{ provide: SecurityService, useValue: service }] });
    TestBed.overrideComponent(SecurityPanelComponent, {
      remove: { imports: [ChartComponent] },
      add: { imports: [ChartStubComponent] },
    });
  });

  const el = () => fixture.nativeElement as HTMLElement;
  const component = () => fixture.componentInstance;
  const text = () => el().textContent?.replace(/\s+/g, ' ') ?? '';

  it('shows the figures of the last day, the attempts and the accounts', async () => {
    await create();

    const stats = [...el().querySelectorAll('.stat')].map(
      (stat) => `${stat.querySelector('.value')?.textContent} ${stat.querySelector('.label')?.textContent?.trim()}`,
    );
    expect(stats).toEqual([
      '12 Successful logins (24 h)',
      '3 Failed logins (24 h)',
      '2 Refused attempts (24 h)',
      '1 Locked accounts',
    ]);
    expect(el().querySelectorAll('.events tbody tr')).toHaveLength(2);
    expect(text()).toContain('Refused: account locked');
    expect(text()).toContain('10.0.0.9');
    expect(text()).toContain('Locked until unlocked');
    expect(text()).toContain('2 failed logins');
    expect(text()).toContain('an address is refused for 5 minutes after 5 failed logins');
    expect(component().series()).toHaveLength(3);
  });

  it('asks the history of the chosen range', async () => {
    await create();
    const [from, to] = service.history.mock.calls[0];
    expect(to - from).toBe(24 * 3600_000);

    component().rangeMs.set(7 * 24 * 3600_000);
    await fixture.whenStable();
    const [from7, to7] = service.history.mock.calls.at(-1)!;
    expect(to7 - from7).toBe(7 * 24 * 3600_000);
  });

  it('fills the policy form and saves a new policy', async () => {
    await create();
    expect(component().form.getRawValue()).toEqual({
      locking: true,
      maxAttempts: 5,
      untilUnlocked: false,
      lockMinutes: 15,
    });

    service.setPolicy.mockReturnValue(of(securityStatus({ policy: { max_attempts: 3, lock_minutes: 0 } })));
    component().form.patchValue({ maxAttempts: 3, untilUnlocked: true });
    expect(component().form.controls.lockMinutes.disabled).toBe(true);
    component().save();
    await fixture.whenStable();

    expect(service.setPolicy).toHaveBeenCalledWith({ max_attempts: 3, lock_minutes: 0 });
    expect(el().querySelector('[role=status]')?.textContent).toContain('Lock policy saved.');
    expect(component().form.getRawValue().untilUnlocked).toBe(true);
  });

  it('turns the lock off', async () => {
    await create();
    service.setPolicy.mockReturnValue(of(securityStatus({ policy: { max_attempts: null, lock_minutes: 15 } })));
    component().form.patchValue({ locking: false });
    expect(component().form.controls.maxAttempts.disabled).toBe(true);
    component().save();
    expect(service.setPolicy).toHaveBeenCalledWith({ max_attempts: null, lock_minutes: 15 });
  });

  it('refuses an invalid policy', async () => {
    await create();
    component().form.patchValue({ maxAttempts: 0 });
    component().save();
    component().form.patchValue({ maxAttempts: 101 });
    component().save();
    expect(service.setPolicy).not.toHaveBeenCalled();
  });

  it('unlocks an account', async () => {
    await create();
    service.unlock.mockReturnValue(
      of(securityStatus({ accounts: [{ username: 'eve', failed_logins: 0, locked: false, locked_until: null }] })),
    );
    el().querySelector<HTMLButtonElement>('button[aria-label="Unlock eve"]')!.click();
    await fixture.whenStable();

    expect(service.unlock).toHaveBeenCalledWith('eve');
    expect(el().querySelector('[role=status]')?.textContent).toContain('eve is unlocked.');
    expect(el().querySelector('button[aria-label="Unlock eve"]')).toBeNull();
    expect(component().lockedAccounts()).toBe(0);
  });

  it('shows the error of a failed load', async () => {
    service.status.mockReturnValue(throwError(() => new HttpErrorResponse({ status: 500 })));
    fixture = TestBed.createComponent(SecurityPanelComponent);
    await fixture.whenStable();
    expect(el().querySelector('[role=alert]')?.textContent).toContain('could not be loaded');
  });
});
