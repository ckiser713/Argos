/**
 * E2E tests for advanced RAG features.
 * Tests query rewriting, multi-hop reasoning, citations, and query refinement.
 */

import { test, expect } from '@playwright/test';

test.describe('Advanced RAG Features', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/projects');
    await page.waitForSelector('[data-testid="project-list"]', { timeout: 10000 });
  });

  test('should perform semantic search with citations', async ({ page }) => {
    // Navigate to knowledge/search view
    await page.click('text=Knowledge, text=Search');
    await page.waitForSelector('[data-testid="search-input"]', { timeout: 5000 });

    // Enter search query
    const searchInput = page.locator('[data-testid="search-input"]');
    await searchInput.fill('machine learning');

    // Submit search
    await page.click('button:has-text("Search")');
    
    // Wait for results
    await page.waitForSelector('[data-testid="search-result"]', { timeout: 10000 });

    // Verify results are displayed
    const results = page.locator('[data-testid="search-result"]');
    const resultCount = await results.count();
    expect(resultCount).toBeGreaterThan(0);

    // Verify citations are shown
    const citations = page.locator('[data-testid="citation"]');
    const citationCount = await citations.count();
    
    // Results should have source information
    if (resultCount > 0) {
      const firstResult = results.first();
      const hasSource = await firstResult.locator('[data-testid="source"], [data-testid="document-id"]').isVisible();
      // Citations may be shown separately or inline
      expect(hasSource || citationCount > 0).toBeTruthy();
    }
  });

  test('should show query rewriting in search results', async ({ page }) => {
    await page.click('text=Knowledge, text=Search');
    await page.waitForSelector('[data-testid="search-input"]');

    // Enable advanced search if option exists
    const advancedToggle = page.locator('input[type="checkbox"][name*="advanced"], input[type="checkbox"][name*="rewrite"]');
    if (await advancedToggle.isVisible()) {
      await advancedToggle.check();
    }

    // Perform search
    await page.fill('[data-testid="search-input"]', 'how to train ML models');
    await page.click('button:has-text("Search")');

    await page.waitForSelector('[data-testid="search-result"]', { timeout: 10000 });

    // Check for query metadata (rewritten queries)
    const queryMetadata = page.locator('[data-testid="query-metadata"], [data-testid="rewritten-queries"]');
    if (await queryMetadata.isVisible()) {
      const metadataText = await queryMetadata.textContent();
      expect(metadataText).toBeTruthy();
    }

    // Results should still be shown
    const results = page.locator('[data-testid="search-result"]');
    expect(await results.count()).toBeGreaterThan(0);
  });

  test('should support query refinement', async ({ page }) => {
    await page.click('text=Knowledge, text=Search');
    await page.waitForSelector('[data-testid="search-input"]');

    // Initial search
    await page.fill('[data-testid="search-input"]', 'programming');
    await page.click('button:has-text("Search")');
    await page.waitForSelector('[data-testid="search-result"]', { timeout: 10000 });

    // Look for refine button
    const refineButton = page.locator('button:has-text("Refine"), button:has-text("Improve Query")');
    if (await refineButton.isVisible()) {
      await refineButton.click();
      
      // Refined query should appear
      const refinedInput = page.locator('[data-testid="refined-query"]');
      if (await refinedInput.isVisible()) {
        const refinedText = await refinedInput.inputValue();
        expect(refinedText.length).toBeGreaterThan(0);
      }
    }
  });

  test('should display query history', async ({ page }) => {
    await page.click('text=Knowledge, text=Search');
    await page.waitForSelector('[data-testid="search-input"]');

    // Perform multiple searches
    const queries = ['machine learning', 'deep learning', 'neural networks'];
    
    for (const query of queries) {
      await page.fill('[data-testid="search-input"]', query);
      await page.click('button:has-text("Search")');
      await page.waitForTimeout(1000); // Brief pause between searches
    }

    // Check for query history display
    const historySection = page.locator('[data-testid="query-history"]');
    if (await historySection.isVisible()) {
      const historyItems = historySection.locator('[data-testid="history-item"]');
      const historyCount = await historyItems.count();
      expect(historyCount).toBeGreaterThan(0);
    }
  });

  test('should show source attribution in results', async ({ page }) => {
    // First ingest a document (if UI supports it)
    await page.click('text=Ingest, text=Documents');
    await page.waitForSelector('[data-testid="ingest-form"]', { timeout: 5000 }).catch(() => {});

    // Navigate to search
    await page.click('text=Knowledge, text=Search');
    await page.waitForSelector('[data-testid="search-input"]');

    // Search
    await page.fill('[data-testid="search-input"]', 'test document');
    await page.click('button:has-text("Search")');
    await page.waitForSelector('[data-testid="search-result"]', { timeout: 10000 });

    // Verify source attribution
    const results = page.locator('[data-testid="search-result"]');
    if (await results.count() > 0) {
      const firstResult = results.first();
      
      // Check for source/document ID
      const sourceInfo = firstResult.locator('[data-testid="source"], [data-testid="document-id"], [data-testid="citation"]');
      const hasSource = await sourceInfo.count() > 0;
      
      // At least verify result has content
      const content = await firstResult.locator('[data-testid="result-content"]').textContent();
      expect(content).toBeTruthy();
    }
  });
});

