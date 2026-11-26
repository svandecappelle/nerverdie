import { DOCUMENT } from '@angular/common';
import { Injectable, computed, inject, signal } from '@angular/core';

export type ThemePreference = 'system' | 'light' | 'dark';

const STORAGE_KEY = 'neverdie.theme';
const PREFERENCES: ThemePreference[] = ['system', 'light', 'dark'];

/**
 * Light / dark theme. Follows the system by default; a forced choice is kept
 * in the browser and applied through `<html data-theme>` (see styles.scss).
 */
@Injectable({ providedIn: 'root' })
export class ThemeService {
  private readonly document = inject(DOCUMENT);
  private readonly media = this.document.defaultView?.matchMedia?.('(prefers-color-scheme: dark)');
  private readonly systemDark = signal(this.media?.matches ?? false);

  readonly preference = signal<ThemePreference>(this.load());
  /** Whether the dark variant is displayed. */
  readonly dark = computed(
    () => this.preference() === 'dark' || (this.preference() === 'system' && this.systemDark()),
  );

  constructor() {
    this.media?.addEventListener?.('change', (event) => this.systemDark.set(event.matches));
    this.apply(this.preference());
  }

  set(preference: ThemePreference): void {
    this.preference.set(preference);
    this.apply(preference);
    try {
      localStorage.setItem(STORAGE_KEY, preference);
    } catch {
      // Storage unavailable (private mode...): the choice lasts for this page only.
    }
  }

  private apply(preference: ThemePreference): void {
    const root = this.document.documentElement;
    if (preference === 'system') {
      delete root.dataset['theme'];
    } else {
      root.dataset['theme'] = preference;
    }
  }

  private load(): ThemePreference {
    try {
      const stored = localStorage.getItem(STORAGE_KEY) as ThemePreference | null;
      return stored && PREFERENCES.includes(stored) ? stored : 'system';
    } catch {
      return 'system';
    }
  }
}
