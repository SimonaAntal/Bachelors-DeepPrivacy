import { Component, ElementRef, inject, ViewChild } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { ToastrService } from 'ngx-toastr';
import { VaultService } from '../../services/vault';

@Component({
  selector: 'app-encrypt-page',
  imports: [
    FormsModule
  ],
  templateUrl: './encrypt-page.html',
  styleUrl: './encrypt-page.scss',
})
export class EncryptPage {
  private vaultService = inject(VaultService);

  sliderValue = 50;
  originalImage: string = '';
  encryptedImage: string = '';
  recoveryKey: string = '';
  keyCopied = false;

  constructor(private toastr: ToastrService, private router: Router) {}
  
  ngOnInit() {
    const { originalImage, recoveryKey, imageId } = history.state;

    if (!originalImage) {
      this.router.navigate(['/vault']);
      return;
    }

    this.originalImage = originalImage;
    this.recoveryKey = recoveryKey;

    // fetch the encrypted image file
    this.vaultService.getImageFile(imageId).subscribe({
      next: (blob) => {
        this.encryptedImage = URL.createObjectURL(blob);
      }
    });
  }

  copyKey() {
    navigator.clipboard.writeText(this.recoveryKey).then(() => {
      this.keyCopied = true;
      setTimeout(() => this.keyCopied = false, 2000);
    });
  }

  goToVault() {
    this.router.navigate(['/vault']);
  }
}
