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

  // Workflows API helpers
  async createWorkflowGraph(projectId: string, graphData: any) {
    const response = await this.api.post(`${API_BASE_URL}/projects/${projectId}/workflows/graphs`, {
      data: graphData,
    });
    if (!response.ok()) {
      const errorText = await response.text();
      throw new Error(`Failed to create workflow graph: ${response.status()} ${errorText}`);
    }
    return await response.json();
  }

  async listWorkflowGraphs(projectId: string) {
    const response = await this.api.get(`${API_BASE_URL}/projects/${projectId}/workflows/graphs`);
    expect(response.ok()).toBeTruthy();
    return await response.json();
  }

  async getWorkflowGraph(projectId: string, workflowId: string) {
    const response = await this.api.get(`${API_BASE_URL}/projects/${projectId}/workflows/graphs/${workflowId}`);
    expect(response.ok()).toBeTruthy();
    return await response.json();
  }

  async updateWorkflowGraph(projectId: string, workflowId: string, graphData: any) {
    const response = await this.api.put(`${API_BASE_URL}/projects/${projectId}/workflows/graphs/${workflowId}`, {
      data: graphData,
    });
    if (!response.ok()) {
      const errorText = await response.text();
      throw new Error(`Failed to update workflow graph: ${response.status()} ${errorText}`);
    }
    return await response.json();
  }

  async createWorkflowRun(projectId: string, workflowId: string, inputData?: any) {
    const response = await this.api.post(`${API_BASE_URL}/projects/${projectId}/workflows/runs`, {
      data: {
        workflow_id: workflowId,
        input_data: inputData,
      },
    });
    if (!response.ok()) {
      const errorText = await response.text();
      throw new Error(`Failed to create workflow run: ${response.status()} ${errorText}`);
    }
    return await response.json();
  }

  async listWorkflowRuns(projectId: string, workflowId?: string) {
    const url = `${API_BASE_URL}/projects/${projectId}/workflows/runs${workflowId ? `?workflow_id=${workflowId}` : ''}`;
    const response = await this.api.get(url);
    expect(response.ok()).toBeTruthy();
    return await response.json();
  }

  async getWorkflowRun(projectId: string, runId: string) {
    const response = await this.api.get(`${API_BASE_URL}/projects/${projectId}/workflows/runs/${runId}`);
    expect(response.ok()).toBeTruthy();
    return await response.json();
  }

  async executeWorkflowRun(projectId: string, runId: string, inputData?: any) {
    const response = await this.api.post(`${API_BASE_URL}/projects/${projectId}/workflows/runs/${runId}/execute`, {
      data: inputData ? { input_data: inputData } : undefined,
    });
    expect(response.ok()).toBeTruthy();
    return await response.json();
  }

  async pauseWorkflowRun(projectId: string, runId: string) {
    const response = await this.api.post(`${API_BASE_URL}/projects/${projectId}/workflows/runs/${runId}/pause`);
    if (!response.ok()) {
      const errorText = await response.text();
      throw new Error(`Failed to pause workflow run: ${response.status()} ${errorText}`);
    }
    return await response.json();
  }

  async resumeWorkflowRun(projectId: string, runId: string, checkpointId?: string) {
    const response = await this.api.post(`${API_BASE_URL}/projects/${projectId}/workflows/runs/${runId}/resume`, {
      data: checkpointId ? { checkpoint_id: checkpointId } : undefined,
    });
    expect(response.ok()).toBeTruthy();
    return await response.json();
  }

  async cancelWorkflowRun(projectId: string, runId: string) {
    const response = await this.api.post(`${API_BASE_URL}/projects/${projectId}/workflows/runs/${runId}/cancel`);
    if (!response.ok()) {
      const errorText = await response.text();
      throw new Error(`Failed to cancel workflow run: ${response.status()} ${errorText}`);
    }
    return await response.json();
  }

  async getWorkflowRunStatus(projectId: string, runId: string) {
    const response = await this.api.get(`${API_BASE_URL}/projects/${projectId}/workflows/runs/${runId}/status`);
    expect(response.ok()).toBeTruthy();
    return await response.json();
  }

  // Ideas API helpers
  async listIdeaCandidates(projectId: string, cursor?: string, limit?: number, status?: string, type?: string) {
    const params = new URLSearchParams();
    if (cursor) params.append('cursor', cursor);
    if (limit) params.append('limit', limit.toString());
    if (status) params.append('status', status);
    if (type) params.append('type', type);
    const url = `${API_BASE_URL}/projects/${projectId}/ideas/candidates${params.toString() ? `?${params.toString()}` : ''}`;
    const response = await this.api.get(url);
    expect(response.ok()).toBeTruthy();
    return await response.json();
  }

  async createIdeaCandidate(projectId: string, candidateData: any) {
    const response = await this.api.post(`${API_BASE_URL}/projects/${projectId}/ideas/candidates`, {
      data: candidateData,
    });
    if (!response.ok()) {
      const errorText = await response.text();
      throw new Error(`Failed to create idea candidate: ${response.status()} ${errorText}`);
    }
    return await response.json();
  }

  async updateIdeaCandidate(projectId: string, ideaId: string, updates: any) {
    const response = await this.api.patch(`${API_BASE_URL}/projects/${projectId}/ideas/candidates/${ideaId}`, {
      data: updates,
    });
    if (!response.ok()) {
      const errorText = await response.text();
      throw new Error(`Failed to update idea candidate: ${response.status()} ${errorText}`);
    }
    return await response.json();
  }

  async listIdeaClusters(projectId: string, cursor?: string, limit?: number) {
    const params = new URLSearchParams();
    if (cursor) params.append('cursor', cursor);
    if (limit) params.append('limit', limit.toString());
    const url = `${API_BASE_URL}/projects/${projectId}/ideas/clusters${params.toString() ? `?${params.toString()}` : ''}`;
    const response = await this.api.get(url);
    expect(response.ok()).toBeTruthy();
    return await response.json();
  }

  async createIdeaCluster(projectId: string, clusterData: any) {
    const response = await this.api.post(`${API_BASE_URL}/projects/${projectId}/ideas/clusters`, {
      data: clusterData,
    });
    if (!response.ok()) {
      const errorText = await response.text();
      throw new Error(`Failed to create idea cluster: ${response.status()} ${errorText}`);
    }
    return await response.json();
  }

  async listIdeaTickets(projectId: string, cursor?: string, limit?: number, status?: string) {
    const params = new URLSearchParams();
    if (cursor) params.append('cursor', cursor);
    if (limit) params.append('limit', limit.toString());
    if (status) params.append('status', status);
    const url = `${API_BASE_URL}/projects/${projectId}/ideas/tickets${params.toString() ? `?${params.toString()}` : ''}`;
    const response = await this.api.get(url);
    expect(response.ok()).toBeTruthy();
    return await response.json();
  }

  async createIdeaTicket(projectId: string, ticketData: any) {
    const response = await this.api.post(`${API_BASE_URL}/projects/${projectId}/ideas/tickets`, {
      data: ticketData,
    });
    if (!response.ok()) {
      const errorText = await response.text();
      throw new Error(`Failed to create idea ticket: ${response.status()} ${errorText}`);
    }
    return await response.json();
  }

  async listTasks(projectId: string, cursor?: string, limit?: number, column?: string, origin?: string) {
    const params = new URLSearchParams();
    if (cursor) params.append('cursor', cursor);
    if (limit) params.append('limit', limit.toString());
    if (column) params.append('column', column);
    if (origin) params.append('origin', origin);
    const url = `${API_BASE_URL}/projects/${projectId}/tasks${params.toString() ? `?${params.toString()}` : ''}`;
    const response = await this.api.get(url);
    expect(response.ok()).toBeTruthy();
    return await response.json();
  }

  async createTask(projectId: string, taskData: any) {
    const response = await this.api.post(`${API_BASE_URL}/projects/${projectId}/tasks`, {
      data: taskData,
    });
    if (!response.ok()) {
      const errorText = await response.text();
      throw new Error(`Failed to create task: ${response.status()} ${errorText}`);
    }
    return await response.json();
  }

  async updateTask(projectId: string, taskId: string, updates: any) {
    const response = await this.api.patch(`${API_BASE_URL}/projects/${projectId}/tasks/${taskId}`, {
      data: updates,
    });
    if (!response.ok()) {
      const errorText = await response.text();
      throw new Error(`Failed to update task: ${response.status()} ${errorText}`);
    }
    return await response.json();
  }

  // Gap Analysis API helpers
  async runGapAnalysis(projectId: string) {
    const response = await this.api.post(`${API_BASE_URL}/projects/${projectId}/gap-analysis/run`);
    if (!response.ok()) {
      const errorText = await response.text();
      throw new Error(`Failed to run gap analysis: ${response.status()} ${errorText}`);
    }
    return await response.json();
  }

  async getLatestGapAnalysis(projectId: string) {
    const response = await this.api.get(`${API_BASE_URL}/projects/${projectId}/gap-analysis/latest`);
    if (!response.ok()) {
      const errorText = await response.text();
      throw new Error(`Failed to get latest gap analysis: ${response.status()} ${errorText}`);
    }
    return await response.json();
  }

  async listGapAnalysisHistory(projectId: string, limit?: number) {
    const url = `${API_BASE_URL}/projects/${projectId}/gap-analysis/history${limit ? `?limit=${limit}` : ''}`;
    const response = await this.api.get(url);
    expect(response.ok()).toBeTruthy();
    return await response.json();
  }

  // Project Intel API helpers
  async rebuildProjectIntel(projectId: string) {
    const response = await this.api.post(`${API_BASE_URL}/projects/${projectId}/ideas/rebuild`);
    expect(response.ok()).toBeTruthy();
    return await response.json();
  }

  async listProjectIntelCandidates(projectId: string) {
    const response = await this.api.get(`${API_BASE_URL}/projects/${projectId}/ideas/candidates`);
    expect(response.ok()).toBeTruthy();
    return await response.json();
  }

  async listProjectIntelClusters(projectId: string) {
    const response = await this.api.get(`${API_BASE_URL}/projects/${projectId}/ideas/clusters`);
    expect(response.ok()).toBeTruthy();
    return await response.json();
  }

  async listProjectIntelTickets(projectId: string) {
    const response = await this.api.get(`${API_BASE_URL}/projects/${projectId}/ideas/tickets`);
    expect(response.ok()).toBeTruthy();
    return await response.json();
  }

  async updateProjectIntelTicket(projectId: string, ticketId: string, updates: any) {
    const response = await this.api.patch(`${API_BASE_URL}/projects/${projectId}/ideas/tickets/${ticketId}`, {
      data: updates,
    });
    if (!response.ok()) {
      const errorText = await response.text();
      throw new Error(`Failed to update project intel ticket: ${response.status()} ${errorText}`);
    }
    return await response.json();
  }

  // Mode API helpers
  async getProjectMode(projectId: string) {
    const response = await this.api.get(`${API_BASE_URL}/projects/${projectId}/mode`);
    expect(response.ok()).toBeTruthy();
    return await response.json();
  }

  async updateProjectMode(projectId: string, updates: any) {
    const response = await this.api.patch(`${API_BASE_URL}/projects/${projectId}/mode`, {
      data: updates,
    });
    if (!response.ok()) {
      const errorText = await response.text();
      throw new Error(`Failed to update project mode: ${response.status()} ${errorText}`);
    }
    return await response.json();
  }

  // System API helpers
  async getHealth() {
    const response = await this.api.get(`${API_BASE_URL}/system/health`);
    expect(response.ok()).toBeTruthy();
    return await response.json();
  }

  async getReady() {
    const response = await this.api.get(`${API_BASE_URL}/system/ready`);
    expect(response.ok()).toBeTruthy();
    return await response.json();
  }

  async getSystemStatus() {
    const response = await this.api.get(`${API_BASE_URL}/system/status`);
    expect(response.ok()).toBeTruthy();
    return await response.json();
  }

  // Auth API helpers
  async getToken(username: string, password: string = 'password') {
    const formData = new URLSearchParams();
    formData.append('username', username);
    formData.append('password', password);
    const response = await this.api.post(`${API_BASE_URL}/token`, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      data: formData.toString(),
    });
    if (!response.ok()) {
      const errorText = await response.text();
      throw new Error(`Failed to get token: ${response.status()} ${errorText}`);
    }
    return await response.json();
  }
}

import { expect } from '@playwright/test';

// Re-export expect for convenience
export { expect };

