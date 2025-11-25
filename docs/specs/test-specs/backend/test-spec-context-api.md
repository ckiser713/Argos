# Test Specification: Context API

## Purpose
Comprehensive test specification for Context API endpoints, covering POST/PATCH endpoints, budget management, item operations, and project-scoped operations.

## Test Cases

### 1. Get Context Budget

#### 1.1 Get Budget for Project
- **Endpoint**: `GET /api/projects/{projectId}/context`
- **Setup**: Add context items to project
- **Action**: GET request
- **Expected**: 
  - Status code: `200 OK`
  - Returns `ContextBudget` object
  - Includes `totalTokens`, `usedTokens`, `availableTokens`, `items: ContextItem[]`
  - Budget calculations are correct

#### 1.2 Get Budget for Empty Project
- **Action**: GET request for project with no context items
- **Expected**: 
  - Status code: `200 OK`
  - Returns budget with `usedTokens: 0`
  - Empty `items` array
  - `availableTokens` equals `totalTokens`

#### 1.3 Get Budget with Token Limit
- **Setup**: Configure project with `maxContextTokens: 100000`
- **Action**: GET request
- **Expected**: 
  - `totalTokens` equals configured limit
  - `availableTokens` calculated correctly

### 2. Add Context Items

#### 2.1 Add Single Context Item
- **Endpoint**: `POST /api/projects/{projectId}/context/items`
- **Request Body**: 
  ```json
  {
    "items": [
      {
        "name": "document.pdf",
        "type": "PDF",
        "tokens": 5000,
        "canonicalDocumentId": "doc_123"
      }
    ]
  }
  ```
- **Expected**: 
  - Status code: `200 OK` or `201 Created`
  - Returns `{ items: ContextItem[], budget: ContextBudget }`
  - Item added to context
  - Budget updated with new token count
  - Item has generated `id`

#### 2.2 Add Multiple Context Items
- **Request Body**: Array with 3 items
- **Expected**: 
  - All items added successfully
  - Budget reflects sum of all tokens
  - All items returned in response

#### 2.3 Add Item Exceeding Budget
- **Setup**: Context already using 95,000 of 100,000 tokens
- **Request Body**: Item with 10,000 tokens
- **Expected**: 
  - Status code: `400 Bad Request` or `409 Conflict`
  - Error message indicates budget exceeded
  - No items added
  - Budget unchanged

#### 2.4 Add Item with Pinned Flag
- **Request Body**: Item with `pinned: true`
- **Expected**: 
  - Item added with `pinned: true`
  - Pinned items persist across context clears (if applicable)

#### 2.5 Add Item with Invalid Type
- **Request Body**: Item with `type: "INVALID_TYPE"`
- **Expected**: 
  - Status code: `400 Bad Request`
  - Error message indicates invalid type

#### 2.6 Add Item with Negative Tokens
- **Request Body**: Item with `tokens: -100`
- **Expected**: 
  - Status code: `400 Bad Request`
  - Error message indicates invalid token count

#### 2.7 Add Item with Missing Required Fields
- **Request Body**: Missing `name` or `type` or `tokens`
- **Expected**: 
  - Status code: `422 Unprocessable Entity`
  - Error details indicate missing fields

### 3. Update Context Item

