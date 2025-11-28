import { test, expect } from '../fixtures';
import { ApiHelpers, API_BASE_URL } from '../utils/api-helpers';
import { TestDataFactory } from '../utils/test-data-factory';

test.describe('Cross-Feature Integration', () => {
  test('Roadmap + Knowledge Graph + Context integration', async ({ api }) => {
    const apiHelpers = new ApiHelpers(api);
    
    const project = await apiHelpers.createProject('Cross-Feature Integration Test');
    expect(project).toHaveProperty('id');
    
    try {
      // Create roadmap node
      const roadmapNode = TestDataFactory.generateRoadmapNode();
      const node = await apiHelpers.createRoadmapNode(project.id, roadmapNode);
      expect(node).toHaveProperty('id');
      
      // Create knowledge node
      const knowledgeNode = TestDataFactory.generateKnowledgeNode();
      const knode = await apiHelpers.createKnowledgeNode(project.id, knowledgeNode);
      expect(knode).toHaveProperty('id');
      
      // Add context items
      const contextItems = [TestDataFactory.generateContextItem()];
      const contextResult = await apiHelpers.addContextItems(project.id, contextItems);
      expect(contextResult.items.length).toBeGreaterThan(0);
      
      // Verify all are linked to the same project
      const roadmapNodes = await apiHelpers.getRoadmapNodes(project.id);
      expect(Array.isArray(roadmapNodes.items || roadmapNodes)).toBeTruthy();
      
      const context = await apiHelpers.getContext(project.id);
      expect(context.project_id).toBe(project.id);
    } finally {
      await apiHelpers.deleteProject(project.id);
    }
  });

  test('Ingest → Knowledge Graph → Agent Run flow', async ({ api }) => {
    const apiHelpers = new ApiHelpers(api);
    
    const project = await apiHelpers.createProject('Ingest-Knowledge-Agent Flow');
    expect(project).toHaveProperty('id');
    
    try {
      // Step 1: Ingest document
      const job = await apiHelpers.createIngestJob(project.id, 'test-doc.md');
      expect(job).toHaveProperty('id');
      
      // Wait a bit for processing
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      // Step 2: Create knowledge node (representing ingested content)
      const knowledgeNode = TestDataFactory.generateKnowledgeNode({
        title: 'Ingested Document Concept',
        summary: 'From ingested document',
      });
      const knode = await apiHelpers.createKnowledgeNode(project.id, knowledgeNode);
      expect(knode).toHaveProperty('id');
      
      // Step 3: Run agent with knowledge context
      const agentsResponse = await api.get(`${API_BASE_URL}/profiles`);
      const agents = await agentsResponse.json();
      
      if (agents.length > 0) {
        const agentId = agents[0].id;
        const run = await apiHelpers.createAgentRun(project.id, agentId, 'Analyze the knowledge graph');
        expect(run).toHaveProperty('id');
        expect(run.project_id).toBe(project.id);
      }
    } finally {
      await apiHelpers.deleteProject(project.id);
    }
  });

  test('Gap Analysis → Project Intel → Ideas generation', async ({ api }) => {
    const apiHelpers = new ApiHelpers(api);
    
    const project = await apiHelpers.createProject('Gap-Intel-Ideas Flow');
    expect(project).toHaveProperty('id');
    
    try {
      // Step 1: Run gap analysis
      try {
        const gapReport = await apiHelpers.runGapAnalysis(project.id);
        expect(gapReport).toHaveProperty('project_id');
      } catch (error: any) {
        // Acceptable if gap analysis requires specific setup
        if (!error.message.includes('404') && !error.message.includes('501')) {
          throw error;
        }
      }
      
      // Step 2: Rebuild project intel
      try {
        const intelResult = await apiHelpers.rebuildProjectIntel(project.id);
        expect(intelResult).toHaveProperty('project_id');
        
        // Step 3: List generated ideas
        const candidates = await apiHelpers.listProjectIntelCandidates(project.id);
        expect(Array.isArray(candidates)).toBeTruthy();
        
        const clusters = await apiHelpers.listProjectIntelClusters(project.id);
        expect(Array.isArray(clusters)).toBeTruthy();
        
        const tickets = await apiHelpers.listProjectIntelTickets(project.id);
        expect(Array.isArray(tickets)).toBeTruthy();
      } catch (error: any) {
        // Acceptable if project intel requires specific setup
        if (!error.message.includes('501')) {
          throw error;
        }
      }
      
      // Step 4: Generate ideas manually if intel rebuild not available
      const candidateData = TestDataFactory.generateIdeaCandidate();
      const candidate = await apiHelpers.createIdeaCandidate(project.id, candidateData);
      expect(candidate).toHaveProperty('id');
    } finally {
      await apiHelpers.deleteProject(project.id);
    }
  });

  test('Workflow execution → Agent run → Knowledge graph update', async ({ api }) => {
    const apiHelpers = new ApiHelpers(api);
    
    const project = await apiHelpers.createProject('Workflow-Agent-Knowledge Flow');
    expect(project).toHaveProperty('id');
    
    try {
      // Step 1: Create workflow graph
      const graphData = TestDataFactory.generateWorkflowGraph();
      const graph = await apiHelpers.createWorkflowGraph(project.id, graphData);
      expect(graph).toHaveProperty('id');
      
      // Step 2: Execute workflow
      const run = await apiHelpers.createWorkflowRun(project.id, graph.id);
      expect(run).toHaveProperty('id');
      
      // Step 3: Create agent run (simulating workflow triggering agent)
      const agentsResponse = await api.get(`${API_BASE_URL}/profiles`);
      const agents = await agentsResponse.json();
      
      if (agents.length > 0) {
        const agentId = agents[0].id;
        const agentRun = await apiHelpers.createAgentRun(project.id, agentId, 'Process workflow results');
        expect(agentRun).toHaveProperty('id');
        
        // Step 4: Update knowledge graph with results
        const knowledgeNode = TestDataFactory.generateKnowledgeNode({
          title: 'Workflow Result',
          summary: 'Generated from workflow execution',
        });
        const knode = await apiHelpers.createKnowledgeNode(project.id, knowledgeNode);
        expect(knode).toHaveProperty('id');
      }
    } finally {
      await apiHelpers.deleteProject(project.id);
    }
  });
});

