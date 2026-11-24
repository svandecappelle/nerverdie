import { TestBed } from '@angular/core/testing';
import {
  ActivatedRouteSnapshot,
  Router,
  RouterStateSnapshot,
  UrlTree,
  provideRouter,
} from '@angular/router';
import { Observable, firstValueFrom, of } from 'rxjs';

import { AuthenticationService } from '../services/authentication.service';
import { authGuard } from './auth.guard';

describe('authGuard', () => {
  function runGuard(connected: boolean) {
    TestBed.configureTestingModule({
      providers: [
        provideRouter([]),
        { provide: AuthenticationService, useValue: { checkSession: () => of(connected) } },
      ],
    });
    const result = TestBed.runInInjectionContext(() =>
      authGuard({} as ActivatedRouteSnapshot, {} as RouterStateSnapshot),
    ) as Observable<boolean | UrlTree>;
    return firstValueFrom(result);
  }

  it('lets a logged in user through', async () => {
    expect(await runGuard(true)).toBe(true);
  });

  it('redirects an anonymous user to /login', async () => {
    const result = await runGuard(false);
    const router = TestBed.inject(Router);
    expect(router.serializeUrl(result as UrlTree)).toBe('/login');
  });
});
