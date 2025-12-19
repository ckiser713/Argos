import { defineConfig, devices } from '@playwright/test';

/**
 * See https://playwright.dev/docs/test-configuration.
 */
const BASE_URL = process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:5173';
const API_BASE = process.env.PLAYWRIGHT_API_BASE || 'http://localhost:8000/api';
const startDevServer = process.env.PLAYWRIGHT_START_DEV_SERVER === '1';

export default defineConfig({
  testDir: './e2e',
  /* Run tests in files in parallel */
  fullyParallel: true,
  /* Fail the build on CI if you accidentally left test.only in the source code. */
  forbidOnly: !!process.env.CI,
  /* Retry on CI only */
  retries: process.env.CI ? 2 : 0,
  /* Opt out of parallel tests on CI. */
  workers: process.env.CI ? 1 : undefined,
  /* Reporter to use. See https://playwright.dev/docs/test-reporters */
  reporter: process.env.CI 
    ? [['html'], ['json', { outputFile: 'test-results/results.json' }]]
    : [['list'], ['html']],
  /* Test timeout */
  timeout: 45000,
  /* Global test timeout */
  globalTimeout: 600000,
  /* Shared settings for all the projects below. See https://playwright.dev/docs/api/class-testoptions. */
  use: {
    /* Base URL to use in actions like `await page.goto('/')`. */
    baseURL: BASE_URL,
    /* Collect trace when retrying the failed test. See https://playwright.dev/docs/trace-viewer */
    trace: 'on-first-retry',
    /* Screenshot on failure */
    screenshot: 'only-on-failure',
    /* Increase timeout for slow environments */
    actionTimeout: 30000,
    metadata: {
      apiBase: API_BASE,
    },
    /* Ensure consistent device scaling for screenshots */
    deviceScaleFactor: 1,
    /* Default viewport to help visual regression tests remain stable */
    viewport: { width: 1408, height: 864 },
    /* Visual comparison threshold */
    video: 'retain-on-failure',
  },
  
  /* Visual comparison configuration */
  expect: {
    /* Threshold for visual comparisons */
    toHaveScreenshot: {
      threshold: 0.05,
      maxDiffPixels: 200000,
      maxDiffPixelRatio: 0.05,
    },
    /* Threshold for snapshot comparisons */
    toMatchSnapshot: {
      threshold: 0.02,
    },
  },

  /* Configure projects for major browsers */
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },

    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },

    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },

    /* Test against mobile viewports. */
    {
      name: 'Mobile Chrome',
      use: { ...devices['Pixel 5'] },
    },
    {
      name: 'Mobile Safari',
      use: { ...devices['iPhone 12'] },
    },
    
    /* Tablet viewports */
    {
      name: 'Tablet Chrome',
      use: { ...devices['iPad Pro'], deviceScaleFactor: 1 },
    },
  ],

  /* Run your local dev server before starting the tests */
  // If PLAYWRIGHT_START_DEV_SERVER=1 is set, Playwright will start Vite dev server.
  // Otherwise, assume the frontend is already served and reuse existing server.
  webServer: startDevServer
    ? [
        {
          command: 'cd frontend && pnpm dev --port 5173',
          url: BASE_URL,
          reuseExistingServer: false,
          timeout: 120 * 1000,
          stdout: 'pipe',
          stderr: 'pipe',
        },
      ]
    : undefined,
});

