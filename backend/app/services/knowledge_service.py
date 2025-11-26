from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from app.db import db_session
from app.domain.common import PaginatedResponse
from app.domain.models import (
    KnowledgeEdge,
    KnowledgeGraph,
    KnowledgeNode,
    KnowledgeSearchRequest,
)
from app.services.qdrant_service import qdrant_service


class KnowledgeService:
    """
    Knowledge graph service with CRUD operations for nodes and edges.
    """

    def get_graph(
        self,
        project_id: str,
        view: Optional[str] = None,
        focus_node_id: Optional[str] = None,
    ) -> KnowledgeGraph:
        nodes = self.list_nodes(project_id, limit=1000).items
        edges = self.list_edges(project_id, limit=1000).items

        # Filter by view if specified
        if view:
            if view == "ideas":
                nodes = [n for n in nodes if n.type == "idea"]
            elif view == "tickets":
                nodes = [n for n in nodes if n.type == "ticket"]
            elif view == "docs":
                nodes = [n for n in nodes if n.type == "document"]

        # Focus on specific node and neighbors
        if focus_node_id:
            node_ids = {focus_node_id}
            # Add neighbors
            for edge in edges:
                if edge.source == focus_node_id:
                    node_ids.add(edge.target)
                elif edge.target == focus_node_id:
                    node_ids.add(edge.source)
            nodes = [n for n in nodes if n.id in node_ids]
            edges = [e for e in edges if e.source in node_ids and e.target in node_ids]

        return KnowledgeGraph(
            nodes=nodes,
            edges=edges,
            generated_at=datetime.now(timezone.utc),
        )

    def get_node(self, project_id: str, node_id: str) -> Optional[KnowledgeNode]:
        with db_session() as conn:
            row = conn.execute(
                "SELECT * FROM knowledge_nodes WHERE id = ? AND project_id = ?", (node_id, project_id)
            ).fetchone()
            if row:
                return self._row_to_node(row)
        return None

    def get_node_neighbors(self, project_id: str, node_id: str) -> dict:
        node = self.get_node(project_id, node_id)
        if not node:
            raise ValueError("Knowledge node not found")

        with db_session() as conn:
            # Get edges connected to this node
            edge_rows = conn.execute(
                """
                SELECT * FROM knowledge_edges
                WHERE project_id = ? AND (source = ? OR target = ?)
                """,
                (project_id, node_id, node_id),
            ).fetchall()

            neighbor_ids = set()
            edges = []
            for edge_row in edge_rows:
                edge = self._row_to_edge(edge_row)
                edges.append(edge)
                if edge.source == node_id:
                    neighbor_ids.add(edge.target)
                else:
                    neighbor_ids.add(edge.source)

            # Get neighbor nodes
            neighbors = []
            if neighbor_ids:
                placeholders = ",".join("?" * len(neighbor_ids))
                neighbor_rows = conn.execute(
                    f"SELECT * FROM knowledge_nodes WHERE project_id = ? AND id IN ({placeholders})",
                    (project_id, *neighbor_ids),
                ).fetchall()
                neighbors = [self._row_to_node(row) for row in neighbor_rows]

        return {
            "node": node,
            "neighbors": neighbors,
            "edges": edges,
        }

    def list_nodes(
        self,
        project_id: str,
        cursor: Optional[str] = None,
        limit: int = 50,
    ) -> PaginatedResponse:
        with db_session() as conn:
            query = "SELECT * FROM knowledge_nodes WHERE project_id = ? LIMIT ?"
            params = [project_id, limit + 1]

            rows = conn.execute(query, params).fetchall()

            items = [self._row_to_node(row) for row in rows[:limit]]

            next_cursor = None
            if len(rows) > limit:
                next_cursor = rows[limit]["id"]

            total_row = conn.execute(
                "SELECT COUNT(*) as total FROM knowledge_nodes WHERE project_id = ?", (project_id,)
            ).fetchone()
            total = total_row["total"] if total_row else len(items)

            return PaginatedResponse(items=items, next_cursor=next_cursor, total=total)

    def create_node(self, project_id: str, node_data: dict) -> KnowledgeNode:
        node_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        node = KnowledgeNode(
            id=node_id,
            project_id=project_id,
            title=node_data["title"],
            summary=node_data.get("summary"),
            text=node_data.get("text"),
            type=node_data.get("type", "concept"),
            tags=node_data.get("tags", []),
            metadata=node_data.get("metadata"),
            created_at=now,
            updated_at=now,
        )

        with db_session() as conn:
            conn.execute(
                """
                INSERT INTO knowledge_nodes
                (id, project_id, title, summary, tags_json, type)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    node.id,
                    node.project_id,
                    node.title,
                    node.summary,
                    json.dumps(node.tags),
                    node.type,
                ),
            )
            conn.commit()

        # Store embedding in Qdrant
        qdrant_service.upsert_knowledge_node(
            project_id=project_id,
            node_id=node_id,
            title=node.title,
            summary=node.summary,
            text=node.text,
            node_type=node.type,
        )

        return node

    def update_node(self, project_id: str, node_id: str, updates: dict) -> KnowledgeNode:
        with db_session() as conn:
            # Check node exists
            existing = conn.execute(
                "SELECT * FROM knowledge_nodes WHERE id = ? AND project_id = ?", (node_id, project_id)
            ).fetchone()
            if not existing:
                raise ValueError("Knowledge node not found")

            update_fields = []
            params = []

            if "title" in updates:
                update_fields.append("title = ?")
                params.append(updates["title"])
            if "summary" in updates:
                update_fields.append("summary = ?")
                params.append(updates["summary"])
            if "tags" in updates:
                update_fields.append("tags_json = ?")
                params.append(json.dumps(updates["tags"]))

            if update_fields:
                params.extend([node_id, project_id])
                query = f"UPDATE knowledge_nodes SET {', '.join(update_fields)} WHERE id = ? AND project_id = ?"
                conn.execute(query, params)
                conn.commit()

            row = conn.execute(
                "SELECT * FROM knowledge_nodes WHERE id = ? AND project_id = ?", (node_id, project_id)
            ).fetchone()
            updated_node = self._row_to_node(row)

            # Update embedding in Qdrant if title/summary changed
            if "title" in updates or "summary" in updates:
                qdrant_service.upsert_knowledge_node(
                    project_id=project_id,
                    node_id=node_id,
                    title=updated_node.title,
                    summary=updated_node.summary,
                    text=updated_node.text,
                    node_type=updated_node.type,
                )

            return updated_node

    def list_edges(
        self,
        project_id: str,
        cursor: Optional[str] = None,
        limit: int = 50,
    ) -> PaginatedResponse:
        with db_session() as conn:
            query = "SELECT * FROM knowledge_edges WHERE project_id = ? ORDER BY created_at DESC LIMIT ?"
            params = [project_id, limit + 1]

            rows = conn.execute(query, params).fetchall()

            items = [self._row_to_edge(row) for row in rows[:limit]]

            next_cursor = None
            if len(rows) > limit:
                next_cursor = rows[limit]["id"]

            total_row = conn.execute(
                "SELECT COUNT(*) as total FROM knowledge_edges WHERE project_id = ?", (project_id,)
            ).fetchone()
            total = total_row["total"] if total_row else len(items)

            return PaginatedResponse(items=items, next_cursor=next_cursor, total=total)

    def create_edge(self, project_id: str, edge_data: dict) -> KnowledgeEdge:
        edge_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        source = edge_data["source"]
        target = edge_data["target"]

        # Validate nodes exist
        source_node = self.get_node(project_id, source)
        target_node = self.get_node(project_id, target)
        if not source_node:
            raise ValueError("Invalid source node")
        if not target_node:
            raise ValueError("Invalid target node")

        # Check if edge already exists
        with db_session() as conn:
            existing = conn.execute(
                "SELECT id FROM knowledge_edges WHERE project_id = ? AND source = ? AND target = ?",
                (project_id, source, target),
            ).fetchone()
            if existing:
                raise ValueError("Edge already exists")

        edge = KnowledgeEdge(
            id=edge_id,
            project_id=project_id,
            source=source,
            target=target,
            type=edge_data.get("type", "relates_to"),
            weight=edge_data.get("weight"),
            label=edge_data.get("label"),
            created_at=now,
        )

        with db_session() as conn:
            conn.execute(
                """
                INSERT INTO knowledge_edges
                (id, project_id, source, target, type, weight, label, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    edge.id,
                    edge.project_id,
                    edge.source,
                    edge.target,
                    edge.type,
                    edge.weight,
                    edge.label,
                    edge.created_at.isoformat(),
                ),
            )
            conn.commit()

        return edge

    def delete_edge(self, project_id: str, edge_id: str) -> None:
        with db_session() as conn:
            conn.execute("DELETE FROM knowledge_edges WHERE id = ? AND project_id = ?", (edge_id, project_id))
            conn.commit()

    def search(
        self,
        project_id: str,
        request: KnowledgeSearchRequest,
    ) -> List[KnowledgeNode]:
        """Search knowledge nodes using vector similarity search."""
        use_vector_search = getattr(request, "useVectorSearch", True)

        # Try vector search first
        if use_vector_search and qdrant_service.client:
            vector_results = qdrant_service.search_knowledge_nodes(
                project_id=project_id,
                query=request.query,
                limit=request.max_results,
                node_type=getattr(request, "type", None),
                use_vector_search=True,
            )

            if vector_results:
                # Fetch full node data from database
                node_ids = [r["node_id"] for r in vector_results]
                with db_session() as conn:
                    placeholders = ",".join("?" * len(node_ids))
                    rows = conn.execute(
                        f"""
                        SELECT * FROM knowledge_nodes
                        WHERE project_id = ? AND id IN ({placeholders})
                        """,
                        (project_id, *node_ids),
                    ).fetchall()

                    # Create a map of node_id -> node
                    nodes_map = {self._row_to_node(row).id: self._row_to_node(row) for row in rows}

                    # Return nodes in order of search results with scores
                    results = []
                    for vec_result in vector_results:
                        node_id = vec_result["node_id"]
                        if node_id in nodes_map:
                            node = nodes_map[node_id]
                            # Add score to metadata
                            if not node.metadata:
                                node.metadata = {}
                            node.metadata["similarity_score"] = vec_result["score"]
                            results.append(node)

                    return results

        # Fallback to text search
        with db_session() as conn:
            query = request.query.lower()
            rows = conn.execute(
                """
                SELECT * FROM knowledge_nodes
                WHERE project_id = ?
                AND (LOWER(title) LIKE ? OR LOWER(summary) LIKE ?)
                LIMIT ?
                """,
                (project_id, f"%{query}%", f"%{query}%", request.max_results),
            ).fetchall()

            results = []
            for row in rows:
                node = self._row_to_node(row)
                # Simple scoring
                score = 0.0
                if query in (node.title or "").lower():
                    score += 0.5
                if query in (node.summary or "").lower():
                    score += 0.3
                if not node.metadata:
                    node.metadata = {}
                node.metadata["similarity_score"] = score
                results.append((node, score))

            # Sort by score
            results.sort(key=lambda x: x[1], reverse=True)
            return [node for node, _ in results]

    def _row_to_node(self, row) -> KnowledgeNode:
        tags = []
        if row.get("tags_json"):
            try:
                tags = json.loads(row["tags_json"])
            except (json.JSONDecodeError, ValueError):
                pass

        return KnowledgeNode(
            id=row["id"],
            project_id=row["project_id"],
            title=row["title"],
            summary=row.get("summary"),
            text=row.get("text"),
            type=row.get("type", "concept"),
            tags=tags,
            metadata=None,  # Could be stored in separate column
            created_at=datetime.fromisoformat(row["created_at"]) if row.get("created_at") else None,
            updated_at=datetime.fromisoformat(row["updated_at"]) if row.get("updated_at") else None,
        )

    def _row_to_edge(self, row) -> KnowledgeEdge:
        return KnowledgeEdge(
            id=row["id"],
            project_id=row["project_id"],
            source=row["source"],
            target=row["target"],
            type=row["type"],
            weight=row.get("weight"),
            label=row.get("label"),
            created_at=datetime.fromisoformat(row["created_at"]) if row.get("created_at") else None,
        )


knowledge_service = KnowledgeService()
