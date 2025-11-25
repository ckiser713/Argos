# Cortex Specifications

This directory contains comprehensive specifications for unfinished work in the Cortex codebase, organized into three categories:

1. **Test Specifications** - Detailed test cases for unfinished features
2. **API Specifications** - API endpoint specifications and OpenAPI schemas
3. **Feature Specifications** - Implementation specifications for incomplete features

## Directory Structure

```
specs/
├── test-specs/
│   ├── backend/
│   │   ├── test-spec-ingest-api.md
│   │   ├── test-spec-roadmap-api.md
│   │   ├── test-spec-knowledge-api.md
│   │   ├── test-spec-context-api.md
│   │   ├── test-spec-agents-api.md
│   │   ├── test-spec-ideas-api.md
│   │   ├── test-spec-workflows-api.md
│   │   ├── test-spec-idea-service.md
│   │   ├── test-spec-context-service.md
│   │   ├── test-spec-workflow-service.md
│   │   └── test-spec-gap-analysis-repo.md
│   └── frontend/
│       ├── test-spec-ingest-station.md
│       ├── test-spec-mission-control.md
│       └── test-spec-hooks.md
├── api-specs/
│   ├── api-spec-ingest-endpoints.md
│   ├── api-spec-roadmap-endpoints.md
│   ├── api-spec-knowledge-endpoints.md
│   ├── api-spec-context-endpoints.md
│   ├── api-spec-agents-endpoints.md
│   ├── api-spec-ideas-endpoints.md
│   ├── api-spec-streaming-endpoints.md
│   ├── openapi-missing-endpoints.yaml
│   └── openapi-error-responses.yaml
└── feature-specs/
    ├── backend/
    │   ├── feature-spec-database-persistence.md
    │   ├── feature-spec-project-scoped-routes.md
    │   ├── feature-spec-ingest-deletion.md
    │   ├── feature-spec-roadmap-crud.md
    │   ├── feature-spec-agent-run-details.md
    │   └── feature-spec-context-management.md
    ├── frontend/
    │   ├── feature-spec-ingest-deletion-ui.md
    │   ├── feature-spec-mission-control-context.md
    │   ├── feature-spec-missing-hooks.md
    │   └── feature-spec-error-handling.md
    └── integration/
        ├── feature-spec-qdrant-integration.md
        ├── feature-spec-langgraph-integration.md
        └── feature-spec-streaming-events.md
```

## Test Specifications

Test specifications provide detailed test cases for unfinished features, including:
- Test scenarios and expected behavior
- Edge cases and error conditions
- Test data structures
- Dependencies and setup requirements

### Backend API Test Specs
- **test-spec-ingest-api.md** - DELETE endpoint, cancel operations, pagination, filtering
- **test-spec-roadmap-api.md** - Full CRUD operations, graph validation, node/edge management
- **test-spec-knowledge-api.md** - Graph operations, node/edge CRUD, search functionality
- **test-spec-context-api.md** - POST/PATCH endpoints, budget management, item operations
- **test-spec-agents-api.md** - Missing endpoints (get run, steps, messages, cancel)
- **test-spec-ideas-api.md** - Project-scoped routes, filtering, pagination
- **test-spec-workflows-api.md** - Workflow execution, node state management

### Service Test Specs
- **test-spec-idea-service.md** - Database persistence migration for IdeaService
- **test-spec-context-service.md** - Database persistence migration for ContextService
- **test-spec-workflow-service.md** - Database persistence migration for WorkflowService
- **test-spec-gap-analysis-repo.md** - Database migration for GapAnalysisRepo

### Frontend Test Specs
- **test-spec-ingest-station.md** - Delete mutation, error states, file upload
- **test-spec-mission-control.md** - Context derivation, drag-drop functionality
- **test-spec-hooks.md** - Missing React hooks and mutations

## API Specifications

API specifications document missing and incomplete endpoints, including:
- Endpoint definitions and parameters
- Request/response schemas
- Error responses
- Authentication requirements
- Examples

### Endpoint Specs
- **api-spec-ingest-endpoints.md** - DELETE, cancel, get job endpoints
- **api-spec-roadmap-endpoints.md** - Full CRUD for nodes/edges, graph operations
- **api-spec-knowledge-endpoints.md** - Graph operations, node/edge CRUD, search
- **api-spec-context-endpoints.md** - POST/PATCH endpoints, budget management
- **api-spec-agents-endpoints.md** - Get run, steps, messages, cancel endpoints
- **api-spec-ideas-endpoints.md** - Project-scoped routes structure
- **api-spec-streaming-endpoints.md** - WebSocket/SSE event specifications

### OpenAPI Schemas
- **openapi-missing-endpoints.yaml** - Complete OpenAPI 3.0 spec for missing endpoints
- **openapi-error-responses.yaml** - Standardized error response schemas

## Feature Specifications

Feature specifications provide detailed implementation plans for incomplete features, including:
- Current state analysis
- Target state definition
- Technical design
- Implementation steps
- Testing strategy
- Success criteria

### Backend Feature Specs
- **feature-spec-database-persistence.md** - Migration plan for in-memory services to database
- **feature-spec-project-scoped-routes.md** - Refactoring plan for project-scoped API structure
- **feature-spec-ingest-deletion.md** - Delete job endpoint specification
- **feature-spec-roadmap-crud.md** - Complete roadmap CRUD operations
- **feature-spec-agent-run-details.md** - Agent run details, steps, messages endpoints
- **feature-spec-context-management.md** - Context budget management, item operations

### Frontend Feature Specs
- **feature-spec-ingest-deletion-ui.md** - Delete mutation implementation in IngestStation
- **feature-spec-mission-control-context.md** - Context derivation from ticket data
- **feature-spec-missing-hooks.md** - React hooks for missing API endpoints
- **feature-spec-error-handling.md** - Comprehensive error handling across components

### Integration Feature Specs
- **feature-spec-qdrant-integration.md** - Vector database integration for knowledge graph
- **feature-spec-langgraph-integration.md** - LangGraph workflow execution integration
- **feature-spec-streaming-events.md** - Real-time event streaming implementation

## Usage

### For Developers
1. Review relevant test specs before implementing features
2. Follow API specs when implementing endpoints
3. Use feature specs as implementation guides
4. Reference OpenAPI schemas for API contracts

### For Testers
1. Use test specs to write comprehensive test suites
2. Follow test cases and edge cases specified
3. Verify implementations match specifications

### For Product/Project Managers
1. Review feature specs to understand scope
2. Use specs for planning and estimation
3. Track implementation progress against specs

## Key Files to Reference

- `../api-contract.md` - Existing API contract (source of truth)
- `backend/app/api/routes/*.py` - Current route implementations
- `backend/app/services/*.py` - Service implementations
- `frontend/components/*.tsx` - Frontend components with TODOs
- `frontend/src/hooks/*.ts` - Existing hooks
- `backend/tests/*.py` - Existing test patterns

## Notes

- All specifications follow consistent formats
- Specifications reference existing code patterns
- OpenAPI specs follow OpenAPI 3.0 standard
- Test specs provide actionable test cases
- Feature specs provide enough detail for implementation

## Status

All specification files have been created and are ready for use. They document all identified unfinished work in the Cortex codebase, providing clear guidance for implementation, testing, and API development.

