# Test Specification: MissionControlBoard Component

## Purpose
Comprehensive test specification for the MissionControlBoard component, covering context derivation from ticket data, drag-drop functionality, and task management.

## Current State
- Component displays tasks from `useIdeas` hook
- Drag-drop implemented for moving tasks between columns
- Context derivation not implemented (TODO at line 77)
- Task transformation incomplete

## Target State
- Complete context derivation from ticket data
- Full drag-drop functionality
- Task filtering and sorting
- Real-time updates
- AI agent integration

## Test Cases

### 1. Component Rendering

#### 1.1 Render with No Tasks
- **Setup**: No tasks in database
- **Action**: Render component
- **Expected**: 
  - Component renders successfully
  - All columns displayed (backlog, todo, in_progress, done)
  - Empty state shown in each column

#### 1.2 Render with Tasks
- **Setup**: Multiple tasks exist
- **Action**: Render component
- **Expected**: 
  - Tasks displayed in correct columns
  - Tasks show correct title, origin, confidence
  - Column counts accurate

#### 1.3 Render Loading State
- **Setup**: Tasks are loading
- **Action**: Render component
- **Expected**: 
  - Loading indicator displayed
  - Skeleton loaders shown (optional)
  - Columns visible but empty

### 2. Context Derivation from Ticket Data

#### 2.1 Derive Context from Ticket Metadata
- **Setup**: Ticket has `repoHints` field
- **Action**: Transform ticket to task
- **Expected**: 
  - Context array populated from `repoHints`
  - Context items have correct structure
  - Context accessible in task

#### 2.2 Derive Context from Related Files
- **Setup**: Ticket has `relatedFiles` or `impliedTaskSummaries`
- **Action**: Transform ticket to task
- **Expected**: 
  - Context derived from related files
  - File paths included in context
  - Context items typed correctly (code/doc)

#### 2.3 Derive Context from Source Quotes
- **Setup**: Ticket has `sourceQuotes`
- **Action**: Transform ticket to task
- **Expected**: 
  - Context includes source quotes
  - Quotes formatted correctly
  - Context accessible

#### 2.4 Derive Context from Multiple Sources
- **Setup**: Ticket has multiple context sources
- **Action**: Transform ticket to task
- **Expected**: 
  - All context sources combined
  - No duplicates
  - Context ordered logically

#### 2.5 Handle Missing Context Data
- **Setup**: Ticket has no context metadata
- **Action**: Transform ticket to task
- **Expected**: 
  - Context array empty (not null)
  - Task still functional
  - No errors thrown

#### 2.6 Derive Origin from Ticket
- **Setup**: Ticket has `sourceChannel` or `originStory`
- **Action**: Transform ticket to task
- **Expected**: 
  - Origin derived correctly (repo/chat/pdf)
  - Origin icon matches
  - Origin badge displays correctly

#### 2.7 Derive Confidence from Ticket
- **Setup**: Ticket has `confidence` field
- **Action**: Transform ticket to task
- **Expected**: 
  - Confidence value used
  - Confidence gauge displays correctly
  - Default confidence if missing

### 3. Drag and Drop Functionality

#### 3.1 Drag Task Between Columns
- **Setup**: Task in "todo" column
- **Action**: Drag task to "in_progress" column
- **Expected**: 
  - Task moves to new column
  - Column counts update
  - API call to update task column
  - Visual feedback during drag

#### 3.2 Drag Task to Same Column
- **Action**: Drag task within same column
- **Expected**: 
  - Task position may change (if reordering supported)
  - No API call if position unchanged
  - Visual feedback shown

#### 3.3 Drag Task to Invalid Column
- **Action**: Attempt invalid column transition
- **Expected**: 
  - Drag prevented or rejected
  - Task returns to original position
  - Error message shown (if applicable)

#### 3.4 Drag Multiple Tasks
- **Setup**: Multiple tasks selected
- **Action**: Drag selected tasks
- **Expected**: 
  - All selected tasks move
  - Batch update sent to API
  - Progress shown for batch operation

