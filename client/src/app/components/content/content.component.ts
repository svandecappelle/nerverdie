import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';

@Component({
  selector: 'app-content',
  imports: [RouterOutlet],
  template: '<main><router-outlet /></main>',
  styles: `
    :host {
      display: block;
    }
  `,
})
export class ContentComponent {}
