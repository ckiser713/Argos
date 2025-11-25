import { test, expect } from './fixtures';
import { ApiHelpers } from './utils/api-helpers';

/**
 * Performance Tests
 * 
 * Tests for API response times and load handling
 */
test.describe('Performance', () => {
  test('should respond to project creation within reasonable time', async ({ api }) => {
    const apiHelpers = new ApiHelpers(api);
    
    const startTime = Date.now();
    const project = await apiHelpers.createProject('Performance Test Project');
    const duration = Date.now() - startTime;
    
    expect(project).toHaveProperty('id');
    expect(duration).toBeLessThan(5000); // Should complete within 5 seconds
    
    // Cleanup
    await apiHelpers.deleteProject(project.id);
  });

  test('should handle multiple concurrent requests', async ({ api }) => {
    const apiHelpers = new ApiHelpers(api);
    
    const startTime = Date.now();
    const promises = Array.from({ length: 10 }, (_, i) =>
      apiHelpers.createProject(`Concurrent Project ${i}`)
    );
    
    const projects = await Promise.all(promises);
    const duration = Date.now() - startTime;
    
    expect(projects).toHaveLength(10);
    expect(duration).toBeLessThan(10000); // Should complete within 10 seconds
    
    // Cleanup
    await Promise.all(projects.map(p => apiHelpers.deleteProject(p.id)));
  });

  test('should paginate large result sets efficiently', async ({ api, testProject }) => {
    const apiHelpers = new ApiHelpers(api);
    
    // Create multiple items
    for (let i = 0; i < 25; i++) {
      await apiHelpers.createIngestJob(testProject.id, `test-doc-${i}.md`);
    }
    
    // Test pagination
    const startTime = Date.now();
    const jobs = await apiHelpers.getIngestJobs(testProject.id);
    const duration = Date.now() - startTime;
    
    expect(jobs.items || jobs).toBeInstanceOf(Array);
    expect(duration).toBeLessThan(2000); // Should complete within 2 seconds
  });

  test('should handle database queries efficiently', async ({ api, testProject }) => {
    const apiHelpers = new ApiHelpers(api);
    
    // Create test data
    await apiHelpers.createIngestJob(testProject.id, 'test-doc.md');
    
    // Measure query time
    const startTime = Date.now();
    const jobs = await apiHelpers.getIngestJobs(testProject.id);
    const duration = Date.now() - startTime;
    
    expect(duration).toBeLessThan(1000); // Should complete within 1 second
  });
});

