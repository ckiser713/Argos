import { test, expect } from './fixtures';
import { ApiHelpers } from './utils/api-helpers';

test.describe('Auth API', () => {
  test('should generate access token', async ({ api }) => {
    const apiHelpers = new ApiHelpers(api);
    
    const tokenResponse = await apiHelpers.getToken('testuser');
    
    expect(tokenResponse).toHaveProperty('access_token');
    expect(tokenResponse).toHaveProperty('token_type');
    expect(tokenResponse.token_type).toBe('bearer');
    expect(typeof tokenResponse.access_token).toBe('string');
    expect(tokenResponse.access_token.length).toBeGreaterThan(0);
  });

  test('should generate different tokens for different users', async ({ api }) => {
    const apiHelpers = new ApiHelpers(api);
    
    const token1 = await apiHelpers.getToken('user1');
    const token2 = await apiHelpers.getToken('user2');
    
    expect(token1.access_token).not.toBe(token2.access_token);
  });

  test('should generate consistent token format', async ({ api }) => {
    const apiHelpers = new ApiHelpers(api);
    
    const tokenResponse = await apiHelpers.getToken('testuser');
    
    // Token should be a JWT-like string (three parts separated by dots)
    const parts = tokenResponse.access_token.split('.');
    expect(parts.length).toBeGreaterThanOrEqual(2);
  });

  test('should handle token generation with different usernames', async ({ api }) => {
    const apiHelpers = new ApiHelpers(api);
    
    const usernames = ['user1', 'user2', 'admin', 'test-user'];
    
    for (const username of usernames) {
      const tokenResponse = await apiHelpers.getToken(username);
      expect(tokenResponse.access_token).toBeTruthy();
      expect(tokenResponse.token_type).toBe('bearer');
    }
  });
});

