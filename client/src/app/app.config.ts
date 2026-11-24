import { provideHttpClient } from '@angular/common/http';
import {
  ApplicationConfig,
  provideBrowserGlobalErrorListeners,
  provideZonelessChangeDetection,
} from '@angular/core';
import { provideRouter } from '@angular/router';
import { provideHighcharts } from 'highcharts-angular';

import { routes } from './app.routes';

export const appConfig: ApplicationConfig = {
  providers: [
    provideBrowserGlobalErrorListeners(),
    provideZonelessChangeDetection(),
    provideRouter(routes),
    provideHttpClient(),
    provideHighcharts({
      instance: () => import('highcharts/esm/highcharts').then((m) => m.default),
      modules: () => [import('highcharts/esm/modules/accessibility')],
      options: {
        // Display timestamps in the browser's time zone (Highcharts defaults to UTC).
        time: { timezone: Intl.DateTimeFormat().resolvedOptions().timeZone },
        credits: { enabled: false },
      },
    }),
  ],
};
