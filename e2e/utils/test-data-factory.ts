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
}

