import { Injectable, inject } from '@angular/core';
import { NavigationStart, Router } from '@angular/router';
import { Observable, Subject } from 'rxjs';

export interface Alert {
  type: 'success' | 'error';
  text: string;
}

@Injectable({ providedIn: 'root' })
export class AlertService {
  private readonly subject = new Subject<Alert | undefined>();
  private keepAfterNavigationChange = false;

  constructor() {
    // Clear the alert message on route change.
    inject(Router).events.subscribe((event) => {
      if (event instanceof NavigationStart) {
        if (this.keepAfterNavigationChange) {
          // Only keep for a single location change.
          this.keepAfterNavigationChange = false;
        } else {
          this.subject.next(undefined);
        }
      }
    });
  }

  success(message: string, keepAfterNavigationChange = false): void {
    this.keepAfterNavigationChange = keepAfterNavigationChange;
    this.subject.next({ type: 'success', text: message });
  }

  error(message: string, keepAfterNavigationChange = false): void {
    this.keepAfterNavigationChange = keepAfterNavigationChange;
    this.subject.next({ type: 'error', text: message });
  }

  getMessage(): Observable<Alert | undefined> {
    return this.subject.asObservable();
  }
}
