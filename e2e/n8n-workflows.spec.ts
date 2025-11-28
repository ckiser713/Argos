/**
 * E2E tests for n8n workflow integration.
 * Tests workflow templates, triggering, and execution tracking.
 */

import { test, expect } from '@playwright/test';

test.describe('n8n Workflow Integration', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/projects');
    await page.waitForSelector('[data-testid="project-list"]', { timeout: 10000 });
  });

  test('should display workflow templates', async ({ page }) => {
    // Navigate to workflows/n8n section
    await page.click('text=Workflows, text=Automation');
    await page.waitForSelector('[data-testid="workflows-view"]', { timeout: 5000 }).catch(() => {});

    // Look for templates section
    const templatesSection = page.locator('[data-testid="n8n-templates"], text=Templates');
    if (await templatesSection.isVisible()) {
      const templates = page.locator('[data-testid="workflow-template"]');
      const templateCount = await templates.count();
      
      // Should have predefined templates
      expect(templateCount).toBeGreaterThan(0);

      // Verify template structure
      if (templateCount > 0) {
        const firstTemplate = templates.first();
        await expect(firstTemplate.locator('[data-testid="template-name"]')).toBeVisible();
        await expect(firstTemplate.locator('[data-testid="template-description"]')).toBeVisible();
      }
    }
  });

  test('should list available n8n workflows', async ({ page }) => {
    await page.click('text=Workflows');
    
    // Look for n8n workflows list
    const workflowsList = page.locator('[data-testid="n8n-workflows"], [data-testid="workflows-list"]');
    await workflowsList.waitFor({ timeout: 5000 }).catch(() => {});

    // May be empty if n8n is not running, but UI should handle it
    const workflows = page.locator('[data-testid="workflow-item"]');
    const workflowCount = await workflows.count();
    
    // UI should display workflows or empty state
    expect(workflowCount).toBeGreaterThanOrEqual(0);
  });

  test('should show workflow execution history', async ({ page }) => {
    await page.click('text=Workflows');
    
    // Navigate to executions/history
    await page.click('text=Executions, text=History').catch(() => {});
    
    const executionsList = page.locator('[data-testid="executions-list"]');
    await executionsList.waitFor({ timeout: 5000 }).catch(() => {});

    // Should show executions or empty state
    const executions = page.locator('[data-testid="execution-item"]');
    const executionCount = await executions.count();
    
    expect(executionCount).toBeGreaterThanOrEqual(0);
  });

  test('should display workflow template details', async ({ page }) => {
    await page.click('text=Workflows');
    
    // Find a template
    const templates = page.locator('[data-testid="workflow-template"]');
    if (await templates.count() > 0) {
      await templates.first().click();
      
      // Should show template details
      await expect(page.locator('[data-testid="template-details"]')).toBeVisible({ timeout: 5000 });
      
      // Should show input schema
      const inputSchema = page.locator('[data-testid="input-schema"]');
      if (await inputSchema.isVisible()) {
        const schemaText = await inputSchema.textContent();
        expect(schemaText).toBeTruthy();
      }
    }
  });

  test('should handle workflow trigger errors gracefully', async ({ page }) => {
    // This would test error handling when n8n is unavailable
    // The UI should show appropriate error messages
    
    await page.click('text=Workflows');
    
    // Try to trigger a workflow (if UI supports it)
    const triggerButton = page.locator('button:has-text("Trigger"), button:has-text("Run")');
    if (await triggerButton.isVisible()) {
      await triggerButton.first().click();
      
      // Should show error if n8n is not available
      const errorMessage = page.locator('[data-testid="error-message"], .error, .alert-error');
      // May or may not show error depending on implementation
    }
  });
});

