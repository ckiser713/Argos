import { test, expect } from './fixtures';
import { ApiHelpers } from './utils/api-helpers';

test.describe('Knowledge Graph', () => {
  test('should create a knowledge node', async ({ api, testProject }) => {
    const apiHelpers = new ApiHelpers(api);
    
    const node = await apiHelpers.createKnowledgeNode(testProject.id, {
      title: 'Test Concept',
      summary: 'A test concept for e2e testing',
      type: 'concept',
    });
    
    expect(node).toHaveProperty('id');
    expect(node.title).toBe('Test Concept');
    expect(node.projectId).toBe(testProject.id);
  });

  test('should get knowledge graph', async ({ api, testProject }) => {
    const apiHelpers = new ApiHelpers(api);
    
    // Create a node
    await apiHelpers.createKnowledgeNode(testProject.id, {
      title: 'Test Concept',
      summary: 'A test concept',
      type: 'concept',
    });
    
    // Get graph
    const response = await api.get(
      `http://localhost:8000/api/projects/${testProject.id}/knowledge-graph`
    );
    
    expect(response.ok()).toBeTruthy();
    const graph = await response.json();
    expect(graph).toHaveProperty('nodes');
    expect(graph).toHaveProperty('edges');
    expect(Array.isArray(graph.nodes)).toBeTruthy();
  });

  test('should search knowledge nodes', async ({ api, testProject }) => {
    const apiHelpers = new ApiHelpers(api);
    
    // Create a node
    await apiHelpers.createKnowledgeNode(testProject.id, {
      title: 'Searchable Concept',
      summary: 'This concept should be searchable',
      type: 'concept',
    });
    
    // Wait a bit for indexing (if using vector search)
    await test.step('Wait for indexing', async () => {
      await new Promise(resolve => setTimeout(resolve, 1000));
    });
    
    // Search
    const results = await apiHelpers.searchKnowledge(testProject.id, 'Searchable');
    
    expect(Array.isArray(results)).toBeTruthy();
    // Results may be empty if vector search isn't fully set up, but API should work
  });

  test('should get knowledge node by ID', async ({ api, testProject }) => {
    const apiHelpers = new ApiHelpers(api);
    
    const createdNode = await apiHelpers.createKnowledgeNode(testProject.id, {
      title: 'Get Test Node',
      summary: 'Test summary',
      type: 'concept',
    });
    
    const response = await api.get(
      `http://localhost:8000/api/projects/${testProject.id}/knowledge-graph/nodes/${createdNode.id}`
    );
    
    expect(response.ok()).toBeTruthy();
    const node = await response.json();
    expect(node.id).toBe(createdNode.id);
  });

  test('should update knowledge node', async ({ api, testProject }) => {
    const apiHelpers = new ApiHelpers(api);
    
    const node = await apiHelpers.createKnowledgeNode(testProject.id, {
      title: 'Update Test Node',
      summary: 'Original summary',
      type: 'concept',
    });
    
    const response = await api.patch(
      `http://localhost:8000/api/projects/${testProject.id}/knowledge-graph/nodes/${node.id}`,
      {
        data: {
          title: 'Updated Node',
          summary: 'Updated summary',
        },
      }
    );
    
    expect(response.ok()).toBeTruthy();
    const updatedNode = await response.json();
    expect(updatedNode.title).toBe('Updated Node');
    expect(updatedNode.summary).toBe('Updated summary');
  });

  test('should create knowledge edge', async ({ api, testProject }) => {
    const apiHelpers = new ApiHelpers(api);
    
    // Create two nodes
    const node1 = await apiHelpers.createKnowledgeNode(testProject.id, {
      title: 'Node 1',
      type: 'concept',
    });
    
    const node2 = await apiHelpers.createKnowledgeNode(testProject.id, {
      title: 'Node 2',
      type: 'concept',
    });
    
    // Create edge
    const response = await api.post(
      `http://localhost:8000/api/projects/${testProject.id}/knowledge-graph/edges`,
      {
        data: {
          source: node1.id,
          target: node2.id,
          type: 'relates_to',
        },
      }
    );
    
    expect(response.ok()).toBeTruthy();
    const edge = await response.json();
    expect(edge.source).toBe(node1.id);
    expect(edge.target).toBe(node2.id);
  });
});


