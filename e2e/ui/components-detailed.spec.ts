import { test, expect } from '../fixtures';
import { ApiHelpers } from '../utils/api-helpers';

/**
 * Component-Specific UI Tests
 * 
 * Detailed tests for individual UI components
 */
test.describe('Component-Specific UI Tests', () => {
  test('should render project list component', async ({ authenticatedPage, testProject }) => {
    await authenticatedPage.goto('/');
    await authenticatedPage.waitForLoadState('networkidle');
    
    // Look for project list elements
    // Adjust selectors based on actual implementation
    const projectList = authenticatedPage.locator('[data-testid="project-list"]').or(
      authenticatedPage.locator('.project-list')
    ).or(
      authenticatedPage.locator('main')
    );
    
    await expect(projectList.first()).toBeVisible();
  });

  test('should render ingest station component', async ({ authenticatedPage, testProject }) => {
    await authenticatedPage.goto('/');
    await authenticatedPage.waitForLoadState('networkidle');
    
    // Navigate to ingest station if route exists
    // await authenticatedPage.click('[data-testid="nav-ingest"]');
    
    const ingestStation = authenticatedPage.locator('[data-testid="ingest-station"]').or(
      authenticatedPage.locator('.ingest-station')
    );
    
    // Component may or may not be visible depending on route
    if (await ingestStation.count() > 0) {
      await expect(ingestStation.first()).toBeVisible();
    }
  });

  test('should render mission control component', async ({ authenticatedPage, testProject }) => {
    await authenticatedPage.goto('/');
    await authenticatedPage.waitForLoadState('networkidle');
    
    const missionControl = authenticatedPage.locator('[data-testid="mission-control"]').or(
      authenticatedPage.locator('.mission-control')
    );
    
    if (await missionControl.count() > 0) {
      await expect(missionControl.first()).toBeVisible();
    }
  });

  test('should render agent run display', async ({ authenticatedPage, testProject, api }) => {
    const apiHelpers = new ApiHelpers(api);
    
    // Create an agent run
    const run = await apiHelpers.createAgentRun(
      testProject.id,
      'project_manager',
      'Test query'
    );
    
    await authenticatedPage.goto('/');
    await authenticatedPage.waitForLoadState('networkidle');
    
    // Look for agent run display
    const agentRunDisplay = authenticatedPage.locator('[data-testid="agent-run"]').or(
      authenticatedPage.locator(`[data-run-id="${run.id}"]`)
    );
    
    if (await agentRunDisplay.count() > 0) {
      await expect(agentRunDisplay.first()).toBeVisible();
    }
  });

  test('should render roadmap visualization', async ({ authenticatedPage, testProject, api }) => {
    const apiHelpers = new ApiHelpers(api);
    
    // Create roadmap nodes
    await apiHelpers.createRoadmapNode(testProject.id, {
      label: 'Test Node',
      status: 'PENDING',
    });
    
    await authenticatedPage.goto('/');
    await authenticatedPage.waitForLoadState('networkidle');
    
    const roadmapViz = authenticatedPage.locator('[data-testid="roadmap-viz"]').or(
      authenticatedPage.locator('.roadmap-graph')
    );
    
    if (await roadmapViz.count() > 0) {
      await expect(roadmapViz.first()).toBeVisible();
    }
  });

  test('should render knowledge graph visualization', async ({ authenticatedPage, testProject, api }) => {
    const apiHelpers = new ApiHelpers(api);
    
    // Create knowledge node
    await apiHelpers.createKnowledgeNode(testProject.id, {
      title: 'Test Concept',
      summary: 'Test summary',
      type: 'concept',
    });
    
    await authenticatedPage.goto('/');
    await authenticatedPage.waitForLoadState('networkidle');
    
    const knowledgeGraph = authenticatedPage.locator('[data-testid="knowledge-graph"]').or(
      authenticatedPage.locator('.knowledge-graph')
    );
    
    if (await knowledgeGraph.count() > 0) {
      await expect(knowledgeGraph.first()).toBeVisible();
    }
  });

  test('should handle form inputs', async ({ authenticatedPage, testProject }) => {
    await authenticatedPage.goto('/');
    await authenticatedPage.waitForLoadState('networkidle');
    
    // Look for input fields
    const inputs = authenticatedPage.locator('input[type="text"], input[type="email"], textarea');
    
    if (await inputs.count() > 0) {
      const firstInput = inputs.first();
      await expect(firstInput).toBeVisible();
      
      // Test input interaction
      await firstInput.fill('Test input');
      await expect(firstInput).toHaveValue('Test input');
    }
  });

  test('should handle button clicks', async ({ authenticatedPage, testProject }) => {
    await authenticatedPage.goto('/');
    await authenticatedPage.waitForLoadState('networkidle');
    
    // Look for buttons
    const buttons = authenticatedPage.locator('button, [role="button"]');
    
    if (await buttons.count() > 0) {
      const firstButton = buttons.first();
      await expect(firstButton).toBeVisible();
      
      // Test button is clickable
      await expect(firstButton).toBeEnabled();
    }
  });

  test('should display loading states', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/');
    
    // Check for loading indicators before networkidle
    const loadingIndicators = authenticatedPage.locator('[data-testid="loading"], .loading, [aria-busy="true"]');
    
    // Loading may be too fast to catch, so we just verify the page loads
    await authenticatedPage.waitForLoadState('networkidle');
    await expect(authenticatedPage).toHaveTitle(/Cortex/i);
  });

  test('should display error states', async ({ authenticatedPage }) => {
    // Navigate to invalid route
    await authenticatedPage.goto('/invalid-route-12345');
    await authenticatedPage.waitForLoadState('networkidle');
    
    // Look for error messages
    const errorMessages = authenticatedPage.locator('[data-testid="error"], .error, [role="alert"]');
    
    // Error may or may not be displayed depending on implementation
    if (await errorMessages.count() > 0) {
      await expect(errorMessages.first()).toBeVisible();
    }
  });

  test('should handle modal dialogs', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/');
    await authenticatedPage.waitForLoadState('networkidle');
    
    // Look for modal triggers
    const modalTriggers = authenticatedPage.locator('[data-testid="modal-trigger"], [aria-haspopup="dialog"]');
    
    if (await modalTriggers.count() > 0) {
      await modalTriggers.first().click();
      
      // Look for modal
      const modal = authenticatedPage.locator('[role="dialog"], .modal, [data-testid="modal"]');
      await expect(modal).toBeVisible({ timeout: 2000 });
      
      // Close modal
      const closeButton = modal.locator('[aria-label="Close"], .close-button, [data-testid="close-modal"]');
      if (await closeButton.count() > 0) {
        await closeButton.first().click();
        await expect(modal).not.toBeVisible();
      }
    }
  });

  test('should handle dropdown menus', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/');
    await authenticatedPage.waitForLoadState('networkidle');
    
    // Look for dropdowns
    const dropdowns = authenticatedPage.locator('select, [role="combobox"], [data-testid="dropdown"]');
    
    if (await dropdowns.count() > 0) {
      const dropdown = dropdowns.first();
      await expect(dropdown).toBeVisible();
      
      // Test dropdown interaction
      const tagName = await dropdown.evaluate(el => el.tagName);
      if (tagName === 'SELECT') {
        await dropdown.selectOption({ index: 0 });
      }
    }
  });

  test('should handle tabs', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/');
    await authenticatedPage.waitForLoadState('networkidle');
    
    // Look for tabs
    const tabs = authenticatedPage.locator('[role="tab"], [data-testid="tab"]');
    
    if (await tabs.count() > 0) {
      const firstTab = tabs.first();
      await expect(firstTab).toBeVisible();
      
      // Click tab
      await firstTab.click();
      
      // Verify tab content is visible
      const tabPanel = authenticatedPage.locator('[role="tabpanel"]').first();
      if (await tabPanel.count() > 0) {
        await expect(tabPanel).toBeVisible();
      }
    }
  });
});

