import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { AuthService } from '../services/auth';
import { filter, map, take, tap } from 'rxjs';

export const authGuard: CanActivateFn = () => {
  const authService = inject(AuthService);
  const router = inject(Router);

  return authService.checkSession().pipe(
    map(isLogged => isLogged ? true : router.createUrlTree(['/sign-in']))
  );
};