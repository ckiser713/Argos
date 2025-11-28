import type { Page, Locator } from '@playwright/test';

/**
 * UI Test Helpers
 * 
 * Utility functions for UI testing and interactions
 */

export class UIHelpers {
  constructor(private page: Page) {}

  /**
   * Navigate to a specific tab/page
   */
  async navigateToTab(tabLabel: string) {
    const navItem = this.page.locator('nav').getByText(tabLabel);
    await navItem.click();
    await this.page.waitForTimeout(500); // Wait for navigation
  }

  /**
   * Wait for page to be fully loaded
   */
  async waitForPageLoad() {
    await this.page.waitForLoadState('networkidle');
  }

  /**
   * Toggle sidebar collapse/expand
   */
  async toggleSidebar() {
    const toggleButton = this.page.locator('button[aria-label="Toggle Sidebar"]');
    await toggleButton.click();
    await this.page.waitForTimeout(300);
  }

  /**
   * Check if sidebar is collapsed
   */
  async isSidebarCollapsed(): Promise<boolean> {
    const missionControlLabel = this.page.locator('nav').getByText('Mission Control');
    return !(await missionControlLabel.isVisible().catch(() => false));
  }

  /**
   * Wait for element to be visible with timeout
   */
  async waitForElement(selector: string, timeout: number = 5000): Promise<Locator> {
    const element = this.page.locator(selector);
    await element.waitFor({ state: 'visible', timeout });
    return element;
  }

  /**
   * Wait for text to appear
   */
  async waitForText(text: string, timeout: number = 5000) {
    await this.page.waitForSelector(`text=${text}`, { timeout });
  }

  /**
   * Click button by text
   */
  async clickButton(text: string) {
    const button = this.page.getByRole('button', { name: text });
    await button.click();
    await this.page.waitForTimeout(300);
  }

  /**
   * Fill form input by label
   */
  async fillInput(label: string, value: string) {
    const input = this.page.getByLabel(label);
    await input.fill(value);
  }

  /**
   * Submit form
   */
  async submitForm() {
    const submitButton = this.page.getByRole('button', { name: /submit|save|create/i });
    await submitButton.click();
    await this.page.waitForTimeout(500);
  }

  /**
   * Check if element contains text
   */
  async elementContainsText(selector: string, text: string): Promise<boolean> {
    const element = this.page.locator(selector);
    const content = await element.textContent();
    return content?.includes(text) ?? false;
  }

  /**
   * Get all navigation items
   */
  async getNavigationItems(): Promise<string[]> {
    const nav = this.page.locator('nav');
    const items = await nav.locator('*').allTextContents();
    return items.filter(item => item.trim().length > 0);
  }

  /**
   * Wait for API call to complete (by waiting for network idle)
   */
  async waitForAPICall() {
    await this.page.waitForLoadState('networkidle');
  }

  /**
   * Check if page is in error state
   */
  async isErrorState(): Promise<boolean> {
    const errorSelectors = [
      '[class*="error"]',
      '[class*="Error"]',
      'text=/error/i',
      'text=/failed/i',
    ];

    for (const selector of errorSelectors) {
      const element = this.page.locator(selector).first();
      if (await element.isVisible().catch(() => false)) {
        return true;
      }
    }

    return false;
  }

  /**
   * Check if page is in loading state
   */
  async isLoadingState(): Promise<boolean> {
    const loadingSelectors = [
      '[class*="loading"]',
      '[class*="Loading"]',
      '[class*="spinner"]',
      'text=/loading/i',
    ];

    for (const selector of loadingSelectors) {
      const element = this.page.locator(selector).first();
      if (await element.isVisible().catch(() => false)) {
        return true;
      }
    }

    return false;
  }

  /**
   * Wait for loading to complete
   */
  async waitForLoadingComplete(timeout: number = 10000) {
    const startTime = Date.now();
    while (await this.isLoadingState() && (Date.now() - startTime) < timeout) {
      await this.page.waitForTimeout(200);
    }
  }

  /**
   * Take screenshot with name
   */
  async takeScreenshot(name: string) {
    await this.page.screenshot({ path: `test-results/screenshots/${name}.png` });
  }

  /**
   * Check if element is visible
   */
  async isVisible(selector: string): Promise<boolean> {
    const element = this.page.locator(selector);
    return await element.isVisible().catch(() => false);
  }

  /**
   * Get text content of element
   */
  async getText(selector: string): Promise<string | null> {
    const element = this.page.locator(selector);
    return await element.textContent();
  }

  /**
   * Scroll to element
   */
  async scrollTo(selector: string) {
    const element = this.page.locator(selector);
    await element.scrollIntoViewIfNeeded();
  }

  /**
   * Wait for navigation to complete
   */
  async waitForNavigation() {
    await this.page.waitForLoadState('networkidle');
    await this.page.waitForTimeout(300);
  }
}


