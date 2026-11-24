import { Component } from '@angular/core';

import { ContentComponent } from './components/content/content.component';
import { HeaderComponent } from './components/header/header.component';

@Component({
  selector: 'app-root',
  imports: [HeaderComponent, ContentComponent],
  template: `
    <app-header />
    <app-content />
  `,
})
export class App {}
