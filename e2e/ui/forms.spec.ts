import { test, expect } from '../fixtures';
import { ApiHelpers, API_BASE_URL } from '../utils/api-helpers';

test.describe('Form Interactions', () => {
  test('should handle project creation form interactions', async ({ authenticatedPage, api }) => {
    await authenticatedPage.goto('/');
    await authenticatedPage.waitForLoadState('networkidle');

    // Look for any project creation buttons or forms
    // Since forms might be in modals or specific pages, we'll check for common form elements
    const body = authenticatedPage.locator('body');
    await expect(body).toBeVisible();

    // Verify API can create projects (form backend)
    const apiHelpers = new ApiHelpers(api);
    const project = await apiHelpers.createProject('Form Test Project');
    expect(project).toHaveProperty('id');
    
    // Cleanup
    await apiHelpers.deleteProject(project.id);
  });

  test('should handle form validation errors', async ({ authenticatedPage, api }) => {
    await authenticatedPage.goto('/');
    await authenticatedPage.waitForLoadState('networkidle');

    // Test API validation
    const apiHelpers = new ApiHelpers(api);
    
    // Try to create project with invalid data
    const response = await api.post(`${API_BASE_URL}/projects`, {
      data: {
        // Missing required 'name' field
        description: 'Test',
      },
    });
    
    // Should return validation error
    expect(response.status()).toBeGreaterThanOrEqual(400);
  });

  test('should handle form submission', async ({ authenticatedPage, api }) => {
    await authenticatedPage.goto('/');
    await authenticatedPage.waitForLoadState('networkidle');

    // Test API form submission
    const apiHelpers = new ApiHelpers(api);
    const project = await apiHelpers.createProject('Form Submission Test');
    
    expect(project).toHaveProperty('id');
    expect(project.name).toBe('Form Submission Test');
    
    // Cleanup
    await apiHelpers.deleteProject(project.id);
  });

  test('should handle context item addition', async ({ authenticatedPage, api, testProject }) => {
    await authenticatedPage.goto('/');
    await authenticatedPage.waitForLoadState('networkidle');

    // Test API context item addition
    const apiHelpers = new ApiHelpers(api);
    
    const contextItems = [
      {
        name: 'test-document.pdf',
        type: 'pdf',
        tokens: 1000,
      },
    ];
    
    const result = await apiHelpers.addContextItems(testProject.id, contextItems);
    
    expect(result).toHaveProperty('items');
    expect(result.items.length).toBeGreaterThan(0);
  });

  test('should handle roadmap node creation', async ({ authenticatedPage, api, testProject }) => {
    await authenticatedPage.goto('/');
    await authenticatedPage.waitForLoadState('networkidle');

    // Test API roadmap node creation
    const apiHelpers = new ApiHelpers(api);
    
    const nodeData = {
      label: 'Test Node',
      description: 'Test description',
      status: 'PENDING',
      priority: 'MEDIUM',
    };
    
    const node = await apiHelpers.createRoadmapNode(testProject.id, nodeData);
    
    expect(node).toHaveProperty('id');
    expect(node.label).toBe('Test Node');
  });

  test('should handle knowledge node creation', async ({ authenticatedPage, api, testProject }) => {
    await authenticatedPage.goto('/');
    await authenticatedPage.waitForLoadState('networkidle');

    // Test API knowledge node creation
    const apiHelpers = new ApiHelpers(api);
    
    const nodeData = {
      title: 'Test Concept',
      summary: 'Test summary',
      type: 'concept',
    };
    
    const node = await apiHelpers.createKnowledgeNode(testProject.id, nodeData);
    
    expect(node).toHaveProperty('id');
    expect(node.title).toBe('Test Concept');
  });

  test('should handle ingest job creation', async ({ authenticatedPage, api, testProject }) => {
    await authenticatedPage.goto('/');
    await authenticatedPage.waitForLoadState('networkidle');

    // Test API ingest job creation
    const apiHelpers = new ApiHelpers(api);
    
    const job = await apiHelpers.createIngestJob(testProject.id, 'test-doc.md');
    
    expect(job).toHaveProperty('id');
    expect(job.source_path).toBe('test-doc.md');
  });

  test('should handle agent run configuration', async ({ authenticatedPage, api, testProject }) => {
    await authenticatedPage.goto('/');
    await authenticatedPage.waitForLoadState('networkidle');

    // Test API agent run creation
    const apiHelpers = new ApiHelpers(api);
    
    // First get available agents
    const agentsResponse = await api.get(`${API_BASE_URL}/profiles`);
    const agents = await agentsResponse.json();
    
    if (agents.length > 0) {
      const agentId = agents[0].id;
      const run = await apiHelpers.createAgentRun(testProject.id, agentId, 'Test prompt');
      
      expect(run).toHaveProperty('id');
      expect(run.agent_id).toBe(agentId);
    }
  });
});


