# Neverdie client

Angular 22 single page app (standalone components, zoneless, Angular Material 3, Chart.js).
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
| `npm start`      | Dev server on http://localhost:4200, proxies `/api` to Flask on `127.0.0.1:5000`, or `NEVERDIE_API_URL` (`proxy.conf.mjs`) |
| `npm run build`  | Production build into `dist/` (no `browser/` sub-folder, served as is by Flask) |
| `npm test`       | Unit tests (Vitest, through `ng test`)                                          |
| `npm run lint`   | ESLint (angular-eslint)                                                         |
| `npm run e2e`    | End-to-end tests (Playwright) against the dev server, with `/api` mocked        |
| `npm run licenses` | Fails if a dependency is not under an accepted free licence (`scripts/check-licenses.mjs`) |

Playwright needs a browser: run `npx playwright install chromium` once, or reuse an
installed one with `PLAYWRIGHT_CHANNEL=msedge npm run e2e` (or `chrome`).

## Licensing note

Every dependency is free for any use, commercial included. Charts use Chart.js (MIT);
Highcharts, which needs a paid licence for commercial use, was removed.

`npm run licenses` (run by the CI) enforces it: packages shipped to the browser must be
under a permissive licence (MIT, Apache-2.0, BSD, ISC...); build and test tools may also use
MPL-2.0 or CC-BY-4.0. Any other licence, or none, fails the check.
