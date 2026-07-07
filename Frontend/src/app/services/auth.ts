import { computed, Injectable, signal } from '@angular/core';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Observable, catchError, map, of, tap } from 'rxjs';
import { Router } from '@angular/router';

@Injectable({
  providedIn: 'root',
})
export class AuthService {
  private readonly API_URL = 'http://localhost:8000';
  private loggedIn = signal(false);

  isLoggedIn = computed(() => this.loggedIn());
  
  constructor(private http: HttpClient, private router: Router) {
    this.checkSession();
  }

  public checkSession(): Observable<boolean> {
    return this.http.get(`${this.API_URL}/auth/me`, { withCredentials: true }).pipe(
      map(() => true),
      catchError(() => of(false)),
      tap(status => this.loggedIn.set(status))
    );
  }

  register(username: string, email: string, first_name: string, last_name:string, password: string) {
    return this.http.post(
      `${this.API_URL}/auth/register`,
      { username, email, first_name, last_name, password },
      { withCredentials: true }
    )
  }

  login(email: string, password: string) {
    return this.http.post(
      `${this.API_URL}/auth/login`,
      { email, password },
      { withCredentials: true }
    ).pipe(
      tap(() => this.loggedIn.set(true))
    );
  }

  logout() {
    return this.http.post(
      `${this.API_URL}/auth/logout`,
      {},
      { withCredentials: true }
    ).pipe(
      tap(() => {
        this.loggedIn.set(false);
        this.router.navigate(['/sign-in']);
      })
    );
  }
}
