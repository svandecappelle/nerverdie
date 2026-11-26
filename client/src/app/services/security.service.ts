import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

/** Account lock policy: `max_attempts` null never locks, `lock_minutes` 0 locks until unlocked. */
export interface LockPolicy {
  max_attempts: number | null;
  lock_minutes: number;
}

export interface AccountStatus {
  username: string;
  /** Failed logins since the last successful one. */
  failed_logins: number;
  locked: boolean;
  /** End of the lock; `null` while locked means until an administrator unlocks it. */
  locked_until: string | null;
}

export type LoginOutcome = 'success' | 'failure' | 'locked' | 'throttled';

export interface LoginEvent {
  time: string;
  username: string;
  address: string;
  outcome: LoginOutcome;
}

/** `/api/admin/security` response. */
export interface SecurityStatus {
  policy: LockPolicy;
  limits: { min_attempts: number; max_attempts: number; max_lock_minutes: number };
  /** Per address throttle of the login route (fixed). */
  throttle: { max_failures: number; window_seconds: number };
  accounts: AccountStatus[];
  /** Login attempts of the last 24 hours by outcome. */
  last_day: Record<LoginOutcome, number>;
  /** Last login attempts, newest first. */
  recent: LoginEvent[];
}

/** `/api/admin/security/history` response: attempts counted by bucket of `step` seconds. */
export interface LoginHistory {
  step: number;
  samples: { date: string; success: number; failure: number; refused: number }[];
}

/** Administration of the login security: lock policy, locked accounts, login journal. */
@Injectable({ providedIn: 'root' })
export class SecurityService {
  private readonly http = inject(HttpClient);
  private readonly url = '/api/admin/security';

  status(): Observable<SecurityStatus> {
    return this.http.get<SecurityStatus>(this.url);
  }

  setPolicy(policy: LockPolicy): Observable<SecurityStatus> {
    return this.http.put<SecurityStatus>(this.url, policy);
  }

  unlock(username: string): Observable<SecurityStatus> {
    return this.http.post<SecurityStatus>(`${this.url}/unlock`, { username });
  }

  /** Login attempts between two times in epoch milliseconds. */
  history(from: number, to: number): Observable<LoginHistory> {
    return this.http.get<LoginHistory>(`${this.url}/history?from=${from}&to=${to}`);
  }
}
