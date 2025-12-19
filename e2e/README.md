# E2E Tests

End-to-end tests for Cortex using Playwright.

## Setup

1. Install dependencies:
```bash
pnpm install
```

2. Install Playwright browsers:
```bash
pnpm exec playwright install --with-deps
```

## Running Tests

### Run all tests
```bash
pnpm e2e
```

### Run tests in UI mode (interactive)
```bash
pnpm e2e:ui
```

### Run tests in debug mode
```bash
pnpm e2e:debug
```

### Run specific test file
```bash
pnpm exec playwright test e2e/projects.spec.ts
```

### Run tests in headed mode (see browser)
```bash
pnpm exec playwright test --headed
```

### Run tests for specific browser
```bash
pnpm exec playwright test --project=chromium
pnpm exec playwright test --project=firefox
pnpm exec playwright test --project=webkit
```

### View test report
```bash
pnpm e2e:report
```

## Test Structure

### Core Test Files
- `fixtures.ts` - Custom Playwright fixtures (API client, authenticated page, test project)
- `utils/api-helpers.ts` - Helper functions for API operations
- `utils/test-data-factory.ts` - Test data generation utilities
- `utils/websocket-client.ts` - WebSocket client for real-time testing

### Test Suites

#### API Tests
- `projects.spec.ts` - Project CRUD operations
- `ingest.spec.ts` - Ingest job management
- `agent-runs.spec.ts` - Agent run operations
- `context.spec.ts` - Context management
- `roadmap.spec.ts` - Roadmap CRUD
- `knowledge.spec.ts` - Knowledge graph operations

#### Advanced Tests
- `websocket.spec.ts` - Basic WebSocket/streaming tests
- `websocket-full.spec.ts` - Full WebSocket implementation tests
- `edge-cases.spec.ts` - Error handling and boundary conditions
- `performance.spec.ts` - Performance and load testing
- `visual-regression.spec.ts` - Screenshot comparison tests
- `accessibility.spec.ts` - WCAG compliance and accessibility tests
- `cross-browser.spec.ts` - Cross-browser compatibility tests

#### UI Tests
- `ui/components.spec.ts` - Basic UI component tests
- `ui/components-detailed.spec.ts` - Detailed component-specific tests
- `example.spec.ts` - Frontend UI examples

## Test Categories

### Visual Regression Tests
Visual regression tests compare screenshots to detect visual changes:
```bash
pnpm exec playwright test e2e/visual-regression.spec.ts
```

Screenshots are stored in `test-results/` and compared against baseline images.

### WebSocket Tests
Full WebSocket client implementation for testing real-time features:
```bash
pnpm exec playwright test e2e/websocket-full.spec.ts
```

### Accessibility Tests
Accessibility tests using axe-core and WCAG guidelines:
```bash
pnpm exec playwright test e2e/accessibility.spec.ts
```

### Cross-Browser Tests
Tests run on multiple browsers:
- Chromium (Chrome/Edge)
- Firefox
- WebKit (Safari)
- Mobile Chrome (Android)
- Mobile Safari (iOS)
- Tablet Chrome (iPad)

```bash
# Run on all browsers
pnpm e2e

# Run on specific browser
pnpm exec playwright test --project=firefox
```

## Test Environment

Tests run against:
- Backend: `http://localhost:8000`
- Frontend: `http://localhost:5173`
- Qdrant: `http://localhost:6333` (via Docker)

The test environment uses:
- Test database: `test_atlas.db` (separate from dev)
- Environment: `ARGOS_ENV=test`
- Auth: Disabled (`ARGOS_SKIP_AUTH=true`)

## Writing New Tests

### API Tests

```typescript
import { test, expect } from './fixtures';
import { ApiHelpers } from './utils/api-helpers';

test.describe('Feature Name', () => {
  test('should do something', async ({ api, testProject }) => {
    const apiHelpers = new ApiHelpers(api);
    
    // Your test code here
    const result = await apiHelpers.someMethod(testProject.id);
    
    expect(result).toHaveProperty('expectedField');
  });
});
```

### Frontend Tests

```typescript
import { test, expect } from './fixtures';

test.describe('UI Feature', () => {
  test('should display something', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/some-page');
    
    await expect(authenticatedPage.locator('[data-testid="element"]')).toBeVisible();
  });
});
```

### Visual Regression Tests

```typescript
test('should match screenshot', async ({ authenticatedPage }) => {
  await authenticatedPage.goto('/');
  await expect(authenticatedPage).toHaveScreenshot('page-name.png');
});
```

### Accessibility Tests

```typescript
test('should be accessible', async ({ authenticatedPage }) => {
  await authenticatedPage.goto('/');
  
  // Use axe-core or Playwright's accessibility API
  const snapshot = await authenticatedPage.accessibility.snapshot();
  expect(snapshot).toBeTruthy();
});
```

## CI/CD

Tests run automatically on:
- Push to `main` or `develop` branches
- Pull requests
- Manual workflow dispatch

See `.github/workflows/e2e.yml` for CI configuration.

## Debugging

1. Use `pnpm e2e:debug` to run tests in debug mode
2. Use `pnpm e2e:ui` for interactive test running
3. Check `playwright-report/` for test reports
4. Screenshots are saved on test failures
5. Videos are saved for failed tests

## Visual Regression

Visual regression tests compare screenshots:
- Baseline images: `test-results/`
- Comparison threshold: 0.2 (20% difference allowed)
- Max diff pixels: 100

To update baseline images:
```bash
pnpm exec playwright test --update-snapshots
```

## Accessibility Testing

Accessibility tests use:
- Playwright's built-in accessibility API
- axe-core for comprehensive scanning
- WCAG 2.1 guidelines

## Cross-Browser Testing

Tests run on:
- Desktop: Chrome, Firefox, Safari
- Mobile: Chrome (Android), Safari (iOS)
- Tablet: Chrome (iPad)

All browsers are tested automatically in CI.

## Notes

- Tests use a separate test database to avoid affecting dev data
- Test projects are automatically cleaned up after tests
- Tests run in parallel by default (configurable)
- Screenshots are saved on test failures
- Videos are saved for failed tests
- CI runs tests on every push/PR to main/develop branches
