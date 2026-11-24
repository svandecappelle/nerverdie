import { defineConfig, devices } from '@playwright/test';

const port = 4300;

/**
 * End-to-end tests. The Flask API is mocked in the tests (see e2e/api-mock.ts),
 * so only the Angular dev server is needed.
 *
 * Browser: `npx playwright install chromium` once, or reuse an installed browser
 * with PLAYWRIGHT_CHANNEL=msedge (or chrome).
 */
export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env['CI'],
  retries: process.env['CI'] ? 2 : 0,
  reporter: 'list',
  use: {
    baseURL: `http://localhost:${port}`,
    trace: 'on-first-retry',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'], channel: process.env['PLAYWRIGHT_CHANNEL'] },
    },
  ],
  webServer: {
    // Production configuration: same optimised output as client/dist.
    command: `npx ng serve --configuration production --port ${port}`,
    url: `http://localhost:${port}`,
    reuseExistingServer: !process.env['CI'],
    timeout: 120_000,
  },
});
