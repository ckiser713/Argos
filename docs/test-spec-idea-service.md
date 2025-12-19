# Test Specification: Idea Service Database Persistence Migration

## Purpose
Test specification for migrating IdeaService from in-memory storage to database persistence, ensuring data integrity, query performance, and backward compatibility.

## Current State
- `IdeaService` uses in-memory `Dict[str, IdeaTicket]`
- No persistence across service restarts
- No project-scoped queries
- No filtering or pagination support

## Target State
- Database-backed persistence using SQLite/PostgreSQL
- Project-scoped operations
- Support for filtering, pagination, and complex queries
- Data persistence across restarts
- Transaction support

## Test Cases

### 1. Database Schema Migration

#### 1.1 Create Ideas Table
- **Action**: Run migration script
- **Expected**: 
  - Table `idea_tickets` created with correct schema
  - Columns: id, project_id, title, description, status, priority, created_at, updated_at
  - Indexes created on project_id, status, priority
  - Foreign key constraint on project_id

#### 1.2 Migrate Existing In-Memory Data
- **Setup**: Service has in-memory ideas
- **Action**: Run migration script
- **Expected**: 
  - All in-memory ideas persisted to database
  - Data integrity maintained
  - Timestamps preserved

#### 1.3 Rollback Migration
- **Action**: Rollback migration
- **Expected**: 
  - Table dropped
  - No data loss (if backup exists)
  - Service can fall back to in-memory mode

### 2. Create Idea with Database

#### 2.1 Create Idea Persists to Database
- **Setup**: Fresh database
- **Action**: Call `create_idea(request)`
- **Expected**: 
  - Idea saved to database
  - Idea retrievable via `get_idea()`
  - Database row matches service return value

#### 2.2 Create Idea with Transaction
- **Setup**: Start transaction
- **Action**: Create idea, then rollback
- **Expected**: 
  - Idea not persisted after rollback
  - Database state unchanged

#### 2.3 Create Idea with Project ID
- **Request**: Includes `projectId`
- **Expected**: 
  - `project_id` stored correctly
  - Idea queryable by project

#### 2.4 Create Idea Generates Unique ID
- **Action**: Create multiple ideas
- **Expected**: 
  - Each idea has unique `id`
  - IDs are UUIDs or sequential (TBD)
  - No ID collisions

### 3. List Ideas with Database

#### 3.1 List All Ideas
- **Setup**: Create 10 ideas in database
- **Action**: Call `list_ideas()`
- **Expected**: 
  - Returns all 10 ideas
  - Results match database query
  - Order is consistent (by created_at DESC)

#### 3.2 List Ideas Filtered by Project
- **Setup**: Create ideas in project A and project B
- **Action**: Call `list_ideas(project_id="proj_a")`
- **Expected**: 
  - Returns only ideas from project A
  - Project B ideas excluded

#### 3.3 List Ideas Filtered by Status
- **Setup**: Create ideas with different statuses
- **Action**: Call `list_ideas(status=IdeaStatus.ACTIVE)`
- **Expected**: 
  - Returns only ACTIVE ideas
  - Other statuses excluded

#### 3.4 List Ideas with Pagination
- **Setup**: Create 100 ideas
- **Action**: Call `list_ideas(limit=20, cursor=None)`
- **Expected**: 
  - Returns first 20 ideas
  - Includes `nextCursor` for pagination
  - Subsequent calls with cursor return next page

#### 3.5 List Ideas with Combined Filters
- **Action**: Call `list_ideas(project_id="proj_a", status=IdeaStatus.ACTIVE)`
- **Expected**: 
  - Returns ideas matching ALL filters
  - Logical AND behavior

### 4. Get Idea with Database

#### 4.1 Get Existing Idea
- **Setup**: Create idea in database
- **Action**: Call `get_idea(idea_id)`
- **Expected**: 
  - Returns idea from database
  - All fields populated correctly
  - Matches database row

#### 4.2 Get Non-Existent Idea
- **Action**: Call `get_idea("nonexistent")`
- **Expected**: 
  - Returns `None`
  - No database error thrown

#### 4.3 Get Idea from Wrong Project
- **Setup**: Create idea in project A
- **Action**: Call `get_idea(idea_id, project_id="proj_b")`
- **Expected**: 
  - Returns `None` (if project-scoped)
  - Or returns idea (if not project-scoped)

### 5. Update Idea with Database

#### 5.1 Update Idea Persists Changes
- **Setup**: Create idea in database
- **Action**: Call `update_idea(idea_id, request)`
- **Expected**: 
  - Changes saved to database
  - `updated_at` timestamp updated
  - Subsequent `get_idea()` returns updated data

#### 5.2 Update Idea with Partial Fields
- **Request**: Only updates `status`
- **Expected**: 
  - Only `status` field updated
  - Other fields unchanged
  - `updated_at` updated

#### 5.3 Update Non-Existent Idea
- **Action**: Call `update_idea("nonexistent", request)`
- **Expected**: 
  - Returns `None`
  - No database error
  - No rows updated

