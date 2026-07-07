import { Component } from '@angular/core';
import { Router, RouterModule } from '@angular/router';
import { FormControl, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatFormFieldModule } from '@angular/material/form-field'; 
import { MatInputModule } from '@angular/material/input'; 
import { MatButtonModule } from '@angular/material/button';
import { AuthService } from '../../services/auth';
import { ToastrService } from 'ngx-toastr';
import { hasUpperCase, hasLowerCase, hasDigit, hasSpecialCharacter, passwordsMatch } from './validators';

@Component({
  selector: 'app-sign-up-page',
  imports: [
    RouterModule,
    ReactiveFormsModule,
    MatFormFieldModule, 
    MatInputModule, 
    MatButtonModule,
  ],
  templateUrl: './sign-up-page.html',
  styleUrl: './sign-up-page.scss',
})
export class SignUpPage {
  signUpForm: FormGroup = new FormGroup({
    username: new FormControl('', [
      Validators.required,
      Validators.minLength(3),
      Validators.maxLength(30),
      Validators.pattern(/^[A-Za-z0-9]+$/)
    ]),

    firstName: new FormControl('', [
      Validators.required,
      Validators.minLength(2),
      Validators.maxLength(50),
      Validators.pattern(/^[A-Za-z-]+$/)
    ]),

    lastName: new FormControl('', [
      Validators.required,
      Validators.minLength(2),
      Validators.maxLength(50),
      Validators.pattern(/^[A-Za-z-]+$/)
    ]),

    email: new FormControl('', [
      Validators.required,
      Validators.email
    ]),

    password: new FormControl('', [
      Validators.required,
      Validators.minLength(6),
      Validators.maxLength(50),
      hasUpperCase,
      hasLowerCase,
      hasDigit,
      hasSpecialCharacter
    ]),

    confirmPassword: new FormControl('', [
      Validators.required,
      passwordsMatch
    ])
  });

  constructor(private authService: AuthService, private router: Router, private toastr: ToastrService) {
    this.signUpForm.get('password')?.valueChanges.subscribe(() => {
      this.signUpForm.get('confirmPassword')?.updateValueAndValidity();
    });
  }
  
  onSubmit() {
    if (this.signUpForm.valid) {
      const username = this.signUpForm.get('username')?.value;
      const firstName = this.signUpForm.get('firstName')?.value;
      const lastName = this.signUpForm.get('lastName')?.value;
      const email = this.signUpForm.get('email')?.value;
      const password = this.signUpForm.get('password')?.value;
      const confirmPassword = this.signUpForm.get('confirmPassword')?.value;

      this.authService.register(username, email, firstName, lastName, password)
      .subscribe({

        next: () => {
          this.router.navigate(['/sign-in']);
        },

        error: (err) => {
          this.toastr.error(
            err.error?.detail || 'Signup failed'
          );
        }
      });

    } else {
      this.toastr.warning('Please fill in all fields');
      return;
    }
  }


  getError(controlName: string): string {
    const control = this.signUpForm.get(controlName);

    if (!control || !control.touched) {
      return '';
    }

    if (control.hasError('required')) {
      return 'This field is required.';
    }

    if (control.hasError('email')) {
      return 'Invalid email.';
    }

    if (control.hasError('minlength')) {
      return `Minimum ${control.errors?.['minlength'].requiredLength} characters.`;
    }

    if (control.hasError('maxlength')) {
      return `Maximum ${control.errors?.['maxlength'].requiredLength} characters.`;
    }

    if (control.hasError('noUpperCase')) {
      return 'Password must contain an uppercase letter.';
    }

    if (control.hasError('noLowerCase')) {
      return 'Password must contain a lowercase letter.';
    }

    if (control.hasError('noDigit')) {
      return 'Password must contain a digit.';
    }

    if (control.hasError('noSpecialCharacter')) {
      return 'Password must contain a special character.';
    }

    return '';
  }

  getConfirmPasswordError() {
    const control = this.signUpForm.get('confirmPassword');

    if (!control) return null;

    if (control.hasError('required')) {
      return 'Please confirm your password.';
    }

    if (control.hasError('passwordsMismatch')) {
      return 'Passwords do not match.';
    }

    return null;
  }

}
