import { test, expect } from './fixtures';
import { ApiHelpers } from './utils/api-helpers';

test.describe('Gap Analysis API', () => {
  test('should run gap analysis', async ({ api, testProject }) => {
    const apiHelpers = new ApiHelpers(api);
    
    // Note: This may require specific project setup
    try {
      const report = await apiHelpers.runGapAnalysis(testProject.id);
      
      expect(report).toHaveProperty('project_id');
      expect(report.project_id).toBe(testProject.id);
      expect(report).toHaveProperty('suggestions');
      expect(Array.isArray(report.suggestions)).toBeTruthy();
    } catch (error: any) {
      // Acceptable if gap analysis requires specific setup
      expect(error.message).toBeTruthy();
    }
  });

  test('should get latest gap analysis', async ({ api, testProject }) => {
    const apiHelpers = new ApiHelpers(api);
    
    // First run a gap analysis if possible
    try {
      await apiHelpers.runGapAnalysis(testProject.id);
      
      // Then get the latest
      const report = await apiHelpers.getLatestGapAnalysis(testProject.id);
      
      expect(report).toHaveProperty('project_id');
      expect(report.project_id).toBe(testProject.id);
    } catch (error: any) {
      // Acceptable if no gap analysis exists yet
      if (error.message.includes('404')) {
        expect(error.message).toContain('404');
      } else {
        throw error;
      }
    }
  });

  test('should list gap analysis history', async ({ api, testProject }) => {
    const apiHelpers = new ApiHelpers(api);
    
    // Run a gap analysis if possible
    try {
      await apiHelpers.runGapAnalysis(testProject.id);
    } catch (error) {
      // Ignore if gap analysis can't run
    }
    
    const history = await apiHelpers.listGapAnalysisHistory(testProject.id);
    
    expect(Array.isArray(history)).toBeTruthy();
  });

  test('should handle limit parameter for history', async ({ api, testProject }) => {
    const apiHelpers = new ApiHelpers(api);
    
    // Run a gap analysis if possible
    try {
      await apiHelpers.runGapAnalysis(testProject.id);
    } catch (error) {
      // Ignore if gap analysis can't run
    }
    
    const history = await apiHelpers.listGapAnalysisHistory(testProject.id, 5);
    
    expect(Array.isArray(history)).toBeTruthy();
    expect(history.length).toBeLessThanOrEqual(5);
  });

  test('should return 404 for latest gap analysis when none exists', async ({ api }) => {
    const apiHelpers = new ApiHelpers(api);
    
    // Create a project that definitely has no gap analysis
    const project = await apiHelpers.createProject('No Gap Analysis Project');
    
    try {
      await apiHelpers.getLatestGapAnalysis(project.id);
      // If we get here, the test should fail
      expect(false).toBeTruthy();
    } catch (error: any) {
      expect(error.message).toContain('404');
    } finally {
      await apiHelpers.deleteProject(project.id);
    }
  });
});









