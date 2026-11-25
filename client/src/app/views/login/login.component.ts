import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressBarModule } from '@angular/material/progress-bar';

import { ThemeToggleComponent } from '../../components/theme-toggle/theme-toggle.component';
import { AuthenticationService } from '../../services/authentication.service';

@Component({
  selector: 'app-login',
  imports: [
    ReactiveFormsModule,
    MatCardModule,
    MatIconModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatProgressBarModule,
    ThemeToggleComponent,
  ],
  templateUrl: './login.component.html',
  styleUrl: './login.component.scss',
})
export class LoginComponent {
  private readonly authService = inject(AuthenticationService);

  readonly form = inject(FormBuilder).nonNullable.group({
    userName: ['', Validators.required],
    password: ['', Validators.required],
  });

  readonly loginInProgress = signal(false);
  readonly loginFailed = signal(false);
  readonly showPassword = signal(false);

  onSubmit(): void {
    this.form.markAllAsTouched();
    if (this.form.invalid) {
      return;
    }
    const { userName, password } = this.form.getRawValue();
    this.loginInProgress.set(true);
    this.loginFailed.set(false);
    this.authService.login(userName, password).subscribe((success) => {
      this.loginInProgress.set(false);
      this.loginFailed.set(!success);
    });
  }
}
