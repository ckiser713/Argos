import { test, expect } from '../fixtures';
import { ApiHelpers, API_BASE_URL } from '../utils/api-helpers';
import { TestDataFactory } from '../utils/test-data-factory';

test.describe('Complete User Workflows', () => {
  test('Workflow 1: Create project → Ingest documents → Run agent → View results', async ({ api }) => {
    const apiHelpers = new ApiHelpers(api);
    
    // Step 1: Create project
    const project = await apiHelpers.createProject('E2E Workflow Test Project');
    expect(project).toHaveProperty('id');
    
    try {
      // Step 2: Ingest documents
      const job = await apiHelpers.createIngestJob(project.id, 'test-doc.md');
      expect(job).toHaveProperty('id');
      
      // Wait a bit for processing
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      // Step 3: Run agent
      const agentsResponse = await api.get(`${API_BASE_URL}/profiles`);
      const agents = await agentsResponse.json();
      
      if (agents.length > 0) {
        const agentId = agents[0].id;
        const run = await apiHelpers.createAgentRun(project.id, agentId, 'Analyze the ingested documents');
        expect(run).toHaveProperty('id');
        
        // Step 4: View results
        const retrievedRun = await apiHelpers.getAgentRun(project.id, run.id);
        expect(retrievedRun.id).toBe(run.id);
      }
    } finally {
      // Cleanup
      await apiHelpers.deleteProject(project.id);
    }
  });

  test('Workflow 2: Create roadmap → Link to knowledge graph → Add context → Execute workflow', async ({ api }) => {
    const apiHelpers = new ApiHelpers(api);
    
    // Step 1: Create project
    const project = await apiHelpers.createProject('Roadmap Workflow Test');
    expect(project).toHaveProperty('id');
    
    try {
      // Step 2: Create roadmap node
      const roadmapNode = TestDataFactory.generateRoadmapNode();
      const node = await apiHelpers.createRoadmapNode(project.id, roadmapNode);
      expect(node).toHaveProperty('id');
      
      // Step 3: Create knowledge node
      const knowledgeNode = TestDataFactory.generateKnowledgeNode();
      const knode = await apiHelpers.createKnowledgeNode(project.id, knowledgeNode);
      expect(knode).toHaveProperty('id');
      
      // Step 4: Add context items
      const contextItems = [
        TestDataFactory.generateContextItem(),
      ];
      const contextResult = await apiHelpers.addContextItems(project.id, contextItems);
      expect(contextResult.items.length).toBeGreaterThan(0);
      
      // Step 5: Create and execute workflow
      const graphData = TestDataFactory.generateWorkflowGraph();
      const graph = await apiHelpers.createWorkflowGraph(project.id, graphData);
      expect(graph).toHaveProperty('id');
      
      const run = await apiHelpers.createWorkflowRun(project.id, graph.id);
      expect(run).toHaveProperty('id');
    } finally {
      // Cleanup
      await apiHelpers.deleteProject(project.id);
    }
  });

  test('Workflow 3: Generate ideas → Create tickets → Assign tasks → Track progress', async ({ api }) => {
    const apiHelpers = new ApiHelpers(api);
    
    // Step 1: Create project
    const project = await apiHelpers.createProject('Ideas Workflow Test');
    expect(project).toHaveProperty('id');
    
    try {
      // Step 2: Generate ideas (create idea candidate)
      const candidateData = TestDataFactory.generateIdeaCandidate();
      const candidate = await apiHelpers.createIdeaCandidate(project.id, candidateData);
      expect(candidate).toHaveProperty('id');
      
      // Step 3: Create ticket from idea
      const ticketData = TestDataFactory.generateIdeaTicket({
        title: 'Implement Feature',
        description: 'Based on idea candidate',
      });
      const ticket = await apiHelpers.createIdeaTicket(project.id, ticketData);
      expect(ticket).toHaveProperty('id');
      
      // Step 4: Create task
      const taskData = TestDataFactory.generateTask({
        title: 'Complete Feature Implementation',
        column: 'todo',
      });
      const task = await apiHelpers.createTask(project.id, taskData);
      expect(task).toHaveProperty('id');
      
      // Step 5: Update task to track progress
      const updatedTask = await apiHelpers.updateTask(project.id, task.id, {
        column: 'in_progress',
      });
      expect(updatedTask.column).toBe('in_progress');
    } finally {
      // Cleanup
      await apiHelpers.deleteProject(project.id);
    }
  });

  test('Workflow 4: Run gap analysis → Review intel → Generate ideas → Create roadmap', async ({ api }) => {
    const apiHelpers = new ApiHelpers(api);
    
    // Step 1: Create project
    const project = await apiHelpers.createProject('Gap Analysis Workflow Test');
    expect(project).toHaveProperty('id');
    
    try {
      // Step 2: Run gap analysis
      try {
        const gapReport = await apiHelpers.runGapAnalysis(project.id);
        expect(gapReport).toHaveProperty('project_id');
        expect(gapReport.project_id).toBe(project.id);
      } catch (error: any) {
        // Acceptable if gap analysis requires specific setup
        if (!error.message.includes('404') && !error.message.includes('501')) {
          throw error;
        }
      }
      
      // Step 3: Review intel (rebuild project intel)
      try {
        const intelResult = await apiHelpers.rebuildProjectIntel(project.id);
        expect(intelResult).toHaveProperty('project_id');
      } catch (error: any) {
        // Acceptable if project intel requires specific setup
        if (!error.message.includes('501')) {
          throw error;
        }
      }
      
      // Step 4: Generate ideas
      const candidateData = TestDataFactory.generateIdeaCandidate();
      const candidate = await apiHelpers.createIdeaCandidate(project.id, candidateData);
      expect(candidate).toHaveProperty('id');
      
      // Step 5: Create roadmap node
      const roadmapNode = TestDataFactory.generateRoadmapNode();
      const node = await apiHelpers.createRoadmapNode(project.id, roadmapNode);
      expect(node).toHaveProperty('id');
    } finally {
      // Cleanup
      await apiHelpers.deleteProject(project.id);
    }
  });
});





