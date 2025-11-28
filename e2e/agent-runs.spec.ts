import { test, expect } from './fixtures';
import { ApiHelpers, API_BASE_URL } from './utils/api-helpers';

test.describe('Agent Runs', () => {
  test('should create an agent run', async ({ api, testProject }) => {
    const apiHelpers = new ApiHelpers(api);
    
    const run = await apiHelpers.createAgentRun(
      testProject.id,
      'project_manager',
      'Analyze the codebase structure'
    );
    
    expect(run).toHaveProperty('id');
    expect(run.project_id ?? run.projectId).toBe(testProject.id);
    expect(run.agent_id ?? run.agentId).toBe('project_manager');
    expect(run.status).toBeDefined();
  });

  test('should get agent run by ID', async ({ api, testProject }) => {
    const apiHelpers = new ApiHelpers(api);
    
    const createdRun = await apiHelpers.createAgentRun(
      testProject.id,
      'project_manager',
      'Test query'
    );
    
    const run = await apiHelpers.getAgentRun(testProject.id, createdRun.id);
    
    expect(run.id).toBe(createdRun.id);
    expect(run.project_id ?? run.projectId).toBe(testProject.id);
  });

  test('should list agent runs', async ({ api, testProject }) => {
    const apiHelpers = new ApiHelpers(api);
    
    // Create a run
    await apiHelpers.createAgentRun(
      testProject.id,
      'project_manager',
      'Test query'
    );
    
    // List runs
    const response = await api.get(
      `${API_BASE_URL}/projects/${testProject.id}/agent-runs`
    );
    
    expect(response.ok()).toBeTruthy();
    const runs = await response.json();
    expect(Array.isArray(runs)).toBeTruthy();
  });

  test('should get agent run steps', async ({ api, testProject }) => {
    const apiHelpers = new ApiHelpers(api);
    
    const run = await apiHelpers.createAgentRun(
      testProject.id,
      'project_manager',
      'Test query'
    );
    
    const response = await api.get(
      `${API_BASE_URL}/projects/${testProject.id}/agent-runs/${run.id}/steps`
    );
    
    expect(response.ok()).toBeTruthy();
    const steps = await response.json();
    expect(steps).toHaveProperty('items');
  });

  test('should get agent run messages', async ({ api, testProject }) => {
    const apiHelpers = new ApiHelpers(api);
    
    const run = await apiHelpers.createAgentRun(
      testProject.id,
      'project_manager',
      'Test query'
    );
    
    const response = await api.get(
      `${API_BASE_URL}/projects/${testProject.id}/agent-runs/${run.id}/messages`
    );
    
    expect(response.ok()).toBeTruthy();
    const messages = await response.json();
    expect(messages).toHaveProperty('items');
  });

  test('should get agent run node states', async ({ api, testProject }) => {
    const apiHelpers = new ApiHelpers(api);
    
    const run = await apiHelpers.createAgentRun(
      testProject.id,
      'project_manager',
      'Test query'
    );
    
    const response = await api.get(
      `${API_BASE_URL}/projects/${testProject.id}/agent-runs/${run.id}/node-states`
    );
    
    expect(response.ok()).toBeTruthy();
    const nodeStates = await response.json();
    expect(Array.isArray(nodeStates)).toBeTruthy();
  });

  test('should cancel an agent run', async ({ api, testProject }) => {
    const apiHelpers = new ApiHelpers(api);
    
    const run = await apiHelpers.createAgentRun(
      testProject.id,
      'project_manager',
      'Test query'
    );
    
    const response = await api.post(
      `${API_BASE_URL}/projects/${testProject.id}/agent-runs/${run.id}/cancel`
    );
    
    // Should succeed or return 400 if already completed
    expect([200, 400]).toContain(response.status());
  });
});


