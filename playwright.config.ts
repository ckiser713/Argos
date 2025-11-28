import { defineConfig, devices } from '@playwright/test';

/**
 * See https://playwright.dev/docs/test-configuration.
 */
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
  timeout: 30000,
  /* Global test timeout */
  globalTimeout: 600000,
  /* Shared settings for all the projects below. See https://playwright.dev/docs/api/class-testoptions. */
  use: {
    /* Base URL to use in actions like `await page.goto('/')`. */
    baseURL: process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:5173',
    /* Collect trace when retrying the failed test. See https://playwright.dev/docs/trace-viewer */
    trace: 'on-first-retry',
    /* Screenshot on failure */
    screenshot: 'only-on-failure',
    /* Increase timeout for slow environments */
    actionTimeout: 30000,
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
      threshold: 0.2,
      maxDiffPixels: 100,
    },
    /* Threshold for snapshot comparisons */
    toMatchSnapshot: {
      threshold: 0.2,
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
  webServer: [
    {
      command: 'cd frontend && pnpm dev --port 5173',
      url: process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:5173',
      reuseExistingServer: true,
      timeout: 120 * 1000,
      stdout: 'pipe',
      stderr: 'pipe',
    },
  ],
});

