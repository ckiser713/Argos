import { test, expect } from './fixtures';
import { ApiHelpers } from './utils/api-helpers';

test.describe('Roadmap', () => {
  test('should create a roadmap node', async ({ api, testProject }) => {
    const apiHelpers = new ApiHelpers(api);
    
    const node = await apiHelpers.createRoadmapNode(testProject.id, {
      label: 'Phase 1: Setup',
      description: 'Initial project setup',
      status: 'PENDING',
      priority: 'HIGH',
    });
    
    expect(node).toHaveProperty('id');
    expect(node.label).toBe('Phase 1: Setup');
    expect(node.projectId).toBe(testProject.id);
  });

  test('should list roadmap nodes', async ({ api, testProject }) => {
    const apiHelpers = new ApiHelpers(api);
    
    // Create a node
    await apiHelpers.createRoadmapNode(testProject.id, {
      label: 'Test Node',
      status: 'PENDING',
    });
    
    // List nodes
    const nodes = await apiHelpers.getRoadmapNodes(testProject.id);
    
    expect(nodes).toHaveProperty('items');
    expect(Array.isArray(nodes.items)).toBeTruthy();
    expect(nodes.items.length).toBeGreaterThan(0);
  });

  test('should get roadmap node by ID', async ({ api, testProject }) => {
    const apiHelpers = new ApiHelpers(api);
    
    const createdNode = await apiHelpers.createRoadmapNode(testProject.id, {
      label: 'Get Test Node',
      status: 'PENDING',
    });
    
    const response = await api.get(
      `http://localhost:8000/api/projects/${testProject.id}/roadmap/nodes/${createdNode.id}`
    );
    
    expect(response.ok()).toBeTruthy();
    const node = await response.json();
    expect(node.id).toBe(createdNode.id);
  });

  test('should update roadmap node', async ({ api, testProject }) => {
    const apiHelpers = new ApiHelpers(api);
    
    const node = await apiHelpers.createRoadmapNode(testProject.id, {
      label: 'Update Test Node',
      status: 'PENDING',
    });
    
    const response = await api.patch(
      `http://localhost:8000/api/projects/${testProject.id}/roadmap/nodes/${node.id}`,
      {
        data: {
          status: 'ACTIVE',
          label: 'Updated Node',
        },
      }
    );
    
    expect(response.ok()).toBeTruthy();
    const updatedNode = await response.json();
    expect(updatedNode.status).toBe('ACTIVE');
    expect(updatedNode.label).toBe('Updated Node');
  });

  test('should delete roadmap node', async ({ api, testProject }) => {
    const apiHelpers = new ApiHelpers(api);
    
    const node = await apiHelpers.createRoadmapNode(testProject.id, {
      label: 'Delete Test Node',
      status: 'PENDING',
    });
    
    const response = await api.delete(
      `http://localhost:8000/api/projects/${testProject.id}/roadmap/nodes/${node.id}`
    );
    
    expect(response.ok()).toBeTruthy();
  });

  test('should create roadmap edge', async ({ api, testProject }) => {
    const apiHelpers = new ApiHelpers(api);
    
    // Create two nodes
    const node1 = await apiHelpers.createRoadmapNode(testProject.id, {
      label: 'Node 1',
      status: 'PENDING',
    });
    
    const node2 = await apiHelpers.createRoadmapNode(testProject.id, {
      label: 'Node 2',
      status: 'PENDING',
    });
    
    // Create edge
    const response = await api.post(
      `http://localhost:8000/api/projects/${testProject.id}/roadmap/edges`,
      {
        data: {
          from_node_id: node1.id,
          to_node_id: node2.id,
          kind: 'depends_on',
        },
      }
    );
    
    expect(response.ok()).toBeTruthy();
    const edge = await response.json();
    expect(edge.fromNodeId).toBe(node1.id);
    expect(edge.toNodeId).toBe(node2.id);
  });
});


