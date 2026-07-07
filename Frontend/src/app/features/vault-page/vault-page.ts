import { Component, inject } from '@angular/core';
import { VaultService } from '../../services/vault';
import { CommonModule, DatePipe, DecimalPipe } from '@angular/common';
import { ToastrService } from 'ngx-toastr';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';

@Component({
  selector: 'app-vault-page',
  imports: [
    CommonModule,
    DecimalPipe, 
    DatePipe,
    FormsModule
  ],
  templateUrl: './vault-page.html',
  styleUrl: './vault-page.scss',
})
export class VaultPage {
  private vaultService = inject(VaultService);

  images: any[] = [];
  searchTitle = '';

  page = 1;
  size = 7;
  total = 0;
  totalPages = 0;

  // File upload modal
  isDragOver = false;
  pendingFile: File | null = null;
  imageTitle = '';
  isUploading = false;

  constructor(private toastr: ToastrService, private router: Router) {}

  ngOnInit() {
    this.loadImages();
  }

  openImage(img: any) {
    this.router.navigate(['/image', img.image_id], {
      state: { image: img }
    });
  }

  loadImages() {
    this.vaultService.getImages(this.page, this.size, this.searchTitle).subscribe({
      next: (response) => {
        this.total = response.total;
        this.totalPages = Math.ceil(this.total / this.size);
        this.images = response.items;
        this.loadImageFiles();
      }
    });
  }

  loadImageFiles() {
    this.images.forEach(img => {
      this.vaultService.getImageFile(img.image_id).subscribe(blob => {
        img.url = URL.createObjectURL(blob);
      });
    });
  }

  onSearch(title: string) {
    this.searchTitle = title;
    this.page = 1;
    this.loadImages();
  }

  get pages() {
    return Array.from(
      { length: this.totalPages },
      (_, i) => i + 1
    );
  }

  changePage(page:number){
    this.page = page;
    this.loadImages();
  }

  // drag and drop file upload handlers
  onDragOver(event: DragEvent) {
    event.preventDefault();
    event.stopPropagation();
    this.isDragOver = true;
  }

  onDragLeave() {
    this.isDragOver = false;
  }

  // file is dropped into the drop zone
  onDrop(event: DragEvent) {
    event.preventDefault();
    event.stopPropagation();
    this.isDragOver = false;

    const files = event.dataTransfer?.files;
    if (files && files.length > 0) {
      this.handleFiles(files[0]);
    }
  }

  // click file select (classic)
  onFileSelected(event: Event) {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      this.handleFiles(input.files[0]);
    }
  }

  // modal upload handlers
  private handleFiles(file: File) {
    if (file.type !== 'image/png' && file.type !== 'image/jpeg') {
      this.toastr.error('Only PNG and JPG images are allowed');
      return;
    }

    if (file.size > 10 * 1024 * 1024) {
      this.toastr.error('File is too large! Maximum accepted is 10MB.');
      return;
    }

    this.pendingFile = file;
    this.imageTitle = '';
  }

  closeUploadModal() {
    this.pendingFile = null;
    this.imageTitle = '';
  }

  isValidImageTitle(): boolean {
    return /^[A-Za-z0-9 _.-]{3,50}$/.test(this.imageTitle);
  }

  uploadImage() {
    if (!this.pendingFile || !this.imageTitle.trim()) 
      return;
    
    this.isUploading = true;

    // keep original image URL before uploading
    const originalUrl = URL.createObjectURL(this.pendingFile);

    this.vaultService.uploadImage(this.pendingFile, this.imageTitle).subscribe({
      next: (response) => {
        this.isUploading = false;
        this.closeUploadModal();
        this.router.navigate(['/encrypt'], {
          state: {
            originalImage: originalUrl,
            recoveryKey: response.recovery_key,
            imageId: response.image_id
          }
        });
      },
      error: (err) => {
        this.isUploading = false;
        this.toastr.error('Upload failed: ' + err.error?.detail || 'Unknown error');
      }
    });
  }
}
