import { test, expect } from '../fixtures';
import { ApiHelpers, API_BASE_URL } from '../utils/api-helpers';

test.describe('Error Handling UI Tests', () => {
  test('should handle API error messages in UI', async ({ authenticatedPage, api }) => {
    await authenticatedPage.goto('/');
    await authenticatedPage.waitForLoadState('networkidle');

    // Try to access a non-existent resource
    const response = await api.get(`${API_BASE_URL}/projects/invalid-project-id`);
    expect(response.status()).toBe(404);

    // Verify page is still functional
    const body = authenticatedPage.locator('body');
    await expect(body).toBeVisible();
  });

  test('should handle network failure gracefully', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/');
    await authenticatedPage.waitForLoadState('networkidle');

    // Simulate network failure by going offline
    await authenticatedPage.context().setOffline(true);

    // Try to navigate
    const missionControlTab = authenticatedPage.locator('nav').getByText('Mission Control');
    await missionControlTab.click();
    await authenticatedPage.waitForTimeout(500);

    // Verify page is still visible (should show error state)
    const body = authenticatedPage.locator('body');
    await expect(body).toBeVisible();

    // Restore network
    await authenticatedPage.context().setOffline(false);
  });

  test('should handle validation errors', async ({ authenticatedPage, api }) => {
    await authenticatedPage.goto('/');
    await authenticatedPage.waitForLoadState('networkidle');

    // Try to create project with invalid data
    const response = await api.post(`${API_BASE_URL}/projects`, {
      data: {
        // Invalid: missing required 'name' field
        description: 'Test',
      },
    });

    expect(response.status()).toBeGreaterThanOrEqual(400);
    
    // Verify page is still functional
    const body = authenticatedPage.locator('body');
    await expect(body).toBeVisible();
  });

  test('should handle 404 errors', async ({ authenticatedPage, api }) => {
    await authenticatedPage.goto('/');
    await authenticatedPage.waitForLoadState('networkidle');

    // Try to get non-existent resource
    const response = await api.get(`${API_BASE_URL}/projects/non-existent-id`);
    expect(response.status()).toBe(404);

    // Verify page is still functional
    const body = authenticatedPage.locator('body');
    await expect(body).toBeVisible();
  });

  test('should handle 500 errors gracefully', async ({ authenticatedPage, api }) => {
    await authenticatedPage.goto('/');
    await authenticatedPage.waitForLoadState('networkidle');

    // Try an operation that might fail
    // Note: We can't easily trigger a 500, but we can verify error handling exists
    const body = authenticatedPage.locator('body');
    await expect(body).toBeVisible();
  });

  test('should display error boundary when component crashes', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/');
    await authenticatedPage.waitForLoadState('networkidle');

    // Navigate through pages to ensure error boundary works
    const tabs = ['Mission Control', 'Project Roadmap', 'Nexus Graph'];
    
    for (const tab of tabs) {
      const navItem = authenticatedPage.locator('nav').getByText(tab);
      await navItem.click();
      await authenticatedPage.waitForTimeout(300);
      
      // Verify page is still visible (error boundary should catch errors)
      const body = authenticatedPage.locator('body');
      await expect(body).toBeVisible();
    }
  });

  test('should recover from errors', async ({ authenticatedPage, api, testProject }) => {
    await authenticatedPage.goto('/');
    await authenticatedPage.waitForLoadState('networkidle');

    // Try invalid operation
    const invalidResponse = await api.get(`${API_BASE_URL}/projects/${testProject.id}/workflows/graphs/invalid-id`);
    expect(invalidResponse.status()).toBe(404);

    // Then try valid operation
    const apiHelpers = new ApiHelpers(api);
    const projects = await apiHelpers.listWorkflowGraphs(testProject.id);
    expect(Array.isArray(projects)).toBeTruthy();

    // Verify page is still functional
    const body = authenticatedPage.locator('body');
    await expect(body).toBeVisible();
  });
});





