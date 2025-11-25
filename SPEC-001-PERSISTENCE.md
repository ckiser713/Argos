Goal: Replace in-memory dictionaries with robust SQL persistence.

Markdown

# SPEC-001: Data Persistence Migration

## Problem
Key repositories (`project_intel_repo`, `gap_analysis_repo`) use `_store = {}`. This causes data loss on restart and prevents scaling.

## Requirements
1.  **Schema Updates (`app/db.py`)**:
    Add the following tables to `init_db`:
    - `idea_tickets`: Stores extracted tasks (id, project_id, title, status, priority).
    - `knowledge_nodes`: Stores graph nodes (id, project_id, type, summary).
    - `agent_runs`: Stores execution history (id, project_id, status, logs).

2.  **Repo Refactoring**:
    Rewrite `backend/app/repos/project_intel_repo.py` to use `app.db.db_session`.

## Implementation Guide

### 1. Update `init_db` in `backend/app/db.py`
```python
# Add inside the executescript block:
"""
CREATE TABLE IF NOT EXISTS idea_tickets (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    status TEXT NOT NULL,
    priority TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(project_id) REFERENCES projects(id)
);
CREATE INDEX IF NOT EXISTS idx_tickets_project ON idea_tickets(project_id);
"""
2. Refactor backend/app/repos/project_intel_repo.py
Python

from app.db import db_session
from app.domain.project_intel import IdeaTicket
from datetime import datetime

def save_ticket(ticket: IdeaTicket) -> None:
    with db_session() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO idea_tickets 
            (id, project_id, title, description, status, priority, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (ticket.id, ticket.project_id, ticket.title, ticket.description, 
             ticket.status, ticket.priority, ticket.created_at.isoformat(), 
             ticket.updated_at.isoformat())
        )
        conn.commit()

def list_tickets(project_id: str) -> list[IdeaTicket]:
    with db_session() as conn:
        rows = conn.execute(
            "SELECT * FROM idea_tickets WHERE project_id = ?", 
            (project_id,)
        ).fetchall()
        return [IdeaTicket(**dict(row)) for row in rows]