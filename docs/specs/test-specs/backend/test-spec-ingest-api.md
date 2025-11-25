# Test Specification: Ingest API

## Purpose
Comprehensive test specification for the Ingest API endpoints, covering missing DELETE endpoint, error handling, pagination, and project-scoped operations.

## Test Cases

### 1. DELETE Ingest Job Endpoint

#### 1.1 Delete Existing Job
- **Endpoint**: `DELETE /api/projects/{projectId}/ingest/jobs/{jobId}`
- **Setup**: Create a job with status `COMPLETED`
- **Action**: DELETE request with valid projectId and jobId
- **Expected**: 
  - Status code: `204 No Content` or `200 OK` with `{ success: true }`
  - Job is removed from database
  - Subsequent GET requests return 404

#### 1.2 Delete Non-Existent Job
- **Endpoint**: `DELETE /api/projects/{projectId}/ingest/jobs/{invalidJobId}`
- **Action**: DELETE request with non-existent jobId
- **Expected**: 
  - Status code: `404 Not Found`
  - Error message: "Ingest job not found"

#### 1.3 Delete Job from Wrong Project
- **Setup**: Create job in project A
- **Action**: DELETE request with project B's ID
- **Expected**: 
  - Status code: `404 Not Found` or `403 Forbidden`
  - Job remains in project A

#### 1.4 Delete Running Job
- **Setup**: Create job with status `RUNNING`
- **Action**: DELETE request
- **Expected**: 
  - Status code: `409 Conflict` or `400 Bad Request`
  - Error message indicates job cannot be deleted while running
  - Job status remains `RUNNING`

#### 1.5 Delete Job with Associated Canonical Document
- **Setup**: Create job that has produced a canonical document
- **Action**: DELETE request
- **Expected**: 
  - Status code: `200 OK` or `204 No Content`
  - Job is deleted (cascade behavior TBD)
  - Canonical document handling (soft delete vs hard delete)

### 2. List Ingest Jobs - Pagination

#### 2.1 List with Default Pagination
- **Endpoint**: `GET /api/projects/{projectId}/ingest/jobs`
- **Setup**: Create 25 jobs
- **Action**: GET request without pagination params
- **Expected**: 
  - Status code: `200 OK`
  - Response includes `items` array (default limit, e.g., 50)
  - Response includes `nextCursor` if more items exist
  - Response includes `total` count

#### 2.2 List with Custom Limit
- **Action**: GET request with `limit=10`
- **Expected**: 
  - Returns exactly 10 items (or fewer if total < 10)
  - `nextCursor` present if more items exist

#### 2.3 List with Cursor Pagination
- **Setup**: Create 30 jobs
- **Action**: GET request with `cursor` from previous response
- **Expected**: 
  - Returns next page of results
  - No duplicate items across pages
  - Cursor is valid and usable

#### 2.4 List with Invalid Cursor
- **Action**: GET request with invalid `cursor` value
- **Expected**: 
  - Status code: `400 Bad Request`
  - Error message indicates invalid cursor

### 3. List Ingest Jobs - Filtering

#### 3.1 Filter by Status
- **Setup**: Create jobs with different statuses (QUEUED, RUNNING, COMPLETED, FAILED)
- **Action**: GET request with `status=COMPLETED`
- **Expected**: 
  - Returns only jobs with status `COMPLETED`
  - Other statuses excluded

#### 3.2 Filter by Stage
- **Setup**: Create jobs at different stages
- **Action**: GET request with `stage=CHUNKING`
- **Expected**: 
  - Returns only jobs at specified stage
  - Other stages excluded

#### 3.3 Filter by Source ID
- **Setup**: Create jobs from different sources
- **Action**: GET request with `sourceId={sourceId}`
- **Expected**: 
  - Returns only jobs from specified source
  - Other sources excluded

#### 3.4 Combined Filters
- **Action**: GET request with multiple filters (`status=COMPLETED&stage=INDEXED&sourceId={id}`)
- **Expected**: 
  - Returns jobs matching ALL filter criteria
  - Logical AND behavior

