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
      use: { ...devices['iPad Pro'] },
    },
  ],

  /* Run your local dev server before starting the tests */
  webServer: [
    {
      command: 'cd backend && LD_LIBRARY_PATH=/nix/store/dj06r96j515npcqi9d8af1d1c60bx2vn-gcc-14.3.0-lib/lib:/nix/store/g8zyryr9cr6540xsyg4avqkwgxpnwj2a-glibc-2.40-66/lib:$LD_LIBRARY_PATH poetry run python -m uvicorn app.main:app --host 0.0.0.0 --port 8000',
      url: 'http://localhost:8000/api/docs',
      reuseExistingServer: !process.env.CI,
      timeout: 120 * 1000,
      env: {
        CORTEX_ENV: 'test',
        CORTEX_ATLAS_DB_PATH: './test_atlas.db',
        CORTEX_QDRANT_URL: 'http://localhost:6333',
        CORTEX_SKIP_AUTH: 'true',
      },
    },
    {
      command: 'cd frontend && pnpm dev --port 5173',
      url: 'http://localhost:5173',
      reuseExistingServer: !process.env.CI,
      timeout: 120 * 1000,
      stdout: 'pipe',
      stderr: 'pipe',
    },
  ],
});

