import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Router } from '@angular/router';
import { BehaviorSubject, Observable, catchError, map, of, shareReplay, tap } from 'rxjs';

import { User } from '../models/user';

export const INVALID_CREDENTIALS = 'Invalid credentials';

/** Message shown on the login page for a refused login. */
export function loginErrorMessage(error: unknown): string {
  if (!(error instanceof HttpErrorResponse)) {
    return INVALID_CREDENTIALS;
  }
  if (error.status === 423) {
    const until = typeof error.error?.locked_until === 'string' ? new Date(error.error.locked_until.replace(' ', 'T')) : null;
    return until && !Number.isNaN(until.getTime())
      ? `This account is locked after too many failed logins. Retry after ${until.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}.`
      : 'This account is locked after too many failed logins. Ask an administrator to unlock it.';
  }
  if (error.status === 429) {
    return 'Too many failed logins from this address. Retry in a few minutes.';
  }
  return INVALID_CREDENTIALS;
}

interface AuthResponse {
  connected?: boolean;
  user?: { uid: string };
}

@Injectable({ providedIn: 'root' })
export class AuthenticationService {
  private readonly http = inject(HttpClient);
  private readonly router = inject(Router);

  /** Nobody is logged in until the server says otherwise. */
  private readonly loggedIn = new BehaviorSubject<boolean>(false);

  /** Asks the server once whether the session cookie is still valid. */
  private readonly sessionCheck$: Observable<boolean> = this.http
    .get<AuthResponse>('/api/auth')
    .pipe(
      map((data) => data?.connected === true),
      // The Flask API answers an anonymous call with a redirect to the SPA (HTML),
      // which HttpClient reports as an error: treat it as "not logged in".
      catchError(() => of(false)),
      tap((connected) => this.loggedIn.next(connected)),
      shareReplay(1),
    );

  isLoggedIn(): Observable<boolean> {
    return this.loggedIn.asObservable();
  }

  /** Resolves once the initial session check is done (used by the route guard). */
  checkSession(): Observable<boolean> {
    return this.loggedIn.value ? of(true) : this.sessionCheck$;
  }

  /** Emits `null` on success (and navigates home), else the reason of the refusal. */
  login(username: string, password: string): Observable<string | null> {
    return this.http.post<AuthResponse>('/api/auth/login', { username, password }).pipe(
      map((data) => {
        if (!data?.user) {
          return INVALID_CREDENTIALS;
        }
        const user: User = { id: data.user.uid, username };
        localStorage.setItem('currentUser', JSON.stringify(user));
        this.loggedIn.next(true);
        void this.router.navigate(['/']);
        return null;
      }),
      catchError((error) => of(loginErrorMessage(error))),
    );
  }

  logout(): void {
    this.http.post('/api/auth/logout', {}).subscribe({
      complete: () => this.clearSession(),
      error: () => this.clearSession(),
    });
  }

  private clearSession(): void {
    localStorage.removeItem('currentUser');
    this.loggedIn.next(false);
    void this.router.navigate(['/login']);
  }
}
