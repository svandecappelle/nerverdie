import { Component, inject } from '@angular/core';

import { ContentComponent } from './components/content/content.component';
import { HeaderComponent } from './components/header/header.component';
import { ThemeService } from './services/theme.service';

@Component({
  selector: 'app-root',
  imports: [HeaderComponent, ContentComponent],
  template: `
    <app-header />
    <app-content />
  `,
})
export class App {
  constructor() {
    // Apply the stored theme as soon as the application starts.
    inject(ThemeService);
  }
}
