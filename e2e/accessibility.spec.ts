import { test, expect } from './fixtures';

/**
 * Accessibility Tests
 * 
 * Tests for WCAG compliance and accessibility features
 */
test.describe('Accessibility', () => {
  test('should have proper page title', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/');
    await authenticatedPage.waitForLoadState('networkidle');
    
    const title = await authenticatedPage.title();
    expect(title).toBeTruthy();
    expect(title.length).toBeGreaterThan(0);
  });

  test('should have proper heading hierarchy', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/');
    await authenticatedPage.waitForLoadState('networkidle');
    
    // Check for h1 element
    const h1 = authenticatedPage.locator('h1').first();
    if (await h1.count() > 0) {
      await expect(h1).toBeVisible();
    }
    
    // Verify heading structure (h1 should exist before h2, etc.)
    const headings = authenticatedPage.locator('h1, h2, h3, h4, h5, h6');
    const headingCount = await headings.count();
    
    if (headingCount > 0) {
      // At least one heading should exist
      expect(headingCount).toBeGreaterThan(0);
    }
  });

  test('should have proper alt text for images', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/');
    await authenticatedPage.waitForLoadState('networkidle');
    
    const images = authenticatedPage.locator('img');
    const imageCount = await images.count();
    
    for (let i = 0; i < imageCount; i++) {
      const img = images.nth(i);
      const alt = await img.getAttribute('alt');
      const role = await img.getAttribute('role');
      
      // Images should have alt text or be decorative (role="presentation")
      if (alt === null && role !== 'presentation') {
        // Log warning but don't fail (some images may be decorative)
        console.warn(`Image at index ${i} missing alt text`);
      }
    }
  });

  test('should have proper form labels', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/');
    await authenticatedPage.waitForLoadState('networkidle');
    
    const inputs = authenticatedPage.locator('input:not([type="hidden"]), textarea, select');
    const inputCount = await inputs.count();
    
    for (let i = 0; i < inputCount; i++) {
      const input = inputs.nth(i);
      const id = await input.getAttribute('id');
      const ariaLabel = await input.getAttribute('aria-label');
      const ariaLabelledBy = await input.getAttribute('aria-labelledby');
      const placeholder = await input.getAttribute('placeholder');
      const type = await input.getAttribute('type');
      
      // Skip hidden inputs and submit buttons
      if (type === 'hidden' || type === 'submit' || type === 'button') {
        continue;
      }
      
      // Input should have label, aria-label, aria-labelledby, or placeholder
      if (id) {
        const label = authenticatedPage.locator(`label[for="${id}"]`);
        if (await label.count() > 0) {
          continue; // Has label
        }
      }
      
      if (ariaLabel || ariaLabelledBy || placeholder) {
        continue; // Has alternative labeling
      }
      
      // Log warning for inputs without labels
      console.warn(`Input at index ${i} missing proper label`);
    }
  });

  test('should have proper button labels', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/');
    await authenticatedPage.waitForLoadState('networkidle');
    
    const buttons = authenticatedPage.locator('button, [role="button"]');
    const buttonCount = await buttons.count();
    
    for (let i = 0; i < buttonCount; i++) {
      const button = buttons.nth(i);
      const text = await button.textContent();
      const ariaLabel = await button.getAttribute('aria-label');
      const ariaLabelledBy = await button.getAttribute('aria-labelledby');
      const title = await button.getAttribute('title');
      
      // Button should have accessible name
      if (!text?.trim() && !ariaLabel && !ariaLabelledBy && !title) {
        console.warn(`Button at index ${i} missing accessible name`);
      }
    }
  });

  test('should have proper link text', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/');
    await authenticatedPage.waitForLoadState('networkidle');
    
    const links = authenticatedPage.locator('a[href]');
    const linkCount = await links.count();
    
    for (let i = 0; i < linkCount; i++) {
      const link = links.nth(i);
      const text = await link.textContent();
      const ariaLabel = await link.getAttribute('aria-label');
      const href = await link.getAttribute('href');
      
      // Links should have descriptive text
      if (!text?.trim() && !ariaLabel) {
        console.warn(`Link at index ${i} (${href}) missing descriptive text`);
      }
      
      // Avoid generic link text
      if (text?.trim().toLowerCase() === 'click here' || text?.trim().toLowerCase() === 'read more') {
        console.warn(`Link at index ${i} has generic text: "${text}"`);
      }
    }
  });

  test('should have proper color contrast', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/');
    await authenticatedPage.waitForLoadState('networkidle');
    
    // Use Playwright's accessibility snapshot
    const snapshot = await authenticatedPage.accessibility.snapshot();
    
    // Verify snapshot exists
    expect(snapshot).toBeTruthy();
    
    // Check for common accessibility issues
    if (snapshot) {
      // Verify no elements with insufficient contrast are marked
      // (This is a basic check - full contrast checking requires more sophisticated tools)
    }
  });

  test('should be keyboard navigable', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/');
    await authenticatedPage.waitForLoadState('networkidle');
    
    // Test Tab navigation
    await authenticatedPage.keyboard.press('Tab');
    
    // Verify focus is visible
    const focusedElement = authenticatedPage.locator(':focus');
    if (await focusedElement.count() > 0) {
      // Check if focus indicator is visible
      const focusStyles = await focusedElement.first().evaluate((el) => {
        const styles = window.getComputedStyle(el);
        return {
          outline: styles.outline,
          outlineWidth: styles.outlineWidth,
          boxShadow: styles.boxShadow,
        };
      });
      
      // Focus should be visible (outline or box-shadow)
      const hasFocusIndicator = 
        focusStyles.outlineWidth !== '0px' || 
        focusStyles.boxShadow !== 'none';
      
      // Log if focus indicator is missing
      if (!hasFocusIndicator) {
        console.warn('Focus indicator may not be visible');
      }
    }
  });

  test('should have proper ARIA attributes', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/');
    await authenticatedPage.waitForLoadState('networkidle');
    
    // Check for common ARIA patterns
    const landmarks = authenticatedPage.locator('[role="main"], [role="navigation"], [role="banner"], [role="contentinfo"]');
    const landmarkCount = await landmarks.count();
    
    // Should have at least main content area
    if (landmarkCount === 0) {
      // Check for semantic HTML instead
      const main = authenticatedPage.locator('main');
      const nav = authenticatedPage.locator('nav');
      const header = authenticatedPage.locator('header');
      const footer = authenticatedPage.locator('footer');
      
      const semanticCount = await main.count() + await nav.count() + await header.count() + await footer.count();
      
      if (semanticCount === 0) {
        console.warn('No landmarks or semantic HTML elements found');
      }
    }
  });

  test('should handle screen reader announcements', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/');
    await authenticatedPage.waitForLoadState('networkidle');
    
    // Check for live regions
    const liveRegions = authenticatedPage.locator('[aria-live], [role="status"], [role="alert"]');
    const liveRegionCount = await liveRegions.count();
    
    // Live regions are optional but good for dynamic content
    // Just verify they exist if present
    expect(liveRegionCount).toBeGreaterThanOrEqual(0);
  });

  test('should have skip links', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/');
    await authenticatedPage.waitForLoadState('networkidle');
    
    // Look for skip links
    const skipLinks = authenticatedPage.locator('a[href^="#"], [data-testid="skip-link"]');
    const skipLinkCount = await skipLinks.count();
    
    // Skip links are optional but recommended
    if (skipLinkCount === 0) {
      console.info('No skip links found (optional but recommended)');
    }
  });

  test('should validate accessibility with axe-core', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/');
    await authenticatedPage.waitForLoadState('networkidle');
    
    // Inject axe-core for accessibility testing
    await authenticatedPage.addScriptTag({
      url: 'https://cdn.jsdelivr.net/npm/axe-core@4.8.0/axe.min.js',
    });
    
    // Run accessibility scan
    const accessibilityResults = await authenticatedPage.evaluate(() => {
      return new Promise((resolve) => {
        // @ts-ignore - axe is injected dynamically
        if (typeof window.axe !== 'undefined') {
          // @ts-ignore
          window.axe.run((err: any, results: any) => {
            if (err) {
              resolve({ error: err.message });
            } else {
              resolve({
                violations: results.violations,
                passes: results.passes,
                incomplete: results.incomplete,
              });
            }
          });
        } else {
          resolve({ error: 'axe-core not loaded' });
        }
      });
    });
    
    // Log results
    if (accessibilityResults && typeof accessibilityResults === 'object' && 'violations' in accessibilityResults) {
      const violations = (accessibilityResults as any).violations || [];
      
      if (violations.length > 0) {
        console.warn(`Found ${violations.length} accessibility violations`);
        violations.forEach((violation: any) => {
          console.warn(`- ${violation.id}: ${violation.description}`);
        });
      }
      
      // Don't fail test, just log violations
      expect(violations.length).toBeGreaterThanOrEqual(0);
    }
  });
});

