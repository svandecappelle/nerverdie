import { expect, test } from '@playwright/test';

import { cspViolations, enforceCsp, mockApi } from './api-mock';

test.beforeEach(async ({ page }) => {
  await enforceCsp(page);
  await mockApi(page);
});

test.afterEach(async ({ page }) => {
  // The production CSP forbids inline scripts and external resources.
  expect(await cspViolations(page)).toEqual([]);
});

test('the global stylesheet applies under the production CSP', async ({ page }) => {
  await page.goto('/login');
  await expect(page.getByText('Please login to continue')).toBeVisible();

  // styles.css sets `body { margin: 0 }` and loads the Material Icons font.
  expect(await page.evaluate(() => getComputedStyle(document.body).margin)).toBe('0px');
  const stylesheetMedia = await page.evaluate(() =>
    [...document.querySelectorAll<HTMLLinkElement>('link[rel=stylesheet]')].map((l) => l.media),
  );
  expect(stylesheetMedia.every((m) => m === '' || m === 'all')).toBe(true);
});

test('an anonymous visitor is sent to the login page', async ({ page }) => {
  await page.goto('/');

  await expect(page).toHaveURL(/\/login$/);
  await expect(page.getByText('Please login to continue')).toBeVisible();
  await expect(page.locator('mat-toolbar')).toHaveCount(0);
});

test('bad credentials show an error', async ({ page }) => {
  await page.goto('/login');
  await page.getByLabel('User').fill('admin');
  await page.getByLabel('Password', { exact: true }).fill('wrong');
  await page.getByRole('button', { name: 'Login' }).click();

  await expect(page.getByRole('alert')).toHaveText('Invalid credentials');
  await expect(page).toHaveURL(/\/login$/);
});

test('logging in shows the dashboard with live charts', async ({ page }) => {
  await page.goto('/login');
  await page.getByLabel('User').fill('admin');
  await page.getByLabel('Password', { exact: true }).fill('password');
  await page.getByRole('button', { name: 'Login' }).click();

  await expect(page).toHaveURL(/\/$/);
  await expect(page.locator('mat-toolbar')).toContainText('Neverdie');

  // Status cards
  const tiles = page.locator('app-indicator');
  await expect(tiles).toHaveCount(6);
  await expect(tiles.filter({ hasText: 'status' })).toContainText('Up');
  await expect(tiles.filter({ hasText: 'uptime' })).toContainText('3 days');
  await expect(tiles.filter({ hasText: 'memory' })).toContainText('4 GB / 8 GB');
  await expect(tiles.filter({ hasText: 'memory' })).toContainText('50% used');
  await expect(tiles.filter({ hasText: 'storage' })).toContainText('25% used');
  await expect(tiles.filter({ hasText: 'cpu' })).toContainText('2 cores');
  await expect(tiles.filter({ hasText: 'host' })).toContainText('test-server');
  await expect(page.locator('.page-header')).toContainText('test-server');
  await expect(page.locator('.page-header .chip')).toHaveText('Live');

  // CPU, memory and network charts (Chart.js canvases)
  const charts = page.locator('app-chart canvas');
  await expect(charts).toHaveCount(3);
  for (const title of ['CPU', 'Memory', 'Network']) {
    await expect(page.getByRole('img', { name: title })).toBeVisible();
  }
  await expect(page.getByRole('img', { name: 'CPU' })).toContainText('Cpu load 0, Cpu load 1');
  await expect(page.getByRole('img', { name: 'Network' })).toContainText('Received, Sent');

  // Every chart is actually drawn (some non-transparent pixels).
  await expect
    .poll(() =>
      charts.evaluateAll((canvases) =>
        (canvases as HTMLCanvasElement[]).map((canvas) => {
          const { data } = canvas.getContext('2d')!.getImageData(0, 0, canvas.width, canvas.height);
          return data.some((value, index) => index % 4 === 3 && value > 0);
        }),
      ),
    )
    .toEqual([true, true, true]);

  // Logout brings the login page back.
  await page.getByRole('button', { name: 'User menu' }).click();
  await page.getByRole('menuitem', { name: 'Logout' }).click();
  await expect(page).toHaveURL(/\/login$/);
});