### 4. Get Ingest Job

#### 4.1 Get Existing Job
- **Endpoint**: `GET /api/projects/{projectId}/ingest/jobs/{jobId}`
- **Setup**: Create a job
- **Action**: GET request with valid IDs
- **Expected**: 
  - Status code: `200 OK`
  - Returns complete job object
  - All required fields present

#### 4.2 Get Non-Existent Job
- **Action**: GET request with invalid jobId
- **Expected**: 
  - Status code: `404 Not Found`
  - Error message: "Ingest job not found"

#### 4.3 Get Job from Wrong Project
- **Setup**: Create job in project A
- **Action**: GET request with project B's ID
- **Expected**: 
  - Status code: `404 Not Found`
  - Error message indicates job not found in project

### 5. Cancel Ingest Job

#### 5.1 Cancel Running Job
- **Endpoint**: `POST /api/projects/{projectId}/ingest/jobs/{jobId}/cancel`
- **Setup**: Create job with status `RUNNING`
- **Action**: POST request to cancel endpoint
- **Expected**: 
  - Status code: `200 OK`
  - Job status changes to `CANCELLED`
  - Background processing stops (if applicable)

#### 5.2 Cancel Already Completed Job
- **Setup**: Create job with status `COMPLETED`
- **Action**: POST request to cancel
- **Expected**: 
  - Status code: `400 Bad Request` or `409 Conflict`
  - Error message indicates job cannot be cancelled
  - Job status remains `COMPLETED`

#### 5.3 Cancel Non-Existent Job
- **Action**: POST request with invalid jobId
- **Expected**: 
  - Status code: `404 Not Found`

### 6. Error Handling

#### 6.1 Invalid Project ID Format
- **Action**: Request with malformed projectId
- **Expected**: 
  - Status code: `400 Bad Request`
  - Error message indicates invalid format

#### 6.2 Missing Authentication
- **Action**: Request without Authorization header
- **Expected**: 
  - Status code: `401 Unauthorized`
  - Error message indicates authentication required

#### 6.3 Invalid Request Body
- **Action**: POST request with malformed JSON
- **Expected**: 
  - Status code: `422 Unprocessable Entity`
  - Error details indicate validation failures

## Test Data

### Sample IngestJob
```json
{
  "id": "job_123",
  "projectId": "proj_abc",
  "sourceId": "src_xyz",
  "originalFilename": "document.pdf",
  "byteSize": 1024000,
  "mimeType": "application/pdf",
  "isDeepScan": false,
  "stage": "CHUNKING",
  "progress": 0.65,
  "status": "RUNNING",
  "createdAt": "2024-01-15T10:30:00Z",
  "updatedAt": "2024-01-15T10:35:00Z",
  "completedAt": null,
  "errorMessage": null,
  "canonicalDocumentId": null
}
```

### Sample CreateIngestJobRequest
```json
{
  "jobs": [
    {
      "sourceId": "src_xyz",
      "originalFilename": "document.pdf",
      "byteSize": 1024000,
      "mimeType": "application/pdf",
      "isDeepScan": false
    }
  ]
}
```

## Edge Cases

1. **Concurrent Deletion**: Multiple DELETE requests for same job
2. **Very Large Pagination**: Request with limit > 1000
3. **Negative Limit**: Request with limit < 1
4. **Special Characters**: Job IDs with special characters
5. **Unicode Filenames**: Jobs with Unicode characters in filename
6. **Extremely Long Filenames**: Filenames > 255 characters
7. **Zero-byte Files**: Jobs created from empty files
8. **Missing Required Fields**: Requests missing required fields

## Dependencies

- FastAPI TestClient
- Database fixtures (projects, sources)
- Mock ingest service (for unit tests)
- Background task mocking (for cancel tests)

## Test Implementation Notes

- Use pytest fixtures for test data setup
- Mock background tasks to avoid actual processing
- Use database transactions that rollback after tests
- Test both unit (service layer) and integration (API layer) levels
- Verify database state changes, not just HTTP responses

