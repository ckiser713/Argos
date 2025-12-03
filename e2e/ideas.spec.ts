import { test, expect } from './fixtures';
import { ApiHelpers, API_BASE_URL } from './utils/api-helpers';
import { TestDataFactory } from './utils/test-data-factory';

test.describe('Ideas API', () => {
  test('should list idea candidates', async ({ api, testProject }) => {
    const apiHelpers = new ApiHelpers(api);
    
    const response = await apiHelpers.listIdeaCandidates(testProject.id);
    
    expect(response).toHaveProperty('items');
    expect(Array.isArray(response.items)).toBeTruthy();
  });

  test('should create idea candidate', async ({ api, testProject }) => {
    const apiHelpers = new ApiHelpers(api);
    const candidateData = TestDataFactory.generateIdeaCandidate();
    
    const candidate = await apiHelpers.createIdeaCandidate(testProject.id, candidateData);
    
    expect(candidate).toHaveProperty('id');
    expect(candidate.title).toBe(candidateData.title);
  });

  test('should update idea candidate', async ({ api, testProject }) => {
    const apiHelpers = new ApiHelpers(api);
    const candidateData = TestDataFactory.generateIdeaCandidate();
    
    const created = await apiHelpers.createIdeaCandidate(testProject.id, candidateData);
    
    const updates = {
      title: 'Updated Idea Title',
      summary: 'Updated summary',
    };
    
    const updated = await apiHelpers.updateIdeaCandidate(testProject.id, created.id, updates);
    
    expect(updated.id).toBe(created.id);
    expect(updated.title).toBe('Updated Idea Title');
  });

  test('should list idea clusters', async ({ api, testProject }) => {
    const apiHelpers = new ApiHelpers(api);
    
    const response = await apiHelpers.listIdeaClusters(testProject.id);
    
    expect(response).toHaveProperty('items');
    expect(Array.isArray(response.items)).toBeTruthy();
  });

  test('should create idea cluster', async ({ api, testProject }) => {
    const apiHelpers = new ApiHelpers(api);
    const clusterData = TestDataFactory.generateIdeaCluster();
    
    const cluster = await apiHelpers.createIdeaCluster(testProject.id, clusterData);
    
    expect(cluster).toHaveProperty('id');
    expect(cluster.label).toBe(clusterData.label);
  });

  test('should list idea tickets', async ({ api, testProject }) => {
    const apiHelpers = new ApiHelpers(api);
    
    const response = await apiHelpers.listIdeaTickets(testProject.id);
    
    expect(response).toHaveProperty('items');
    expect(Array.isArray(response.items)).toBeTruthy();
  });

  test('should create idea ticket', async ({ api, testProject }) => {
    const apiHelpers = new ApiHelpers(api);
    const ticketData = TestDataFactory.generateIdeaTicket();
    
    const ticket = await apiHelpers.createIdeaTicket(testProject.id, ticketData);
    
    expect(ticket).toHaveProperty('id');
    expect(ticket.title).toBe(ticketData.title);
  });

  test('should list tasks', async ({ api, testProject }) => {
    const apiHelpers = new ApiHelpers(api);
    
    const response = await apiHelpers.listTasks(testProject.id);
    
    expect(response).toHaveProperty('items');
    expect(Array.isArray(response.items)).toBeTruthy();
  });

  test('should create task', async ({ api, testProject }) => {
    const apiHelpers = new ApiHelpers(api);
    const taskData = TestDataFactory.generateTask();
    
    const task = await apiHelpers.createTask(testProject.id, taskData);
    
    expect(task).toHaveProperty('id');
    expect(task.title).toBe(taskData.title);
  });

  test('should update task', async ({ api, testProject }) => {
    const apiHelpers = new ApiHelpers(api);
    const taskData = TestDataFactory.generateTask();
    
    const created = await apiHelpers.createTask(testProject.id, taskData);
    
    const updates = {
      title: 'Updated Task Title',
      column: 'in_progress',
    };
    
    const updated = await apiHelpers.updateTask(testProject.id, created.id, updates);
    
    expect(updated.id).toBe(created.id);
    expect(updated.title).toBe('Updated Task Title');
  });

  test('should filter idea candidates by status', async ({ api, testProject }) => {
    const apiHelpers = new ApiHelpers(api);
    
    const response = await apiHelpers.listIdeaCandidates(testProject.id, undefined, undefined, 'active');
    
    expect(response).toHaveProperty('items');
    expect(Array.isArray(response.items)).toBeTruthy();
  });

  test('should filter idea tickets by status', async ({ api, testProject }) => {
    const apiHelpers = new ApiHelpers(api);
    
    const response = await apiHelpers.listIdeaTickets(testProject.id, undefined, undefined, 'candidate');
    
    expect(response).toHaveProperty('items');
    expect(Array.isArray(response.items)).toBeTruthy();
  });

  test('should filter tasks by column', async ({ api, testProject }) => {
    const apiHelpers = new ApiHelpers(api);
    
    const response = await apiHelpers.listTasks(testProject.id, undefined, undefined, 'todo');
    
    expect(response).toHaveProperty('items');
    expect(Array.isArray(response.items)).toBeTruthy();
  });

  test('should handle pagination for idea candidates', async ({ api, testProject }) => {
    const apiHelpers = new ApiHelpers(api);
    
    const firstPage = await apiHelpers.listIdeaCandidates(testProject.id, undefined, 10);
    expect(firstPage).toHaveProperty('items');
    
    if (firstPage.next_cursor) {
      const secondPage = await apiHelpers.listIdeaCandidates(testProject.id, firstPage.next_cursor, 10);
      expect(secondPage).toHaveProperty('items');
    }
  });

  test('should handle invalid idea candidate ID', async ({ api, testProject }) => {
    const apiHelpers = new ApiHelpers(api);
    
    const response = await api.patch(`${API_BASE_URL}/projects/${testProject.id}/ideas/candidates/invalid-id`, {
      data: { title: 'Updated' },
    });
    expect(response.status()).toBe(404);
  });

  test('should handle invalid task ID', async ({ api, testProject }) => {
    const apiHelpers = new ApiHelpers(api);
    
    const response = await api.patch(`${API_BASE_URL}/projects/${testProject.id}/tasks/invalid-id`, {
      data: { title: 'Updated' },
    });
    expect(response.status()).toBe(404);
  });
});









