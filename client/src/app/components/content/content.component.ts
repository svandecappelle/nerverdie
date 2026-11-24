import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';

@Component({
  selector: 'app-content',
  imports: [RouterOutlet],
  template: '<router-outlet />',
  styles: `
    :host {
      display: block;
      position: absolute;
      left: 0;
      right: 0;
      top: 64px;
    }
  `,
})
export class ContentComponent {}
