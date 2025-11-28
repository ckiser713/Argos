import { test, expect } from './fixtures';
import { ApiHelpers, WS_BASE_URL } from './utils/api-helpers';
import WebSocket from 'ws';

/**
 * WebSocket/Streaming Tests
 * 
 * Tests for real-time event streaming via WebSocket/SSE
 */
test.describe('WebSocket/Streaming', () => {
  test('should receive ingest job events', async ({ api, testProject }) => {
    const apiHelpers = new ApiHelpers(api);
    
    // Create an ingest job
    const job = await apiHelpers.createIngestJob(testProject.id, 'test-document.md');
    
    const wsUrl = `${WS_BASE_URL}/projects/${testProject.id}/ingest/${job.id}`;
    const message = await waitForFirstMessage(wsUrl);
    expect(message).toHaveProperty('type');
    expect(message.job?.id).toBe(job.id);
  });

  test('should receive agent run events', async ({ api, testProject }) => {
    const apiHelpers = new ApiHelpers(api);
    
    // Create an agent run
    const run = await apiHelpers.createAgentRun(
      testProject.id,
      'project_manager',
      'Test query'
    );

    const wsUrl = `${WS_BASE_URL}/projects/${testProject.id}/agent-runs/${run.id}`;
    const message = await waitForFirstMessage(wsUrl);
    expect(message).toHaveProperty('type');
    expect(message.run?.id).toBe(run.id);
    expect(message.run?.project_id ?? message.run?.projectId).toBe(testProject.id);
  });

});

async function waitForFirstMessage(url: string, timeoutMs = 5000): Promise<any> {
  return await new Promise((resolve, reject) => {
    const ws = new WebSocket(url);
    const timeout = setTimeout(() => {
      ws.terminate();
      reject(new Error(`No message received from ${url} within ${timeoutMs}ms`));
    }, timeoutMs);

    ws.on('message', (data: WebSocket.Data) => {
      clearTimeout(timeout);
      ws.close();
      try {
        resolve(JSON.parse(data.toString()));
      } catch (err) {
        reject(err);
      }
    });

    ws.on('error', (err) => {
      clearTimeout(timeout);
      reject(err);
    });
  });
}