#### 5.4 Update Idea with Transaction
- **Setup**: Start transaction
- **Action**: Update idea, then rollback
- **Expected**: 
  - Changes not persisted after rollback
  - Original data restored

### 6. Delete Idea with Database

#### 6.1 Delete Idea Removes from Database
- **Setup**: Create idea in database
- **Action**: Call `delete_idea(idea_id)`
- **Expected**: 
  - Idea removed from database
  - Subsequent `get_idea()` returns `None`
  - No orphaned records

#### 6.2 Delete Non-Existent Idea
- **Action**: Call `delete_idea("nonexistent")`
- **Expected**: 
  - No error thrown
  - Idempotent operation

#### 6.3 Delete Idea with Foreign Key Constraints
- **Setup**: Idea referenced by other entities
- **Action**: Call `delete_idea(idea_id)`
- **Expected**: 
  - Behavior depends on cascade rules
  - Either: deletion prevented (error)
  - Or: cascading deletion of related entities

### 7. Query Performance

#### 7.1 List Ideas Performance
- **Setup**: Create 10,000 ideas
- **Action**: Measure `list_ideas()` execution time
- **Expected**: 
  - Query completes in < 100ms (with indexes)
  - Uses database indexes efficiently
  - No full table scan

#### 7.2 Filtered Query Performance
- **Setup**: Create 10,000 ideas across 100 projects
- **Action**: Measure `list_ideas(project_id="proj_1")` execution time
- **Expected**: 
  - Query uses index on `project_id`
  - Completes in < 50ms
  - Returns only relevant results

#### 7.3 Pagination Performance
- **Setup**: Create 10,000 ideas
- **Action**: Measure paginated queries
- **Expected**: 
  - Each page loads in < 50ms
  - Cursor-based pagination efficient
  - No performance degradation on later pages

### 8. Concurrent Operations

#### 8.1 Concurrent Creates
- **Setup**: Multiple threads creating ideas simultaneously
- **Action**: Create 100 ideas concurrently
- **Expected**: 
  - All ideas created successfully
  - No ID collisions
  - Database integrity maintained
  - Transaction isolation works correctly

#### 8.2 Concurrent Updates
- **Setup**: Single idea in database
- **Action**: Multiple threads updating same idea
- **Expected**: 
  - Last write wins (or optimistic locking TBD)
  - No data corruption
  - `updated_at` reflects latest change

#### 8.3 Concurrent Deletes
- **Setup**: Single idea in database
- **Action**: Multiple threads deleting same idea
- **Expected**: 
  - Idempotent operation
  - No errors thrown
  - Idea deleted once

### 9. Data Integrity

#### 9.1 Foreign Key Constraints
- **Setup**: Create idea with `project_id` referencing non-existent project
- **Action**: Attempt to create idea
- **Expected**: 
  - Database constraint violation
  - Error thrown
  - Idea not created

#### 9.2 Required Field Validation
- **Action**: Attempt to create idea without `title`
- **Expected**: 
  - Database constraint violation or service validation
  - Error thrown
  - Idea not created

#### 9.3 Status Enum Validation
- **Action**: Attempt to create idea with invalid status
- **Expected**: 
  - Validation error
  - Idea not created
  - Error message indicates invalid status

#### 9.4 Timestamp Consistency
- **Action**: Create idea, then immediately update
- **Expected**: 
  - `created_at` remains constant
  - `updated_at` changes
  - Timestamps are UTC

### 10. Migration Compatibility

#### 10.1 Service Interface Unchanged
- **Expected**: 
  - Public methods have same signatures
  - Return types unchanged
  - No breaking changes to callers

#### 10.2 Backward Compatibility
- **Setup**: Code using old in-memory service
- **Action**: Switch to database-backed service
- **Expected**: 
  - No code changes required
  - Same behavior (except persistence)
  - Performance acceptable

#### 10.3 Error Handling Consistency
- **Expected**: 
  - Errors match in-memory behavior
  - Same exceptions thrown
  - Error messages consistent

## Test Data

### Sample Database Schema
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
CREATE INDEX idx_idea_tickets_priority ON idea_tickets(priority);
CREATE INDEX idx_idea_tickets_created_at ON idea_tickets(created_at);
```

## Edge Cases

1. **Database Connection Failures**: Handling connection errors gracefully
2. **Transaction Deadlocks**: Detecting and resolving deadlocks
3. **Very Large Datasets**: 1M+ ideas in database
4. **Unicode Content**: Ideas with Unicode characters
5. **Very Long Titles**: Titles > 255 characters
6. **Null Values**: Handling NULL in optional fields
7. **Date Edge Cases**: Timestamps at boundaries (epoch, max date)

## Dependencies

- Database (SQLite for tests, PostgreSQL for production)
- Database migration framework (Alembic or similar)
- ORM or raw SQL (TBD)
- Connection pooling
- Transaction management

## Test Implementation Notes

- Use in-memory SQLite for fast unit tests
- Use PostgreSQL for integration tests
- Test both unit (service layer) and integration (database) levels
- Use database transactions that rollback after tests
- Test migration scripts separately
- Verify indexes are used (EXPLAIN queries)
- Test with realistic data volumes
- Mock database failures for error handling tests

