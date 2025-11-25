# Test Specification: IngestStation Component

## Purpose
Comprehensive test specification for the IngestStation component, covering delete mutation implementation, error states, file upload, and job management.

## Current State
- Component displays ingest jobs from `useIngestJobs` hook
- File upload via drag-and-drop implemented
- Delete mutation not implemented (TODO at line 66)
- Error handling incomplete

## Target State
- Complete delete mutation implementation
- Comprehensive error handling
- Loading states for all operations
- Optimistic updates
- Error recovery

## Test Cases

### 1. Component Rendering

#### 1.1 Render with No Jobs
- **Setup**: No ingest jobs in database
- **Action**: Render component
- **Expected**: 
  - Component renders successfully
  - Empty state displayed (or "No files" message)
  - Drop zone visible and functional

#### 1.2 Render with Jobs
- **Setup**: Multiple ingest jobs exist
- **Action**: Render component
- **Expected**: 
  - All jobs displayed in list
  - Jobs show correct status, progress, filename
  - Progress bars render correctly

#### 1.3 Render Loading State
- **Setup**: Jobs are loading
- **Action**: Render component
- **Expected**: 
  - Loading indicator displayed
  - Drop zone disabled or shows loading state
  - No jobs displayed until loaded

### 2. File Upload

#### 2.1 Drag and Drop File
- **Setup**: Component rendered
- **Action**: Drag file over drop zone and drop
- **Expected**: 
  - Drop zone highlights on drag over
  - File uploaded on drop
  - Upload progress shown
  - Job appears in list after creation

#### 2.2 Drag and Drop Multiple Files
- **Action**: Drag multiple files and drop
- **Expected**: 
  - All files uploaded
  - Multiple jobs created
  - All jobs appear in list

#### 2.3 Click to Upload File
- **Action**: Click drop zone to open file picker
- **Expected**: 
  - File picker opens
  - Selected file uploaded
  - Job created

#### 2.4 Upload Invalid File Type
- **Action**: Attempt to upload invalid file type
- **Expected**: 
  - Error message displayed
  - File not uploaded
  - Error state shown

#### 2.5 Upload Very Large File
- **Action**: Attempt to upload file > size limit
- **Expected**: 
  - Error message displayed
  - File size limit message shown
  - File not uploaded

#### 2.6 Upload File with Deep Scan Toggle
- **Setup**: Deep scan toggle enabled
- **Action**: Upload file
- **Expected**: 
  - Job created with `isDeepScan: true`
  - Toggle state preserved
  - Job reflects deep scan status

### 3. Delete Mutation Implementation

#### 3.1 Delete Job Successfully
- **Setup**: Job exists in list
- **Action**: Click delete button for job
- **Expected**: 
  - Confirmation dialog shown (if required)
  - DELETE request sent to API
  - Job removed from list on success
  - Optimistic update (job removed immediately)
  - Success message shown (optional)

#### 3.2 Delete Job with Confirmation
- **Setup**: Confirmation required for deletion
- **Action**: Click delete, confirm
- **Expected**: 
  - Confirmation dialog appears
  - On confirm, deletion proceeds
  - On cancel, deletion cancelled

#### 3.3 Delete Running Job
- **Setup**: Job with status RUNNING
- **Action**: Attempt to delete
- **Expected**: 
  - Delete button disabled or warning shown
  - Error message: "Cannot delete running job"
  - Job not deleted

#### 3.4 Delete Job Error Handling
- **Setup**: API returns error
- **Action**: Attempt to delete job
- **Expected**: 
  - Error message displayed
  - Job remains in list
  - Error state shown
  - Retry option available (optional)

#### 3.5 Delete Job Optimistic Update
- **Action**: Click delete
- **Expected**: 
  - Job removed from UI immediately
  - If API fails, job restored
  - Error message shown if restore needed

#### 3.6 Delete Multiple Jobs
- **Setup**: Multiple jobs selected
- **Action**: Delete selected jobs
- **Expected**: 
  - All selected jobs deleted
  - Batch deletion handled correctly
  - Progress shown for batch operation

### 4. Job Status Display

#### 4.1 Display Job Status
- **Setup**: Jobs with different statuses
- **Action**: Render component
- **Expected**: 
  - Status badges show correct colors
  - Status text matches job status
  - Icons match status (if applicable)

#### 4.2 Display Job Progress
- **Setup**: Job with progress 0.65
- **Action**: Render component
- **Expected**: 
  - Progress bar shows 65%
  - Progress percentage displayed
  - Progress bar animates (if applicable)

#### 4.3 Display Completed Job
- **Setup**: Job with status COMPLETED
- **Action**: Render component
- **Expected**: 
  - Status shows "COMPLETED" or "INDEXED"
  - Progress bar at 100%
  - Success indicator shown

#### 4.4 Display Failed Job
- **Setup**: Job with status FAILED
- **Action**: Render component
- **Expected**: 
  - Status shows "FAILED"
  - Error message displayed (if available)
  - Retry option shown (optional)

