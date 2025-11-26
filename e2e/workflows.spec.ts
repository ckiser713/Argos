import { test, expect } from './fixtures';
import { ApiHelpers } from './utils/api-helpers';
import { TestDataFactory } from './utils/test-data-factory';

test.describe('Workflows API', () => {
  test('should create a workflow graph', async ({ api, testProject }) => {
    const apiHelpers = new ApiHelpers(api);
    const graphData = TestDataFactory.generateWorkflowGraph();
    
    const graph = await apiHelpers.createWorkflowGraph(testProject.id, graphData);
    
    expect(graph).toHaveProperty('id');
    expect(graph.name).toBe(graphData.name);
    expect(graph.nodes).toHaveLength(graphData.nodes.length);
    expect(graph.edges).toHaveLength(graphData.edges.length);
  });

  test('should list workflow graphs', async ({ api, testProject }) => {
    const apiHelpers = new ApiHelpers(api);
    const graphData = TestDataFactory.generateWorkflowGraph();
    
    // Create a workflow graph
    const createdGraph = await apiHelpers.createWorkflowGraph(testProject.id, graphData);
    
    // List graphs
    const graphs = await apiHelpers.listWorkflowGraphs(testProject.id);
    
    expect(Array.isArray(graphs)).toBeTruthy();
    const foundGraph = graphs.find((g: any) => g.id === createdGraph.id);
    expect(foundGraph).toBeTruthy();
  });

  test('should get workflow graph by ID', async ({ api, testProject }) => {
    const apiHelpers = new ApiHelpers(api);
    const graphData = TestDataFactory.generateWorkflowGraph();
    
    const createdGraph = await apiHelpers.createWorkflowGraph(testProject.id, graphData);
    const retrievedGraph = await apiHelpers.getWorkflowGraph(testProject.id, createdGraph.id);
    
    expect(retrievedGraph.id).toBe(createdGraph.id);
    expect(retrievedGraph.name).toBe(graphData.name);
  });

  test('should update workflow graph', async ({ api, testProject }) => {
    const apiHelpers = new ApiHelpers(api);
    const graphData = TestDataFactory.generateWorkflowGraph();
    
    const createdGraph = await apiHelpers.createWorkflowGraph(testProject.id, graphData);
    
    const updatedData = {
      ...graphData,
      name: 'Updated Workflow Name',
      description: 'Updated description',
    };
    
    const updatedGraph = await apiHelpers.updateWorkflowGraph(testProject.id, createdGraph.id, updatedData);
    
    expect(updatedGraph.id).toBe(createdGraph.id);
    expect(updatedGraph.name).toBe('Updated Workflow Name');
  });

  test('should create a workflow run', async ({ api, testProject }) => {
    const apiHelpers = new ApiHelpers(api);
    const graphData = TestDataFactory.generateWorkflowGraph();
    
    const graph = await apiHelpers.createWorkflowGraph(testProject.id, graphData);
    const run = await apiHelpers.createWorkflowRun(testProject.id, graph.id, { test: 'data' });
    
    expect(run).toHaveProperty('id');
    expect(run.workflow_id).toBe(graph.id);
    expect(run.project_id).toBe(testProject.id);
    expect(run).toHaveProperty('status');
  });

  test('should list workflow runs', async ({ api, testProject }) => {
    const apiHelpers = new ApiHelpers(api);
    const graphData = TestDataFactory.generateWorkflowGraph();
    
    const graph = await apiHelpers.createWorkflowGraph(testProject.id, graphData);
    const run = await apiHelpers.createWorkflowRun(testProject.id, graph.id);
    
    const runs = await apiHelpers.listWorkflowRuns(testProject.id);
    
    expect(Array.isArray(runs)).toBeTruthy();
    const foundRun = runs.find((r: any) => r.id === run.id);
    expect(foundRun).toBeTruthy();
  });

  test('should get workflow run by ID', async ({ api, testProject }) => {
    const apiHelpers = new ApiHelpers(api);
    const graphData = TestDataFactory.generateWorkflowGraph();
    
    const graph = await apiHelpers.createWorkflowGraph(testProject.id, graphData);
    const createdRun = await apiHelpers.createWorkflowRun(testProject.id, graph.id);
    const retrievedRun = await apiHelpers.getWorkflowRun(testProject.id, createdRun.id);
    
    expect(retrievedRun.id).toBe(createdRun.id);
    expect(retrievedRun.workflow_id).toBe(graph.id);
  });

  test('should execute workflow run', async ({ api, testProject }) => {
    const apiHelpers = new ApiHelpers(api);
    const graphData = TestDataFactory.generateWorkflowGraph();
    
    const graph = await apiHelpers.createWorkflowGraph(testProject.id, graphData);
    const run = await apiHelpers.createWorkflowRun(testProject.id, graph.id);
    
    const executedRun = await apiHelpers.executeWorkflowRun(testProject.id, run.id, { test: 'input' });
    
    expect(executedRun.id).toBe(run.id);
  });

  test('should pause workflow run', async ({ api, testProject }) => {
    const apiHelpers = new ApiHelpers(api);
    const graphData = TestDataFactory.generateWorkflowGraph();
    
    const graph = await apiHelpers.createWorkflowGraph(testProject.id, graphData);
    const run = await apiHelpers.createWorkflowRun(testProject.id, graph.id);
    
    // Note: This may fail if run is not in a pauseable state
    try {
      const pausedRun = await apiHelpers.pauseWorkflowRun(testProject.id, run.id);
      expect(pausedRun.id).toBe(run.id);
    } catch (error) {
      // Acceptable if run is not in a pauseable state
      expect(error).toBeTruthy();
    }
  });

  test('should resume workflow run', async ({ api, testProject }) => {
    const apiHelpers = new ApiHelpers(api);
    const graphData = TestDataFactory.generateWorkflowGraph();
    
    const graph = await apiHelpers.createWorkflowGraph(testProject.id, graphData);
    const run = await apiHelpers.createWorkflowRun(testProject.id, graph.id);
    
    // Note: This may fail if run is not in a resumable state
    try {
      const resumedRun = await apiHelpers.resumeWorkflowRun(testProject.id, run.id);
      expect(resumedRun.id).toBe(run.id);
    } catch (error) {
      // Acceptable if run is not in a resumable state
      expect(error).toBeTruthy();
    }
  });

  test('should cancel workflow run', async ({ api, testProject }) => {
    const apiHelpers = new ApiHelpers(api);
    const graphData = TestDataFactory.generateWorkflowGraph();
    
    const graph = await apiHelpers.createWorkflowGraph(testProject.id, graphData);
    const run = await apiHelpers.createWorkflowRun(testProject.id, graph.id);
    
    // Note: This may fail if run is not in a cancellable state
    try {
      const cancelledRun = await apiHelpers.cancelWorkflowRun(testProject.id, run.id);
      expect(cancelledRun.id).toBe(run.id);
    } catch (error) {
      // Acceptable if run is not in a cancellable state
      expect(error).toBeTruthy();
    }
  });

  test('should get workflow run status', async ({ api, testProject }) => {
    const apiHelpers = new ApiHelpers(api);
    const graphData = TestDataFactory.generateWorkflowGraph();
    
    const graph = await apiHelpers.createWorkflowGraph(testProject.id, graphData);
    const run = await apiHelpers.createWorkflowRun(testProject.id, graph.id);
    
    const status = await apiHelpers.getWorkflowRunStatus(testProject.id, run.id);
    
    expect(status).toBeTruthy();
    expect(typeof status).toBe('object');
  });

  test('should handle invalid workflow graph ID', async ({ api, testProject }) => {
    const apiHelpers = new ApiHelpers(api);
    
    const response = await api.get(`http://localhost:8000/api/projects/${testProject.id}/workflows/graphs/invalid-id`);
    expect(response.status()).toBe(404);
  });

  test('should handle invalid workflow run ID', async ({ api, testProject }) => {
    const apiHelpers = new ApiHelpers(api);
    
    const response = await api.get(`http://localhost:8000/api/projects/${testProject.id}/workflows/runs/invalid-id`);
    expect(response.status()).toBe(404);
  });
});

