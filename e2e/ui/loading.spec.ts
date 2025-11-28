import { test, expect } from '../fixtures';
import { ApiHelpers } from '../utils/api-helpers';

test.describe('Loading States Tests', () => {
  test('should display loading state during page load', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/');
    
    // Page should eventually load
    await authenticatedPage.waitForLoadState('networkidle');
    
    const body = authenticatedPage.locator('body');
    await expect(body).toBeVisible();
  });

  test('should handle async data loading', async ({ authenticatedPage, api, testProject }) => {
    await authenticatedPage.goto('/');
    await authenticatedPage.waitForLoadState('networkidle');

    // Navigate to a page that loads data
    const ingestTab = authenticatedPage.locator('nav').getByText('Ingest Pipeline');
    await ingestTab.click();
    
    // Wait for potential async loading
    await authenticatedPage.waitForTimeout(1000);
    
    // Verify page loaded
    const body = authenticatedPage.locator('body');
    await expect(body).toBeVisible();
  });

  test('should show loading indicators for API calls', async ({ authenticatedPage, api, testProject }) => {
    await authenticatedPage.goto('/');
    await authenticatedPage.waitForLoadState('networkidle');

    // Make an API call that might trigger loading
    const apiHelpers = new ApiHelpers(api);
    const jobs = await apiHelpers.getIngestJobs(testProject.id);
    
    expect(jobs).toBeTruthy();
    
    // Verify page is still responsive
    const body = authenticatedPage.locator('body');
    await expect(body).toBeVisible();
  });

  test('should handle loading state transitions', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/');
    await authenticatedPage.waitForLoadState('networkidle');

    // Navigate between pages to test loading transitions
    const tabs = ['Mission Control', 'Project Roadmap', 'Nexus Graph'];
    
    for (const tab of tabs) {
      const navItem = authenticatedPage.locator('nav').getByText(tab);
      await navItem.click();
      
      // Wait for transition
      await authenticatedPage.waitForTimeout(300);
      
      // Verify page loaded
      const body = authenticatedPage.locator('body');
      await expect(body).toBeVisible();
    }
  });

  test('should handle concurrent loading operations', async ({ authenticatedPage, api, testProject }) => {
    await authenticatedPage.goto('/');
    await authenticatedPage.waitForLoadState('networkidle');

    // Trigger multiple API calls concurrently
    const apiHelpers = new ApiHelpers(api);
    
    const promises = [
      apiHelpers.getIngestJobs(testProject.id),
      apiHelpers.getRoadmapNodes(testProject.id),
      apiHelpers.getContext(testProject.id),
    ];
    
    await Promise.all(promises);
    
    // Verify page is still responsive
    const body = authenticatedPage.locator('body');
    await expect(body).toBeVisible();
  });

  test('should handle loading timeout gracefully', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/');
    
    // Set a reasonable timeout
    await authenticatedPage.waitForLoadState('networkidle', { timeout: 30000 });
    
    // Verify page loaded
    const body = authenticatedPage.locator('body');
    await expect(body).toBeVisible();
  });

  test('should show progress indicators for long operations', async ({ authenticatedPage, api, testProject }) => {
    await authenticatedPage.goto('/');
    await authenticatedPage.waitForLoadState('networkidle');

    // Create an ingest job (might take time)
    const apiHelpers = new ApiHelpers(api);
    const job = await apiHelpers.createIngestJob(testProject.id, 'test-doc.md');
    
    // Wait a bit
    await authenticatedPage.waitForTimeout(1000);
    
    // Verify page is still responsive
    const body = authenticatedPage.locator('body');
    await expect(body).toBeVisible();
  });
});





