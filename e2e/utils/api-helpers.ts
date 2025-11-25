import type { APIRequestContext } from '@playwright/test';

const API_BASE_URL = 'http://localhost:8000/api';

export class ApiHelpers {
  constructor(private api: APIRequestContext) {}

  async createProject(name: string, description?: string) {
    const response = await this.api.post(`${API_BASE_URL}/projects`, {
      data: {
        name,
        description: description || `Test project: ${name}`,
      },
    });
    if (!response.ok()) {
      const errorText = await response.text();
      throw new Error(`Failed to create project: ${response.status()} ${errorText}`);
    }
    return await response.json();
  }

  async deleteProject(projectId: string) {
    const response = await this.api.delete(`${API_BASE_URL}/projects/${projectId}`);
    return response.ok();
  }

  async createIngestJob(projectId: string, sourcePath: string) {
    const response = await this.api.post(`${API_BASE_URL}/projects/${projectId}/ingest/jobs`, {
      data: {
        source_path: sourcePath,
      },
    });
    if (!response.ok()) {
      const errorText = await response.text();
      throw new Error(`Failed to create ingest job: ${response.status()} ${errorText}`);
    }
    return await response.json();
  }

  async getIngestJobs(projectId: string) {
    const response = await this.api.get(`${API_BASE_URL}/projects/${projectId}/ingest/jobs`);
    expect(response.ok()).toBeTruthy();
    return await response.json();
  }

  async createAgentRun(projectId: string, agentId: string, inputPrompt: string) {
    const response = await this.api.post(`${API_BASE_URL}/projects/${projectId}/agent-runs`, {
      data: {
        project_id: projectId,
        agent_id: agentId,
        input_prompt: inputPrompt,
      },
    });
    if (!response.ok()) {
      const errorText = await response.text();
      throw new Error(`Failed to create agent run: ${response.status()} ${errorText}`);
    }
    return await response.json();
  }

  async getAgentRun(projectId: string, runId: string) {
    const response = await this.api.get(`${API_BASE_URL}/projects/${projectId}/agent-runs/${runId}`);
    expect(response.ok()).toBeTruthy();
    return await response.json();
  }

  async createRoadmapNode(projectId: string, nodeData: any) {
    const response = await this.api.post(`${API_BASE_URL}/projects/${projectId}/roadmap/nodes`, {
      data: nodeData,
    });
    if (!response.ok()) {
      const errorText = await response.text();
      throw new Error(`Failed to create roadmap node: ${response.status()} ${errorText}`);
    }
    return await response.json();
  }

  async getRoadmapNodes(projectId: string) {
    const response = await this.api.get(`${API_BASE_URL}/projects/${projectId}/roadmap/nodes`);
    expect(response.ok()).toBeTruthy();
    return await response.json();
  }

  async addContextItems(projectId: string, items: any[]) {
    const response = await this.api.post(`${API_BASE_URL}/projects/${projectId}/context/items`, {
      data: { items },
    });
    if (!response.ok()) {
      const errorText = await response.text();
      throw new Error(`Failed to add context items: ${response.status()} ${errorText}`);
    }
    return await response.json();
  }

  async getContext(projectId: string) {
    const response = await this.api.get(`${API_BASE_URL}/projects/${projectId}/context`);
    expect(response.ok()).toBeTruthy();
    return await response.json();
  }

  async createKnowledgeNode(projectId: string, nodeData: any) {
    const response = await this.api.post(`${API_BASE_URL}/projects/${projectId}/knowledge-graph/nodes`, {
      data: nodeData,
    });
    if (!response.ok()) {
      const errorText = await response.text();
      throw new Error(`Failed to create knowledge node: ${response.status()} ${errorText}`);
    }
    return await response.json();
  }

  async searchKnowledge(projectId: string, query: string) {
    const response = await this.api.post(`${API_BASE_URL}/projects/${projectId}/knowledge/search`, {
      data: { query },
    });
    expect(response.ok()).toBeTruthy();
    return await response.json();
  }
}

import { expect } from '@playwright/test';

// Re-export expect for convenience
export { expect };

