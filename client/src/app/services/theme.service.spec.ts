import { TestBed } from '@angular/core/testing';

import { ThemeService } from './theme.service';

describe('ThemeService', () => {
  const root = document.documentElement;

  beforeEach(() => {
    localStorage.clear();
    delete root.dataset['theme'];
  });

  it('follows the system by default', () => {
    const theme = TestBed.inject(ThemeService);
    expect(theme.preference()).toBe('system');
    expect(root.dataset['theme']).toBeUndefined();
  });

  it('forces a theme on <html> and remembers it', () => {
    TestBed.inject(ThemeService).set('dark');
    expect(root.dataset['theme']).toBe('dark');
    expect(localStorage.getItem('neverdie.theme')).toBe('dark');

    TestBed.resetTestingModule();
    delete root.dataset['theme'];
    const theme = TestBed.inject(ThemeService);
    expect(theme.preference()).toBe('dark');
    expect(theme.dark()).toBe(true);
    expect(root.dataset['theme']).toBe('dark');
  });

  it('ignores an unknown stored value', () => {
    localStorage.setItem('neverdie.theme', 'purple');
    expect(TestBed.inject(ThemeService).preference()).toBe('system');
  });

  it('goes back to the system preference', () => {
    const theme = TestBed.inject(ThemeService);
    theme.set('light');
    theme.set('system');
    expect(root.dataset['theme']).toBeUndefined();
  });
});
