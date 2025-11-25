# Feature Specification: Ingest Job Deletion

## Overview
Implementation specification for DELETE endpoint for ingest jobs, including validation, error handling, and cascade behavior.

## Current State
- DELETE endpoint missing
- Frontend has TODO for delete mutation
- No way to remove completed/failed jobs

## Target State
- DELETE endpoint implemented
- Validation prevents deleting running jobs
- Cascade behavior defined
- Frontend delete mutation implemented

## Requirements

### Functional Requirements
1. DELETE endpoint deletes ingest job
2. Only completed/failed/cancelled jobs can be deleted
3. Running jobs must be cancelled first
4. Cascade behavior for associated data (TBD)
5. Soft delete vs hard delete (TBD)

### Non-Functional Requirements
1. Fast response time (< 100ms)
2. Atomic operation
3. Clear error messages

## Technical Design

### Endpoint
```
DELETE /api/projects/{projectId}/ingest/jobs/{jobId}
```

### Implementation

#### 1. Route Handler
```python
@router.delete("/jobs/{jobId}")
async def delete_ingest_job(
    project_id: str,
    job_id: str,
    service: IngestService = Depends(get_ingest_service)
) -> None:
    job = service.get_job(job_id)
    if not job or job.project_id != project_id:
        raise HTTPException(404, "Ingest job not found")
    
    if job.status == IngestStatus.RUNNING:
        raise HTTPException(400, "Cannot delete running job")
    
    service.delete_job(job_id)
    return Response(status_code=204)
```

#### 2. Service Method
```python
def delete_job(self, job_id: str) -> None:
    # Check status
    job = self.get_job(job_id)
    if job.status == IngestStatus.RUNNING:
        raise ValueError("Cannot delete running job")
    
    # Delete associated data (if cascade)
    # Delete job record
    self.repo.delete(job_id)
```

#### 3. Database Changes
- Add DELETE operation to repository
- Consider cascade deletes for canonical documents
- Add soft delete flag (optional)

### API Changes
- New DELETE endpoint
- Error responses for invalid states
- 204 No Content on success

### Frontend Changes
- Implement `useDeleteIngestJob` hook
- Add delete button to IngestStation
- Add confirmation dialog
- Handle errors gracefully

## Testing Strategy

### Unit Tests
- Test delete success
- Test delete running job (error)
- Test delete non-existent job (error)
- Test cascade behavior

### Integration Tests
- Test delete with database
- Test concurrent deletions
- Test error handling

## Implementation Steps

1. Implement backend DELETE endpoint
2. Add service method
3. Add repository method
4. Write tests
5. Implement frontend hook
6. Update IngestStation component
7. Test end-to-end

## Success Criteria

1. DELETE endpoint works correctly
2. Validation prevents invalid deletions
3. Frontend delete mutation works
4. Error handling works
5. Tests pass

## Notes

- Decide on cascade behavior (delete canonical documents?)
- Consider soft delete for audit trail
- Add confirmation dialog in UI