#### 3.1 Pin Context Item
- **Endpoint**: `PATCH /api/projects/{projectId}/context/items/{contextItemId}`
- **Setup**: Add context item
- **Request Body**: `{ pinned: true }`
- **Expected**: 
  - Status code: `200 OK`
  - Returns `{ item: ContextItem, budget: ContextBudget }`
  - Item `pinned` field updated to `true`
  - Budget unchanged (pinning doesn't affect tokens)

#### 3.2 Unpin Context Item
- **Setup**: Add pinned context item
- **Request Body**: `{ pinned: false }`
- **Expected**: 
  - Item `pinned` field updated to `false`
  - Budget unchanged

#### 3.3 Update Non-Existent Item
- **Action**: PATCH request with invalid contextItemId
- **Expected**: 
  - Status code: `404 Not Found`
  - Error message: "Context item not found"

#### 3.4 Update Item from Wrong Project
- **Setup**: Add item to project A
- **Action**: PATCH request with project B's ID
- **Expected**: 
  - Status code: `404 Not Found`

### 4. Remove Context Item

#### 4.1 Remove Existing Item
- **Endpoint**: `DELETE /api/projects/{projectId}/context/items/{contextItemId}`
- **Setup**: Add context item with 5000 tokens
- **Action**: DELETE request
- **Expected**: 
  - Status code: `200 OK`
  - Returns `{ budget: ContextBudget }`
  - Item removed from context
  - Budget `usedTokens` decreased by 5000
  - Budget `availableTokens` increased by 5000

#### 4.2 Remove Non-Existent Item
- **Action**: DELETE request with invalid contextItemId
- **Expected**: 
  - Status code: `404 Not Found`
  - Error message: "Context item not found"

#### 4.3 Remove Pinned Item
- **Setup**: Add pinned context item
- **Action**: DELETE request
- **Expected**: 
  - Item removed successfully
  - Pinned status doesn't prevent deletion (or prevents if TBD)

### 5. Context Budget Management

#### 5.1 Budget Calculation Accuracy
- **Setup**: Add items with known token counts (1000, 2000, 3000)
- **Action**: GET budget
- **Expected**: 
  - `usedTokens` equals sum: 6000
  - `availableTokens` equals `totalTokens - 6000`
  - Calculations are accurate

#### 5.2 Budget Updates on Item Addition
- **Setup**: Initial budget with 10,000 used tokens
- **Action**: Add item with 5,000 tokens
- **Expected**: 
  - Budget `usedTokens` updated to 15,000
  - Budget `availableTokens` decreased by 5,000

#### 5.3 Budget Updates on Item Removal
- **Setup**: Budget with 15,000 used tokens
- **Action**: Remove item with 5,000 tokens
- **Expected**: 
  - Budget `usedTokens` updated to 10,000
  - Budget `availableTokens` increased by 5,000

#### 5.4 Budget Exceeds Limit Prevention
- **Setup**: Context at 99,000 of 100,000 tokens
- **Action**: Attempt to add item with 2,000 tokens
- **Expected**: 
  - Status code: `400 Bad Request`
  - Error message indicates would exceed limit
  - Budget unchanged

### 6. Context Item Types

#### 6.1 Add PDF Context Item
- **Request Body**: Item with `type: "PDF"`
- **Expected**: 
  - Item created successfully
  - Type stored correctly
  - Can reference `canonicalDocumentId`

#### 6.2 Add Repo Context Item
- **Request Body**: Item with `type: "REPO"`
- **Expected**: 
  - Item created successfully
  - Type stored correctly
  - Can reference code files

#### 6.3 Add Chat Context Item
- **Request Body**: Item with `type: "CHAT"`
- **Expected**: 
  - Item created successfully
  - Type stored correctly
  - Can reference chat logs

#### 6.4 Add Custom Context Item
- **Request Body**: Item with `type: "CUSTOM"`
- **Expected**: 
  - Item created successfully
  - Type stored correctly

### 7. Context Item References

#### 7.1 Add Item with Canonical Document Reference
- **Request Body**: Item with `canonicalDocumentId: "doc_123"`
- **Expected**: 
  - Reference stored correctly
  - Can retrieve document via reference
  - Invalid reference returns error (if validation exists)

#### 7.2 Add Item with Invalid Document Reference
- **Request Body**: Item with `canonicalDocumentId: "nonexistent"`
- **Expected**: 
  - Status code: `400 Bad Request` or allowed (TBD)
  - Error message if validation exists

### 8. Context Clearing

#### 8.1 Clear All Context Items
- **Endpoint**: `DELETE /api/projects/{projectId}/context/items` (if exists)
- **Setup**: Add multiple context items
- **Action**: DELETE request (or clear operation)
- **Expected**: 
  - All items removed
  - Budget reset to `usedTokens: 0`
  - Pinned items behavior (cleared or preserved TBD)

#### 8.2 Clear Non-Pinned Items Only
- **Setup**: Add pinned and non-pinned items
- **Action**: Clear non-pinned items
- **Expected**: 
  - Only non-pinned items removed
  - Pinned items remain
  - Budget updated accordingly

## Test Data

### Sample ContextItem
```json
{
  "id": "ctx_123",
  "projectId": "proj_abc",
  "name": "Project_Titan_Specs.pdf",
  "type": "PDF",
  "tokens": 45000,
  "pinned": false,
  "canonicalDocumentId": "doc_456",
  "createdAt": "2024-01-15T10:00:00Z"
}
```

### Sample ContextBudget
```json
{
  "projectId": "proj_abc",
  "totalTokens": 100000,
  "usedTokens": 45000,
  "availableTokens": 55000,
  "items": [
    {
      "id": "ctx_123",
      "name": "document.pdf",
      "type": "PDF",
      "tokens": 45000,
      "pinned": false
    }
  ]
}
```

### Sample AddContextItemsRequest
```json
{
  "items": [
    {
      "canonicalDocumentId": "doc_123",
      "name": "Research Paper",
      "type": "PDF",
      "tokens": 5000,
      "pinned": false
    },
    {
      "name": "auth_middleware.rs",
      "type": "REPO",
      "tokens": 12500,
      "pinned": true
    }
  ]
}
```

## Edge Cases

1. **Very Large Token Counts**: Items with tokens > 1M
2. **Zero Token Items**: Items with `tokens: 0` (if allowed)
3. **Concurrent Additions**: Multiple requests adding items simultaneously
4. **Budget Race Conditions**: Adding items when budget is near limit
5. **Invalid Token Calculations**: Items with incorrect token counts
6. **Circular References**: Items referencing each other (if applicable)
7. **Unicode Names**: Items with Unicode characters in names
8. **Very Long Names**: Items with names > 255 characters

## Dependencies

- FastAPI TestClient
- Database fixtures (projects, canonical documents)
- Mock context service (for unit tests)
- Token counting service (for validation)

## Test Implementation Notes

- Use pytest fixtures for context setup
- Mock token counting for consistent tests
- Test budget calculations at both API and service layers
- Verify database constraints and triggers
- Test concurrent operations for race conditions
- Use transaction rollback for data cleanup
- Test performance with many context items (100+)

