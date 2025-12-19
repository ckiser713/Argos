# Test Specification: Context Service Database Persistence Migration

## Purpose
Test specification for migrating ContextService from in-memory storage to database persistence, including budget calculations, item management, and project-scoped operations.

## Current State
- `ContextService` persists items in SQLite
- Project-scoped operations supported
- Budget calculated on the fly (no dedicated budget table), default limit 100,000 tokens

## Target State
- Database-backed persistence
- Project-scoped context windows
- Accurate budget calculations
- Support for pinned items
- Transaction support

## Test Cases

### 1. Database Schema Migration

#### 1.1 Create Context Items Table
- **Action**: Run migration script
- **Expected**: 
  - Table `context_items` created
  - Columns: id, project_id, name, type, tokens, pinned, canonical_document_id, created_at
  - Indexes on project_id, pinned
  - Foreign key on project_id

#### 1.2 Budget Calculation Model
- **Action**: Query budget for a project with existing items
- **Expected**: 
  - No dedicated budget table created
  - `total_tokens` fixed to 100,000
  - `used_tokens` equals sum of item tokens for the project
  - `available_tokens` equals `total_tokens - used_tokens`

### 2. Add Context Item with Database

#### 2.1 Add Item Persists to Database
- **Setup**: Fresh database
- **Action**: Call `add_item(item)`
- **Expected**: 
  - Item saved to database
  - Item retrievable via `list_items()`
  - Database row matches service return value

#### 2.2 Add Item Updates Budget
- **Setup**: Project with 50,000 used tokens, max 100,000
- **Action**: Add item with 10,000 tokens
- **Expected**: 
  - Budget `usedTokens` updated to 60,000
  - Budget `availableTokens` updated to 40,000
  - Budget calculation accurate

#### 2.3 Add Item Exceeding Budget
- **Setup**: Project with 95,000 used tokens, max 100,000
- **Action**: Attempt to add item with 10,000 tokens
- **Expected**: 
  - Error thrown (budget exceeded)
  - Item not added
  - Budget unchanged

#### 2.4 Add Item with Project ID
- **Item**: Includes `projectId`
- **Expected**: 
  - `project_id` stored correctly
  - Item queryable by project

#### 2.5 Add Pinned Item
- **Item**: Includes `pinned: true`
- **Expected**: 
  - `pinned` flag stored correctly
  - Item marked as pinned in database

### 3. List Context Items with Database

#### 3.1 List All Items
- **Setup**: Create 10 context items in database
- **Action**: Call `list_items()`
- **Expected**: 
  - Returns all 10 items
  - Results match database query
  - Order is consistent

#### 3.2 List Items Filtered by Project
- **Setup**: Create items in project A and project B
- **Action**: Call `list_items(project_id="proj_a")`
- **Expected**: 
  - Returns only items from project A
  - Project B items excluded

#### 3.3 List Ordering
- **Setup**: Create items with staggered timestamps
- **Action**: Call `list_items(project_id=<id>)`
- **Expected**: 
  - Returns all items for the project
  - Ordered by `created_at DESC`
  - No filter/pagination arguments supported

### 4. Remove Context Item with Database

#### 4.1 Remove Item Deletes from Database
- **Setup**: Create item in database
- **Action**: Call `remove_item(item_id)`
- **Expected**: 
  - Item removed from database
  - Subsequent `list_items()` excludes item
  - No orphaned records

#### 4.2 Remove Item Updates Budget
- **Setup**: Project with 60,000 used tokens
- **Action**: Remove item with 10,000 tokens
- **Expected**: 
  - Budget `usedTokens` updated to 50,000
  - Budget `availableTokens` increased by 10,000
  - Budget calculation accurate

#### 4.3 Remove Non-Existent Item
- **Action**: Call `remove_item("nonexistent")`
- **Expected**: 
  - No error thrown
  - Idempotent operation
  - Budget unchanged

#### 4.4 Remove Pinned Item
- **Setup**: Create pinned item
- **Action**: Call `remove_item(item_id)`
- **Expected**: 
  - Item removed successfully
  - Pinned status doesn't prevent deletion

### 5. Budget Calculation

#### 5.1 Calculate Budget from Items
- **Setup**: Create items with known token counts
- **Action**: Call `get_budget(project_id)`
- **Expected**: 
  - `usedTokens` equals sum of item tokens
  - `availableTokens` equals `totalTokens - usedTokens`
  - Calculation is accurate

#### 5.2 Budget Updates on Item Addition
- **Setup**: Initial budget with 10,000 used tokens
- **Action**: Add item with 5,000 tokens
- **Expected**: 
  - Budget `usedTokens` updated to 15,000
  - Budget `availableTokens` decreased by 5,000
  - Update is atomic

#### 5.3 Budget Updates on Item Removal
- **Setup**: Budget with 15,000 used tokens
- **Action**: Remove item with 5,000 tokens
- **Expected**: 
  - Budget `usedTokens` updated to 10,000
  - Budget `availableTokens` increased by 5,000
  - Update is atomic

