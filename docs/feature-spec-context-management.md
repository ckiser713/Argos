# Feature Specification: Context Management

## Overview
Complete implementation specification for context management, including budget calculations, item operations, and project-scoped context windows.

## Current State
- Basic context service exists (in-memory)
- Missing: POST/PATCH endpoints
- Missing: budget calculation logic
- Missing: database persistence

## Target State
- Complete context CRUD API
- Accurate budget calculations
- Project-scoped context windows
- Database persistence
- Support for pinned items

## Requirements

### Functional Requirements
1. Add context items (with budget validation)
2. Update context items (pin/unpin, update tokens)
3. Remove context items (update budget)
4. Get context budget (with items)
5. Calculate budget accurately
6. Prevent budget overflow

### Non-Functional Requirements
1. Budget calculations atomic
2. Fast response time (< 50ms)
3. Support 100+ context items

## Technical Design

### Endpoints

#### GET /api/projects/{projectId}/context
- Returns budget with items
- Calculates used/available tokens
- Includes all context items

#### POST /api/projects/{projectId}/context/items
- Adds one or more items
- Validates budget not exceeded
- Updates budget atomically
- Returns items and updated budget

#### PATCH /api/projects/{projectId}/context/items/{contextItemId}
- Updates item (pin/unpin, tokens)
- Recalculates budget if tokens change
- Returns item and updated budget

#### DELETE /api/projects/{projectId}/context/items/{contextItemId}
- Removes item
- Updates budget
- Returns updated budget

### Database Schema
- Use existing `context_items` table (if exists)
- Add `context_budgets` table (or calculate on-the-fly)
- Add indexes for performance

### Implementation

#### 1. Budget Calculation
```python
def calculate_budget(project_id: str) -> ContextBudget:
    items = repo.list_items(project_id)
    used_tokens = sum(item.tokens for item in items)
    total_tokens = get_project_max_tokens(project_id)
    available_tokens = total_tokens - used_tokens
    return ContextBudget(...)
```

#### 2. Add Items with Validation
```python
def add_items(project_id: str, items: List[ContextItem]) -> AddItemsResponse:
    current_budget = calculate_budget(project_id)
    new_tokens = sum(item.tokens for item in items)
    
    if current_budget.used_tokens + new_tokens > current_budget.total_tokens:
        raise BudgetExceededError()
    
    # Add items atomically
    with transaction():
        for item in items:
            repo.add_item(item)
    
    return AddItemsResponse(...)
```

### Frontend Changes
- Create hooks for new endpoints
- Update ContextPrism component
- Add budget display
- Add item management UI

## Testing Strategy

### Unit Tests
- Test budget calculations
- Test add items validation
- Test update items
- Test remove items

### Integration Tests
- Test with database
- Test concurrent operations
- Test budget accuracy

## Implementation Steps

1. Design database schema
2. Implement repository layer
3. Implement service layer
4. Implement API routes
5. Write tests
6. Update frontend

## Success Criteria

1. All endpoints work correctly
2. Budget calculations accurate
3. Budget overflow prevented
4. Atomic operations work
5. Tests pass

## Notes

- Consider caching budget calculations
- Optimize token sum queries
- Handle concurrent updates correctly

