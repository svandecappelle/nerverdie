import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

/** Database storage status returned by `/api/admin/storage`. */
export interface StorageStatus {
  /** Size limit in MB, `null` when unlimited. */
  limit_mb: number | null;
  limit_bytes: number | null;
  /** Bytes of the database pages holding data. */
  used_bytes: number;
  /** Size on disk of the database file and its write-ahead log. */
  file_bytes: number;
  /** Free pages that compacting gives back to the file system. */
  free_bytes: number;
  samples: number;
  oldest: string | null;
  newest: string | null;
  min_limit_mb: number;
  max_limit_mb: number;
  /** Samples deleted when a new limit was applied. */
  deleted?: number;
}

/** Administration of the database size limit. */
@Injectable({ providedIn: 'root' })
export class StorageService {
  private readonly http = inject(HttpClient);
  private readonly url = '/api/admin/storage';

  status(): Observable<StorageStatus> {
    return this.http.get<StorageStatus>(this.url);
  }

  /** Sets the limit (`null`: unlimited); the server purges the oldest data at once. */
  setLimit(limitMb: number | null): Observable<StorageStatus> {
    return this.http.put<StorageStatus>(this.url, { limit_mb: limitMb });
  }

  compact(): Observable<StorageStatus> {
    return this.http.post<StorageStatus>(`${this.url}/compact`, {});
  }
}
