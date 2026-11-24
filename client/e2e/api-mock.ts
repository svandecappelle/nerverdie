import { Page } from '@playwright/test';

const GB = 1024 ** 3;

/** Payloads shaped like the Flask API responses (server/web/api). */
export const API_FIXTURES: Record<string, unknown> = {
  metrics: ['cpu', 'memory', 'partitions', 'network'],
  uptime: 3 * 86400 * 1000,
  // psutil.virtual_memory(): total, available, percent, used, free
  memory: { virtual: [8 * GB, 4 * GB, 50, 4 * GB, 4 * GB], swap: [2 * GB, 0, 0, 2 * GB, 0, 0] },
  // psutil.disk_usage('/'): total, used, free, percent
  partitions: { usage: [100 * GB, 25 * GB, 75 * GB, 25] },
  cpu: { info: { count: 2 }, usage: [12.5, 40] },
  system_info: { hostname: 'test-server' },
  network: { eth0: { incoming: { bytes: '1.50M' }, outgoing: { bytes: '512.00K' } } },
  'history/cpu/load': [
    { date: '2026-11-24 10:00:00', cpu0: 10, cpu1: 20 },
    { date: '2026-11-24 10:00:03', cpu0: 15, cpu1: 25 },
  ],
};

/** Content-Security-Policy sent by the Flask server in production. */
export const PRODUCTION_CSP = [
  "default-src 'self'",
  "script-src 'self'",
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data:",
  "font-src 'self' data:",
  "connect-src 'self'",
  "object-src 'none'",
  "base-uri 'self'",
  "form-action 'self'",
  "frame-ancestors 'none'",
].join('; ');

/**
 * Serves every page with the production CSP and records violations in
 * `window.__cspViolations` (read it back with `cspViolations(page)`).
 */
export async function enforceCsp(page: Page): Promise<void> {
  await page.addInitScript(() => {
    const violations: string[] = [];
    (window as unknown as { __cspViolations: string[] }).__cspViolations = violations;
    document.addEventListener('securitypolicyviolation', (e) =>
      violations.push(`${e.violatedDirective} ${e.blockedURI}`),
    );
  });
  await page.route(
    (url) => !url.pathname.startsWith('/api/'),
    async (route) => {
      if (route.request().resourceType() !== 'document') {
        return route.fallback();
      }
      const response = await route.fetch();
      return route.fulfill({
        response,
        headers: { ...response.headers(), 'content-security-policy': PRODUCTION_CSP },
      });
    },
  );
}

export function cspViolations(page: Page): Promise<string[]> {
  return page.evaluate(() => (window as unknown as { __cspViolations: string[] }).__cspViolations);
}

/**
 * Mocks `/api/*` like the Flask API: protected routes answer 401 (JSON) until
 * `admin` / `password` logs in, unknown routes 404 (JSON).
 */
export async function mockApi(page: Page): Promise<void> {
  let loggedIn = false;
  const unauthorized = { status: 401, json: { error: 'unauthorized' } };

  await page.route('**/api/**', async (route) => {
    const url = new URL(route.request().url());
    const endpoint = url.pathname.replace(/^\/api\//, '');

    if (endpoint === 'auth/login') {
      const { username, password } = route.request().postDataJSON() ?? {};
      if (username === 'admin' && password === 'password') {
        loggedIn = true;
        return route.fulfill({
          json: { token: 'token', duration: 600, user: { uid: 'uid' }, connected: true },
        });
      }
      return route.fulfill({
        status: 400,
        contentType: 'text/html',
        body: '<p>Invalid credentials</p>',
      });
    }
    if (endpoint === 'auth/logout') {
      loggedIn = false;
      return route.fulfill({ json: { message: 'ok' } });
    }
    if (!loggedIn) {
      return route.fulfill(unauthorized);
    }
    if (endpoint === 'auth') {
      return route.fulfill({
        json: { token: 'token', duration: 600, user: { uid: 'uid' }, connected: true },
      });
    }
    if (endpoint in API_FIXTURES) {
      return route.fulfill({ json: API_FIXTURES[endpoint] });
    }
    return route.fulfill({ status: 404, json: { error: 'not found' } });
  });
}
