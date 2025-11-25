# Feature Specification: Project-Scoped Routes Refactoring

## Overview
Refactoring plan for converting API routes to project-scoped structure as specified in the API contract, ensuring consistent routing and data isolation.

## Current State
- Some routes are project-scoped (`/api/projects/{projectId}/...`)
- Some routes are not project-scoped (`/api/ingest/jobs`, `/api/ideas`)
- Inconsistent routing patterns
- API contract specifies project-scoped routes for all resources

## Target State
- All routes follow project-scoped pattern: `/api/projects/{projectId}/resource`
- Consistent routing across all endpoints
- Data isolation by project
- API matches contract specification

## Requirements

### Functional Requirements
1. All routes include `projectId` in path
2. Project validation on all requests
3. Data filtered by project automatically
4. Consistent error handling for invalid projects
5. Backward compatibility during transition (optional)

### Non-Functional Requirements
1. No performance degradation
2. Minimal code changes
3. Clear migration path

## Technical Design

### Route Structure Changes

#### Before
```
GET /api/ingest/jobs
GET /api/ideas
GET /api/context/items
```

#### After
```
GET /api/projects/{projectId}/ingest/jobs
GET /api/projects/{projectId}/ideas/candidates
GET /api/projects/{projectId}/context
```

### Implementation Approach

#### 1. Update Route Definitions
- Add `projectId` parameter to all routes
- Update route paths to include `/projects/{projectId}`
- Update route handlers to extract `projectId`

#### 2. Add Project Validation
- Create middleware for project validation
- Validate project exists and user has access
- Return 404 if project not found

#### 3. Update Service Layer
- Add `project_id` parameter to service methods
- Filter data by project in services
- Update repository queries

#### 4. Update Frontend
- Update API client to include `projectId` in paths
- Update hooks to pass `projectId`
- Update components to use project-scoped routes

### API Changes

#### Routes to Update
1. `/api/ingest/jobs` → `/api/projects/{projectId}/ingest/jobs`
2. `/api/ideas` → `/api/projects/{projectId}/ideas/candidates`
3. `/api/context/items` → `/api/projects/{projectId}/context/items`
4. `/api/agents/runs` → `/api/projects/{projectId}/agent-runs`
5. `/api/workflows/graphs` → `/api/projects/{projectId}/workflows/graphs`
6. `/api/knowledge/nodes` → `/api/projects/{projectId}/knowledge-graph/nodes`

### Database Changes
- No schema changes required
- Queries filtered by `project_id`
- Indexes on `project_id` columns

### Frontend Changes
- Update `cortexApi.ts` to include `projectId` in paths
- Update all hooks to accept `projectId`
- Update components to pass `projectId` from context

## Testing Strategy

### Unit Tests
- Test route parameter extraction
- Test project validation
- Test service layer filtering

### Integration Tests
- Test project-scoped queries
- Test invalid project handling
- Test data isolation

## Implementation Steps

1. **Phase 1: Update Backend Routes**
   - Update route definitions
   - Add project validation middleware
   - Update service methods

2. **Phase 2: Update Frontend**
   - Update API client
   - Update hooks
   - Update components

3. **Phase 3: Testing**
   - Test all endpoints
   - Test project isolation
   - Test error handling

4. **Phase 4: Deployment**
   - Deploy backend changes
   - Deploy frontend changes
   - Monitor for issues

## Success Criteria

1. All routes are project-scoped
2. Project validation works correctly
3. Data isolation verified
4. API matches contract specification
5. No breaking changes for valid requests
6. Error handling consistent

## Notes

- Consider backward compatibility during transition
- Update API documentation
- Update OpenAPI specs
- Communicate changes to team

