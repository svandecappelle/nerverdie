import { Page } from '@playwright/test';

const MB = 1024 ** 2;
const GB = 1024 ** 3;

/** `/api/admin/storage` before any change (unlimited database). */
export const STORAGE_STATUS = {
  limit_mb: null as number | null,
  limit_bytes: null as number | null,
  used_bytes: 48 * MB,
  file_bytes: 52 * MB,
  free_bytes: 4 * MB,
  samples: 86_400,
  oldest: '2026-11-22T10:00:00+05:30',
  newest: '2026-11-25T10:00:00+05:30',
  min_limit_mb: 1,
  max_limit_mb: 1_048_576,
};

/** `/api/admin/security` before any change: `eve` is locked until unlocked. */
export const SECURITY_STATUS = {
  policy: { max_attempts: 5 as number | null, lock_minutes: 15 },
  limits: { min_attempts: 1, max_attempts: 100, max_lock_minutes: 10080 },
  throttle: { max_failures: 5, window_seconds: 300 },
  accounts: [
    { username: 'admin', failed_logins: 0, locked: false, locked_until: null as string | null },
    { username: 'eve', failed_logins: 5, locked: true, locked_until: null as string | null },
  ],
  last_day: { success: 14, failure: 6, locked: 2, throttled: 1 },
  recent: [
    { time: '2026-11-25T10:02:00+05:30', username: 'eve', address: '203.0.113.7', outcome: 'locked' },
    { time: '2026-11-25T10:01:00+05:30', username: 'eve', address: '203.0.113.7', outcome: 'failure' },
    { time: '2026-11-25T10:00:00+05:30', username: 'admin', address: '127.0.0.1', outcome: 'success' },
  ],
};

/** `/api/admin/security/history`: hourly buckets with a burst of failures. */
export function securityHistoryResponse(url: URL): unknown {
  const to = Number(url.searchParams.get('to') ?? Date.now());
  const from = Number(url.searchParams.get('from') ?? to - 86400_000);
  const step = 3600;
  const samples = [];
  for (let t = Math.floor(from / 3600_000) * 3600_000, i = 0; t <= to; t += step * 1000, i++) {
    samples.push({ date: serverDate(t), success: i % 3, failure: i % 8 === 5 ? 4 : 0, refused: i % 8 === 6 ? 2 : 0 });
  }
  return { step, from: serverDate(from), to: serverDate(to), samples };
}

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
};

/**
 * The mocked server runs in UTC+05:30, a time zone other than the browser's: its dates must be
 * placed by their UTC offset, not read as browser-local clock times.
 */
const SERVER_OFFSET = '+05:30';
const SERVER_OFFSET_MS = (5 * 60 + 30) * 60_000;

/** ISO 8601 date with the UTC offset of the server, like the server dates. */
function serverDate(time: number): string {
  return new Date(time + SERVER_OFFSET_MS).toISOString().slice(0, 19) + SERVER_OFFSET;
}

/** Values of each history metric at time t. */
const HISTORY_VALUES: Record<string, (t: number) => Record<string, number>> = {
  cpu: (t) => ({ cpu0: 30 + 20 * Math.sin(t / 600_000), cpu1: 50 + 10 * Math.cos(t / 400_000) }),
  memory: () => ({ used: 4 * GB, swap: 0.5 * GB }),
  network: (t) => ({ incoming: 200_000 + 100_000 * Math.sin(t / 300_000), outgoing: 50_000 }),
};

/** `/api/history/<metric>`: about 60 samples over the requested range (default: last hour). */
export function historyResponse(metric: string, url: URL): unknown {
  const to = Number(url.searchParams.get('to') ?? Date.now());
  const from = Number(url.searchParams.get('from') ?? to - 3600_000);
  const step = Math.max(3, Math.ceil((to - from) / 1000 / 60));
  const samples = [];
  for (let t = from; t <= to; t += step * 1000) {
    samples.push({ date: serverDate(t), ...HISTORY_VALUES[metric](t) });
  }
  return { step, from: serverDate(from), to: serverDate(to), samples };
}

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
  let storage = { ...STORAGE_STATUS };
  let security = structuredClone(SECURITY_STATUS);
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
      if (username === 'eve' && security.accounts.find((account) => account.username === 'eve')?.locked) {
        return route.fulfill({
          status: 423,
          json: { error: 'account locked after too many failed logins', locked_until: null },
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
    if (endpoint === 'admin/security' && route.request().method() === 'PUT') {
      const { max_attempts, lock_minutes } = route.request().postDataJSON() ?? {};
      if (max_attempts !== null && !(max_attempts >= 1 && max_attempts <= 100)) {
        return route.fulfill({ status: 400, json: { error: 'max_attempts must be between 1 and 100' } });
      }
      security = { ...security, policy: { max_attempts, lock_minutes } };
      return route.fulfill({ json: security });
    }
    if (endpoint === 'admin/security/unlock') {
      const { username } = route.request().postDataJSON() ?? {};
      security = {
        ...security,
        accounts: security.accounts.map((account) =>
          account.username === username ? { ...account, failed_logins: 0, locked: false, locked_until: null } : account,
        ),
      };
      return route.fulfill({ json: security });
    }
    if (endpoint === 'admin/security/history') {
      return route.fulfill({ json: securityHistoryResponse(url) });
    }
    if (endpoint === 'admin/security') {
      return route.fulfill({ json: security });
    }
    if (endpoint === 'admin/storage' && route.request().method() === 'PUT') {
      const { limit_mb } = route.request().postDataJSON() ?? {};
      const limit = limit_mb ? limit_mb * MB : null;
      // Like the server: over the limit, the oldest samples go until 90% of it is used.
      const over = limit !== null && storage.used_bytes > limit;
      const used = over ? Math.round(limit * 0.9) : storage.used_bytes;
      const deleted = over ? Math.round(storage.samples * (1 - used / storage.used_bytes)) : 0;
      storage = {
        ...storage,
        limit_mb: limit_mb || null,
        limit_bytes: limit,
        used_bytes: used,
        free_bytes: storage.free_bytes + storage.used_bytes - used,
        samples: storage.samples - deleted,
      };
      return route.fulfill({ json: { ...storage, deleted } });
    }
    if (endpoint === 'admin/storage/compact') {
      storage = { ...storage, file_bytes: storage.used_bytes, free_bytes: 0 };
      return route.fulfill({ json: storage });
    }
    if (endpoint === 'admin/storage') {
      return route.fulfill({ json: storage });
    }
    const history = /^history[/](cpu|memory|network)$/.exec(endpoint);
    if (history) {
      return route.fulfill({ json: historyResponse(history[1], url) });
    }
    if (endpoint in API_FIXTURES) {
      return route.fulfill({ json: API_FIXTURES[endpoint] });
    }
    return route.fulfill({ status: 404, json: { error: 'not found' } });
  });
}
