from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Set

from app.db import db_session
from app.domain.common import PaginatedResponse
from app.domain.models import (
    RoadmapEdge,
    RoadmapEdgeKind,
    RoadmapGraph,
    RoadmapNode,
    RoadmapNodePriority,
    RoadmapNodeStatus,
)


class RoadmapService:
    """
    Roadmap service with CRUD operations for nodes and edges.
    Includes graph validation (DAG structure, no cycles).
    """

    def list_nodes(
        self,
        project_id: str,
        cursor: Optional[str] = None,
        limit: int = 50,
        status: Optional[str] = None,
        lane_id: Optional[str] = None,
    ) -> PaginatedResponse:
        with db_session() as conn:
            query = "SELECT * FROM roadmap_nodes WHERE project_id = ?"
            params = [project_id]

            if status:
                query += " AND status = ?"
                params.append(status)
            if lane_id:
                query += " AND lane_id = ?"
                params.append(lane_id)

            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit + 1)

            rows = conn.execute(query, params).fetchall()

            items = [self._row_to_node(row) for row in rows[:limit]]

            next_cursor = None
            if len(rows) > limit:
                next_cursor = rows[limit]["id"]

            # Get total count
            count_query = "SELECT COUNT(*) as total FROM roadmap_nodes WHERE project_id = ?"
            count_params = [project_id]
            if status:
                count_query += " AND status = ?"
                count_params.append(status)
            if lane_id:
                count_query += " AND lane_id = ?"
                count_params.append(lane_id)

            total_row = conn.execute(count_query, count_params).fetchone()
            total = total_row["total"] if total_row else len(items)

            return PaginatedResponse(items=items, next_cursor=next_cursor, total=total)

    def get_node(self, project_id: str, node_id: str) -> Optional[RoadmapNode]:
        with db_session() as conn:
            row = conn.execute(
                "SELECT * FROM roadmap_nodes WHERE id = ? AND project_id = ?", (node_id, project_id)
            ).fetchone()
            if row:
                return self._row_to_node(row)
        return None

    def create_node(self, project_id: str, node_data: dict) -> RoadmapNode:
        node_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        # Validate dependencies exist
        depends_on_ids = node_data.get("depends_on_ids", [])
        if depends_on_ids:
            self._validate_dependencies(project_id, depends_on_ids)

        # Normalize status and priority to uppercase
        status_str = str(node_data.get("status", "pending")).upper()
        priority_str = str(node_data.get("priority", "")).upper() if node_data.get("priority") else None
        
        node = RoadmapNode(
            id=node_id,
            project_id=project_id,
            label=node_data["label"],
            description=node_data.get("description"),
            status=RoadmapNodeStatus(status_str if status_str in [s.value for s in RoadmapNodeStatus] else "pending"),
            priority=RoadmapNodePriority(priority_str) if priority_str and priority_str in [p.value for p in RoadmapNodePriority] else None,
            start_date=datetime.fromisoformat(node_data["start_date"]) if node_data.get("start_date") else None,
            target_date=datetime.fromisoformat(node_data["target_date"]) if node_data.get("target_date") else None,
            depends_on_ids=depends_on_ids,
            lane_id=node_data.get("lane_id"),
            idea_id=node_data.get("idea_id"),
            ticket_id=node_data.get("ticket_id"),
            mission_control_task_id=node_data.get("mission_control_task_id"),
            created_at=now,
            updated_at=now,
        )

        with db_session() as conn:
            conn.execute(
                """
                INSERT INTO roadmap_nodes
                (id, project_id, label, description, status, priority, start_date, target_date,
                 depends_on_ids_json, lane_id, idea_id, ticket_id, mission_control_task_id, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    node.id,
                    node.project_id,
                    node.label,
                    node.description,
                    node.status.value,
                    node.priority.value if node.priority else None,
                    node.start_date.isoformat() if node.start_date else None,
                    node.target_date.isoformat() if node.target_date else None,
                    json.dumps(node.depends_on_ids),
                    node.lane_id,
                    node.idea_id,
                    node.ticket_id,
                    node.mission_control_task_id,
                    node.created_at.isoformat(),
                    node.updated_at.isoformat(),
                ),
            )
            conn.commit()

        return node

    def update_node(self, project_id: str, node_id: str, updates: dict) -> RoadmapNode:
        with db_session() as conn:
            # Check node exists
            existing = conn.execute(
                "SELECT * FROM roadmap_nodes WHERE id = ? AND project_id = ?", (node_id, project_id)
            ).fetchone()
            if not existing:
                raise ValueError("Roadmap node not found")

            # Validate dependencies if updating
            if "depends_on_ids" in updates:
                depends_on_ids = updates["depends_on_ids"]
                if depends_on_ids:
                    self._validate_dependencies(project_id, depends_on_ids)
                    # Check for circular dependencies
                    if self._has_circular_dependency(project_id, node_id, depends_on_ids):
                        raise ValueError("Circular dependency detected")

            update_fields = []
            params = []

            if "label" in updates:
                update_fields.append("label = ?")
                params.append(updates["label"])
            if "description" in updates:
                update_fields.append("description = ?")
                params.append(updates["description"])
            if "status" in updates:
                update_fields.append("status = ?")
                params.append(updates["status"])
            if "priority" in updates:
                update_fields.append("priority = ?")
                params.append(updates["priority"])
            if "depends_on_ids" in updates:
                update_fields.append("depends_on_ids_json = ?")
                params.append(json.dumps(updates["depends_on_ids"]))
            if "lane_id" in updates:
                update_fields.append("lane_id = ?")
                params.append(updates["lane_id"])

            update_fields.append("updated_at = ?")
            params.append(datetime.now(timezone.utc).isoformat())
            params.extend([node_id, project_id])

            query = f"UPDATE roadmap_nodes SET {', '.join(update_fields)} WHERE id = ? AND project_id = ?"
            conn.execute(query, params)
            conn.commit()

            row = conn.execute(
                "SELECT * FROM roadmap_nodes WHERE id = ? AND project_id = ?", (node_id, project_id)
            ).fetchone()
            return self._row_to_node(row)

    def delete_node(self, project_id: str, node_id: str) -> None:
        with db_session() as conn:
            # Check if node has dependent nodes
            rows = conn.execute(
                "SELECT id FROM roadmap_nodes WHERE project_id = ? AND depends_on_ids_json LIKE ?",
                (project_id, f"%{node_id}%"),
            ).fetchall()
            if rows:
                raise ValueError("Cannot delete node: other nodes depend on it")

            # Delete edges first
            conn.execute(
                "DELETE FROM roadmap_edges WHERE project_id = ? AND (from_node_id = ? OR to_node_id = ?)",
                (project_id, node_id, node_id),
            )
            # Delete node
            conn.execute("DELETE FROM roadmap_nodes WHERE id = ? AND project_id = ?", (node_id, project_id))
            conn.commit()

    def list_edges(
        self,
        project_id: str,
        cursor: Optional[str] = None,
        limit: int = 50,
    ) -> PaginatedResponse:
        with db_session() as conn:
            query = "SELECT * FROM roadmap_edges WHERE project_id = ? ORDER BY created_at DESC LIMIT ?"
            params = [project_id, limit + 1]

            rows = conn.execute(query, params).fetchall()

            items = [self._row_to_edge(row) for row in rows[:limit]]

            next_cursor = None
            if len(rows) > limit:
                next_cursor = rows[limit]["id"]

            total_row = conn.execute(
                "SELECT COUNT(*) as total FROM roadmap_edges WHERE project_id = ?", (project_id,)
            ).fetchone()
            total = total_row["total"] if total_row else len(items)

            return PaginatedResponse(items=items, next_cursor=next_cursor, total=total)

    def create_edge(self, project_id: str, edge_data: dict) -> RoadmapEdge:
        edge_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        from_node_id = edge_data["from_node_id"]
        to_node_id = edge_data["to_node_id"]

        # Validate nodes exist
        from_node = self.get_node(project_id, from_node_id)
        to_node = self.get_node(project_id, to_node_id)
        if not from_node:
            raise ValueError(f"Invalid source node: {from_node_id} does not exist")
        if not to_node:
            raise ValueError(f"Invalid target node: {to_node_id} does not exist")

        # Check if edge already exists
        with db_session() as conn:
            existing = conn.execute(
                "SELECT id FROM roadmap_edges WHERE project_id = ? AND from_node_id = ? AND to_node_id = ?",
                (project_id, from_node_id, to_node_id),
            ).fetchone()
            if existing:
                raise ValueError("Edge already exists")

        # Check for cycles
        if self._would_create_cycle(project_id, from_node_id, to_node_id):
            raise ValueError("Circular dependency detected")

        edge = RoadmapEdge(
            id=edge_id,
            project_id=project_id,
            from_node_id=from_node_id,
            to_node_id=to_node_id,
            kind=RoadmapEdgeKind(edge_data.get("kind", "depends_on")),
            label=edge_data.get("label"),
            created_at=now,
        )

        with db_session() as conn:
            conn.execute(
                """
                INSERT INTO roadmap_edges
                (id, project_id, from_node_id, to_node_id, kind, label, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    edge.id,
                    edge.project_id,
                    edge.from_node_id,
                    edge.to_node_id,
                    edge.kind.value,
                    edge.label,
                    edge.created_at.isoformat(),
                ),
            )
            conn.commit()

        return edge

    def delete_edge(self, project_id: str, edge_id: str) -> None:
        with db_session() as conn:
            conn.execute("DELETE FROM roadmap_edges WHERE id = ? AND project_id = ?", (edge_id, project_id))
            conn.commit()

    def get_graph(self, project_id: str) -> RoadmapGraph:
        nodes = self.list_nodes(project_id, limit=1000).items
        edges = self.list_edges(project_id, limit=1000).items

        return RoadmapGraph(
            nodes=nodes,
            edges=edges,
            generated_at=datetime.now(timezone.utc),
        )

    def _validate_dependencies(self, project_id: str, depends_on_ids: List[str]) -> None:
        with db_session() as conn:
            for dep_id in depends_on_ids:
                row = conn.execute(
                    "SELECT id FROM roadmap_nodes WHERE id = ? AND project_id = ?", (dep_id, project_id)
                ).fetchone()
                if not row:
                    raise ValueError(f"Invalid dependencies: {dep_id} does not exist")

    def _has_circular_dependency(self, project_id: str, node_id: str, depends_on_ids: List[str]) -> bool:
        """Check if adding these dependencies would create a cycle."""
        visited: Set[str] = set()

        def dfs(current: str) -> bool:
            if current == node_id:
                return True  # Cycle detected
            if current in visited:
                return False
            visited.add(current)

            with db_session() as conn:
                rows = conn.execute(
                    "SELECT to_node_id FROM roadmap_edges WHERE project_id = ? AND from_node_id = ?",
                    (project_id, current),
                ).fetchall()
                for row in rows:
                    if dfs(row["to_node_id"]):
                        return True
            return False

        for dep_id in depends_on_ids:
            if dfs(dep_id):
                return True
        return False

    def _would_create_cycle(self, project_id: str, from_node_id: str, to_node_id: str) -> bool:
        """Check if adding this edge would create a cycle."""
        visited: Set[str] = set()

        def dfs(current: str) -> bool:
            if current == from_node_id:
                return True  # Cycle detected
            if current in visited:
                return False
            visited.add(current)

            with db_session() as conn:
                rows = conn.execute(
                    "SELECT to_node_id FROM roadmap_edges WHERE project_id = ? AND from_node_id = ?",
                    (project_id, current),
                ).fetchall()
                for row in rows:
                    if dfs(row["to_node_id"]):
                        return True
            return False

        return dfs(to_node_id)

    def _row_to_node(self, row) -> RoadmapNode:
        depends_on_ids = []
        if row.get("depends_on_ids_json"):
            try:
                depends_on_ids = json.loads(row["depends_on_ids_json"])
            except (json.JSONDecodeError, ValueError):
                pass

        return RoadmapNode(
            id=row["id"],
            project_id=row["project_id"],
            label=row["label"],
            description=row.get("description"),
            status=RoadmapNodeStatus(row["status"]),
            priority=RoadmapNodePriority(row["priority"]) if row.get("priority") else None,
            start_date=datetime.fromisoformat(row["start_date"]) if row.get("start_date") else None,
            target_date=datetime.fromisoformat(row["target_date"]) if row.get("target_date") else None,
            depends_on_ids=depends_on_ids,
            lane_id=row.get("lane_id"),
            idea_id=row.get("idea_id"),
            ticket_id=row.get("ticket_id"),
            mission_control_task_id=row.get("mission_control_task_id"),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    def _row_to_edge(self, row) -> RoadmapEdge:
        return RoadmapEdge(
            id=row["id"],
            project_id=row["project_id"],
            from_node_id=row["from_node_id"],
            to_node_id=row["to_node_id"],
            kind=RoadmapEdgeKind(row["kind"]),
            label=row.get("label"),
            created_at=datetime.fromisoformat(row["created_at"]),
        )


roadmap_service = RoadmapService()
