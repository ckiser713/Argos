# Test Specification: Gap Analysis Repository Database Migration

## Purpose
Test specification for migrating GapAnalysisRepo from in-memory implementation to database persistence, ensuring gap reports are stored and retrieved correctly.

## Current State
- `InMemoryGapAnalysisRepo` uses `Dict[str, List[GapReport]]`
- Reports stored per project in insertion order
- No persistence across service restarts
- Simple in-memory list operations

## Target State
- Database-backed persistence
- Project-scoped gap reports
- Support for querying latest report
- Support for report history
- Efficient storage and retrieval

## Test Cases

### 1. Database Schema Migration

#### 1.1 Create Gap Reports Table
- **Action**: Run migration script
- **Expected**: 
  - Table `gap_reports` created
  - Columns: id, project_id, generated_at, report_json, summary
  - Indexes on project_id, generated_at
  - Foreign key on project_id

#### 1.2 Create Gap Suggestions Table
- **Action**: Run migration script (if suggestions stored separately)
- **Expected**: 
  - Table `gap_suggestions` created
  - Columns: id, report_id, ticket_id, status, notes, related_files_json
  - Indexes on report_id, ticket_id, status
  - Foreign key on report_id

#### 1.3 Migrate Existing In-Memory Data
- **Setup**: Repository has in-memory reports
- **Action**: Run migration script
- **Expected**: 
  - All reports persisted to database
  - Data integrity maintained
  - Reports ordered correctly

### 2. Save Gap Report with Database

#### 2.1 Save Report Persists to Database
- **Setup**: Fresh database
- **Action**: Call `save_gap_report(report)`
- **Expected**: 
  - Report saved to database
  - Report retrievable via `get_latest_gap_report()`
  - Database row matches report structure

#### 2.2 Save Report with Project ID
- **Report**: Includes `projectId`
- **Expected**: 
  - `project_id` stored correctly
  - Report queryable by project

#### 2.3 Save Report with Timestamp
- **Report**: Includes `generatedAt`
- **Expected**: 
  - Timestamp stored correctly
  - Reports ordered by timestamp (newest first)

#### 2.4 Save Report with Suggestions
- **Report**: Includes suggestions array
- **Expected**: 
  - Suggestions stored (in JSON or separate table)
  - Suggestions retrievable with report
  - Structure preserved

### 3. Get Latest Gap Report with Database

#### 3.1 Get Latest Report for Project
- **Endpoint**: `get_latest_gap_report(project_id)`
- **Setup**: Create multiple reports for project A
- **Action**: Get latest report
- **Expected**: 
  - Returns most recent report (by `generatedAt`)
  - Report is complete with all fields
  - Suggestions included

#### 3.2 Get Latest Report When None Exists
- **Action**: Get latest report for project with no reports
- **Expected**: 
  - Returns `None`
  - No error thrown

#### 3.3 Get Latest Report Across Projects
- **Setup**: Create reports in project A and project B
- **Action**: Get latest report for project A
- **Expected**: 
  - Returns latest report for project A only
  - Project B reports not included

#### 3.4 Get Latest Report Performance
- **Setup**: Create 1,000 reports for project
- **Action**: Measure `get_latest_gap_report()` execution time
- **Expected**: 
  - Query completes in < 50ms
  - Uses index on (project_id, generated_at)
  - Efficient query (LIMIT 1 with ORDER BY)

### 4. List Gap Reports with Database

#### 4.1 List Reports for Project
- **Endpoint**: `list_gap_reports(project_id, limit=20)`
- **Setup**: Create 50 reports for project
- **Action**: List reports
- **Expected**: 
  - Returns 20 most recent reports
  - Reports ordered by `generatedAt` DESC (newest first)
  - All reports belong to specified project

#### 4.2 List Reports with Custom Limit
- **Action**: List reports with `limit=10`
- **Expected**: 
  - Returns exactly 10 reports (or fewer if total < 10)
  - Limit respected

#### 4.3 List Reports for Empty Project
- **Action**: List reports for project with no reports
- **Expected**: 
  - Returns empty list
  - No error thrown

#### 4.4 List Reports Performance
- **Setup**: Create 10,000 reports for project
- **Action**: Measure `list_gap_reports()` execution time
- **Expected**: 
  - Query completes in < 100ms
  - Uses index efficiently
  - Pagination works correctly

### 5. Report Querying

#### 5.1 Query Reports by Date Range
- **Action**: Query reports between two dates (if supported)
- **Expected**: 
  - Returns reports within date range
  - Date filtering works correctly
  - Inclusive/exclusive boundaries handled

#### 5.2 Query Reports by Status
- **Action**: Query reports with specific gap status (if supported)
- **Expected**: 
  - Returns reports containing suggestions with specified status
  - Filtering works correctly

#### 5.3 Query Reports with Pagination
- **Action**: Query reports with cursor-based pagination
- **Expected**: 
  - Returns page of results
  - Includes cursor for next page
  - No duplicate results across pages

### 6. Report Structure

#### 6.1 Report Includes All Fields
- **Setup**: Create complete report
- **Action**: Retrieve report
- **Expected**: 
  - All fields present: id, projectId, generatedAt, suggestions
  - Field types correct
  - No missing data

