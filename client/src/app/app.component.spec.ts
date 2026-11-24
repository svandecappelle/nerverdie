import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { App } from './app.component';
import { AuthenticationService } from './services/authentication.service';

describe('App', () => {
  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideRouter([]), provideHttpClient(), provideHttpClientTesting()],
    });
  });

  it('hides the toolbar until the user is logged in', async () => {
    const fixture = TestBed.createComponent(App);
    await fixture.whenStable();
    expect(fixture.nativeElement.querySelector('mat-toolbar')).toBeNull();

    TestBed.inject(AuthenticationService).checkSession().subscribe();
    TestBed.inject(HttpTestingController).expectOne('/api/auth').flush({ connected: true });
    await fixture.whenStable();

    expect(fixture.nativeElement.querySelector('mat-toolbar')?.textContent).toContain('Neverdie');
  });
});
