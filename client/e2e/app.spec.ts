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
  await page.getByLabel('Password').fill('wrong');
  await page.getByRole('button', { name: 'Login' }).click();

  await expect(page.getByRole('alert')).toHaveText('Invalid credentials');
  await expect(page).toHaveURL(/\/login$/);
});

test('logging in shows the dashboard with live charts', async ({ page }) => {
  await page.goto('/login');
  await page.getByLabel('User').fill('admin');
  await page.getByLabel('Password').fill('password');
  await page.getByRole('button', { name: 'Login' }).click();

  await expect(page).toHaveURL(/\/$/);
  await expect(page.locator('mat-toolbar')).toContainText('Neverdie');

  // Status tiles
  const tiles = page.locator('mat-grid-tile');
  await expect(tiles).toHaveCount(6);
  await expect(tiles.filter({ hasText: 'status' })).toContainText('Up');
  await expect(tiles.filter({ hasText: 'uptime' })).toContainText('3 days');
  await expect(tiles.filter({ hasText: 'memory' })).toContainText('4096Mo / 8192Mo');
  await expect(tiles.filter({ hasText: 'cpu' })).toContainText('2 cores');
  await expect(tiles.filter({ hasText: 'system_info' })).toContainText('test-server');

  // CPU, memory and network charts (Chart.js canvases)
  const charts = page.locator('app-chart canvas');
  await expect(charts).toHaveCount(3);
  for (const title of ['CPU', 'Memory', 'Network']) {
    await expect(page.getByRole('img', { name: title })).toBeVisible();
  }
  await expect(page.getByRole('img', { name: 'CPU' })).toContainText('Cpu load 0, Cpu load 1');
  await expect(page.getByRole('img', { name: 'Network' })).toContainText('Incoming, Outgoing');

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
  await page.getByLabel('Password').fill('password');
  await page.getByRole('button', { name: 'Login' }).click();
  await expect(page).toHaveURL(/\/$/);

  await page.getByRole('link', { name: 'Admin panel' }).click();
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
