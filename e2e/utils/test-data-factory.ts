/**
 * Test Data Factory
 * 
 * Generates consistent test data for e2e tests
 */

export class TestDataFactory {
  static generateProject(overrides: Partial<{ name: string; description: string }> = {}) {
    return {
      name: overrides.name || `Test Project ${Date.now()}`,
      description: overrides.description || 'Generated test project',
    };
  }

  static generateIngestJob(overrides: Partial<{ sourcePath: string }> = {}) {
    return {
      source_path: overrides.sourcePath || `test-document-${Date.now()}.md`,
    };
  }

  static generateAgentRun(overrides: Partial<{ agentId: string; inputPrompt: string }> = {}) {
    return {
      agent_id: overrides.agentId || 'project_manager',
      input_prompt: overrides.inputPrompt || `Test query ${Date.now()}`,
    };
  }

  static generateRoadmapNode(overrides: Partial<{
    label: string;
    description: string;
    status: string;
    priority: string;
  }> = {}) {
    return {
      label: overrides.label || `Test Node ${Date.now()}`,
      description: overrides.description || 'Test description',
      status: overrides.status || 'PENDING',
      priority: overrides.priority || 'MEDIUM',
    };
  }

  static generateContextItem(overrides: Partial<{
    name: string;
    type: string;
    tokens: number;
  }> = {}) {
    return {
      name: overrides.name || `test-document-${Date.now()}.pdf`,
      type: overrides.type || 'PDF',
      tokens: overrides.tokens || 1000,
      pinned: false,
    };
  }

  static generateKnowledgeNode(overrides: Partial<{
    title: string;
    summary: string;
    type: string;
  }> = {}) {
    return {
      title: overrides.title || `Test Concept ${Date.now()}`,
      summary: overrides.summary || 'Test summary',
      type: overrides.type || 'concept',
    };
  }

  static generateWorkflowGraph(overrides: Partial<{
    name: string;
    description: string;
    nodes: any[];
    edges: any[];
  }> = {}) {
    return {
      name: overrides.name || `Test Workflow ${Date.now()}`,
      description: overrides.description || 'Test workflow description',
      nodes: overrides.nodes || [
        { id: 'start', label: 'Start', x: 0, y: 0 },
        { id: 'process', label: 'Process', x: 100, y: 100 },
        { id: 'end', label: 'End', x: 200, y: 200 },
      ],
      edges: overrides.edges || [
        { id: 'e1', source: 'start', target: 'process' },
        { id: 'e2', source: 'process', target: 'end' },
      ],
    };
  }

  static generateIdeaCandidate(overrides: Partial<{
    title: string;
    summary: string;
    segmentId: string;
    confidence: number;
  }> = {}) {
    return {
      title: overrides.title || `Test Idea ${Date.now()}`,
      summary: overrides.summary || 'Test idea summary',
      segment_id: overrides.segmentId || `seg-${Date.now()}`,
      confidence: overrides.confidence || 0.8,
      labels: [],
      source_chat_ids: [],
    };
  }

  static generateIdeaCluster(overrides: Partial<{
    label: string;
    description: string;
    ideaIds: string[];
  }> = {}) {
    return {
      label: overrides.label || `Test Cluster ${Date.now()}`,
      description: overrides.description || 'Test cluster description',
      idea_ids: overrides.ideaIds || [],
      priority: 'medium',
    };
  }

  static generateIdeaTicket(overrides: Partial<{
    title: string;
    description: string;
    clusterId: string;
    status: string;
    priority: string;
  }> = {}) {
    return {
      title: overrides.title || `Test Ticket ${Date.now()}`,
      description: overrides.description || 'Test ticket description',
      cluster_id: overrides.clusterId,
      status: overrides.status || 'candidate',
      priority: overrides.priority || 'medium',
      origin_idea_ids: [],
    };
  }

  static generateTask(overrides: Partial<{
    title: string;
    description: string;
    column: string;
    origin: string;
  }> = {}) {
    return {
      title: overrides.title || `Test Task ${Date.now()}`,
      description: overrides.description || 'Test task description',
      column: overrides.column || 'todo',
      origin: overrides.origin || 'manual',
    };
  }

  static generateModeSettings(overrides: Partial<{
    mode: string;
    llmTemperature: number;
    validationPasses: number;
    maxParallelTools: number;
  }> = {}) {
    return {
      mode: overrides.mode || 'normal',
      llm_temperature: overrides.llmTemperature || 0.7,
      validation_passes: overrides.validationPasses || 1,
      max_parallel_tools: overrides.maxParallelTools || 4,
    };
  }
}

