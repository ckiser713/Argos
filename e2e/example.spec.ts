import { test, expect } from './fixtures';

/**
 * Example e2e test showing frontend interaction
 * This test demonstrates how to test the UI layer
 */
test.describe('Frontend Example', () => {
  test('should load the application', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/');
    
    // Wait for the page to load
    await authenticatedPage.waitForLoadState('networkidle');
    
    // Check that the page loaded successfully
    await expect(authenticatedPage).toHaveTitle(/Cortex/i);
  });

  // Add more frontend tests here as UI components are developed
  // Example:
  // test('should display projects list', async ({ authenticatedPage }) => {
  //   await authenticatedPage.goto('/');
  //   await expect(authenticatedPage.locator('[data-testid="projects-list"]')).toBeVisible();
  // });
});


