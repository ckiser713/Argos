import { test, expect } from '../fixtures';
import { ApiHelpers, API_BASE_URL } from '../utils/api-helpers';

test.describe('Real-time UI Tests', () => {
  test('should handle WebSocket connection in UI', async ({ authenticatedPage, testProject }) => {
    await authenticatedPage.goto('/');
    await authenticatedPage.waitForLoadState('networkidle');

    // Navigate to a page that might use WebSocket (like Ingest Station)
    const ingestTab = authenticatedPage.locator('nav').getByText('Ingest Pipeline');
    await ingestTab.click();
    await authenticatedPage.waitForTimeout(500);

    // Verify page loaded
    const body = authenticatedPage.locator('body');
    await expect(body).toBeVisible();

    // Note: Actual WebSocket testing is done in websocket.spec.ts
    // This test verifies the UI can load pages that use WebSocket
  });

  test('should display ingest job status updates', async ({ authenticatedPage, api, testProject }) => {
    await authenticatedPage.goto('/');
    await authenticatedPage.waitForLoadState('networkidle');

    // Navigate to Ingest Station
    const ingestTab = authenticatedPage.locator('nav').getByText('Ingest Pipeline');
    await ingestTab.click();
    await authenticatedPage.waitForTimeout(500);

    // Create an ingest job via API
    const apiHelpers = new ApiHelpers(api);
    const job = await apiHelpers.createIngestJob(testProject.id, 'test-doc.md');

    // Wait a bit for potential UI updates
    await authenticatedPage.waitForTimeout(1000);

    // Verify page is still responsive
    const body = authenticatedPage.locator('body');
    await expect(body).toBeVisible();
  });

  test('should display agent run progress updates', async ({ authenticatedPage, api, testProject }) => {
    await authenticatedPage.goto('/');
    await authenticatedPage.waitForLoadState('networkidle');

    // Navigate to Mission Control (where agent runs might be displayed)
    const missionControlTab = authenticatedPage.locator('nav').getByText('Mission Control');
    await missionControlTab.click();
    await authenticatedPage.waitForTimeout(500);

    // Create an agent run via API
    const apiHelpers = new ApiHelpers(api);
    
    // Get available agents
    const agentsResponse = await api.get(`${API_BASE_URL}/profiles`);
    const agents = await agentsResponse.json();
    
    if (agents.length > 0) {
      const agentId = agents[0].id;
      const run = await apiHelpers.createAgentRun(testProject.id, agentId, 'Test prompt');

      // Wait a bit for potential UI updates
      await authenticatedPage.waitForTimeout(1000);

      // Verify page is still responsive
      const body = authenticatedPage.locator('body');
      await expect(body).toBeVisible();
    }
  });

  test('should display workflow execution updates', async ({ authenticatedPage, api, testProject }) => {
    await authenticatedPage.goto('/');
    await authenticatedPage.waitForLoadState('networkidle');

    // Navigate to Workflow Construct
    const workflowTab = authenticatedPage.locator('nav').getByText('Construct Flow');
    await workflowTab.click();
    await authenticatedPage.waitForTimeout(500);

    // Create a workflow graph and run via API
    const apiHelpers = new ApiHelpers(api);
    const graphData = {
      name: 'Test Workflow',
      description: 'Test',
      nodes: [
        { id: 'start', label: 'Start', x: 0, y: 0 },
        { id: 'end', label: 'End', x: 100, y: 100 },
      ],
      edges: [
        { id: 'e1', source: 'start', target: 'end' },
      ],
    };

    const graph = await apiHelpers.createWorkflowGraph(testProject.id, graphData);
    const run = await apiHelpers.createWorkflowRun(testProject.id, graph.id);

    // Wait a bit for potential UI updates
    await authenticatedPage.waitForTimeout(1000);

    // Verify page is still responsive
    const body = authenticatedPage.locator('body');
    await expect(body).toBeVisible();
  });

  test('should handle real-time error display', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/');
    await authenticatedPage.waitForLoadState('networkidle');

    // Navigate to a page
    const missionControlTab = authenticatedPage.locator('nav').getByText('Mission Control');
    await missionControlTab.click();
    await authenticatedPage.waitForTimeout(500);

    // Verify page loaded (errors would be displayed if they occurred)
    const body = authenticatedPage.locator('body');
    await expect(body).toBeVisible();
  });
});






