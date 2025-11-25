# Test Specification: React Hooks for Missing API Endpoints

## Purpose
Comprehensive test specification for React hooks covering missing API endpoints, mutations, and data management patterns.

## Current State
- Some hooks exist (`useIngestJobs`, `useIdeas`, `useRoadmap`)
- Missing hooks for many API endpoints
- Missing mutations for create/update/delete operations
- Incomplete error handling

## Target State
- Complete hook coverage for all API endpoints
- Mutations for all CRUD operations
- Comprehensive error handling
- Optimistic updates
- Cache invalidation

## Test Cases

### 1. Ingest Hooks

#### 1.1 useDeleteIngestJob Hook
- **Purpose**: Delete ingest job mutation
- **Implementation**: 
  ```typescript
  export function useDeleteIngestJob(projectId?: string) {
    const queryClient = useQueryClient();
    return useMutation({
      mutationFn: (jobId: string) => deleteIngestJob({ projectId, jobId }),
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
- **Tests**:
  - Mutation calls API correctly
  - Cache invalidated on success
  - Error handled correctly
  - Optimistic update (optional)

#### 1.2 useCancelIngestJob Hook
- **Purpose**: Cancel running ingest job
- **Tests**:
  - Mutation calls cancel endpoint
  - Job status updated
  - Cache invalidated
  - Error handling

#### 1.3 useIngestJob Hook
- **Purpose**: Get single ingest job
- **Tests**:
  - Fetches job by ID
  - Returns job data
  - Handles not found error
  - Caching works correctly

### 2. Roadmap Hooks

#### 2.1 useCreateRoadmapNode Hook
- **Purpose**: Create roadmap node mutation
- **Tests**:
  - Mutation creates node
  - Node added to cache
  - Optimistic update
  - Error handling

#### 2.2 useUpdateRoadmapNode Hook
- **Purpose**: Update roadmap node mutation
- **Tests**:
  - Mutation updates node
  - Cache updated
  - Optimistic update
  - Partial updates work

#### 2.3 useDeleteRoadmapNode Hook
- **Purpose**: Delete roadmap node mutation
- **Tests**:
  - Mutation deletes node
  - Node removed from cache
  - Related edges handled
  - Error handling

#### 2.4 useCreateRoadmapEdge Hook
- **Purpose**: Create roadmap edge mutation
- **Tests**:
  - Mutation creates edge
  - Edge added to cache
  - Graph structure updated
  - Validation errors handled

#### 2.5 useDeleteRoadmapEdge Hook
- **Purpose**: Delete roadmap edge mutation
- **Tests**:
  - Mutation deletes edge
  - Edge removed from cache
  - Graph structure updated
  - Error handling

#### 2.6 useRoadmapNodes Hook
- **Purpose**: List roadmap nodes with filters
- **Tests**:
  - Fetches nodes with filters
  - Pagination works
  - Status filter works
  - Lane filter works

#### 2.7 useRoadmapEdges Hook
- **Purpose**: List roadmap edges
- **Tests**:
  - Fetches edges
  - Pagination works
  - Caching works

### 3. Knowledge Graph Hooks

#### 3.1 useKnowledgeGraph Hook
- **Purpose**: Get knowledge graph snapshot
- **Tests**:
  - Fetches graph with nodes and edges
  - View parameter works
  - Focus node parameter works
  - Caching works

#### 3.2 useKnowledgeNode Hook
- **Purpose**: Get single knowledge node
- **Tests**:
  - Fetches node by ID
  - Returns node data
  - Handles not found error
  - Caching works

#### 3.3 useKnowledgeNodeNeighbors Hook
- **Purpose**: Get neighbors for node
- **Tests**:
  - Fetches neighbors
  - Returns node and neighbors
  - Returns edges
  - Caching works

#### 3.4 useCreateKnowledgeNode Hook
- **Purpose**: Create knowledge node mutation
- **Tests**:
  - Mutation creates node
  - Node added to cache
  - Graph cache invalidated
  - Error handling

#### 3.5 useUpdateKnowledgeNode Hook
- **Purpose**: Update knowledge node mutation
- **Tests**:
  - Mutation updates node
  - Cache updated
  - Graph cache invalidated
  - Error handling

#### 3.6 useCreateKnowledgeEdge Hook
- **Purpose**: Create knowledge edge mutation
- **Tests**:
  - Mutation creates edge
  - Edge added to cache
  - Graph cache invalidated
  - Validation errors handled

#### 3.7 useDeleteKnowledgeEdge Hook
- **Purpose**: Delete knowledge edge mutation
- **Tests**:
  - Mutation deletes edge
  - Edge removed from cache
  - Graph cache invalidated
  - Error handling

#### 3.8 useSearchKnowledge Hook
- **Purpose**: Search knowledge nodes
- **Tests**:
  - Search query works
  - Type filter works
  - Tag filter works
  - Results ordered by relevance

### 4. Context Hooks

#### 4.1 useContextBudget Hook
- **Purpose**: Get context budget
- **Tests**:
  - Fetches budget for project
  - Returns budget with items
  - Calculations accurate
  - Caching works

#### 4.2 useAddContextItems Hook
- **Purpose**: Add context items mutation
- **Tests**:
  - Mutation adds items
  - Budget updated
  - Items added to cache
  - Budget exceeded error handled

#### 4.3 useUpdateContextItem Hook
- **Purpose**: Update context item mutation
- **Tests**:
  - Mutation updates item
  - Pinned status updates
  - Budget recalculated if tokens change
  - Cache updated

#### 4.4 useRemoveContextItem Hook
- **Purpose**: Remove context item mutation
- **Tests**:
  - Mutation removes item
  - Budget updated
  - Item removed from cache
  - Error handling

### 5. Agent Hooks

#### 5.1 useAgentRun Hook
- **Purpose**: Get single agent run
- **Tests**:
  - Fetches run by ID
  - Returns run data
  - Handles not found error
  - Caching works

#### 5.2 useAgentRunSteps Hook
- **Purpose**: List steps for agent run
- **Tests**:
  - Fetches steps for run
  - Pagination works
  - Steps ordered correctly
  - Caching works

#### 5.3 useAgentRunMessages Hook
- **Purpose**: List messages for agent run
- **Tests**:
  - Fetches messages for run
  - Pagination works
  - Messages ordered chronologically
  - Caching works

#### 5.4 useAgentRunNodeStates Hook
- **Purpose**: List node states for agent run
- **Tests**:
  - Fetches node states
  - Returns all node states
  - Caching works

#### 5.5 useAppendAgentRunMessage Hook
- **Purpose**: Append message to agent run mutation
- **Tests**:
  - Mutation appends message
  - Message added to cache
  - Run status may update
  - Error handling

#### 5.6 useCancelAgentRun Hook
- **Purpose**: Cancel agent run mutation
- **Tests**:
  - Mutation cancels run
  - Run status updated
  - Cache updated
  - Error handling

### 6. Ideas Hooks

#### 6.1 useIdeaCandidates Hook
- **Purpose**: List idea candidates
- **Tests**:
  - Fetches candidates with filters
  - Status filter works
  - Type filter works
  - Pagination works

#### 6.2 useCreateIdeaCandidate Hook
- **Purpose**: Create idea candidate mutation
- **Tests**:
  - Mutation creates candidate
  - Candidate added to cache
  - Optimistic update
  - Error handling

#### 6.3 useUpdateIdeaCandidate Hook
- **Purpose**: Update idea candidate mutation
- **Tests**:
  - Mutation updates candidate
  - Cache updated
  - Optimistic update
  - Error handling

#### 6.4 useIdeaClusters Hook
- **Purpose**: List idea clusters
- **Tests**:
  - Fetches clusters
  - Pagination works
  - Caching works

#### 6.5 useCreateIdeaCluster Hook
- **Purpose**: Create idea cluster mutation
- **Tests**:
  - Mutation creates cluster
  - Cluster added to cache
  - Ideas associated
  - Error handling

#### 6.6 useUpdateIdeaCluster Hook
- **Purpose**: Update idea cluster mutation
- **Tests**:
  - Mutation updates cluster
  - Cache updated
  - Ideas updated
  - Error handling

#### 6.7 useIdeaTickets Hook
- **Purpose**: List idea tickets
- **Tests**:
  - Fetches tickets with filters
  - Status filter works
  - Pagination works
  - Caching works

#### 6.8 useCreateIdeaTicket Hook
- **Purpose**: Create ticket from idea mutation
- **Tests**:
  - Mutation creates ticket
  - Ticket linked to idea
  - Ticket added to cache
  - Error handling

#### 6.9 useUpdateIdeaTicket Hook
- **Purpose**: Update ticket mutation
- **Tests**:
  - Mutation updates ticket
  - Cache updated
  - Optimistic update
  - Error handling

#### 6.10 useMissionControlTasks Hook
- **Purpose**: List mission control tasks
- **Tests**:
  - Fetches tasks with filters
  - Column filter works
  - Origin filter works
  - Pagination works

#### 6.11 useCreateMissionControlTask Hook
- **Purpose**: Create mission control task mutation
- **Tests**:
  - Mutation creates task
  - Task added to cache
  - Optimistic update
  - Error handling

#### 6.12 useUpdateMissionControlTask Hook
- **Purpose**: Update mission control task mutation
- **Tests**:
  - Mutation updates task
  - Column updates work
  - Priority updates work
  - Cache updated

### 7. Hook Patterns

#### 7.1 Optimistic Updates
- **Tests**:
  - Updates applied immediately
  - Rollback on error
  - Error message shown
  - State restored

#### 7.2 Cache Invalidation
- **Tests**:
  - Related queries invalidated
  - Cache updated correctly
  - No stale data
  - Performance acceptable

#### 7.3 Error Handling
- **Tests**:
  - Errors caught and handled
  - Error messages displayed
  - Retry mechanisms work
  - Error states managed

#### 7.4 Loading States
- **Tests**:
  - Loading states accurate
  - Loading indicators shown
  - Skeleton loaders work
  - Loading clears on completion

#### 7.5 Pagination
- **Tests**:
  - Pagination works correctly
  - Cursor-based pagination
  - Page navigation works
  - Infinite scroll (if applicable)

## Test Data

### Sample Hook Usage
```typescript
// Example hook implementation
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
      console.error('Failed to delete ingest job:', error);
    }
  });
}
```

## Edge Cases

1. **Network Failures**: Handling network errors
2. **Concurrent Mutations**: Multiple mutations simultaneously
3. **Stale Data**: Handling stale cache data
4. **Race Conditions**: Handling race conditions
5. **Invalid Data**: Handling invalid responses
6. **Timeout Errors**: Handling request timeouts
7. **Optimistic Update Failures**: Handling rollback

## Dependencies

- React Query (@tanstack/react-query)
- React Testing Library
- Jest
- Mock Service Worker (MSW)
- React Hook Testing Library

## Test Implementation Notes

- Use React Hook Testing Library for hook tests
- Mock API calls with MSW
- Test query hooks separately from mutation hooks
- Test error states
- Test loading states
- Test cache invalidation
- Test optimistic updates
- Test pagination logic
- Use fixtures for test data
- Test hook dependencies
- Test hook cleanup

