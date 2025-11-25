import { test, expect } from './fixtures';
import { ApiHelpers } from './utils/api-helpers';

test.describe('Context Management', () => {
  test('should get context budget', async ({ api, testProject }) => {
    const apiHelpers = new ApiHelpers(api);
    
    const context = await apiHelpers.getContext(testProject.id);
    
    expect(context).toHaveProperty('totalTokens');
    expect(context).toHaveProperty('usedTokens');
    expect(context).toHaveProperty('availableTokens');
    expect(context).toHaveProperty('items');
    expect(Array.isArray(context.items)).toBeTruthy();
  });

  test('should add context items', async ({ api, testProject }) => {
    const apiHelpers = new ApiHelpers(api);
    
    const result = await apiHelpers.addContextItems(testProject.id, [
      {
        id: undefined, // Let server generate
        name: 'test-document.pdf',
        type: 'PDF',
        tokens: 1000,
        pinned: false,
      },
    ]);
    
    expect(result).toHaveProperty('items');
    expect(result).toHaveProperty('budget');
    expect(result.items).toHaveLength(1);
    expect(result.items[0].name).toBe('test-document.pdf');
  });

  test('should update context item', async ({ api, testProject }) => {
    const apiHelpers = new ApiHelpers(api);
    
    // Add an item first
    const addResult = await apiHelpers.addContextItems(testProject.id, [
      {
        id: undefined,
        name: 'test-document.pdf',
        type: 'PDF',
        tokens: 1000,
        pinned: false,
      },
    ]);
    
    const itemId = addResult.items[0].id;
    
    // Update the item
    const response = await api.patch(
      `http://localhost:8000/api/projects/${testProject.id}/context/items/${itemId}`,
      {
        data: { pinned: true },
      }
    );
    
    expect(response.ok()).toBeTruthy();
    const updatedItem = await response.json();
    expect(updatedItem.pinned).toBe(true);
  });

  test('should remove context item', async ({ api, testProject }) => {
    const apiHelpers = new ApiHelpers(api);
    
    // Add an item first
    const addResult = await apiHelpers.addContextItems(testProject.id, [
      {
        id: undefined,
        name: 'test-document.pdf',
        type: 'PDF',
        tokens: 1000,
        pinned: false,
      },
    ]);
    
    const itemId = addResult.items[0].id;
    
    // Remove the item
    const response = await api.delete(
      `http://localhost:8000/api/projects/${testProject.id}/context/items/${itemId}`
    );
    
    expect(response.ok()).toBeTruthy();
    const budget = await response.json();
    expect(budget).toHaveProperty('budget');
  });

  test('should prevent budget overflow', async ({ api, testProject }) => {
    const apiHelpers = new ApiHelpers(api);
    
    // Get initial budget
    const context = await apiHelpers.getContext(testProject.id);
    const totalTokens = context.totalTokens;
    
    // Try to add items that exceed budget
    const response = await api.post(
      `http://localhost:8000/api/projects/${testProject.id}/context/items`,
      {
        data: {
          items: [
            {
              name: 'huge-document.pdf',
              type: 'PDF',
              tokens: totalTokens + 10000, // Exceeds budget
            },
          ],
        },
      }
    );
    
    // Should fail with 400
    expect(response.status()).toBe(400);
  });
});


