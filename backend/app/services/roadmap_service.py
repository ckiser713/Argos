from __future__ import annotations

import json
import logging
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
from app.services.llm_service import generate_text, ModelLane

logger = logging.getLogger(__name__)


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
        row_data = dict(row)
        depends_on_ids = []
        if row_data.get("depends_on_ids_json"):
            try:
                depends_on_ids = json.loads(row_data["depends_on_ids_json"])
            except (json.JSONDecodeError, ValueError):
                pass

        return RoadmapNode(
            id=row_data["id"],
            project_id=row_data["project_id"],
            label=row_data["label"],
            description=row_data.get("description"),
            status=RoadmapNodeStatus(row_data["status"]),
            priority=RoadmapNodePriority(row_data["priority"]) if row_data.get("priority") else None,
            start_date=datetime.fromisoformat(row_data["start_date"]) if row_data.get("start_date") else None,
            target_date=datetime.fromisoformat(row_data["target_date"]) if row_data.get("target_date") else None,
            depends_on_ids=depends_on_ids,
            lane_id=row_data.get("lane_id"),
            idea_id=row_data.get("idea_id"),
            ticket_id=row_data.get("ticket_id"),
            mission_control_task_id=row_data.get("mission_control_task_id"),
            created_at=datetime.fromisoformat(row_data["created_at"]),
            updated_at=datetime.fromisoformat(row_data["updated_at"]),
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


def create_roadmap_nodes_from_intent(project_id: str, intent: str) -> List[RoadmapNode]:
    """
    Generate roadmap nodes from a natural language intent using LLM.
    
    Args:
        project_id: The project ID to create nodes for
        intent: Natural language description of what roadmap nodes should be created
        
    Returns:
        List of created RoadmapNode objects
    """
    logger.info(
        "roadmap_service.create_roadmap_nodes_from_intent.start",
        extra={"project_id": project_id, "intent": intent[:100]},
    )
    
    # Generate structured roadmap plan using LLM with decision nodes support
    prompt = f"""Given the following intent, create a structured roadmap as a Directed Acyclic Graph (DAG).
Break down the intent into logical phases with decision nodes where technology choices are needed.

Intent: {intent}

Generate a JSON array of roadmap nodes. Each node should have:
- label: A short, descriptive title (required)
- description: A detailed description of what needs to be done (optional)
- status: One of ["pending", "in_progress", "blocked", "done"] (default: "pending")
- priority: One of ["low", "medium", "high"] (optional)
- node_type: One of ["task", "milestone", "decision"] (default: "task")
  - "task": Regular work item
  - "milestone": Major checkpoint or deliverable
  - "decision": Point where a choice needs to be made (e.g., "Choose Database: PostgreSQL vs MongoDB")
- depends_on_labels: Array of node labels this node depends on (for sequencing)
- decision_options: If node_type is "decision", provide array of options (optional)

Return ONLY a valid JSON array, no markdown formatting, no explanation.
Example format:
[
  {{
    "label": "Phase 1: Setup",
    "description": "Initial project setup and infrastructure",
    "status": "pending",
    "priority": "high",
    "node_type": "milestone"
  }},
  {{
    "label": "Choose Database",
    "description": "Select database technology for the project",
    "status": "pending",
    "priority": "high",
    "node_type": "decision",
    "decision_options": ["PostgreSQL", "MongoDB", "SQLite"],
    "depends_on_labels": ["Phase 1: Setup"]
  }},
  {{
    "label": "Setup database schema",
    "description": "Create initial database tables and migrations",
    "status": "pending",
    "priority": "high",
    "node_type": "task",
    "depends_on_labels": ["Choose Database"]
  }},
  {{
    "label": "Implement API endpoints",
    "description": "Create REST API endpoints for the feature",
    "status": "pending",
    "priority": "high",
    "node_type": "task",
    "depends_on_labels": ["Setup database schema"]
  }}
]"""

    try:
        # Generate roadmap structure using LLM
        llm_response = generate_text(
            prompt=prompt,
            project_id=project_id,
            lane=ModelLane.ORCHESTRATOR,
            temperature=0.3,
            max_tokens=2000,
            json_mode=True,
        )
        
        # Parse JSON response
        # Remove markdown code blocks if present
        llm_response = llm_response.strip()
        if llm_response.startswith("```json"):
            llm_response = llm_response[7:]
        if llm_response.startswith("```"):
            llm_response = llm_response[3:]
        if llm_response.endswith("```"):
            llm_response = llm_response[:-3]
        llm_response = llm_response.strip()
        
        nodes_data = json.loads(llm_response)
        if not isinstance(nodes_data, list):
            raise ValueError("LLM response is not a JSON array")
        
        # Create nodes and resolve dependencies
        created_nodes: List[RoadmapNode] = []
        label_to_id_map: dict[str, str] = {}
        
        # First pass: create all nodes without dependencies
        for node_data in nodes_data:
            label = node_data.get("label", "Untitled Node")
            
            node_payload = {
                "label": label,
                "description": node_data.get("description"),
                "status": node_data.get("status", "pending"),
                "priority": node_data.get("priority"),
            }
            
            # Store decision options in description if present
            node_type = node_data.get("node_type", "task")
            if node_type == "decision":
                decision_options = node_data.get("decision_options", [])
                if decision_options:
                    options_text = "Options: " + ", ".join(decision_options)
                    if node_payload.get("description"):
                        node_payload["description"] += f"\n\n{options_text}"
                    else:
                        node_payload["description"] = options_text
            
            node = roadmap_service.create_node(project_id, node_payload)
            label_to_id_map[label] = node.id
            created_nodes.append(node)
        
        # Second pass: update nodes with resolved dependency IDs and create edges
        for i, node_data in enumerate(nodes_data):
            node = created_nodes[i]
            depends_on_labels = node_data.get("depends_on_labels", node_data.get("depends_on_ids", []))
            if depends_on_labels:
                depends_on_ids = [
                    label_to_id_map[label]
                    for label in depends_on_labels
                    if label in label_to_id_map
                ]
                
                if depends_on_ids:
                    # Update node with dependency IDs
                    roadmap_service.update_node(
                        project_id,
                        node.id,
                        {"depends_on_ids": depends_on_ids},
                    )
                    
                    # Create edges for dependencies
                    for dep_id in depends_on_ids:
                        try:
                            roadmap_service.create_edge(
                                project_id,
                                {
                                    "from_node_id": dep_id,
                                    "to_node_id": node.id,
                                    "kind": "depends_on",
                                },
                            )
                        except ValueError as e:
                            # Edge might already exist, skip
                            logger.debug(f"Skipping edge creation: {e}")
        
        logger.info(
            "roadmap_service.create_roadmap_nodes_from_intent.success",
            extra={"project_id": project_id, "nodes_created": len(created_nodes)},
        )
        
        return created_nodes
    except json.JSONDecodeError as e:
        logger.error(
            "roadmap_service.create_roadmap_nodes_from_intent.json_error",
            extra={"project_id": project_id, "error": str(e), "response": llm_response[:500]},
        )
        raise ValueError(f"Failed to parse LLM response as JSON: {e}")
    except Exception as e:
        logger.exception(
            "roadmap_service.create_roadmap_nodes_from_intent.error",
            extra={"project_id": project_id, "error": str(e)},
        )
        raise


def generate_roadmap_from_project_intent(
    project_id: str,
    intent: Optional[str] = None,
    use_existing_ideas: bool = True,
) -> RoadmapGraph:
    """
    Generate a complete roadmap DAG from project intent, ideas, and knowledge.
    This is the main entry point for dynamic roadmap generation.
    
    Args:
        project_id: Project ID
        intent: Optional natural language intent (if None, extracts from project ideas)
        use_existing_ideas: Whether to incorporate existing idea tickets
        
    Returns:
        RoadmapGraph with nodes and edges
    """
    logger.info(
        "roadmap_service.generate_roadmap_from_project_intent.start",
        extra={"project_id": project_id, "has_intent": intent is not None},
    )
    
    # Gather context from project
    from app.services.knowledge_service import knowledge_service
    from app.services.idea_service import idea_service
    
    # Get project ideas if available
    ideas_context = ""
    if use_existing_ideas:
        try:
            tickets = idea_service.list_tickets(project_id, limit=20)
            if tickets.items:
                ideas_context = "\n".join([
                    f"- {ticket.title}: {ticket.description or ''}"
                    for ticket in tickets.items[:10]
                ])
        except Exception as e:
            logger.warning(f"Failed to fetch ideas: {e}")
    
    # Get relevant knowledge nodes
    knowledge_context = ""
    try:
        from app.domain.models import KnowledgeSearchRequest
        # Search for relevant knowledge
        search_request = KnowledgeSearchRequest(
            query=intent or "project requirements",
            max_results=5,
        )
        search_results = knowledge_service.search(project_id, search_request)
        if search_results:
            knowledge_context = "\n".join([
                f"- {node.title}: {node.summary or ''}"
                for node in search_results[:5]
            ])
    except Exception as e:
        logger.warning(f"Failed to fetch knowledge: {e}")
    
    # Build comprehensive intent
    if not intent:
        intent = f"Create a roadmap based on the following project ideas:\n{ideas_context}"
    
    enhanced_intent = f"""{intent}

Context from existing ideas:
{ideas_context if ideas_context else "None"}

Relevant knowledge:
{knowledge_context if knowledge_context else "None"}

Generate a comprehensive roadmap with:
1. Sequential phases (setup, implementation, testing, deployment)
2. Decision nodes where technology choices need to be made
3. Proper dependencies between tasks
4. Links to relevant research/knowledge where applicable"""
    
    # Generate roadmap nodes
    nodes = create_roadmap_nodes_from_intent(project_id, enhanced_intent)
    
    # Get the complete graph
    graph = roadmap_service.get_graph(project_id)
    
    logger.info(
        "roadmap_service.generate_roadmap_from_project_intent.success",
        extra={"project_id": project_id, "nodes": len(graph.nodes), "edges": len(graph.edges)},
    )
    
    return graph