### 5. Error States

#### 5.1 Display API Error
- **Setup**: API returns error
- **Action**: Component loads
- **Expected**: 
  - Error message displayed
  - Error state shown
  - Retry button available

#### 5.2 Display Network Error
- **Setup**: Network request fails
- **Action**: Attempt operation
- **Expected**: 
  - Network error message shown
  - Retry option available
  - Offline indicator (if applicable)

#### 5.3 Display Validation Error
- **Setup**: Invalid file uploaded
- **Action**: Upload file
- **Expected**: 
  - Validation error message shown
  - Error near upload area
  - File not added to list

#### 5.4 Error Recovery
- **Setup**: Error occurred
- **Action**: Click retry
- **Expected**: 
  - Operation retried
  - Error cleared on success
  - Normal state restored

### 6. Loading States

#### 6.1 Show Loading During Upload
- **Action**: Upload file
- **Expected**: 
  - Loading indicator shown
  - Upload button disabled
  - Progress shown

#### 6.2 Show Loading During Delete
- **Action**: Delete job
- **Expected**: 
  - Loading indicator on delete button
  - Delete button disabled
  - Other actions disabled (optional)

#### 6.3 Show Loading During Refresh
- **Action**: Refresh job list
- **Expected**: 
  - Loading indicator shown
  - Jobs remain visible (or skeleton shown)
  - Loading clears on completion

### 7. Real-time Updates

#### 7.1 Update Job Progress
- **Setup**: Job running
- **Action**: Progress updates via WebSocket/SSE
- **Expected**: 
  - Progress bar updates in real-time
  - Percentage updates
  - No page refresh needed

#### 7.2 Update Job Status
- **Setup**: Job status changes
- **Action**: Status update received
- **Expected**: 
  - Status badge updates
  - Status text changes
  - Visual feedback shown

#### 7.3 Add New Job
- **Setup**: New job created externally
- **Action**: Job creation event received
- **Expected**: 
  - New job appears in list
  - List updates automatically
  - No manual refresh needed

### 8. User Interactions

#### 8.1 Toggle Deep Scan Mode
- **Action**: Toggle deep scan button
- **Expected**: 
  - Toggle state changes
  - Visual indicator updates
  - Mode persists for next upload

#### 8.2 Filter Jobs by Status
- **Action**: Select status filter
- **Expected**: 
  - List filtered by status
  - Only matching jobs shown
  - Filter state persists

#### 8.3 Sort Jobs
- **Action**: Select sort option
- **Expected**: 
  - Jobs sorted correctly
  - Sort order persists
  - Visual indicator shows sort direction

#### 8.4 Search Jobs
- **Action**: Enter search query
- **Expected**: 
  - Jobs filtered by search term
  - Search highlights matches
  - Search clears on reset

### 9. Accessibility

#### 9.1 Keyboard Navigation
- **Action**: Navigate with keyboard
- **Expected**: 
  - All interactive elements focusable
  - Tab order logical
  - Enter/Space activate buttons

#### 9.2 Screen Reader Support
- **Action**: Use screen reader
- **Expected**: 
  - Status announced correctly
  - Progress announced
  - Actions announced
  - Errors announced

#### 9.3 ARIA Labels
- **Expected**: 
  - All buttons have labels
  - Status badges have labels
  - Progress bars have labels
  - Form inputs have labels

### 10. Performance

#### 10.1 Render with Many Jobs
- **Setup**: 1000+ jobs
- **Action**: Render component
- **Expected**: 
  - Component renders in < 1 second
  - Virtual scrolling used (if applicable)
  - Pagination works correctly

#### 10.2 Efficient Re-renders
- **Action**: Update single job
- **Expected**: 
  - Only affected job re-renders
  - Other jobs unchanged
  - No unnecessary re-renders

## Test Data

### Sample IngestJob
```typescript
{
  id: "job_123",
  projectId: "proj_abc",
  sourcePath: "document.pdf",
  progress: 0.65,
  status: "RUNNING",
  stage: "CHUNKING",
  createdAt: "2024-01-15T10:00:00Z"
}
```

## Edge Cases

1. **Very Long Filenames**: Files with names > 255 characters
2. **Unicode Filenames**: Files with Unicode characters
3. **Concurrent Deletions**: Multiple users deleting same job
4. **Rapid Status Changes**: Status changing quickly
5. **Network Interruption**: Network fails during operation
6. **Browser Back/Forward**: Navigation during operations
7. **Tab Switching**: Switch tabs during upload

## Dependencies

- React Testing Library
- Jest
- Mock Service Worker (MSW) for API mocking
- React Query for data fetching
- WebSocket mocking (for real-time updates)

## Test Implementation Notes

- Use React Testing Library for component tests
- Mock `useIngestJobs` hook
- Mock API calls with MSW
- Test user interactions (clicks, drag-drop)
- Test error states and recovery
- Test loading states
- Test accessibility with jest-axe
- Use snapshot tests for UI consistency
- Test real-time updates with mocked WebSocket

