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
    const projects = await apiHelpers.listProjects();

    expect(Array.isArray(projects.items || projects)).toBeTruthy();

    // Cleanup
    await apiHelpers.deleteProject(project.id);
  });

  test('should get project by ID', async ({ api }) => {
    const apiHelpers = new ApiHelpers(api);
    
    const createdProject = await apiHelpers.createProject('Get Test Project');
    
    const project = await apiHelpers.getProject(createdProject.id);
    
    expect(project.id).toBe(createdProject.id);
    expect(project.name).toBe('Get Test Project');
    
    // Cleanup
    await apiHelpers.deleteProject(createdProject.id);
  });
});


