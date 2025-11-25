Goal: Remove Frontend Mocks.

Markdown

# SPEC-004: Frontend API Wiring

## Problem
The frontend components use hardcoded `MOCK_DATA`. They ignore the data returned by the custom hooks (`useIngestJobs`, `useIdeas`, etc.).

## Plan
Refactor key components to consume `useQuery` data.

## Implementation Guide (Example: `MissionControlBoard.tsx`)

**Current State:**
```typescript
const INITIAL_TASKS: Task[] = [ ...mock data... ];
const [tasks, setTasks] = useState<Task[]>(INITIAL_TASKS);
Target State:

TypeScript

import { useIdeas } from '../hooks/useIdeas'; // Mapping "Ideas" to "Tasks" for now

export const MissionControlBoard: React.FC = () => {
  const { data, isLoading } = useIdeas({ projectId: currentProjectId });

  // Transform Backend "IdeaTicket" -> Frontend "Task"
  const tasks = React.useMemo(() => {
    if (!data?.items) return [];
    return data.items.map(ticket => ({
      id: ticket.id,
      title: ticket.title,
      origin: 'chat', // Default or derived
      confidence: 80, // Default
      column: mapStatusToColumn(ticket.status),
      priority: ticket.priority
    }));
  }, [data]);

  if (isLoading) return <div>Loading Neural Interface...</div>;
  
  return (
     // Render `tasks` instead of state
  );
};
Note: Repeat this pattern for IngestStation (using useIngestJobs) and DeepResearch (using useAgentRuns).