# Neverdie client

Angular 22 single page app (standalone components, zoneless, Angular Material 3, Highcharts).
It talks to the Flask API under `/api/*`; in production Flask serves the build from `client/dist`
(`server/web/ui/static.py`).

## Requirements

Node.js `^22.22.3 || ^24.15.0 || >=26` (required by Angular CLI 22).

```bash
npm ci
```

## Commands

| Command          | What it does                                                                    |
| ---------------- | ------------------------------------------------------------------------------- |
| `npm start`      | Dev server on http://localhost:4200, proxies `/api` to Flask on `127.0.0.1:5000` (`proxy.conf.json`) |
| `npm run build`  | Production build into `dist/` (no `browser/` sub-folder, served as is by Flask) |
| `npm test`       | Unit tests (Vitest, through `ng test`)                                          |
| `npm run lint`   | ESLint (angular-eslint)                                                         |
| `npm run e2e`    | End-to-end tests (Playwright) against the dev server, with `/api` mocked        |

Playwright needs a browser: run `npx playwright install chromium` once, or reuse an
installed one with `PLAYWRIGHT_CHANNEL=msedge npm run e2e` (or `chrome`).

## Licensing note

Highcharts is **not free for commercial use**: it is free only for personal, school and
non-profit projects. Any commercial use needs a Highcharts licence
(https://shop.highcharts.com/). `highcharts-angular` itself is MIT.
