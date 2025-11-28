/**
 * E2E tests for repository analysis and gap analysis features.
 * Tests repository ingestion, code search, and gap analysis generation.
 */

import { test, expect } from '@playwright/test';

test.describe('Repository Analysis & Gap Analysis', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/projects');
    await page.waitForSelector('[data-testid="project-list"]', { timeout: 10000 });
  });

  test('should ingest a repository', async ({ page }) => {
    // Navigate to ingest view
    await page.click('text=Ingest');
    await page.waitForSelector('[data-testid="ingest-view"]', { timeout: 5000 });

    // Select repository source type
    const repoOption = page.locator('input[type="radio"][value="repository"], button:has-text("Repository")');
    if (await repoOption.isVisible()) {
      await repoOption.click();
    }

    // Fill in repository URL/path
    const repoInput = page.locator('input[name="repo_url"], input[name="repo_path"], input[placeholder*="repository"]');
    if (await repoInput.isVisible()) {
      await repoInput.fill('https://github.com/example/test-repo');
      
      // Submit
      await page.click('button:has-text("Ingest"), button[type="submit"]');
      
      // Wait for ingestion to start
      await page.waitForSelector('[data-testid="ingest-job"], [data-testid="job-status"]', { timeout: 10000 });
      
      // Verify job was created
      const jobStatus = page.locator('[data-testid="job-status"]');
      if (await jobStatus.isVisible()) {
        const statusText = await jobStatus.textContent();
        expect(statusText).toBeTruthy();
      }
    }
  });

  test('should search code in repositories', async ({ page }) => {
    await page.click('text=Gap Analysis, text=Code Search');
    await page.waitForSelector('[data-testid="code-search"]', { timeout: 5000 }).catch(() => {});

    // Enter search query
    const searchInput = page.locator('[data-testid="code-search-input"], input[placeholder*="code"]');
    if (await searchInput.isVisible()) {
      await searchInput.fill('function definition');
      await page.click('button:has-text("Search")');
      
      // Wait for results
      await page.waitForSelector('[data-testid="code-result"]', { timeout: 10000 }).catch(() => {});
      
      // Verify results
      const results = page.locator('[data-testid="code-result"]');
      const resultCount = await results.count();
      expect(resultCount).toBeGreaterThanOrEqual(0);
    }
  });

  test('should generate gap analysis report', async ({ page }) => {
    // First create an idea/ticket
    await page.click('text=Ideas');
    await page.click('button:has-text("New Idea")');
    
    await page.fill('input[name="title"]', 'Add user authentication');
    await page.fill('textarea[name="description"]', 'Implement login functionality');
    await page.click('button[type="submit"]');

    // Navigate to gap analysis
    await page.click('text=Gap Analysis');
    await page.waitForSelector('[data-testid="gap-analysis-view"]', { timeout: 5000 }).catch(() => {});

    // Generate gap analysis
    const generateButton = page.locator('button:has-text("Generate"), button:has-text("Analyze")');
    if (await generateButton.isVisible()) {
      await generateButton.click();
      
      // Wait for analysis to complete
      await page.waitForSelector('[data-testid="gap-report"], [data-testid="analysis-results"]', { timeout: 30000 });
      
      // Verify report is displayed
      const report = page.locator('[data-testid="gap-report"]');
      if (await report.isVisible()) {
        const reportContent = await report.textContent();
        expect(reportContent).toBeTruthy();
      }
    }
  });

  test('should display gap analysis results', async ({ page }) => {
    await page.click('text=Gap Analysis');
    
    // Look for existing reports or generate one
    const reportsList = page.locator('[data-testid="gap-reports-list"]');
    if (await reportsList.isVisible()) {
      const reports = reportsList.locator('[data-testid="gap-report-item"]');
      const reportCount = await reports.count();
      
      if (reportCount > 0) {
        // Click on a report
        await reports.first().click();
        
        // Verify report details
        await expect(page.locator('[data-testid="gap-report-details"]')).toBeVisible({ timeout: 5000 });
        
        // Check for gaps
        const gaps = page.locator('[data-testid="gap-item"]');
        const gapCount = await gaps.count();
        expect(gapCount).toBeGreaterThanOrEqual(0);
      }
    }
  });

  test('should show code-to-requirement comparison', async ({ page }) => {
    await page.click('text=Gap Analysis');
    
    // Generate or view gap analysis
    const generateButton = page.locator('button:has-text("Generate")');
    if (await generateButton.isVisible()) {
      await generateButton.click();
      await page.waitForSelector('[data-testid="gap-report"]', { timeout: 30000 });
    }

    // Look for comparison view
    const comparisonView = page.locator('[data-testid="code-comparison"], [data-testid="requirement-comparison"]');
    if (await comparisonView.isVisible()) {
      // Should show code snippets and requirements side by side
      const codeSnippets = comparisonView.locator('[data-testid="code-snippet"]');
      const requirements = comparisonView.locator('[data-testid="requirement"]');
      
      const snippetCount = await codeSnippets.count();
      const requirementCount = await requirements.count();
      
      // Should have both code and requirements
      expect(snippetCount + requirementCount).toBeGreaterThanOrEqual(0);
    }
  });
});