#### 6.2 Suggestions Structure Preserved
- **Setup**: Create report with suggestions
- **Action**: Retrieve report
- **Expected**: 
  - Suggestions array intact
  - Each suggestion has: ticketId, status, notes, relatedFiles
  - Structure matches original

#### 6.3 Related Files Structure Preserved
- **Setup**: Create suggestion with relatedFiles
- **Action**: Retrieve report
- **Expected**: 
  - Related files array intact
  - File paths preserved
  - JSON deserialization works

### 7. Concurrent Operations

#### 7.1 Concurrent Report Saves
- **Setup**: Multiple threads saving reports simultaneously
- **Action**: Save 100 reports concurrently
- **Expected**: 
  - All reports saved successfully
  - No data corruption
  - Latest report correctly identified

#### 7.2 Concurrent Reads
- **Setup**: Single report in database
- **Action**: Multiple threads reading same report
- **Expected**: 
  - All reads succeed
  - No locking issues
  - Consistent data returned

#### 7.3 Concurrent Save and Read
- **Setup**: Thread saving new report
- **Action**: Thread reading latest report simultaneously
- **Expected**: 
  - No race conditions
  - Read may get old or new report (acceptable)
  - No errors thrown

### 8. Data Integrity

#### 8.1 Foreign Key Constraints
- **Setup**: Create report with `project_id` referencing non-existent project
- **Action**: Attempt to save report
- **Expected**: 
  - Database constraint violation
  - Error thrown
  - Report not saved

#### 8.2 Report ID Uniqueness
- **Setup**: Attempt to save report with duplicate ID
- **Action**: Save report
- **Expected**: 
  - Database constraint violation or update (TBD)
  - Error thrown if insert, or update if upsert

#### 8.3 Timestamp Consistency
- **Action**: Save reports with timestamps
- **Expected**: 
  - Timestamps stored correctly
  - Ordering by timestamp works
  - UTC timezone handled

#### 8.4 JSON Structure Validation
- **Action**: Attempt to save report with invalid JSON
- **Expected**: 
  - Validation error
  - Report not saved
  - Error message indicates invalid JSON

### 9. Report History

#### 9.1 Maintain Report History
- **Setup**: Save multiple reports for project
- **Action**: List all reports
- **Expected**: 
  - All reports preserved
  - History maintained
  - Can access historical reports

#### 9.2 Report Ordering
- **Setup**: Save reports at different times
- **Action**: List reports
- **Expected**: 
  - Reports ordered by `generatedAt` DESC
  - Newest first
  - Order is consistent

#### 9.3 Report Retention
- **Action**: Query old reports
- **Expected**: 
  - Old reports still accessible
  - No automatic deletion (or retention policy TBD)
  - History preserved

## Test Data

### Sample Database Schema
```sql
CREATE TABLE gap_reports (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    generated_at TEXT NOT NULL,
    report_json TEXT NOT NULL,
    summary TEXT,
    FOREIGN KEY(project_id) REFERENCES projects(id)
);

CREATE INDEX idx_gap_reports_project ON gap_reports(project_id);
CREATE INDEX idx_gap_reports_generated_at ON gap_reports(project_id, generated_at DESC);

-- If suggestions stored separately:
CREATE TABLE gap_suggestions (
    id TEXT PRIMARY KEY,
    report_id TEXT NOT NULL,
    ticket_id TEXT NOT NULL,
    status TEXT NOT NULL,
    notes TEXT,
    related_files_json TEXT,
    FOREIGN KEY(report_id) REFERENCES gap_reports(id)
);

CREATE INDEX idx_gap_suggestions_report ON gap_suggestions(report_id);
CREATE INDEX idx_gap_suggestions_ticket ON gap_suggestions(ticket_id);
CREATE INDEX idx_gap_suggestions_status ON gap_suggestions(status);
```

### Sample GapReport Structure
```json
{
  "id": "report_123",
  "projectId": "proj_abc",
  "generatedAt": "2024-01-15T10:00:00Z",
  "summary": "Gap analysis completed",
  "suggestions": [
    {
      "ticketId": "ticket_1",
      "status": "unmapped",
      "notes": "No matches found",
      "relatedFiles": []
    },
    {
      "ticketId": "ticket_2",
      "status": "implemented",
      "notes": "Found 3 matches",
      "relatedFiles": ["file1.py", "file2.py", "file3.py"]
    }
  ]
}
```

## Edge Cases

1. **Very Large Reports**: Reports with 10,000+ suggestions
2. **Very Long Notes**: Notes > 10KB
3. **Many Related Files**: Suggestions with 100+ files
4. **Rapid Report Generation**: Multiple reports generated simultaneously
5. **Database Connection Failures**: Handling connection errors
6. **JSON Size Limits**: Very large JSON structures
7. **Unicode Content**: Reports with Unicode characters

## Dependencies

- Database (SQLite for tests, PostgreSQL for production)
- Database migration framework
- ORM or raw SQL
- JSON handling library
- Connection pooling
- Transaction management

## Test Implementation Notes

- Use in-memory SQLite for fast unit tests
- Use PostgreSQL for integration tests
- Test JSON serialization/deserialization
- Use database transactions that rollback after tests
- Test concurrent operations for race conditions
- Verify indexes are used (EXPLAIN queries)
- Test with realistic data volumes
- Mock database failures for error handling tests
- Test report ordering and latest report logic

