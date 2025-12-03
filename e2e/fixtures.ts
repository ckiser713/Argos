import { test as base, expect } from '@playwright/test';
import type { Page, APIRequestContext } from '@playwright/test';
import { UIHelpers } from './utils/ui-helpers';
import { ApiHelpers } from './utils/api-helpers';

/**
 * Custom fixtures for e2e tests
 */

export interface TestFixtures {
  api: APIRequestContext;
  authenticatedPage: Page;
  testProject: { id: string; name: string };
  uiHelpers: UIHelpers;
  apiHelpers: ApiHelpers;
}

/**
 * API client fixture for making direct API calls
 */
const API_BASE = (process.env.PLAYWRIGHT_API_BASE || process.env.PLAYWRIGHT_BACKEND_URL || 'http://127.0.0.1:8000')
  .replace(/\/(?:api|api\/docs)?$/i, '') + '/api';

export const test = base.extend<TestFixtures>({
  api: async ({ request }, use) => {
    // Use the same request context for API calls
    await use(request);
  },

  authenticatedPage: async ({ page, request }, use) => {
    // For now, we'll skip auth in tests
    // In production, you'd set up auth tokens here
    // Ensure a consistent viewport for visual regression tests
    try {
      await page.setViewportSize({ width: 1408, height: 864 });
    } catch (e) {
      // some Playwright devices may throw if viewport cannot be set; ignore
    }
    // Disable animations and enforce deterministic fonts for visual tests
    try {
      await page.addStyleTag({ content: `* { animation: none !important; transition: none !important; } .animate-pulse { opacity: 1 !important; } body { font-family: 'JetBrains Mono', 'Inter', monospace, sans-serif !important; }` });
    } catch (e) {
      // ignore if injection fails
    }
    await page.goto('/');
    await use(page);
  },

  testProject: async ({ api }, use) => {
    // Create a test project
    const response = await api.post(`${API_BASE}/projects`, {
      data: {
        name: `Test Project ${Date.now()}`,
        description: 'E2E test project',
      },
    });

    expect(response.ok()).toBeTruthy();
    const project = await response.json();
    expect(project).toHaveProperty('id');

    await use({ id: project.id, name: project.name });

    // Cleanup: delete the project after test
    await api.delete(`${API_BASE}/projects/${project.id}`).catch(() => {
      // Ignore cleanup errors
    });
  },

  uiHelpers: async ({ authenticatedPage }, use) => {
    const helpers = new UIHelpers(authenticatedPage);
    await use(helpers);
  },

  apiHelpers: async ({ api }, use) => {
    const helpers = new ApiHelpers(api);
    await use(helpers);
  },
});

export { expect };


