import { Component, inject } from '@angular/core';
import { VaultService } from '../../services/vault';
import { ToastrService } from 'ngx-toastr';
import { Router } from '@angular/router';
import { DatePipe, DecimalPipe } from '@angular/common';
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'app-image-page',
  imports: [
    DatePipe,
    DecimalPipe,
    FormsModule
  ],
  templateUrl: './image-page.html',
  styleUrl: './image-page.scss',
})
export class ImagePage {
  private vaultService = inject(VaultService);

  image: any = null;
  encryptedUrl: string = '';
  decryptedUrl: string = '';
  recoveryKey: string = '';
  isDecrypting = false;

  constructor(private router: Router, private toastr: ToastrService) {}

  ngOnInit() {
    const { image } = history.state;
    if (!image) {
      this.router.navigate(['/vault']);
      return;
    }
    this.image = image;

    this.vaultService.getImageFile(image.image_id).subscribe({
      next: (blob) => {
        this.encryptedUrl = URL.createObjectURL(blob);
      }
    });
  }

  decrypt() {
    if (!this.recoveryKey.trim()) return;
    this.isDecrypting = true;

    this.vaultService.decryptImage(this.image.image_id, this.recoveryKey).subscribe({
      next: (blob) => {
        this.decryptedUrl = URL.createObjectURL(blob);
        this.isDecrypting = false;
      },
      error: (err) => {
        this.isDecrypting = false;
        if (err.status === 422) {
          this.toastr.error('Invalid recovery key.');
        } else if (err.status === 404) {
          this.toastr.error('Image not found.');
        } else {
          this.toastr.error('Something went wrong. Please try again.');
        }
      }
    });
  }

  download() {
    const a = document.createElement('a');
    a.href = this.decryptedUrl;
    a.download = this.image.name + '.png';
    a.click();
  }
}
