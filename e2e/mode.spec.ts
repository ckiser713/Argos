import { test, expect } from './fixtures';
import { ApiHelpers } from './utils/api-helpers';
import { TestDataFactory } from './utils/test-data-factory';

test.describe('Mode API', () => {
  test('should get project execution mode', async ({ api, testProject }) => {
    const apiHelpers = new ApiHelpers(api);
    
    const settings = await apiHelpers.getProjectMode(testProject.id);
    
    expect(settings).toHaveProperty('project_id');
    expect(settings.project_id).toBe(testProject.id);
    expect(settings).toHaveProperty('mode');
    expect(settings).toHaveProperty('llm_temperature');
    expect(settings).toHaveProperty('validation_passes');
    expect(settings).toHaveProperty('max_parallel_tools');
  });

  test('should update project execution mode', async ({ api, testProject }) => {
    const apiHelpers = new ApiHelpers(api);
    const modeData = TestDataFactory.generateModeSettings({ mode: 'paranoid' });
    
    const updated = await apiHelpers.updateProjectMode(testProject.id, {
      mode: modeData.mode,
    });
    
    expect(updated.mode).toBe('paranoid');
    expect(updated.project_id).toBe(testProject.id);
  });

  test('should update LLM temperature', async ({ api, testProject }) => {
    const apiHelpers = new ApiHelpers(api);
    
    const updated = await apiHelpers.updateProjectMode(testProject.id, {
      llm_temperature: 0.9,
    });
    
    expect(updated.llm_temperature).toBe(0.9);
  });

  test('should update validation passes', async ({ api, testProject }) => {
    const apiHelpers = new ApiHelpers(api);
    
    const updated = await apiHelpers.updateProjectMode(testProject.id, {
      validation_passes: 3,
    });
    
    expect(updated.validation_passes).toBe(3);
  });

  test('should update max parallel tools', async ({ api, testProject }) => {
    const apiHelpers = new ApiHelpers(api);
    
    const updated = await apiHelpers.updateProjectMode(testProject.id, {
      max_parallel_tools: 8,
    });
    
    expect(updated.max_parallel_tools).toBe(8);
  });

  test('should update multiple settings at once', async ({ api, testProject }) => {
    const apiHelpers = new ApiHelpers(api);
    
    const updated = await apiHelpers.updateProjectMode(testProject.id, {
      mode: 'normal',
      llm_temperature: 0.8,
      validation_passes: 2,
      max_parallel_tools: 6,
    });
    
    expect(updated.mode).toBe('normal');
    expect(updated.llm_temperature).toBe(0.8);
    expect(updated.validation_passes).toBe(2);
    expect(updated.max_parallel_tools).toBe(6);
  });

  test('should require at least one field for update', async ({ api, testProject }) => {
    const apiHelpers = new ApiHelpers(api);
    
    const response = await api.patch(`http://localhost:8000/api/projects/${testProject.id}/mode`, {
      data: {},
    });
    expect(response.status()).toBe(400);
  });

  test('should validate temperature range', async ({ api, testProject }) => {
    const apiHelpers = new ApiHelpers(api);
    
    const response = await api.patch(`http://localhost:8000/api/projects/${testProject.id}/mode`, {
      data: {
        llm_temperature: 3.0, // Invalid: should be <= 2.0
      },
    });
    expect(response.status()).toBe(422); // Validation error
  });

  test('should validate validation passes range', async ({ api, testProject }) => {
    const apiHelpers = new ApiHelpers(api);
    
    const response = await api.patch(`http://localhost:8000/api/projects/${testProject.id}/mode`, {
      data: {
        validation_passes: 15, // Invalid: should be <= 10
      },
    });
    expect(response.status()).toBe(422); // Validation error
  });
});

