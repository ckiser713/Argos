import { test, expect } from './fixtures';
import { ApiHelpers } from './utils/api-helpers';

test.describe('Ingest Jobs', () => {
  test('should create an ingest job', async ({ api, testProject }) => {
    const apiHelpers = new ApiHelpers(api);
    
    const job = await apiHelpers.createIngestJob(
      testProject.id,
      'test-document.md'
    );
    
    expect(job).toHaveProperty('id');
    expect(job.projectId).toBe(testProject.id);
    expect(job.status).toBeDefined();
  });

  test('should list ingest jobs for a project', async ({ api, testProject }) => {
    const apiHelpers = new ApiHelpers(api);
    
    // Create a job
    const job = await apiHelpers.createIngestJob(
      testProject.id,
      'test-document.md'
    );
    
    // List jobs
    const jobs = await apiHelpers.getIngestJobs(testProject.id);
    
    expect(jobs.items || jobs).toBeInstanceOf(Array);
    const jobList = Array.isArray(jobs) ? jobs : jobs.items;
    expect(jobList.length).toBeGreaterThan(0);
    expect(jobList.some((j: any) => j.id === job.id)).toBeTruthy();
  });

  test('should get ingest job by ID', async ({ api, testProject }) => {
    const apiHelpers = new ApiHelpers(api);
    
    const createdJob = await apiHelpers.createIngestJob(
      testProject.id,
      'test-document.md'
    );
    
    const response = await api.get(
      `http://localhost:8000/api/projects/${testProject.id}/ingest/jobs/${createdJob.id}`
    );
    
    expect(response.ok()).toBeTruthy();
    const job = await response.json();
    expect(job.id).toBe(createdJob.id);
  });

  test('should cancel an ingest job', async ({ api, testProject }) => {
    const apiHelpers = new ApiHelpers(api);
    
    const job = await apiHelpers.createIngestJob(
      testProject.id,
      'test-document.md'
    );
    
    const response = await api.post(
      `http://localhost:8000/api/projects/${testProject.id}/ingest/jobs/${job.id}/cancel`
    );
    
    expect(response.ok()).toBeTruthy();
    const cancelledJob = await response.json();
    expect(cancelledJob.status).toBe('CANCELLED');
  });

  test('should delete an ingest job', async ({ api, testProject }) => {
    const apiHelpers = new ApiHelpers(api);
    
    const job = await apiHelpers.createIngestJob(
      testProject.id,
      'test-document.md'
    );
    
    // Cancel first (required for deletion)
    await api.post(
      `http://localhost:8000/api/projects/${testProject.id}/ingest/jobs/${job.id}/cancel`
    );
    
    // Delete
    const deleteResponse = await api.delete(
      `http://localhost:8000/api/projects/${testProject.id}/ingest/jobs/${job.id}`
    );
    
    expect(deleteResponse.status()).toBe(204);
  });
});


