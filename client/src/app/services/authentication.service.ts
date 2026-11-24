import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Router } from '@angular/router';
import { BehaviorSubject, Observable, catchError, map, of, shareReplay, tap } from 'rxjs';

import { User } from '../models/user';

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

  /** Emits `true` on success (and navigates home), `false` on bad credentials. */
  login(username: string, password: string): Observable<boolean> {
    return this.http.post<AuthResponse>('/api/auth/login', { username, password }).pipe(
      map((data) => {
        if (!data?.user) {
          return false;
        }
        const user: User = { id: data.user.uid, username };
        localStorage.setItem('currentUser', JSON.stringify(user));
        this.loggedIn.next(true);
        void this.router.navigate(['/']);
        return true;
      }),
      catchError(() => of(false)),
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
