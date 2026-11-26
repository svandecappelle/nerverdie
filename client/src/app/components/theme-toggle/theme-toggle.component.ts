import { Component, computed, inject } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatMenuModule } from '@angular/material/menu';
import { MatTooltipModule } from '@angular/material/tooltip';

import { ThemePreference, ThemeService } from '../../services/theme.service';

const OPTIONS: { value: ThemePreference; label: string; icon: string }[] = [
  { value: 'system', label: 'System', icon: 'brightness_auto' },
  { value: 'light', label: 'Light', icon: 'light_mode' },
  { value: 'dark', label: 'Dark', icon: 'dark_mode' },
];

/** Button opening the System / Light / Dark theme menu. */
@Component({
  selector: 'app-theme-toggle',
  imports: [MatButtonModule, MatIconModule, MatMenuModule, MatTooltipModule],
  template: `
    <button mat-icon-button [matMenuTriggerFor]="menu" aria-label="Theme" matTooltip="Theme">
      <mat-icon>{{ current().icon }}</mat-icon>
    </button>
    <mat-menu #menu="matMenu" xPosition="before">
      @for (option of options; track option.value) {
        <button
          mat-menu-item
          role="menuitemradio"
          [attr.aria-checked]="option.value === theme.preference()"
          (click)="theme.set(option.value)"
        >
          <mat-icon>{{ option.icon }}</mat-icon>
          <span>{{ option.label }}</span>
          @if (option.value === theme.preference()) {
            <mat-icon class="check" aria-hidden="true">check</mat-icon>
          }
        </button>
      }
    </mat-menu>
  `,
  styles: `
    .check {
      margin: 0 0 0 16px;
      color: var(--mat-sys-primary);
    }
  `,
})
export class ThemeToggleComponent {
  protected readonly theme = inject(ThemeService);
  protected readonly options = OPTIONS;
  protected readonly current = computed(
    () => OPTIONS.find((option) => option.value === this.theme.preference()) ?? OPTIONS[0],
  );
}
