import { expect, test } from '@playwright/test';

import { mockApi } from './api-mock';

test.beforeEach(async ({ page }) => {
  await mockApi(page);
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

  // CPU, memory and network charts
  await expect(page.locator('.highcharts-container')).toHaveCount(3);
  for (const title of ['CPU', 'Memory', 'Network']) {
    await expect(page.locator('.highcharts-title', { hasText: title })).toBeVisible();
  }
  await expect(page.locator('.highcharts-legend')).toContainText(['Cpu load 0']);
  await expect(page.locator('.highcharts-legend').nth(2)).toContainText('Incoming');

  // Logout brings the login page back.
  await page.getByRole('button', { name: 'User menu' }).click();
  await page.getByRole('menuitem', { name: 'Logout' }).click();
  await expect(page).toHaveURL(/\/login$/);
});
