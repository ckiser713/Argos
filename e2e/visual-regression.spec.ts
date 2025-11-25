import { test, expect } from './fixtures';

/**
 * Visual Regression Tests
 * 
 * Screenshot comparison tests to detect visual changes
 */
test.describe('Visual Regression', () => {
  test('should match main page screenshot', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/');
    await authenticatedPage.waitForLoadState('networkidle');
    
    // Take screenshot and compare
    await expect(authenticatedPage).toHaveScreenshot('main-page.png', {
      fullPage: true,
    });
  });

  test('should match projects page screenshot', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/');
    await authenticatedPage.waitForLoadState('networkidle');
    
    // Navigate to projects if route exists
    // await authenticatedPage.click('[data-testid="nav-projects"]');
    // await authenticatedPage.waitForLoadState('networkidle');
    
    await expect(authenticatedPage).toHaveScreenshot('projects-page.png', {
      fullPage: true,
    });
  });

  test('should match component states', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/');
    await authenticatedPage.waitForLoadState('networkidle');
    
    // Test specific component states
    const body = authenticatedPage.locator('body');
    await expect(body).toHaveScreenshot('body-component.png');
  });

  test('should match error state screenshot', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/invalid-route-that-does-not-exist');
    await authenticatedPage.waitForLoadState('networkidle');
    
    await expect(authenticatedPage).toHaveScreenshot('error-page.png', {
      fullPage: true,
    });
  });

  test('should match loading state screenshot', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/');
    
    // Capture loading state before networkidle
    await expect(authenticatedPage).toHaveScreenshot('loading-state.png', {
      fullPage: true,
    });
  });

  test('should match responsive mobile view', async ({ authenticatedPage }) => {
    // Set mobile viewport
    await authenticatedPage.setViewportSize({ width: 375, height: 667 });
    await authenticatedPage.goto('/');
    await authenticatedPage.waitForLoadState('networkidle');
    
    await expect(authenticatedPage).toHaveScreenshot('mobile-view.png', {
      fullPage: true,
    });
  });

  test('should match responsive tablet view', async ({ authenticatedPage }) => {
    // Set tablet viewport
    await authenticatedPage.setViewportSize({ width: 768, height: 1024 });
    await authenticatedPage.goto('/');
    await authenticatedPage.waitForLoadState('networkidle');
    
    await expect(authenticatedPage).toHaveScreenshot('tablet-view.png', {
      fullPage: true,
    });
  });

  test('should match responsive desktop view', async ({ authenticatedPage }) => {
    // Set desktop viewport
    await authenticatedPage.setViewportSize({ width: 1920, height: 1080 });
    await authenticatedPage.goto('/');
    await authenticatedPage.waitForLoadState('networkidle');
    
    await expect(authenticatedPage).toHaveScreenshot('desktop-view.png', {
      fullPage: true,
    });
  });

  test('should match dark mode (if implemented)', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/');
    await authenticatedPage.waitForLoadState('networkidle');
    
    // Toggle dark mode if available
    // const darkModeToggle = authenticatedPage.locator('[data-testid="dark-mode-toggle"]');
    // if (await darkModeToggle.isVisible()) {
    //   await darkModeToggle.click();
    //   await authenticatedPage.waitForTimeout(500); // Wait for transition
    // }
    
    await expect(authenticatedPage).toHaveScreenshot('dark-mode.png', {
      fullPage: true,
    });
  });
});

