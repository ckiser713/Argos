# Feature Specification: Database Persistence Migration

## Overview
Migration plan for converting in-memory services to database-backed persistence, ensuring data durability, scalability, and consistency.

## Current State
- `IdeaService` uses in-memory `Dict[str, IdeaTicket]`
- `ContextService` uses in-memory `Dict[str, ContextItem]`
- `WorkflowService` uses in-memory dictionaries
- `GapAnalysisRepo` uses in-memory storage
- No data persistence across restarts
- No project-scoped queries
- Limited scalability

## Target State
- All services use database persistence (SQLite for dev, PostgreSQL for prod)
- Data persists across service restarts
- Project-scoped operations supported
- Efficient querying with indexes
- Transaction support for consistency
- Migration path from in-memory to database

## Requirements

### Functional Requirements
1. All CRUD operations persist to database
2. Data survives service restarts
3. Project-scoped queries work correctly
4. Transactions ensure data consistency
5. Migration script converts existing in-memory data
6. Rollback capability if migration fails

### Non-Functional Requirements
1. Query performance < 100ms for typical operations
2. Support for 10,000+ records per project
3. Concurrent access handled correctly
4. Database connection pooling
5. Error handling for database failures

## Technical Design

### Database Schema

#### Idea Tickets Table
```sql
CREATE TABLE idea_tickets (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    status TEXT NOT NULL,
    priority TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(project_id) REFERENCES projects(id)
);

CREATE INDEX idx_idea_tickets_project ON idea_tickets(project_id);
CREATE INDEX idx_idea_tickets_status ON idea_tickets(status);
```

#### Context Items Table
```sql
CREATE TABLE context_items (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    tokens INTEGER NOT NULL,
    pinned INTEGER NOT NULL DEFAULT 0,
    canonical_document_id TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(project_id) REFERENCES projects(id)
);

CREATE INDEX idx_context_items_project ON context_items(project_id);
CREATE INDEX idx_context_items_pinned ON context_items(pinned);
```

#### Workflow Graphs Table
```sql
CREATE TABLE workflow_graphs (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    graph_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(project_id) REFERENCES projects(id)
);
```

#### Workflow Runs Table
```sql
CREATE TABLE workflow_runs (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    workflow_id TEXT NOT NULL,
    status TEXT NOT NULL,
    input_json TEXT,
    output_json TEXT,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    last_message TEXT,
    FOREIGN KEY(project_id) REFERENCES projects(id),
    FOREIGN KEY(workflow_id) REFERENCES workflow_graphs(id)
);

CREATE INDEX idx_workflow_runs_project ON workflow_runs(project_id);
CREATE INDEX idx_workflow_runs_status ON workflow_runs(status);
```

#### Workflow Node States Table
```sql
CREATE TABLE workflow_node_states (
    run_id TEXT NOT NULL,
    node_id TEXT NOT NULL,
    status TEXT NOT NULL,
    progress REAL NOT NULL DEFAULT 0,
    messages_json TEXT,
    started_at TEXT,
    completed_at TEXT,
    error TEXT,
    PRIMARY KEY (run_id, node_id),
    FOREIGN KEY(run_id) REFERENCES workflow_runs(id)
);
```

### Implementation Approach

#### 1. Repository Pattern
- Create repository interfaces for each service
- Implement database repositories
- Keep service layer unchanged (dependency injection)

#### 2. Migration Script
- Create Alembic migrations
- Migrate existing in-memory data
- Validate data integrity
- Support rollback

#### 3. Service Updates
- Update services to use repositories
- Add project-scoped methods
- Implement transaction support
- Add error handling

### API Changes
- No breaking changes to API
- All endpoints remain the same
- Response formats unchanged
- Performance improvements transparent

### Database Changes
- New tables created via migrations
- Indexes added for performance
- Foreign key constraints enforced
- Data validation at database level

### Frontend Changes
- No changes required
- Existing API calls work unchanged
- Performance improvements transparent

## Testing Strategy

### Unit Tests
- Test repository implementations
- Test service layer with mocked repositories
- Test migration scripts
- Test error handling

### Integration Tests
- Test database operations end-to-end
- Test concurrent access
- Test transaction rollback
- Test migration scripts

### Performance Tests
- Test query performance with large datasets
- Test concurrent operations
- Test connection pooling
- Test index usage

## Dependencies

### Blocking Dependencies
- Database migration framework (Alembic)
- Database driver (psycopg for PostgreSQL, sqlite3 for SQLite)
- ORM or raw SQL library

### Non-Blocking Dependencies
- Connection pooling library
- Database monitoring tools

## Implementation Steps

1. **Phase 1: Schema Design**
   - Design database schemas
   - Create migration scripts
   - Review with team

2. **Phase 2: Repository Implementation**
   - Implement repository interfaces
   - Implement database repositories
   - Write unit tests

3. **Phase 3: Service Updates**
   - Update services to use repositories
   - Add project-scoped methods
   - Update error handling

4. **Phase 4: Migration**
   - Create migration script
   - Test migration on sample data
   - Execute migration in dev environment

5. **Phase 5: Testing**
   - Run integration tests
   - Performance testing
   - Load testing

6. **Phase 6: Deployment**
   - Deploy to staging
   - Monitor performance
   - Deploy to production

## Success Criteria

1. All services use database persistence
2. Data persists across restarts
3. Project-scoped queries work correctly
4. Query performance meets requirements
5. Migration completes successfully
6. No data loss during migration
7. Rollback tested and working

## Risks and Mitigation

### Risk: Data Loss During Migration
- **Mitigation**: Backup all data before migration, test migration on copy

### Risk: Performance Degradation
- **Mitigation**: Add indexes, optimize queries, use connection pooling

### Risk: Concurrent Access Issues
- **Mitigation**: Use transactions, implement proper locking, test concurrency

### Risk: Migration Failure
- **Mitigation**: Support rollback, test migration thoroughly, have rollback plan

## Notes

- Start with SQLite for development
- Migrate to PostgreSQL for production
- Use connection pooling for performance
- Monitor database performance
- Consider read replicas for scaling

