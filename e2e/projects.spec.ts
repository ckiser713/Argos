import { test, expect } from './fixtures';
import { ApiHelpers } from './utils/api-helpers';

test.describe('Projects', () => {
  test('should create a new project', async ({ api }) => {
    const apiHelpers = new ApiHelpers(api);
    
    const project = await apiHelpers.createProject('E2E Test Project');
    
    expect(project).toHaveProperty('id');
    expect(project.name).toBe('E2E Test Project');
    
    // Cleanup
    await apiHelpers.deleteProject(project.id);
  });

  test('should list projects', async ({ api }) => {
    const apiHelpers = new ApiHelpers(api);
    
    // Create a test project
    const project = await apiHelpers.createProject('List Test Project');
    
    // List projects
    const response = await api.get('http://localhost:8000/api/projects');
    expect(response.ok()).toBeTruthy();
    const projects = await response.json();
    
    expect(Array.isArray(projects.items || projects)).toBeTruthy();
    
    // Cleanup
    await apiHelpers.deleteProject(project.id);
  });

  test('should get project by ID', async ({ api }) => {
    const apiHelpers = new ApiHelpers(api);
    
    const createdProject = await apiHelpers.createProject('Get Test Project');
    
    const response = await api.get(`http://localhost:8000/api/projects/${createdProject.id}`);
    expect(response.ok()).toBeTruthy();
    const project = await response.json();
    
    expect(project.id).toBe(createdProject.id);
    expect(project.name).toBe('Get Test Project');
    
    // Cleanup
    await apiHelpers.deleteProject(createdProject.id);
  });
});