test('the admin screen shows the database size and sets its limit', async ({ page }) => {
  await page.goto('/login');
  await page.getByLabel('User').fill('admin');
  await page.getByLabel('Password', { exact: true }).fill('password');
  await page.getByRole('button', { name: 'Login' }).click();
  await expect(page).toHaveURL(/\/$/);

  await page.getByRole('link', { name: 'Administration' }).click();
  await expect(page).toHaveURL(/\/admin$/);
  const usage = page.getByRole('region', { name: 'Database usage' });
  await expect(usage).toHaveText('48 MB used, no size limit');
  await expect(page.getByText('52 MB')).toBeVisible();
  await expect(page.getByText('86,400')).toBeVisible();

  // Limit the database to 40 MB: the oldest samples are deleted at once.
  const limit = page.getByRole('spinbutton', { name: 'Size limit' });
  await expect(limit).toBeDisabled();
  await page.getByRole('switch', { name: 'Limit the database size' }).click();
  await limit.fill('40');
  await page.getByRole('button', { name: 'Save' }).click();
  await expect(page.getByRole('status')).toHaveText(/Limit set to 40 MB\. \d+ old samples were deleted\./);
  await expect(usage).toContainText('36 MB used of 40 MB (90%)');
  await expect(page.getByRole('progressbar', { name: 'Share of the size limit in use' })).toHaveAttribute(
    'aria-valuenow',
    '90',
  );

  // An invalid limit is not sent.
  await limit.fill('0');
  await page.getByRole('button', { name: 'Save' }).click();
  await expect(page.getByText('A whole number of MB, at least 1')).toBeVisible();

  // Compacting gives the free pages back.
  await page.getByRole('button', { name: 'Compact' }).click();
  await expect(page.getByRole('status')).toHaveText('Database compacted: 36 MB on disk.');

  // Reloading keeps the saved limit (the form is filled from the server).
  await page.reload();
  await expect(limit).toHaveValue('40');
});

test('the theme follows the system and can be forced to dark or light', async ({ page }) => {
  await page.emulateMedia({ colorScheme: 'light' });
  await page.goto('/login');
  const background = () => page.evaluate(() => getComputedStyle(document.body).backgroundColor);
  const light = await background();

  // System preference
  await page.emulateMedia({ colorScheme: 'dark' });
  await expect.poll(background).not.toBe(light);
  const dark = await background();

  // Forced light, kept after a reload
  await page.getByRole('button', { name: 'Theme' }).click();
  await page.getByRole('menuitemradio', { name: 'Light' }).click();
  await expect.poll(background).toBe(light);
  await page.reload();
  await expect.poll(background).toBe(light);
  expect(await page.evaluate(() => document.documentElement.dataset['theme'])).toBe('light');

  // Forced dark, also once logged in
  await page.getByRole('button', { name: 'Theme' }).click();
  await page.getByRole('menuitemradio', { name: 'Dark' }).click();
  await expect.poll(background).toBe(dark);
  await page.getByLabel('User').fill('admin');
  await page.getByLabel('Password', { exact: true }).fill('password');
  await page.getByRole('button', { name: 'Login' }).click();
  await expect(page).toHaveURL(/\/$/);
  await expect.poll(background).toBe(dark);
  await expect(page.getByRole('menuitemradio')).toHaveCount(0);
});

test('the time range picker drives the charts, like Grafana', async ({ page }) => {
  const historyRequests: URL[] = [];
  page.on('request', (request) => {
    const url = new URL(request.url());
    if (url.pathname === '/api/history/cpu') {
      historyRequests.push(url);
    }
  });
  const lastSpan = () => {
    const url = historyRequests.at(-1)!;
    return Number(url.searchParams.get('to')) - Number(url.searchParams.get('from'));
  };

  await page.goto('/login');
  await page.getByLabel('User').fill('admin');
  await page.getByLabel('Password', { exact: true }).fill('password');
  await page.getByRole('button', { name: 'Login' }).click();
  await expect(page).toHaveURL(/\/$/);

  // Default: the last hour.
  const picker = page.getByRole('button', { name: 'Time range', exact: true });
  await expect(picker).toHaveText(/Last hour/);
  await expect.poll(lastSpan).toBe(3600_000);

  // Quick range, kept in the URL.
  await picker.click();
  await page.getByRole('dialog', { name: 'Choose a time range' }).getByRole('button', { name: 'Last 6 hours' }).click();
  await expect(picker).toHaveText(/Last 6 hours/);
  await expect(page).toHaveURL(/from=now-6h/);
  await expect.poll(lastSpan).toBe(6 * 3600_000);

  // Zoom out doubles the span.
  await page.getByRole('button', { name: 'Zoom out time range' }).click();
  await expect(picker).toHaveText(/Last 12 hours/);

  // Absolute range typed by hand; an invalid one is refused.
  await picker.click();
  const dialog = page.getByRole('dialog', { name: 'Choose a time range' });
  await dialog.getByLabel('From').fill('soon');
  await dialog.getByRole('button', { name: 'Apply time range' }).click();
  await expect(dialog.getByRole('alert')).toContainText('Invalid "From"');
  await dialog.getByLabel('From').fill('2026-11-24 08:00:00');
  await dialog.getByLabel('To').fill('2026-11-24 10:00:00');
  await dialog.getByRole('button', { name: 'Apply time range' }).click();
  await expect(picker).toHaveText(/2026-11-24 08:00:00 to 2026-11-24 10:00:00/);
  await expect.poll(lastSpan).toBe(2 * 3600_000);

  // Dragging over a chart zooms into the selected span.
  const canvas = page.getByRole('img', { name: 'CPU' });
  const box = (await canvas.boundingBox())!;
  await page.mouse.move(box.x + box.width * 0.4, box.y + box.height / 2);
  await page.mouse.down();
  await page.mouse.move(box.x + box.width * 0.6, box.y + box.height / 2, { steps: 5 });
  await page.mouse.up();
  await expect(picker).toHaveText(/2026-11-24 08:\d\d:\d\d to 2026-11-24 09:\d\d:\d\d/);
  await expect.poll(lastSpan).toBeLessThan(2 * 3600_000 * 0.3);

  // The view survives a reload (the range is in the URL).
  const url = page.url();
  await page.reload();
  expect(page.url()).toBe(url);
  await expect(picker).not.toHaveText(/Last/);

  // Auto-refresh can be turned off.
  await page.getByRole('button', { name: 'Auto-refresh interval' }).click();
  await page.getByRole('menuitemradio', { name: 'Off' }).click();
  await expect(page).not.toHaveURL(/refresh=/);
});

