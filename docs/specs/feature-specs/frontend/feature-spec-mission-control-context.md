# Feature Specification: Mission Control Context Derivation

## Overview
Implementation specification for deriving context from ticket data in MissionControlBoard component, including context extraction logic and UI updates.

## Current State
- TODO comment at line 77 in `MissionControlBoard.tsx`
- Context array is empty: `context: []`
- Ticket data not used for context

## Target State
- Context derived from ticket metadata
- Context displayed in task cards
- Context accessible for AI agent integration

## Requirements

### Functional Requirements
1. Extract context from ticket `repoHints`
2. Extract context from ticket `impliedTaskSummaries`
3. Extract context from ticket `sourceQuotes`
4. Derive origin from ticket `sourceChannel`
5. Derive confidence from ticket data
6. Display context in task cards

### Non-Functional Requirements
1. Fast context extraction
2. Handle missing data gracefully
3. Support multiple context sources

## Technical Design

### Context Derivation Logic

#### Transform Ticket to Task
```typescript
function transformTicketToTask(ticket: IdeaTicket): Task {
  const context: ContextFile[] = [];
  
  // Extract from repoHints
  if (ticket.repoHints) {
    ticket.repoHints.forEach(hint => {
      context.push({
        name: hint,
        type: 'code' as const
      });
    });
  }
  
  // Extract from impliedTaskSummaries
  if (ticket.impliedTaskSummaries) {
    ticket.impliedTaskSummaries.forEach(summary => {
      // Parse summary for file references
      const files = extractFileReferences(summary);
      files.forEach(file => {
        context.push({
          name: file,
          type: 'code' as const
        });
      });
    });
  }
  
  // Extract origin from sourceChannel
  const origin: OriginType = 
    ticket.sourceChannel === 'chat' ? 'chat' :
    ticket.sourceChannel === 'file' ? 'pdf' :
    'repo';
  
  // Derive confidence
  const confidence = ticket.confidence || 0.85;
  
  return {
    id: ticket.id,
    title: ticket.title,
    origin,
    confidence,
    column: mapStatusToColumn(ticket.status),
    context,
    priority: ticket.priority || 'medium'
  };
}
```

### Component Updates

#### MissionControlBoard Component
```typescript
const tasks: Task[] = data?.items.map(ticket => 
  transformTicketToTask(ticket)
) || [];
```

### UI Updates
- Context displayed in task cards
- Context tooltip shows files
- Context accessible for drag-drop to chat

## Testing Strategy

### Unit Tests
- Test context extraction logic
- Test origin derivation
- Test confidence calculation
- Test missing data handling

### Integration Tests
- Test with real ticket data
- Test context display
- Test AI agent integration

## Implementation Steps

1. Create `transformTicketToTask` function
2. Update MissionControlBoard component
3. Add context extraction helpers
4. Update task card display
5. Write tests
6. Test with real data

## Success Criteria

1. Context derived correctly
2. Context displayed in UI
3. Origin derived correctly
4. Confidence derived correctly
5. Missing data handled gracefully
6. Tests pass

## Notes

- Consider caching context extraction
- Support multiple context formats
- Add context validation

