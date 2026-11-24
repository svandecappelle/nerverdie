import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { map } from 'rxjs';

import { AuthenticationService } from '../services/authentication.service';

/** Lets the route through only once the server has confirmed the session. */
export const authGuard: CanActivateFn = () => {
  const router = inject(Router);
  return inject(AuthenticationService)
    .checkSession()
    .pipe(map((connected) => connected || router.createUrlTree(['/login'])));
};
