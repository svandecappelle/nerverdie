import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { of } from 'rxjs';

import { AuthenticationService } from '../../services/authentication.service';
import { LoginComponent } from './login.component';

describe('LoginComponent', () => {
  let fixture: ComponentFixture<LoginComponent>;
  let login: ReturnType<typeof vi.fn>;

  beforeEach(async () => {
    login = vi.fn();
    TestBed.configureTestingModule({
      providers: [provideRouter([]), { provide: AuthenticationService, useValue: { login } }],
    });
    fixture = TestBed.createComponent(LoginComponent);
    await fixture.whenStable();
  });

  const el = () => fixture.nativeElement as HTMLElement;

  it('does not call the API when the form is empty', async () => {
    el().querySelector<HTMLButtonElement>('button[type=submit]')!.click();
    await fixture.whenStable();

    expect(login).not.toHaveBeenCalled();
    expect(el().textContent).toContain('Please inform your user name');
  });

  it('shows an error on bad credentials', async () => {
    login.mockReturnValue(of('Invalid credentials'));
    fixture.componentInstance.form.setValue({ userName: 'admin', password: 'nope' });
    fixture.componentInstance.onSubmit();
    await fixture.whenStable();

    expect(login).toHaveBeenCalledWith('admin', 'nope');
    expect(el().textContent).toContain('Invalid credentials');
  });
});
