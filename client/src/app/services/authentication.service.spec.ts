import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { Router, provideRouter } from '@angular/router';
import { firstValueFrom } from 'rxjs';

import { AuthenticationService } from './authentication.service';

describe('AuthenticationService', () => {
  let service: AuthenticationService;
  let http: HttpTestingController;
  let router: Router;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([])],
    });
    service = TestBed.inject(AuthenticationService);
    http = TestBed.inject(HttpTestingController);
    router = TestBed.inject(Router);
    vi.spyOn(router, 'navigate').mockResolvedValue(true);
    localStorage.clear();
  });

  afterEach(() => http.verify());

  it('starts logged out', async () => {
    expect(await firstValueFrom(service.isLoggedIn())).toBe(false);
  });

  it('is logged in when the server confirms the session', async () => {
    const result = firstValueFrom(service.checkSession());
    http.expectOne('/api/auth').flush({ connected: true, user: { uid: 'uid' } });

    expect(await result).toBe(true);
    expect(await firstValueFrom(service.isLoggedIn())).toBe(true);
  });

  it('stays logged out when the session check fails', async () => {
    const result = firstValueFrom(service.checkSession());
    // Anonymous calls are redirected to the SPA, so HttpClient cannot parse JSON.
    http.expectOne('/api/auth').flush('<html></html>', { status: 200, statusText: 'OK' });

    expect(await result).toBe(false);
    expect(await firstValueFrom(service.isLoggedIn())).toBe(false);
  });

  it('explains a locked account', async () => {
    const until = firstValueFrom(service.login('admin', 'nope'));
    http
      .expectOne('/api/auth/login')
      .flush({ error: 'locked', locked_until: '2026-11-25 10:15:00' }, { status: 423, statusText: 'Locked' });
    expect(await until).toMatch(/^This account is locked after too many failed logins\. Retry after .*10.15/);

    const forever = firstValueFrom(service.login('admin', 'nope'));
    http.expectOne('/api/auth/login').flush({ error: 'locked', locked_until: null }, { status: 423, statusText: 'Locked' });
    expect(await forever).toContain('Ask an administrator to unlock it');
  });

  it('explains a throttled address', async () => {
    const result = firstValueFrom(service.login('admin', 'nope'));
    http.expectOne('/api/auth/login').flush({ error: 'throttled' }, { status: 429, statusText: 'Too Many Requests' });
    expect(await result).toBe('Too many failed logins from this address. Retry in a few minutes.');
  });

  it('logs in and navigates home', async () => {
    const result = firstValueFrom(service.login('admin', 'password'));
    const req = http.expectOne('/api/auth/login');
    expect(req.request.body).toEqual({ username: 'admin', password: 'password' });
    req.flush({ connected: true, user: { uid: 'uid' } });

    expect(await result).toBeNull();
    expect(await firstValueFrom(service.isLoggedIn())).toBe(true);
    expect(router.navigate).toHaveBeenCalledWith(['/']);
    expect(JSON.parse(localStorage.getItem('currentUser') ?? '{}')).toEqual({
      id: 'uid',
      username: 'admin',
    });
  });

  it('reports bad credentials', async () => {
    const result = firstValueFrom(service.login('admin', 'nope'));
    http
      .expectOne('/api/auth/login')
      .flush('<p>Invalid credentials</p>', { status: 400, statusText: 'Bad Request' });

    expect(await result).toBe('Invalid credentials');
    expect(await firstValueFrom(service.isLoggedIn())).toBe(false);
  });

  it('logs out and goes back to the login page', async () => {
    service.logout();
    http.expectOne('/api/auth/logout').flush({ message: 'ok' });

    expect(await firstValueFrom(service.isLoggedIn())).toBe(false);
    expect(router.navigate).toHaveBeenCalledWith(['/login']);
  });
});
