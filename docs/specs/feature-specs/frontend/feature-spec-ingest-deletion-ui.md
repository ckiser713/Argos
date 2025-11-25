# Feature Specification: Ingest Deletion UI

## Overview
Implementation specification for delete mutation in IngestStation component, including UI updates, error handling, and user feedback.

## Current State
- TODO comment at line 66 in `IngestStation.tsx`
- Delete button exists but not functional
- No delete mutation hook

## Target State
- Delete mutation hook implemented
- Delete button functional
- Confirmation dialog
- Error handling
- Optimistic updates

## Requirements

### Functional Requirements
1. Delete button triggers deletion
2. Confirmation dialog for deletion
3. Error handling for failed deletions
4. Success feedback
5. Optimistic update (optional)

### Non-Functional Requirements
1. Fast UI response
2. Clear error messages
3. Accessible confirmation dialog

## Technical Design

### Hook Implementation

#### useDeleteIngestJob Hook
```typescript
export function useDeleteIngestJob(projectId?: string) {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (jobId: string) => 
      deleteIngestJob({ projectId, jobId }),
    onSuccess: () => {
      queryClient.invalidateQueries({ 
        queryKey: ingestJobsQueryKey(projectId) 
      });
    },
    onError: (error) => {
      // Error handling
    }
  });
}
```

### Component Updates

#### IngestStation Component
```typescript
const deleteMutation = useDeleteIngestJob(projectId);
const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);

const removeFile = (id: string) => {
  setDeleteConfirm(id);
};

const confirmDelete = () => {
  if (deleteConfirm) {
    deleteMutation.mutate(deleteConfirm);
    setDeleteConfirm(null);
  }
};
```

### UI Changes
- Add confirmation dialog component
- Update delete button handler
- Add loading state during deletion
- Add error toast notification
- Add success feedback

## Testing Strategy

### Unit Tests
- Test hook mutation
- Test component rendering
- Test confirmation dialog
- Test error handling

### Integration Tests
- Test delete flow end-to-end
- Test error scenarios
- Test optimistic updates

## Implementation Steps

1. Create `useDeleteIngestJob` hook
2. Add `deleteIngestJob` to API client
3. Update IngestStation component
4. Add confirmation dialog
5. Add error handling
6. Write tests
7. Test end-to-end

## Success Criteria

1. Delete button works
2. Confirmation dialog appears
3. Deletion succeeds
4. Error handling works
5. UI updates correctly
6. Tests pass

## Notes

- Consider bulk delete for multiple jobs
- Add keyboard shortcuts
- Consider undo functionality

