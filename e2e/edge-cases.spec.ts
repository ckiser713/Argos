import { test, expect } from './fixtures';
import { ApiHelpers, API_BASE_URL } from './utils/api-helpers';

/**
 * Edge Cases and Error Handling Tests
 * 
 * Tests for boundary conditions, validation, and error scenarios
 */
test.describe('Edge Cases and Error Handling', () => {
  test('should handle invalid project ID', async ({ api }) => {
    const response = await api.get(`${API_BASE_URL}/projects/invalid-project-id`);
    
    // Should return 404 or 400
    expect([404, 400]).toContain(response.status());
  });

  test('should handle missing required fields', async ({ api, testProject }) => {
    // Try to create project without name
    const response = await api.post(`${API_BASE_URL}/projects`, {
      data: {},
    });
    
    expect(response.status()).toBe(422); // Validation error
  });

  test('should handle pagination boundaries', async ({ api, testProject }) => {
    const apiHelpers = new ApiHelpers(api);
    
    // Test with limit=0 (should fail)
    const response1 = await api.get(
      `${API_BASE_URL}/projects/${testProject.id}/ingest/jobs?limit=0`
    );
    expect([400, 422]).toContain(response1.status());
    
    // Test with very large limit
    const response2 = await api.get(
      `${API_BASE_URL}/projects/${testProject.id}/ingest/jobs?limit=1000`
    );
    // Should either succeed with clamped limit or return 400
    expect([200, 400, 422]).toContain(response2.status());
  });

  test('should handle concurrent operations', async ({ api, testProject }) => {
    const apiHelpers = new ApiHelpers(api);
    
    // Create multiple projects concurrently
    const promises = Array.from({ length: 5 }, (_, i) =>
      apiHelpers.createProject(`Concurrent Project ${i}`)
    );
    
    const projects = await Promise.all(promises);
    
    expect(projects).toHaveLength(5);
    projects.forEach(project => {
      expect(project).toHaveProperty('id');
    });
    
    // Cleanup
    await Promise.all(projects.map(p => apiHelpers.deleteProject(p.id)));
  });

  test('should handle very long strings', async ({ api, testProject }) => {
    const apiHelpers = new ApiHelpers(api);
    
    // Create project with very long name
    const longName = 'A'.repeat(10000);
    const project = await apiHelpers.createProject(longName);
    
    expect(project).toHaveProperty('id');
    
    // Cleanup
    await apiHelpers.deleteProject(project.id);
  });

  test('should handle special characters in names', async ({ api, testProject }) => {
    const apiHelpers = new ApiHelpers(api);
    
    const specialChars = '!@#$%^&*()_+-=[]{}|;:,.<>?';
    const project = await apiHelpers.createProject(`Test ${specialChars}`);
    
    expect(project).toHaveProperty('id');
    
    // Cleanup
    await apiHelpers.deleteProject(project.id);
  });

  test('should handle duplicate operations gracefully', async ({ api, testProject }) => {
    const apiHelpers = new ApiHelpers(api);
    
    // Create same job twice
    const job1 = await apiHelpers.createIngestJob(testProject.id, 'test-doc.md');
    const job2 = await apiHelpers.createIngestJob(testProject.id, 'test-doc.md');
    
    // Both should succeed (duplicates allowed)
    expect(job1).toHaveProperty('id');
    expect(job2).toHaveProperty('id');
    expect(job1.id).not.toBe(job2.id); // Should have different IDs
  });

  test('should handle deletion of non-existent resources', async ({ api, testProject }) => {
    const response = await api.delete(
      `${API_BASE_URL}/projects/${testProject.id}/ingest/jobs/non-existent-id`
    );
    
    expect(response.status()).toBe(404);
  });

  test('should handle update of non-existent resources', async ({ api, testProject }) => {
    const response = await api.patch(
      `${API_BASE_URL}/projects/${testProject.id}/roadmap/nodes/non-existent-id`,
      {
        data: { status: 'ACTIVE' },
      }
    );
    
    expect(response.status()).toBe(404);
  });

  test('should validate context budget limits', async ({ api, testProject }) => {
    const apiHelpers = new ApiHelpers(api);
    
    // Get budget
    const context = await apiHelpers.getContext(testProject.id);
    const maxTokens = context.totalTokens;
    
    // Try to add item exceeding budget
    const response = await api.post(
      `${API_BASE_URL}/projects/${testProject.id}/context/items`,
      {
        data: {
          items: [
            {
              name: 'huge-doc.pdf',
              type: 'PDF',
              tokens: maxTokens + 1,
            },
          ],
        },
      }
    );
    
    expect(response.status()).toBe(400);
  });

  test('should handle empty lists gracefully', async ({ api, testProject }) => {
    // List operations should return empty arrays, not errors
    const response = await api.get(
      `${API_BASE_URL}/projects/${testProject.id}/agent-runs`
    );
    
    expect(response.ok()).toBeTruthy();
    const runs = await response.json();
    expect(Array.isArray(runs)).toBeTruthy();
  });
});

