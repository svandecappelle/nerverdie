import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

/** Thin wrapper around the Flask monitoring API (`/api/<endpoint>`). */
@Injectable({ providedIn: 'root' })
export class DataService {
  private readonly http = inject(HttpClient);

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  get<T = any>(endpoint: string): Observable<T> {
    return this.http.get<T>(`/api/${endpoint}`);
  }
}
