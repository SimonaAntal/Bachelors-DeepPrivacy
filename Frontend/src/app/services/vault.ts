import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';

@Injectable({
  providedIn: 'root',
})
export class VaultService {
  private API_URL = "http://localhost:8000";

  constructor(private http: HttpClient) {}

  getImages(page: number, size: number, title?: string) {
    let params: any = {
      page,
      size
    };

    if (title) {
      params.title = title;
    }

    return this.http.get<any>(
      `${this.API_URL}/vault/images`,
      {
        params,
        withCredentials: true
      }
    );
  }

  getImageFile(imageId: string) {
    return this.http.get(
      `${this.API_URL}/vault/images/${imageId}/file`,
      { withCredentials: true, responseType: 'blob' }
    );
  }

  uploadImage(file: File, title: string) {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('name', title);

    return this.http.post<any>(
      `${this.API_URL}/vault/images`,
      formData,
      { withCredentials: true }
    );
  }

  decryptImage(imageId: string, key: string) {
    const formData = new FormData();
    formData.append('key', key);

    return this.http.post(
      `${this.API_URL}/vault/images/${imageId}/recover`,
      formData,
      { withCredentials: true, responseType: 'blob' }
    );
  }
}
