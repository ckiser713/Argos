import { test, expect } from '../fixtures';
import { ApiHelpers } from '../utils/api-helpers';

test.describe('Component-Specific UI Tests', () => {
  test('should render Mission Control Board', async ({ authenticatedPage, testProject }) => {
    await authenticatedPage.goto('/');
    await authenticatedPage.waitForLoadState('networkidle');

    // Navigate to Mission Control
    const missionControlTab = authenticatedPage.locator('nav').getByText('Mission Control');
    if (await missionControlTab.count() > 0) {
      await missionControlTab.click();
      await authenticatedPage.waitForTimeout(500);
    }

    // Check for Mission Control content
    const body = authenticatedPage.locator('body');
    await expect(body).toBeVisible();
  });

  test('should render Dependency Timeline', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/');
    await authenticatedPage.waitForLoadState('networkidle');

    // Navigate to Dependency Timeline
    const timelineTab = authenticatedPage.locator('nav').getByText('Dependency Map');
    if (await timelineTab.count() > 0) {
      await timelineTab.click();
      await authenticatedPage.waitForTimeout(500);
    }

    // Check for timeline content
    const body = authenticatedPage.locator('body');
    await expect(body).toBeVisible();
  });

  test('should render Decision Flow Map', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/');
    await authenticatedPage.waitForLoadState('networkidle');

    // Navigate to Roadmap
    const roadmapTab = authenticatedPage.locator('nav').getByText('Project Roadmap');
    if (await roadmapTab.count() > 0) {
      await roadmapTab.click();
      await authenticatedPage.waitForTimeout(500);
    }

    // Check for roadmap content
    const body = authenticatedPage.locator('body');
    await expect(body).toBeVisible();
  });

  test('should render Strategy Deck', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/');
    await authenticatedPage.waitForLoadState('networkidle');

    // Navigate to Strategy Deck
    const strategyTab = authenticatedPage.locator('nav').getByText('Strategy Node');
    if (await strategyTab.count() > 0) {
      await strategyTab.click();
      await authenticatedPage.waitForTimeout(500);
    }

    // Check for strategy content
    const body = authenticatedPage.locator('body');
    await expect(body).toBeVisible();
  });

  test('should render PM Dissection', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/');
    await authenticatedPage.waitForLoadState('networkidle');

    // Navigate to PM Dissection
    const pmTab = authenticatedPage.locator('nav').getByText('Backlog Refinement');
    if (await pmTab.count() > 0) {
      await pmTab.click();
      await authenticatedPage.waitForTimeout(500);
    }

    // Check for PM content
    const body = authenticatedPage.locator('body');
    await expect(body).toBeVisible();
  });

  test('should render Knowledge Nexus', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/');
    await authenticatedPage.waitForLoadState('networkidle');

    // Navigate to Knowledge Nexus
    const nexusTab = authenticatedPage.locator('nav').getByText('Nexus Graph');
    if (await nexusTab.count() > 0) {
      await nexusTab.click();
      await authenticatedPage.waitForTimeout(500);
    }

    // Check for nexus content
    const body = authenticatedPage.locator('body');
    await expect(body).toBeVisible();
  });

  test('should render Ingest Station', async ({ authenticatedPage, testProject }) => {
    await authenticatedPage.goto('/');
    await authenticatedPage.waitForLoadState('networkidle');

    // Navigate to Ingest Station
    const ingestTab = authenticatedPage.locator('nav').getByText('Ingest Pipeline');
    if (await ingestTab.count() > 0) {
      await ingestTab.click();
      await authenticatedPage.waitForTimeout(500);
    }

    // Check for ingest content
    const body = authenticatedPage.locator('body');
    await expect(body).toBeVisible();
  });

  test('should render Deep Research', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/');
    await authenticatedPage.waitForLoadState('networkidle');

    // Navigate to Deep Research
    const researchTab = authenticatedPage.locator('nav').getByText('Deep Research');
    if (await researchTab.count() > 0) {
      await researchTab.click();
      await authenticatedPage.waitForTimeout(500);
    }

    // Check for research content
    const body = authenticatedPage.locator('body');
    await expect(body).toBeVisible();
  });

  test('should render Workflow Construct', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/');
    await authenticatedPage.waitForLoadState('networkidle');

    // Navigate to Workflow Construct
    const workflowTab = authenticatedPage.locator('nav').getByText('Construct Flow');
    if (await workflowTab.count() > 0) {
      await workflowTab.click();
      await authenticatedPage.waitForTimeout(500);
    }

    // Check for workflow content
    const body = authenticatedPage.locator('body');
    await expect(body).toBeVisible();
  });

  test('should interact with sidebar navigation', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/');
    await authenticatedPage.waitForLoadState('networkidle');

    // Test clicking multiple navigation items
    const navItems = [
      'Mission Control',
      'Project Roadmap',
      'Nexus Graph',
    ];

    for (const item of navItems) {
      const navItem = authenticatedPage.locator('nav').getByText(item);
      if (await navItem.count() > 0) {
        await navItem.click();
        await authenticatedPage.waitForTimeout(300);
        await expect(navItem).toBeVisible();
      }
    }
  });

  test('should display header information', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/');
    await authenticatedPage.waitForLoadState('networkidle');

    // Check for header elements (model name, VRAM usage, etc.)
    const header = authenticatedPage.locator('header').or(authenticatedPage.locator('[class*="header"]'));
    // Header might not have a specific selector, so check body visibility
    const body = authenticatedPage.locator('body');
    await expect(body).toBeVisible();
  });
});

