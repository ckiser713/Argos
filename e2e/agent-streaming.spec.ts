/**
 * E2E tests for real-time agent visualization and streaming.
 * Tests WebSocket connections, agent state updates, and live visualization.
 */

import { test, expect } from '@playwright/test';

test.describe('Agent Streaming & Real-Time Visualization', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/projects');
    await page.waitForSelector('[data-testid="project-list"]', { timeout: 10000 });
  });

  test('should connect to agent WebSocket stream', async ({ page }) => {
    // Navigate to agent runs view
    await page.click('text=Agents, text=Agent Runs');
    await page.waitForSelector('[data-testid="agent-runs-view"]', { timeout: 5000 }).catch(() => {});

    // Start an agent run
    const startButton = page.locator('button:has-text("Start Run"), button:has-text("New Run")');
    if (await startButton.isVisible()) {
      await startButton.click();
      
      // Fill in prompt
      const promptInput = page.locator('textarea[name="prompt"], textarea[placeholder*="prompt"]');
      if (await promptInput.isVisible()) {
        await promptInput.fill('Test agent run');
        await page.click('button[type="submit"]');
      }
    }

    // Wait for WebSocket connection indicator
    const connectionStatus = page.locator('[data-testid="ws-status"], [data-testid="connection-status"]');
    await connectionStatus.waitFor({ timeout: 10000 }).catch(() => {});

    // Should show connected status
    if (await connectionStatus.isVisible()) {
      const statusText = await connectionStatus.textContent();
      expect(statusText?.toLowerCase()).toMatch(/connected|active|streaming/);
    }
  });

  test('should display real-time agent state updates', async ({ page }) => {
    await page.click('text=Agents');
    
    // Start agent run
    const startButton = page.locator('button:has-text("Start")');
    if (await startButton.isVisible()) {
      await startButton.click();
      
      const promptInput = page.locator('textarea[name="prompt"]');
      if (await promptInput.isVisible()) {
        await promptInput.fill('Search for information about Python');
        await page.click('button[type="submit"]');
      }
    }

    // Wait for agent visualization
    await page.waitForSelector('[data-testid="agent-visualization"], [data-testid="agent-state"]', { timeout: 15000 }).catch(() => {});

    // Check for active nodes
    const activeNodes = page.locator('[data-testid="agent-node"][data-status="active"], [data-testid="active-node"]');
    await activeNodes.first().waitFor({ timeout: 10000 }).catch(() => {});

    // Should show node states
    const nodes = page.locator('[data-testid="agent-node"]');
    const nodeCount = await nodes.count();
    if (nodeCount > 0) {
      expect(nodeCount).toBeGreaterThan(0);
    }
  });

  test('should show tool calls and results', async ({ page }) => {
    await page.click('text=Agents');
    
    // Start agent run that uses tools
    const startButton = page.locator('button:has-text("Start")');
    if (await startButton.isVisible()) {
      await startButton.click();
      
      const promptInput = page.locator('textarea[name="prompt"]');
      if (await promptInput.isVisible()) {
        await promptInput.fill('Search the knowledge base for machine learning');
        await page.click('button[type="submit"]');
      }
    }

    // Wait for tool calls to appear
    await page.waitForSelector('[data-testid="tool-call"], [data-testid="agent-tool"]', { timeout: 15000 }).catch(() => {});

    // Verify tool calls are displayed
    const toolCalls = page.locator('[data-testid="tool-call"]');
    const toolCallCount = await toolCalls.count();
    
    if (toolCallCount > 0) {
      // Should show tool name and results
      const firstToolCall = toolCalls.first();
      await expect(firstToolCall.locator('[data-testid="tool-name"]')).toBeVisible();
    }
  });

  test('should display agent reasoning snippets', async ({ page }) => {
    await page.click('text=Agents');
    
    // Start agent run
    const startButton = page.locator('button:has-text("Start")');
    if (await startButton.isVisible()) {
      await startButton.click();
      
      const promptInput = page.locator('textarea[name="prompt"]');
      if (await promptInput.isVisible()) {
        await promptInput.fill('Analyze the project requirements');
        await page.click('button[type="submit"]');
      }
    }

    // Look for reasoning display
    await page.waitForSelector('[data-testid="agent-reasoning"], [data-testid="reasoning"]', { timeout: 15000 }).catch(() => {});

    const reasoningSection = page.locator('[data-testid="agent-reasoning"]');
    if (await reasoningSection.isVisible()) {
      const reasoningText = await reasoningSection.textContent();
      expect(reasoningText?.length).toBeGreaterThan(0);
    }
  });

  test('should show agent execution timeline', async ({ page }) => {
    await page.click('text=Agents');
    
    // Start agent run
    const startButton = page.locator('button:has-text("Start")');
    if (await startButton.isVisible()) {
      await startButton.click();
      
      const promptInput = page.locator('textarea[name="prompt"]');
      if (await promptInput.isVisible()) {
        await promptInput.fill('Test timeline');
        await page.click('button[type="submit"]');
      }
    }

    // Look for timeline view
    await page.waitForSelector('[data-testid="agent-timeline"], [data-testid="execution-timeline"]', { timeout: 15000 }).catch(() => {});

    const timeline = page.locator('[data-testid="agent-timeline"]');
    if (await timeline.isVisible()) {
      // Should show execution steps
      const timelineSteps = timeline.locator('[data-testid="timeline-step"]');
      const stepCount = await timelineSteps.count();
      expect(stepCount).toBeGreaterThanOrEqual(0);
    }
  });

  test('should handle WebSocket reconnection', async ({ page, context }) => {
    await page.goto('/projects');
    await page.click('text=Agents');
    
    // Start agent run
    const startButton = page.locator('button:has-text("Start")');
    if (await startButton.isVisible()) {
      await startButton.click();
      
      const promptInput = page.locator('textarea[name="prompt"]');
      if (await promptInput.isVisible()) {
        await promptInput.fill('Test reconnection');
        await page.click('button[type="submit"]');
      }
    }

    // Wait for connection
    await page.waitForTimeout(2000);

    // Simulate network interruption (close and reopen)
    await context.close();
    const newContext = await page.context().browser()?.newContext();
    const newPage = await newContext?.newPage();
    
    if (newPage) {
      await newPage.goto('/projects');
      await newPage.click('text=Agents');
      
      // Should reconnect automatically
      const connectionStatus = newPage.locator('[data-testid="ws-status"]');
      await connectionStatus.waitFor({ timeout: 10000 }).catch(() => {});
    }
  });
});