#### 3.5 Drag Task to Chat Zone
- **Setup**: Task in column
- **Action**: Drag task to chat drop zone (right side)
- **Expected**: 
  - AI prompt triggered
  - Context loaded
  - Agent run started
  - Visual feedback shown

#### 3.6 Drag Drop Error Handling
- **Setup**: API returns error on update
- **Action**: Drag task to new column
- **Expected**: 
  - Task returns to original position
  - Error message displayed
  - Retry option available

#### 3.7 Drag Drop Optimistic Update
- **Action**: Drag task to new column
- **Expected**: 
  - Task moves immediately (optimistic)
  - If API fails, task restored
  - Error shown if restore needed

### 4. Task Display

#### 4.1 Display Task Title
- **Setup**: Task with title
- **Action**: Render task card
- **Expected**: 
  - Title displayed correctly
  - Title truncated if too long
  - Tooltip shows full title (if truncated)

#### 4.2 Display Task Origin
- **Setup**: Task with origin (repo/chat/pdf)
- **Action**: Render task card
- **Expected**: 
  - Origin badge displayed
  - Origin icon shown
  - Origin color matches type

#### 4.3 Display Task Confidence
- **Setup**: Task with confidence value
- **Action**: Render task card
- **Expected**: 
  - Confidence gauge displayed
  - Percentage shown
  - Gauge color matches confidence level

#### 4.4 Display Task Context
- **Setup**: Task with context files
- **Action**: Hover over context button
- **Expected**: 
  - Tooltip shows context files
  - Files listed with icons
  - File types indicated

#### 4.5 Display Task Priority
- **Setup**: Task with priority
- **Action**: Render task card
- **Expected**: 
  - Priority indicator shown
  - Priority color matches level
  - Priority accessible

### 5. Column Management

#### 5.1 Map Status to Column
- **Setup**: Tasks with different statuses
- **Action**: Render component
- **Expected**: 
  - Status mapped to correct column
  - Mapping logic correct
  - All statuses handled

#### 5.2 Update Task Column
- **Action**: Move task to new column
- **Expected**: 
  - Task status updated
  - Column mapping updated
  - API call with correct status

#### 5.3 Column Counts Update
- **Action**: Move task between columns
- **Expected**: 
  - Source column count decreases
  - Target column count increases
  - Counts accurate

#### 5.4 Filter Tasks by Column
- **Action**: Select column filter
- **Expected**: 
  - Only tasks in column shown
  - Filter persists
  - Filter clears on reset

### 6. AI Agent Integration

#### 6.1 Trigger AI Prompt on Drop
- **Action**: Drop task in chat zone
- **Expected**: 
  - AI prompt notification shown
  - Context loaded from task
  - Agent run initiated
  - Loading state shown

#### 6.2 Load Context for Agent
- **Setup**: Task with context files
- **Action**: Drop task in chat zone
- **Expected**: 
  - Context items added to agent run
  - Context accessible to agent
  - Context displayed in prompt

#### 6.3 Handle Agent Run Success
- **Setup**: Agent run completes
- **Action**: Receive completion event
- **Expected**: 
  - Success message shown
  - Task may update (if applicable)
  - Notification dismissed

#### 6.4 Handle Agent Run Error
- **Setup**: Agent run fails
- **Action**: Receive error event
- **Expected**: 
  - Error message shown
  - Retry option available
  - Task unchanged

### 7. Task Filtering and Sorting

#### 7.1 Filter Tasks by Origin
- **Action**: Select origin filter
- **Expected**: 
  - Only tasks with selected origin shown
  - Filter applies across all columns
  - Filter state persists

#### 7.2 Filter Tasks by Priority
- **Action**: Select priority filter
- **Expected**: 
  - Only tasks with selected priority shown
  - Filter applies correctly
  - Filter clears on reset

