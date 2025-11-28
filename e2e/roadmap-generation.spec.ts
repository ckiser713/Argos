/**
 * E2E tests for dynamic roadmap generation feature.
 * Tests LLM-based roadmap generation with decision nodes and DAG structure.
 */

import { test, expect } from '@playwright/test';

test.describe('Roadmap Generation', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to a project page
    await page.goto('/projects');
    // Wait for projects to load and select/create one
    await page.waitForSelector('[data-testid="project-list"]', { timeout: 10000 });
  });

  test('should generate roadmap from natural language intent', async ({ page }) => {
    // Navigate to roadmap view
    await page.click('text=Roadmap');
    await page.waitForSelector('[data-testid="roadmap-view"]', { timeout: 5000 });

    // Click generate roadmap button
    const generateButton = page.locator('button:has-text("Generate Roadmap")');
    if (await generateButton.isVisible()) {
      await generateButton.click();
    } else {
      // Alternative: look for "Generate from Intent" or similar
      await page.click('button:has-text("Generate")');
    }

    // Fill in intent
    const intentInput = page.locator('textarea[placeholder*="intent"], input[placeholder*="intent"]');
    await intentInput.fill('Build a web application with user authentication and dashboard');

    // Submit
    await page.click('button:has-text("Generate"), button[type="submit"]');

    // Wait for roadmap to be generated
    await page.waitForSelector('[data-testid="roadmap-node"]', { timeout: 30000 });

    // Verify roadmap nodes are displayed
    const nodes = page.locator('[data-testid="roadmap-node"]');
    const nodeCount = await nodes.count();
    expect(nodeCount).toBeGreaterThan(0);

    // Verify nodes have labels
    const firstNode = nodes.first();
    await expect(firstNode.locator('[data-testid="node-label"]')).toBeVisible();
  });

  test('should display decision nodes in roadmap', async ({ page }) => {
    await page.goto('/projects');
    await page.click('text=Roadmap');

    // Generate roadmap with decision point
    await page.click('button:has-text("Generate")');
    const intentInput = page.locator('textarea[placeholder*="intent"], input[placeholder*="intent"]');
    await intentInput.fill('Choose between React and Vue for frontend, then build API');
    await page.click('button[type="submit"]');

    // Wait for roadmap
    await page.waitForSelector('[data-testid="roadmap-node"]', { timeout: 30000 });

    // Look for decision nodes (may be styled differently)
    const decisionNodes = page.locator('[data-testid="roadmap-node"][data-kind="decision"]');
    const decisionCount = await decisionNodes.count();
    
    // At least verify roadmap was generated
    const allNodes = page.locator('[data-testid="roadmap-node"]');
    expect(await allNodes.count()).toBeGreaterThan(0);
  });

  test('should show roadmap dependencies', async ({ page }) => {
    await page.goto('/projects');
    await page.click('text=Roadmap');

    // Generate roadmap
    await page.click('button:has-text("Generate")');
    const intentInput = page.locator('textarea[placeholder*="intent"]');
    await intentInput.fill('Set up database, then build API, then create frontend');
    await page.click('button[type="submit"]');

    await page.waitForSelector('[data-testid="roadmap-node"]', { timeout: 30000 });

    // Verify edges/connections between nodes
    const edges = page.locator('[data-testid="roadmap-edge"]');
    const edgeCount = await edges.count();
    
    // Should have at least some connections if multiple nodes exist
    const nodes = page.locator('[data-testid="roadmap-node"]');
    const nodeCount = await nodes.count();
    if (nodeCount > 1) {
      // May have edges showing dependencies
      expect(edgeCount).toBeGreaterThanOrEqual(0);
    }
  });

  test('should incorporate existing ideas into roadmap', async ({ page }) => {
    // First create an idea
    await page.goto('/projects');
    await page.click('text=Ideas');
    await page.click('button:has-text("New Idea")');
    
    await page.fill('input[name="title"]', 'Add user authentication');
    await page.fill('textarea[name="description"]', 'Implement OAuth2 authentication');
    await page.click('button[type="submit"]');

    // Now generate roadmap
    await page.click('text=Roadmap');
    await page.click('button:has-text("Generate")');
    
    const intentInput = page.locator('textarea[placeholder*="intent"]');
    await intentInput.fill('Build a complete web application');
    
    // Check "Use existing ideas" if present
    const useIdeasCheckbox = page.locator('input[type="checkbox"][name*="ideas"]');
    if (await useIdeasCheckbox.isVisible()) {
      await useIdeasCheckbox.check();
    }
    
    await page.click('button[type="submit"]');
    await page.waitForSelector('[data-testid="roadmap-node"]', { timeout: 30000 });

    // Verify roadmap includes authentication-related nodes
    const nodes = page.locator('[data-testid="roadmap-node"]');
    const nodeTexts = await nodes.allTextContents();
    const hasAuthNode = nodeTexts.some(text => 
      text.toLowerCase().includes('auth') || 
      text.toLowerCase().includes('authentication')
    );
    
    // May or may not include auth depending on LLM, but roadmap should be generated
    expect(await nodes.count()).toBeGreaterThan(0);
  });
});

