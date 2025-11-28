import { test, expect } from './fixtures';
import { ApiHelpers } from './utils/api-helpers';

test.describe('System API', () => {
  test('should return health check', async ({ api }) => {
    const apiHelpers = new ApiHelpers(api);
    
    const health = await apiHelpers.getHealth();
    
    expect(health).toHaveProperty('message');
    expect(health.message).toBe('ok');
  });

  test('should return readiness check', async ({ api }) => {
    const apiHelpers = new ApiHelpers(api);
    
    const ready = await apiHelpers.getReady();
    
    expect(ready).toHaveProperty('message');
    expect(ready.message).toBe('ready');
  });

  test('should return system status', async ({ api }) => {
    const apiHelpers = new ApiHelpers(api);
    
    const status = await apiHelpers.getSystemStatus();
    
    expect(status).toHaveProperty('gpu');
    expect(status).toHaveProperty('cpu');
    expect(status).toHaveProperty('memory');
    expect(status).toHaveProperty('context_tokens');
    expect(status).toHaveProperty('active_agent_runs');
    
    // Validate structure
    expect(typeof status.gpu).toBe('object');
    expect(typeof status.cpu).toBe('object');
    expect(typeof status.memory).toBe('object');
    expect(typeof status.context_tokens).toBe('object');
    expect(typeof status.active_agent_runs).toBe('number');
  });

  test('should have valid GPU metrics in system status', async ({ api }) => {
    const apiHelpers = new ApiHelpers(api);
    
    const status = await apiHelpers.getSystemStatus();
    
    if (status.gpu) {
      expect(status.gpu).toHaveProperty('vram_used_mb');
      expect(status.gpu).toHaveProperty('vram_total_mb');
      expect(typeof status.gpu.vram_used_mb).toBe('number');
      expect(typeof status.gpu.vram_total_mb).toBe('number');
    }
  });

  test('should have valid CPU metrics in system status', async ({ api }) => {
    const apiHelpers = new ApiHelpers(api);
    
    const status = await apiHelpers.getSystemStatus();
    
    if (status.cpu) {
      expect(status.cpu).toHaveProperty('usage_percent');
      expect(typeof status.cpu.usage_percent).toBe('number');
    }
  });

  test('should have valid memory metrics in system status', async ({ api }) => {
    const apiHelpers = new ApiHelpers(api);
    
    const status = await apiHelpers.getSystemStatus();
    
    if (status.memory) {
      expect(status.memory).toHaveProperty('used_mb');
      expect(status.memory).toHaveProperty('total_mb');
      expect(typeof status.memory.used_mb).toBe('number');
      expect(typeof status.memory.total_mb).toBe('number');
    }
  });

  test('should have valid context token metrics in system status', async ({ api }) => {
    const apiHelpers = new ApiHelpers(api);
    
    const status = await apiHelpers.getSystemStatus();
    
    if (status.context_tokens) {
      expect(status.context_tokens).toHaveProperty('used');
      expect(status.context_tokens).toHaveProperty('total');
      expect(typeof status.context_tokens.used).toBe('number');
      expect(typeof status.context_tokens.total).toBe('number');
    }
  });
});