#### 5.4 Budget Exceeds Limit Prevention
- **Setup**: Context at 99,000 of 100,000 tokens
- **Action**: Attempt to add item with 2,000 tokens
- **Expected**: 
  - Error thrown before item added
  - Budget unchanged
  - Transaction rolled back

#### 5.5 Budget Calculation Performance
- **Setup**: 1,000 context items
- **Action**: Measure `get_budget()` execution time
- **Expected**: 
  - Calculation completes in < 50ms
  - Uses database aggregation (SUM)
  - No full table scan

### 6. Update Context Item

#### 6.1 Update Item Pinned Status
- **Setup**: Create non-pinned item
- **Action**: Call `update_item(item_id, pinned=True)`
- **Expected**: 
  - `pinned` flag updated in database
  - Budget unchanged (pinning doesn't affect tokens)
  - Change persisted

#### 6.2 Update Item Tokens
- **Setup**: Create item with 5,000 tokens
- **Action**: Call `update_item(item_id, tokens=7,500)`
- **Expected**: 
  - Tokens updated in database
  - Budget recalculated (+2,500 tokens)
  - Update is atomic

#### 6.3 Update Item Name
- **Action**: Call `update_item(item_id, name="New Name")`
- **Expected**: 
  - Name updated in database
  - Budget unchanged
  - Change persisted

#### 6.4 Update Non-Existent Item
- **Action**: Call `update_item("nonexistent", ...)`
- **Expected**: 
  - Returns `None` or raises error
  - No database changes

### 7. Project-Scoped Operations

#### 7.1 Get Budget for Project
- **Endpoint**: `get_budget(project_id)`
- **Setup**: Create items in multiple projects
- **Action**: Get budget for project A
- **Expected**: 
  - Returns budget for project A only
  - Other projects' items not included
  - Calculation is project-specific

#### 7.2 Clear Context for Project
- **Action**: Clear all items for project
- **Expected**: 
  - All items for project removed
  - Budget reset to 0 used tokens
  - Other projects' items unaffected

#### 7.3 Clear Non-Pinned Items
- **Setup**: Create pinned and non-pinned items
- **Action**: Clear non-pinned items
- **Expected**: 
  - Only non-pinned items removed
  - Pinned items remain
  - Budget updated accordingly

### 8. Concurrent Operations

#### 8.1 Concurrent Adds
- **Setup**: Multiple threads adding items simultaneously
- **Action**: Add 100 items concurrently
- **Expected**: 
  - All items added successfully
  - Budget calculations accurate
  - No race conditions
  - Transaction isolation works

#### 8.2 Concurrent Removes
- **Setup**: Single item in database
- **Action**: Multiple threads removing same item
- **Expected**: 
  - Idempotent operation
  - No errors thrown
  - Item deleted once

#### 8.3 Concurrent Budget Updates
- **Setup**: Multiple threads adding/removing items
- **Action**: Concurrent operations
- **Expected**: 
  - Budget remains accurate
  - No lost updates
  - Atomic operations

### 9. Data Integrity

#### 9.1 Foreign Key Constraints
- **Setup**: Create item with `project_id` referencing non-existent project
- **Action**: Attempt to add item
- **Expected**: 
  - Database constraint violation
  - Error thrown
  - Item not added

#### 9.2 Token Count Validation
- **Action**: Attempt to add item with negative tokens
- **Expected**: 
  - Validation error
  - Item not added
  - Error message indicates invalid tokens

#### 9.3 Type Enum Validation
- **Action**: Attempt to add item with invalid type
- **Expected**: 
  - Validation error
  - Item not added
  - Error message indicates invalid type

#### 9.4 Budget Consistency
- **Action**: Multiple operations affecting budget
- **Expected**: 
  - Budget always consistent
  - No discrepancies between calculated and stored values
  - Atomic updates

## Test Data

### Sample Database Schema
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
CREATE INDEX idx_context_items_type ON context_items(type);
```

## Edge Cases

1. **Very Large Token Counts**: Items with tokens > 1M
2. **Zero Token Items**: Items with `tokens: 0` (if allowed)
3. **Budget Overflow**: Attempting to exceed max tokens
4. **Concurrent Budget Updates**: Race conditions
5. **Very Many Items**: 10,000+ context items per project
6. **Unicode Names**: Items with Unicode characters
7. **Very Long Names**: Names > 255 characters

## Dependencies

- Database (SQLite for tests, PostgreSQL for production)
- Database migration framework
- ORM or raw SQL
- Connection pooling
- Transaction management
- Budget calculation service

## Test Implementation Notes

- Use in-memory SQLite for fast unit tests
- Use PostgreSQL for integration tests
- Test budget calculations at both service and database levels
- Use database transactions that rollback after tests
- Test concurrent operations for race conditions
- Verify atomicity of budget updates
- Test with realistic data volumes
- Mock database failures for error handling tests
