import { Routes } from '@angular/router';
import { HomePage } from './features/home-page/home-page';
import { VaultPage } from './features/vault-page/vault-page';
import { SignInPage } from './features/sign-in-page/sign-in-page';
import { SignUpPage } from './features/sign-up-page/sign-up-page';
import { EncryptPage } from './features/encrypt-page/encrypt-page';
import { authGuard } from './guards/auth.guard';
import { ImagePage } from './features/image-page/image-page';

export const routes: Routes = [
    {path: '', redirectTo: 'home', pathMatch: 'full'},

    {path: 'home', component: HomePage},
    {path: 'vault', component: VaultPage, canActivate: [authGuard]},
    {path: 'sign-in', component: SignInPage},
    {path: 'sign-up', component: SignUpPage},
    {path: 'encrypt', component: EncryptPage, canActivate: [authGuard]},
    {path: 'image/:id', component: ImagePage, canActivate: [authGuard]}
];
