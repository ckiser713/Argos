# Feature Specification: Missing React Hooks

## Overview
Implementation specification for missing React hooks covering all API endpoints, including queries, mutations, and data management.

## Current State
- Some hooks exist (`useIngestJobs`, `useIdeas`, `useRoadmap`)
- Missing hooks for many endpoints
- Missing mutations for CRUD operations

## Target State
- Complete hook coverage for all API endpoints
- Mutations for all CRUD operations
- Consistent hook patterns
- Error handling
- Optimistic updates

## Requirements

### Functional Requirements
1. Query hooks for all GET endpoints
2. Mutation hooks for all POST/PATCH/DELETE endpoints
3. Consistent hook patterns
4. Error handling
5. Loading states
6. Cache invalidation

### Non-Functional Requirements
1. Type-safe hooks
2. Reusable patterns
3. Good performance
4. Easy to use

## Technical Design

### Hook Patterns

#### Query Hook Pattern
```typescript
export function useResource(projectId?: string, options?: QueryOptions) {
  return useQuery({
    queryKey: resourceQueryKey(projectId, options),
    queryFn: () => fetchResource({ projectId, ...options }),
    enabled: !!projectId,
    ...options
  });
}
```

#### Mutation Hook Pattern
```typescript
export function useCreateResource(projectId?: string) {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (data: CreateRequest) => 
      createResource({ projectId, ...data }),
    onSuccess: () => {
      queryClient.invalidateQueries({ 
        queryKey: resourceQueryKey(projectId) 
      });
    }
  });
}
```

### Hooks to Implement

#### Ingest Hooks
- `useDeleteIngestJob`
- `useCancelIngestJob`
- `useIngestJob` (single job)

#### Roadmap Hooks
- `useCreateRoadmapNode`
- `useUpdateRoadmapNode`
- `useDeleteRoadmapNode`
- `useCreateRoadmapEdge`
- `useDeleteRoadmapEdge`
- `useRoadmapNodes` (with filters)
- `useRoadmapEdges`

#### Knowledge Hooks
- `useKnowledgeGraph`
- `useKnowledgeNode`
- `useKnowledgeNodeNeighbors`
- `useCreateKnowledgeNode`
- `useUpdateKnowledgeNode`
- `useCreateKnowledgeEdge`
- `useDeleteKnowledgeEdge`
- `useSearchKnowledge`

#### Context Hooks
- `useContextBudget`
- `useAddContextItems`
- `useUpdateContextItem`
- `useRemoveContextItem`

#### Agent Hooks
- `useAgentRun`
- `useAgentRunSteps`
- `useAgentRunMessages`
- `useAgentRunNodeStates`
- `useAppendAgentRunMessage`
- `useCancelAgentRun`

#### Ideas Hooks
- `useIdeaCandidates`
- `useCreateIdeaCandidate`
- `useUpdateIdeaCandidate`
- `useIdeaClusters`
- `useCreateIdeaCluster`
- `useUpdateIdeaCluster`
- `useIdeaTickets`
- `useCreateIdeaTicket`
- `useUpdateIdeaTicket`
- `useMissionControlTasks`
- `useCreateMissionControlTask`
- `useUpdateMissionControlTask`

## Testing Strategy

### Unit Tests
- Test hook behavior
- Test error handling
- Test cache invalidation
- Test optimistic updates

### Integration Tests
- Test with API
- Test with React Query
- Test component integration

## Implementation Steps

1. Create hook templates
2. Implement query hooks
3. Implement mutation hooks
4. Add error handling
5. Add optimistic updates
6. Write tests
7. Update components

## Success Criteria

1. All hooks implemented
2. Consistent patterns
3. Error handling works
4. Cache invalidation works
5. Tests pass

## Notes

- Use React Query best practices
- Consider custom hooks for common patterns
- Document hook usage
- Provide TypeScript types

