import { AbstractControl, ValidationErrors, ValidatorFn } from '@angular/forms';

export const hasUpperCase: ValidatorFn = (control: AbstractControl): ValidationErrors | null => {
  return /[A-Z]/.test(control.value) ? null : { noUpperCase: true };
};

export const hasLowerCase: ValidatorFn = (control: AbstractControl): ValidationErrors | null => {
  return /[a-z]/.test(control.value) ? null : { noLowerCase: true };
};

export const hasDigit: ValidatorFn = (control: AbstractControl): ValidationErrors | null => {
  return /\d/.test(control.value) ? null : { noDigit: true };
};

export const hasSpecialCharacter: ValidatorFn = (control: AbstractControl): ValidationErrors | null => {
  return /[!@#$%^&*.?]/.test(control.value)
    ? null
    : { noSpecialCharacter: true };
};

export const passwordsMatch: ValidatorFn = (
  control: AbstractControl
): ValidationErrors | null => {

  const parent = control.parent;

  if (!parent) {
    return null;
  }

  const password = parent.get('password')?.value;

  if (control.value !== password) {
    return { passwordsMismatch: true };
  }

  return null;
};