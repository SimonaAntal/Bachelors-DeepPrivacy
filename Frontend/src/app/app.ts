import { Component, inject } from '@angular/core';
import { Router, RouterModule } from '@angular/router';
import { AuthService } from './services/auth';

@Component({
  selector: 'app-root',
  imports: [
    RouterModule
  ],
  templateUrl: './app.html',
  styleUrl: './app.scss'
})
export class App {
  isLightMode: boolean = false; 
  protected authService = inject(AuthService);

  constructor(private router: Router) {
  }

  ngOnInit() {
    // the device has Light Mode in settings
    const prefersLight = window.matchMedia('(prefers-color-scheme: light)').matches;
    this.setTheme(prefersLight);

    // listen for changes in the device's color scheme preference
    window.matchMedia('(prefers-color-scheme: light)').addEventListener('change', (e) => {
      this.setTheme(e.matches);
    });
  }

  setTheme(light: boolean) {
    this.isLightMode = light;

    if (light) {
      document.documentElement.classList.add('light-theme');
    } else {
      document.documentElement.classList.remove('light-theme');
    }
  }

  logout() {
    this.authService.logout().subscribe();
  }
}
