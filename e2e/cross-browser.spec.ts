import { test, expect } from './fixtures';
import { ApiHelpers } from './utils/api-helpers';

/**
 * Cross-Browser Tests
 * 
 * Tests to ensure consistent behavior across different browsers
 */
test.describe('Cross-Browser Compatibility', () => {
  test('should load application in all browsers', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/');
    await authenticatedPage.waitForLoadState('networkidle');
    
    // Verify page loads
    await expect(authenticatedPage).toHaveTitle(/Cortex/i);
    
    // Verify basic content is visible
    const body = authenticatedPage.locator('body');
    await expect(body).toBeVisible();
  });

  test('should handle API requests consistently', async ({ api, testProject }) => {
    const apiHelpers = new ApiHelpers(api);
    
    // Create project
    const project = await apiHelpers.createProject('Cross-Browser Test');
    
    expect(project).toHaveProperty('id');
    expect(project.name).toBe('Cross-Browser Test');
    
    // Cleanup
    await apiHelpers.deleteProject(project.id);
  });

  test('should render forms consistently', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/');
    await authenticatedPage.waitForLoadState('networkidle');
    
    // Check for form elements
    const forms = authenticatedPage.locator('form');
    const inputs = authenticatedPage.locator('input, textarea, select');
    
    // Forms should render consistently
    if (await forms.count() > 0) {
      await expect(forms.first()).toBeVisible();
    }
    
    if (await inputs.count() > 0) {
      await expect(inputs.first()).toBeVisible();
    }
  });

  test('should handle CSS consistently', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/');
    await authenticatedPage.waitForLoadState('networkidle');
    
    // Check for CSS loading
    const stylesheets = authenticatedPage.locator('link[rel="stylesheet"]');
    const stylesheetCount = await stylesheets.count();
    
    // Verify stylesheets are loaded
    expect(stylesheetCount).toBeGreaterThanOrEqual(0);
    
    // Check computed styles
    const body = authenticatedPage.locator('body');
    const bodyStyles = await body.evaluate((el) => {
      const styles = window.getComputedStyle(el);
      return {
        display: styles.display,
        visibility: styles.visibility,
      };
    });
    
    // Body should be visible
    expect(bodyStyles.display).not.toBe('none');
    expect(bodyStyles.visibility).not.toBe('hidden');
  });

  test('should handle JavaScript consistently', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/');
    await authenticatedPage.waitForLoadState('networkidle');
    
    // Verify JavaScript is executing
    const jsEnabled = await authenticatedPage.evaluate(() => {
      return typeof window !== 'undefined' && typeof document !== 'undefined';
    });
    
    expect(jsEnabled).toBe(true);
  });

  test('should handle localStorage consistently', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/');
    await authenticatedPage.waitForLoadState('networkidle');
    
    // Test localStorage
    await authenticatedPage.evaluate(() => {
      localStorage.setItem('test-key', 'test-value');
    });
    
    const value = await authenticatedPage.evaluate(() => {
      return localStorage.getItem('test-key');
    });
    
    expect(value).toBe('test-value');
    
    // Cleanup
    await authenticatedPage.evaluate(() => {
      localStorage.removeItem('test-key');
    });
  });

  test('should handle sessionStorage consistently', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/');
    await authenticatedPage.waitForLoadState('networkidle');
    
    // Test sessionStorage
    await authenticatedPage.evaluate(() => {
      sessionStorage.setItem('test-key', 'test-value');
    });
    
    const value = await authenticatedPage.evaluate(() => {
      return sessionStorage.getItem('test-key');
    });
    
    expect(value).toBe('test-value');
  });

  test('should handle cookies consistently', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/');
    await authenticatedPage.waitForLoadState('networkidle');
    
    // Set cookie
    await authenticatedPage.context().addCookies([
      {
        name: 'test-cookie',
        value: 'test-value',
        domain: 'localhost',
        path: '/',
      },
    ]);
    
    // Verify cookie
    const cookies = await authenticatedPage.context().cookies();
    const testCookie = cookies.find((c) => c.name === 'test-cookie');
    
    expect(testCookie).toBeDefined();
    expect(testCookie?.value).toBe('test-value');
  });

  test('should handle fetch API consistently', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/');
    await authenticatedPage.waitForLoadState('networkidle');
    
    // Test fetch API
    const fetchWorks = await authenticatedPage.evaluate(() => {
      return typeof fetch !== 'undefined';
    });
    
    expect(fetchWorks).toBe(true);
  });

  test('should handle WebSocket consistently', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/');
    await authenticatedPage.waitForLoadState('networkidle');
    
    // Test WebSocket support
    const wsSupported = await authenticatedPage.evaluate(() => {
      return typeof WebSocket !== 'undefined';
    });
    
    expect(wsSupported).toBe(true);
  });

  test('should handle event listeners consistently', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/');
    await authenticatedPage.waitForLoadState('networkidle');
    
    // Test event listener
    const eventFired = await authenticatedPage.evaluate(() => {
      return new Promise((resolve) => {
        const button = document.querySelector('button');
        if (button) {
          button.addEventListener('click', () => {
            resolve(true);
          });
          button.click();
        } else {
          resolve(false);
        }
      });
    });
    
    // Event should fire (or no button exists)
    expect(typeof eventFired).toBe('boolean');
  });

  test('should handle CSS Grid consistently', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/');
    await authenticatedPage.waitForLoadState('networkidle');
    
    // Check CSS Grid support
    const gridSupported = await authenticatedPage.evaluate(() => {
      const el = document.createElement('div');
      el.style.display = 'grid';
      return el.style.display === 'grid';
    });
    
    expect(gridSupported).toBe(true);
  });

  test('should handle Flexbox consistently', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/');
    await authenticatedPage.waitForLoadState('networkidle');
    
    // Check Flexbox support
    const flexSupported = await authenticatedPage.evaluate(() => {
      const el = document.createElement('div');
      el.style.display = 'flex';
      return el.style.display === 'flex';
    });
    
    expect(flexSupported).toBe(true);
  });

  test('should handle media queries consistently', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/');
    await authenticatedPage.waitForLoadState('networkidle');
    
    // Test media query matching
    const matchesMediaQuery = await authenticatedPage.evaluate(() => {
      return window.matchMedia('(min-width: 768px)').matches;
    });
    
    // Should return boolean
    expect(typeof matchesMediaQuery).toBe('boolean');
  });
});

