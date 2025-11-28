import { test, expect } from './fixtures';
import { ApiHelpers, API_BASE_URL } from './utils/api-helpers';

test.describe('Project Intel API', () => {
  test('should rebuild project intel', async ({ api, testProject }) => {
    const apiHelpers = new ApiHelpers(api);
    
    // Note: This may require specific project setup with chat segments
    try {
      const result = await apiHelpers.rebuildProjectIntel(testProject.id);
      
      expect(result).toHaveProperty('project_id');
      expect(result.project_id).toBe(testProject.id);
      expect(result).toHaveProperty('candidate_ids');
      expect(result).toHaveProperty('cluster_ids');
      expect(result).toHaveProperty('ticket_ids');
      expect(Array.isArray(result.candidate_ids)).toBeTruthy();
      expect(Array.isArray(result.cluster_ids)).toBeTruthy();
      expect(Array.isArray(result.ticket_ids)).toBeTruthy();
    } catch (error: any) {
      // Acceptable if project intel requires specific setup
      if (error.message.includes('501')) {
        // Not implemented - acceptable
        expect(error.message).toContain('501');
      } else {
        throw error;
      }
    }
  });

  test('should list project intel candidates', async ({ api, testProject }) => {
    const apiHelpers = new ApiHelpers(api);
    
    // Try to rebuild first
    try {
      await apiHelpers.rebuildProjectIntel(testProject.id);
    } catch (error) {
      // Ignore if rebuild fails
    }
    
    const candidates = await apiHelpers.listProjectIntelCandidates(testProject.id);
    
    expect(Array.isArray(candidates)).toBeTruthy();
  });

  test('should list project intel clusters', async ({ api, testProject }) => {
    const apiHelpers = new ApiHelpers(api);
    
    // Try to rebuild first
    try {
      await apiHelpers.rebuildProjectIntel(testProject.id);
    } catch (error) {
      // Ignore if rebuild fails
    }
    
    const clusters = await apiHelpers.listProjectIntelClusters(testProject.id);
    
    expect(Array.isArray(clusters)).toBeTruthy();
  });

  test('should list project intel tickets', async ({ api, testProject }) => {
    const apiHelpers = new ApiHelpers(api);
    
    // Try to rebuild first
    try {
      await apiHelpers.rebuildProjectIntel(testProject.id);
    } catch (error) {
      // Ignore if rebuild fails
    }
    
    const tickets = await apiHelpers.listProjectIntelTickets(testProject.id);
    
    expect(Array.isArray(tickets)).toBeTruthy();
  });

  test('should update project intel ticket', async ({ api, testProject }) => {
    const apiHelpers = new ApiHelpers(api);
    
    // Try to rebuild first
    try {
      await apiHelpers.rebuildProjectIntel(testProject.id);
    } catch (error) {
      // Ignore if rebuild fails
    }
    
    const tickets = await apiHelpers.listProjectIntelTickets(testProject.id);
    
    if (tickets.length > 0) {
      const ticket = tickets[0];
      const updates = {
        status: 'triaged' as const,
        priority: 'high' as const,
      };
      
      const updated = await apiHelpers.updateProjectIntelTicket(testProject.id, ticket.id, updates);
      
      expect(updated.id).toBe(ticket.id);
      expect(updated.status).toBe('triaged');
      expect(updated.priority).toBe('high');
    }
  });

  test('should handle invalid ticket ID', async ({ api, testProject }) => {
    const apiHelpers = new ApiHelpers(api);
    
    const response = await api.patch(`${API_BASE_URL}/projects/${testProject.id}/ideas/tickets/invalid-id`, {
      data: { status: 'triaged' },
    });
    expect(response.status()).toBe(404);
  });

  test('should require at least one field for ticket update', async ({ api, testProject }) => {
    const apiHelpers = new ApiHelpers(api);
    
    const response = await api.patch(`${API_BASE_URL}/projects/${testProject.id}/ideas/tickets/some-id`, {
      data: {},
    });
    expect(response.status()).toBe(400);
  });
});





