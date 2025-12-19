# Model Lanes E2E Testing Guide

## Overview

End-to-end tests for Model Lanes verify that:
1. Lane routing works correctly
2. Services use appropriate lanes
3. Fallback logic functions properly
4. Configuration is loaded correctly

## Test File

**Location**: `e2e/model-lanes.spec.ts`

## Running Tests

```bash
# Run all Model Lanes tests
pnpm exec playwright test e2e/model-lanes.spec.ts

# Run specific test suite
pnpm exec playwright test e2e/model-lanes.spec.ts -g "Lane Configuration"
pnpm exec playwright test e2e/model-lanes.spec.ts -g "Service Lane Routing"

# Run in UI mode for debugging
pnpm exec playwright test e2e/model-lanes.spec.ts --ui
```

## Test Suites

### 1. Lane Configuration Tests

Tests that verify lane configuration and availability:

- **`should get available model lanes`**: Verifies lane endpoint returns expected lanes
- **`should resolve lane configuration with fallback`**: Tests fallback behavior

### 2. Service Lane Routing Tests

Tests that verify services route to correct lanes:

- **`roadmap generation should use ORCHESTRATOR lane`**: Tests roadmap generation uses ORCHESTRATOR
- **`RAG search should use FAST_RAG lane`**: Tests RAG queries use FAST_RAG
- **`gap analysis should use CODER lane`**: Tests gap analysis uses CODER

### 3. Deep Ingest Detection Tests

Tests for large file and repository detection:

- **`should detect large files for deep ingest`**: Tests file size detection (>50MB)
- **`should detect repositories for deep ingest`**: Tests repository detection

### 4. Fallback Behavior Tests

Tests fallback logic when lanes aren't configured:

- **`should fallback to default lane when specific lane not configured`**: Verifies fallback works

### 5. Code Analysis Tests

Tests repository analysis with CODER lane:

- **`repo analysis should support CODER lane`**: Tests repo indexing

### 6. Configuration Validation Tests

Tests that system handles missing configuration gracefully:

- **`should handle missing lane configuration gracefully`**: Verifies graceful degradation

## Test Environment

Tests run against:
- **Backend**: `http://localhost:8000` (auto-started)
- **Database**: `test_atlas.db` (isolated)
- **Models**: May not be available (tests handle gracefully)

## Expected Behavior

### When LLM is Available

- Tests should complete successfully
- Lane routing should work correctly
- Services should use appropriate lanes

### When LLM is Unavailable

- Tests should still verify routing logic
- Configuration should be validated
- Fallback should be tested
- Tests skip actual LLM calls gracefully

## Notes

- Tests are designed to work even without actual LLM models
- Configuration and routing logic is tested independently
- Actual LLM calls may fail if models aren't available (expected)
- Tests verify the system handles missing models gracefully

## Integration with CI/CD

These tests run as part of the E2E test suite in CI/CD:

```yaml
# .github/workflows/e2e.yml
- name: Run E2E tests
  run: pnpm exec playwright test
```

## Future Enhancements

- Add tests for actual LLM responses (requires models)
- Add performance tests for lane switching
- Add tests for OOM detection and fallback
- Add tests for health checking