test('the dashboard can be customized and keeps its layout', async ({ page }) => {
  const historyCalls: string[] = [];
  page.on('request', (request) => {
    const path = new URL(request.url()).pathname;
    if (path.startsWith('/api/history/')) {
      historyCalls.push(path.slice('/api/history/'.length));
    }
  });

  await page.goto('/login');
  await page.getByLabel('User').fill('admin');
  await page.getByLabel('Password', { exact: true }).fill('password');
  await page.getByRole('button', { name: 'Login' }).click();
  await expect(page).toHaveURL(/\/$/);

  const chartTitles = page.locator('.charts .panel-title');
  await expect(chartTitles).toHaveText(['CPU', 'Memory', 'Network']);
  // Every chart spans the full width by default.
  const fullWidth = await page.locator('.charts').evaluate((el) => el.clientWidth);
  const cpuPanel = page.locator('.charts .panel').first();
  expect(await cpuPanel.evaluate((el) => el.getBoundingClientRect().width)).toBeGreaterThan(fullWidth * 0.95);

  await page.getByRole('button', { name: 'Customize' }).click();
  const editor = page.getByRole('region', { name: 'Customize dashboard' });
  await expect(editor).toBeVisible();

  // Hide a tile.
  await editor.getByRole('checkbox', { name: 'Uptime' }).uncheck();
  await expect(page.locator('app-indicator')).toHaveCount(5);

  // Hide the CPU chart: its history is no longer requested.
  await editor.getByRole('list', { name: 'Charts' }).getByRole('checkbox', { name: 'CPU' }).uncheck();
  await expect(chartTitles).toHaveText(['Memory', 'Network']);
  historyCalls.length = 0;
  await page.getByRole('button', { name: 'Refresh', exact: true }).click();
  await expect.poll(() => historyCalls.length).toBeGreaterThan(0);
  expect(historyCalls).not.toContain('cpu');

  // Network first, half width, tall.
  await editor.getByRole('button', { name: 'Move Network up' }).click();
  await expect(chartTitles).toHaveText(['Network', 'Memory']);
  await editor.getByRole('radiogroup', { name: 'Network width' }).getByRole('radio', { name: 'Half' }).click();
  await editor.getByRole('radiogroup', { name: 'Network height' }).getByRole('radio', { name: 'Large' }).click();
  const network = page.locator('.charts .panel').first();
  await expect.poll(() => network.evaluate((el) => el.getBoundingClientRect().width)).toBeLessThan(fullWidth * 0.6);
  await expect.poll(() => network.locator('app-chart').evaluate((el) => el.clientHeight)).toBe(460);

  await editor.getByRole('button', { name: 'Done' }).click();
  await expect(editor).toBeHidden();

  // The layout survives a reload.
  await page.reload();
  await expect(chartTitles).toHaveText(['Network', 'Memory']);
  await expect(page.locator('app-indicator')).toHaveCount(5);

  // Reset brings the default layout back.
  await page.getByRole('button', { name: 'Customize' }).click();
  await editor.getByRole('button', { name: 'Reset' }).click();
  await expect(chartTitles).toHaveText(['CPU', 'Memory', 'Network']);
  await expect(page.locator('app-indicator')).toHaveCount(6);
});
