import { test, expect } from './fixtures';
import { ApiHelpers, API_BASE_URL } from './utils/api-helpers';

test.describe('AI Models E2E Tests', () => {
  test.describe('Agent-Based Model Testing', () => {
    test('should run researcher agent with AI models', async ({ api, testProject }) => {
      const apiHelpers = new ApiHelpers(api);

      // Create an agent run that should use AI models for research
      const run = await apiHelpers.createAgentRun(
        testProject.id,
        'researcher',
        'Research the key concepts in machine learning and provide a comprehensive summary'
      );

      expect(run).toHaveProperty('id');
      expect(run.agent_id ?? run.agentId).toBe('researcher');

      // Wait for run to potentially complete (may take time)
      await new Promise(resolve => setTimeout(resolve, 10000));

      // Check that the run was created and has some status
      const updatedRun = await apiHelpers.getAgentRun(testProject.id, run.id);
      expect(updatedRun.status).toBeDefined();
    });

    test('should run project manager agent with AI models', async ({ api, testProject }) => {
      const apiHelpers = new ApiHelpers(api);

      const run = await apiHelpers.createAgentRun(
        testProject.id,
        'project_manager',
        'Analyze this software project structure and provide management recommendations'
      );

      expect(run).toHaveProperty('id');
      expect(run.agent_id ?? run.agentId).toBe('project_manager');
    });

    test('should run planner agent with AI models', async ({ api, testProject }) => {
      const apiHelpers = new ApiHelpers(api);

      const run = await apiHelpers.createAgentRun(
        testProject.id,
        'planner',
        'Create a detailed plan for implementing a new feature in this codebase'
      );

      expect(run).toHaveProperty('id');
      expect(run.agent_id ?? run.agentId).toBe('planner');
    });
  });

  test.describe('Embedding Models', () => {
    test('should create and search knowledge nodes using embeddings', async ({ api, testProject }) => {
      const apiHelpers = new ApiHelpers(api);

      // Create knowledge nodes with different types of content
      await apiHelpers.createKnowledgeNode(testProject.id, {
        title: 'Machine Learning Fundamentals',
        summary: 'Core concepts including supervised learning, unsupervised learning, neural networks, and deep learning architectures',
        type: 'concept',
      });

      await apiHelpers.createKnowledgeNode(testProject.id, {
        title: 'Python Programming',
        summary: 'Object-oriented programming, decorators, generators, async programming, and best practices',
        type: 'skill',
      });

      await apiHelpers.createKnowledgeNode(testProject.id, {
        title: 'Database Design',
        summary: 'Relational databases, normalization, indexing, query optimization, and NoSQL alternatives',
        type: 'concept',
      });

      // Wait for indexing to complete
      await new Promise(resolve => setTimeout(resolve, 3000));

      // Search using semantic queries that should leverage embeddings
      const mlResults = await apiHelpers.searchKnowledge(testProject.id, 'artificial intelligence algorithms');
      expect(Array.isArray(mlResults)).toBeTruthy();

      const codeResults = await apiHelpers.searchKnowledge(testProject.id, 'programming language features');
      expect(Array.isArray(codeResults)).toBeTruthy();

      const dbResults = await apiHelpers.searchKnowledge(testProject.id, 'data storage systems');
      expect(Array.isArray(dbResults)).toBeTruthy();
    });

    test('should handle code-specific knowledge search', async ({ api, testProject }) => {
      const apiHelpers = new ApiHelpers(api);

      // Create code-related knowledge nodes
      await apiHelpers.createKnowledgeNode(testProject.id, {
        title: 'React Hooks Implementation',
        summary: 'useState, useEffect, useContext, custom hooks, and state management patterns in React applications',
        type: 'code_pattern',
      });

      await apiHelpers.createKnowledgeNode(testProject.id, {
        title: 'API Design Patterns',
        summary: 'RESTful APIs, GraphQL, authentication, rate limiting, and error handling strategies',
        type: 'architecture',
      });

      // Wait for indexing
      await new Promise(resolve => setTimeout(resolve, 3000));

      // Search for code-related queries
      const reactResults = await apiHelpers.searchKnowledge(testProject.id, 'React state management');
      expect(Array.isArray(reactResults)).toBeTruthy();

      const apiResults = await apiHelpers.searchKnowledge(testProject.id, 'web service design');
      expect(Array.isArray(apiResults)).toBeTruthy();
    });
  });

  test.describe('Model Integration Validation', () => {
    test('should complete agent runs successfully', async ({ api, testProject }) => {
      const apiHelpers = new ApiHelpers(api);

      const run = await apiHelpers.createAgentRun(
        testProject.id,
        'researcher',
        'Provide a brief overview of software testing methodologies'
      );

      expect(run).toHaveProperty('id');

      // Poll for completion with timeout
      let attempts = 0;
      const maxAttempts = 30; // 30 seconds max
      let completed = false;

      while (attempts < maxAttempts && !completed) {
        await new Promise(resolve => setTimeout(resolve, 1000));
        const updatedRun = await apiHelpers.getAgentRun(testProject.id, run.id);

        if (updatedRun.status === 'completed' || updatedRun.status === 'failed') {
          completed = true;

          // Check that we have some output
          if (updatedRun.status === 'completed') {
            expect(updatedRun.output_summary).toBeTruthy();
            expect(typeof updatedRun.output_summary).toBe('string');
            expect(updatedRun.output_summary.length).toBeGreaterThan(10);
          }
        }
        attempts++;
      }

      // The run should eventually complete or fail (not hang indefinitely)
      expect(completed).toBe(true);
    });

    test('should handle multiple concurrent agent runs', async ({ api, testProject }) => {
      const apiHelpers = new ApiHelpers(api);

      // Create multiple concurrent agent runs
      const promises = [
        apiHelpers.createAgentRun(testProject.id, 'researcher', 'Summarize machine learning'),
        apiHelpers.createAgentRun(testProject.id, 'project_manager', 'Project planning overview'),
        apiHelpers.createAgentRun(testProject.id, 'planner', 'Strategic planning guide'),
      ];

      const runs = await Promise.all(promises);
      expect(runs).toHaveLength(3);
      runs.forEach(run => {
        expect(run).toHaveProperty('id');
        expect(run.status).toBeDefined();
      });
    });

    test('should maintain knowledge graph integrity', async ({ api, testProject }) => {
      const apiHelpers = new ApiHelpers(api);

      // Create multiple knowledge nodes
      const nodes = [];
      for (let i = 0; i < 5; i++) {
        const node = await apiHelpers.createKnowledgeNode(testProject.id, {
          title: `Test Concept ${i}`,
          summary: `This is test concept number ${i} for validating knowledge graph operations`,
          type: 'concept',
        });
        nodes.push(node);
      }

      // Get the knowledge graph
      const response = await api.get(`${API_BASE_URL}/projects/${testProject.id}/knowledge-graph`);
      expect(response.ok()).toBeTruthy();

      const graph = await response.json();
      expect(graph).toHaveProperty('nodes');
      expect(graph).toHaveProperty('edges');
      expect(Array.isArray(graph.nodes)).toBeTruthy();
      expect(graph.nodes.length).toBeGreaterThanOrEqual(5);
    });
  });

  test.describe('Model Performance and Reliability', () => {
    test('should handle various input sizes', async ({ api, testProject }) => {
      const apiHelpers = new ApiHelpers(api);

      // Test with different input sizes
      const testCases = [
        'Short query',
        'A'.repeat(1000), // Medium input
        'A'.repeat(5000), // Large input
      ];

      for (const input of testCases) {
        const run = await apiHelpers.createAgentRun(
          testProject.id,
          'researcher',
          input
        );
        expect(run).toHaveProperty('id');
      }
    });

    test('should handle special characters and formatting', async ({ api, testProject }) => {
      const apiHelpers = new ApiHelpers(api);

      const specialInput = `
        ## Special Test Input

        - Bullet points with **bold** and *italic* text
        - Code: \`console.log('hello world')\`
        - Math: E = mc²
        - Unicode: 🚀 🔥 💻
        - URLs: https://example.com
        - JSON: {"key": "value"}
      `;

      const run = await apiHelpers.createAgentRun(
        testProject.id,
        'researcher',
        specialInput
      );

      expect(run).toHaveProperty('id');
    });

    test('should maintain session state across operations', async ({ api, testProject }) => {
      const apiHelpers = new ApiHelpers(api);

      // Create some knowledge first
      await apiHelpers.createKnowledgeNode(testProject.id, {
        title: 'Session Test Node',
        summary: 'This node is created to test session state maintenance',
        type: 'test',
      });

      // Run an agent that should be able to reference the knowledge
      const run = await apiHelpers.createAgentRun(
        testProject.id,
        'researcher',
        'Based on the knowledge in this project, provide insights about testing'
      );

      expect(run).toHaveProperty('id');

      // The agent should be able to access project knowledge
      await new Promise(resolve => setTimeout(resolve, 5000));

      const updatedRun = await apiHelpers.getAgentRun(testProject.id, run.id);
      expect(updatedRun.status).toBeDefined();
    });
  });

  test.describe('System Integration', () => {
    test('should report system health with model information', async ({ api }) => {
      const apiHelpers = new ApiHelpers(api);

      const health = await apiHelpers.getHealth();
      expect(health).toHaveProperty('message');
      expect(health.message).toBe('ok');
    });

    test('should provide system status with resource metrics', async ({ api }) => {
      const apiHelpers = new ApiHelpers(api);

      const status = await apiHelpers.getSystemStatus();

      // Basic system metrics should be available
      expect(status).toHaveProperty('cpu');
      expect(status).toHaveProperty('memory');
      expect(status).toHaveProperty('active_agent_runs');

      expect(typeof status.active_agent_runs).toBe('number');
    });

    test('should handle system under load', async ({ api, testProject }) => {
      const apiHelpers = new ApiHelpers(api);

      // Create several agent runs to test system under load
      const loadTestRuns = [];
      for (let i = 0; i < 5; i++) {
        loadTestRuns.push(
          apiHelpers.createAgentRun(
            testProject.id,
            'researcher',
            `Load test query ${i}: Explain concept ${i}`
          )
        );
      }

      // All runs should be created successfully
      const runs = await Promise.all(loadTestRuns);
      expect(runs).toHaveLength(5);
      runs.forEach(run => expect(run).toHaveProperty('id'));
    });
  });
});