#### 7.3 Sort Tasks in Column
- **Action**: Select sort option
- **Expected**: 
  - Tasks sorted correctly
  - Sort order persists
  - Visual indicator shows sort

#### 7.4 Search Tasks
- **Action**: Enter search query
- **Expected**: 
  - Tasks filtered by search term
  - Search highlights matches
  - Search applies across columns

### 8. Real-time Updates

#### 8.1 Update Task Status
- **Setup**: Task status changes externally
- **Action**: Receive status update
- **Expected**: 
  - Task moves to correct column
  - Column counts update
  - Visual feedback shown

#### 8.2 Add New Task
- **Setup**: New task created externally
- **Action**: Receive task creation event
- **Expected**: 
  - New task appears in correct column
  - Column count updates
  - No manual refresh needed

#### 8.3 Update Task Details
- **Setup**: Task details change
- **Action**: Receive update event
- **Expected**: 
  - Task card updates
  - Changes reflected immediately
  - No full refresh needed

### 9. Error Handling

#### 9.1 Display API Error
- **Setup**: API returns error
- **Action**: Component loads
- **Expected**: 
  - Error message displayed
  - Error state shown
  - Retry button available

#### 9.2 Handle Drag Drop Error
- **Setup**: API error on column update
- **Action**: Drag task to new column
- **Expected**: 
  - Task returns to original position
  - Error message shown
  - Retry option available

#### 9.3 Handle Context Derivation Error
- **Setup**: Ticket data invalid
- **Action**: Transform ticket to task
- **Expected**: 
  - Error handled gracefully
  - Task still displays
  - Context empty or default

### 10. Accessibility

#### 10.1 Keyboard Navigation
- **Action**: Navigate with keyboard
- **Expected**: 
  - All tasks focusable
  - Tab order logical
  - Arrow keys move between tasks
  - Enter activates task

#### 10.2 Screen Reader Support
- **Action**: Use screen reader
- **Expected**: 
  - Column names announced
  - Task details announced
  - Status changes announced
  - Actions announced

#### 10.3 ARIA Labels
- **Expected**: 
  - Columns have labels
  - Tasks have labels
  - Drag handles have labels
  - Buttons have labels

## Test Data

### Sample Task
```typescript
{
  id: "task_123",
  title: "Refactor authentication module",
  origin: "repo",
  confidence: 0.9,
  column: "todo",
  context: [
    { name: "auth.ts", type: "code" },
    { name: "middleware.ts", type: "code" }
  ],
  priority: "HIGH"
}
```

### Sample Ticket with Context
```typescript
{
  id: "ticket_123",
  title: "Refactor authentication module",
  repoHints: ["auth/", "middleware/"],
  impliedTaskSummaries: ["Update auth routes", "Add middleware"],
  sourceQuotes: "User said: 'We need to refactor auth'",
  sourceChannel: "chat",
  confidence: 0.9
}
```

## Edge Cases

1. **Very Long Titles**: Tasks with titles > 100 characters
2. **Many Context Files**: Tasks with 50+ context files
3. **Concurrent Updates**: Multiple users updating same task
4. **Rapid Status Changes**: Status changing quickly
5. **Network Interruption**: Network fails during drag-drop
6. **Browser Back/Forward**: Navigation during operations
7. **Tab Switching**: Switch tabs during drag

## Dependencies

- React Testing Library
- Jest
- @testing-library/user-event for drag-drop
- Mock Service Worker (MSW) for API mocking
- React Query for data fetching
- WebSocket mocking (for real-time updates)
- Framer Motion mocking (for animations)

## Test Implementation Notes

- Use React Testing Library for component tests
- Mock `useIdeas` hook
- Mock API calls with MSW
- Test drag-drop with @testing-library/user-event
- Test context derivation logic separately
- Test error states and recovery
- Test loading states
- Test accessibility with jest-axe
- Use snapshot tests for UI consistency
- Test real-time updates with mocked WebSocket
- Mock Framer Motion for animation tests

