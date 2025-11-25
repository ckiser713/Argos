# API Specification: Context Endpoints

## Overview
Complete API specification for context management endpoints, covering budget management, item operations, and project-scoped routes.

## Endpoints

### GET /api/projects/{projectId}/context

Get context budget and items.

#### Responses

**200 OK**
```json
{
  "projectId": "proj_abc",
  "totalTokens": 100000,
  "usedTokens": 45000,
  "availableTokens": 55000,
  "items": [
    {
      "id": "ctx_123",
      "name": "Project_Titan_Specs.pdf",
      "type": "PDF",
      "tokens": 45000,
      "pinned": false,
      "canonicalDocumentId": "doc_456",
      "createdAt": "2024-01-15T10:00:00Z"
    }
  ]
}
```

---

### POST /api/projects/{projectId}/context/items

Add context items.

#### Request Body
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

#### Responses

**200 OK**
```json
{
  "items": [
    {
      "id": "ctx_123",
      "name": "Research Paper",
      "type": "PDF",
      "tokens": 5000,
      "pinned": false
    }
  ],
  "budget": {
    "totalTokens": 100000,
    "usedTokens": 50000,
    "availableTokens": 50000
  }
}
```

**400 Bad Request**
```json
{
  "detail": "Budget exceeded. Would use 105000 tokens, limit is 100000"
}
```

---

### PATCH /api/projects/{projectId}/context/items/{contextItemId}

Update context item.

#### Request Body
```json
{
  "pinned": true
}
```

#### Responses

**200 OK**
```json
{
  "item": {
    "id": "ctx_123",
    "name": "Research Paper",
    "type": "PDF",
    "tokens": 5000,
    "pinned": true
  },
  "budget": {
    "totalTokens": 100000,
    "usedTokens": 50000,
    "availableTokens": 50000
  }
}
```

**404 Not Found**
```json
{
  "detail": "Context item not found"
}
```

---

### DELETE /api/projects/{projectId}/context/items/{contextItemId}

Remove context item.

#### Responses

**200 OK**
```json
{
  "budget": {
    "totalTokens": 100000,
    "usedTokens": 45000,
    "availableTokens": 55000
  }
}
```

**404 Not Found**
```json
{
  "detail": "Context item not found"
}
```

---

## Error Responses

### 400 Bad Request
- Budget exceeded
- Invalid token count
- Invalid item type

### 404 Not Found
- Context item not found
- Project not found

## Notes

- All endpoints are project-scoped
- Budget calculations are atomic
- Token counts validated (non-negative)
- Pinned items persist across clears (TBD)
- Item types: PDF, REPO, CHAT, CUSTOM

