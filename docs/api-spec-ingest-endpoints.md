# API Specification: Ingest Endpoints

## Overview
Specification for missing and incomplete ingest API endpoints, including DELETE operations, cancel operations, and project-scoped routes.

## Endpoints

### DELETE /api/projects/{projectId}/ingest/jobs/{jobId}

Delete an ingest job.

#### Path Parameters
- `projectId` (string, required): Project ID
- `jobId` (string, required): Ingest job ID

#### Responses

**204 No Content**
- Job successfully deleted

**404 Not Found**
```json
{
  "detail": "Ingest job not found"
}
```

**400 Bad Request**
```json
{
  "detail": "Cannot delete job with status RUNNING. Cancel the job first."
}
```

**401 Unauthorized**
- Authentication required

#### Example Request
```http
DELETE /api/projects/proj_123/ingest/jobs/job_456
Authorization: Bearer <token>
```

#### Example Response
```http
HTTP/1.1 204 No Content
```

#### Notes
- Only jobs with status COMPLETED, FAILED, or CANCELLED can be deleted
- Jobs with status RUNNING must be cancelled first
- Delete is a soft delete: row is retained with `deleted_at` and excluded from listings
- Canonical documents are not cascaded; clean-up is explicit

---

### POST /api/projects/{projectId}/ingest/jobs/{jobId}/cancel

Cancel a running ingest job.

#### Path Parameters
- `projectId` (string, required): Project ID
- `jobId` (string, required): Ingest job ID

#### Responses

**200 OK**
```json
{
  "id": "job_456",
  "projectId": "proj_123",
  "status": "CANCELLED",
  "stage": "CHUNKING",
  "progress": 0.45,
  "sourcePath": "document.pdf",
  "createdAt": "2024-01-15T10:00:00Z",
  "updatedAt": "2024-01-15T10:30:00Z",
  "completedAt": "2024-01-15T10:30:00Z"
}
```

**404 Not Found**
```json
{
  "detail": "Ingest job not found"
}
```

**400 Bad Request**
```json
{
  "detail": "Job cannot be cancelled. Current status: COMPLETED"
}
```

**401 Unauthorized**
- Authentication required

#### Example Request
```http
POST /api/projects/proj_123/ingest/jobs/job_456/cancel
Authorization: Bearer <token>
```

#### Example Response
```json
{
  "id": "job_456",
  "projectId": "proj_123",
  "status": "CANCELLED",
  "stage": "CHUNKING",
  "progress": 0.45,
  "sourcePath": "document.pdf",
  "createdAt": "2024-01-15T10:00:00Z",
  "updatedAt": "2024-01-15T10:30:00Z",
  "completedAt": "2024-01-15T10:30:00Z"
}
```

#### Notes
- Only jobs with status QUEUED or RUNNING can be cancelled
- Cancelling stops background processing
- Job status changes to CANCELLED
- `completedAt` timestamp set

---

### GET /api/projects/{projectId}/ingest/jobs/{jobId}

Get a single ingest job.

#### Path Parameters
- `projectId` (string, required): Project ID
- `jobId` (string, required): Ingest job ID

#### Responses

**200 OK**
```json
{
  "id": "job_456",
  "projectId": "proj_123",
  "sourceId": "src_789",
  "originalFilename": "document.pdf",
  "byteSize": 1024000,
  "mimeType": "application/pdf",
  "isDeepScan": false,
  "stage": "CHUNKING",
  "progress": 0.65,
  "status": "RUNNING",
  "createdAt": "2024-01-15T10:00:00Z",
  "updatedAt": "2024-01-15T10:35:00Z",
  "completedAt": null,
  "errorMessage": null,
  "canonicalDocumentId": null
}
```

**404 Not Found**
```json
{
  "detail": "Ingest job not found"
}
```

**401 Unauthorized**
- Authentication required

#### Example Request
```http
GET /api/projects/proj_123/ingest/jobs/job_456
Authorization: Bearer <token>
```

#### Notes
- Returns complete job details
- Includes all fields from IngestJob model
- Project-scoped: only returns jobs from specified project

---

### GET /api/projects/{projectId}/ingest/jobs

List ingest jobs with filtering and pagination.

#### Path Parameters
- `projectId` (string, required): Project ID

#### Query Parameters
- `cursor` (string, optional): Pagination cursor
- `limit` (integer, optional, default: 50): Maximum number of results (1-100)
- `status` (string, optional): Filter by status (QUEUED, RUNNING, COMPLETED, FAILED, CANCELLED)
- `stage` (string, optional): Filter by stage
- `sourceId` (string, optional): Filter by source ID

#### Responses

**200 OK**
```json
{
  "items": [
    {
      "id": "job_456",
      "projectId": "proj_123",
      "status": "RUNNING",
      "stage": "CHUNKING",
      "progress": 0.65,
      "sourcePath": "document.pdf",
      "createdAt": "2024-01-15T10:00:00Z"
    }
  ],
  "nextCursor": "cursor_abc123",
  "total": 150
}
```

**400 Bad Request**
```json
{
  "detail": "Invalid limit. Must be between 1 and 100."
}
```

**401 Unauthorized**
- Authentication required

#### Example Request
```http
GET /api/projects/proj_123/ingest/jobs?status=RUNNING&limit=20
Authorization: Bearer <token>
```

#### Notes
- Results ordered by `createdAt` DESC (newest first)
- Pagination uses cursor-based approach
- Filters can be combined (logical AND)
- Project-scoped: only returns jobs from specified project

---

## Error Responses

All endpoints may return these standard error responses:

### 401 Unauthorized
```json
{
  "detail": "Authentication required"
}
```

### 403 Forbidden
```json
{
  "detail": "Insufficient permissions"
}
```

### 500 Internal Server Error
```json
{
  "detail": "Internal server error"
}
```

## Authentication

All endpoints require authentication via Bearer token:
```
Authorization: Bearer <token>
```

## Rate Limiting

- 100 requests per minute per project
- 1000 requests per hour per user

## Notes

- All timestamps are ISO-8601 strings in UTC
- All IDs are string UUIDs
- Project-scoped routes ensure data isolation
- Pagination uses cursor-based approach for consistency
- Filtering supports multiple criteria with AND logic
