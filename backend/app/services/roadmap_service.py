from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional, Set

from langchain.output_parsers import PydanticOutputParser
from langchain.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda
from pydantic import BaseModel, Field, RootModel

from app.db import db_session
from app.domain.common import PaginatedResponse
from app.domain.models import (
    RoadmapEdge,
    RoadmapEdgeKind,
    RoadmapGraph,
    RoadmapNode,
    RoadmapNodeType,
)
from app.services.llm_service import generate_text

logger = logging.getLogger(__name__)


class GeneratedRoadmapNode(BaseModel):
    label: str
    description: Optional[str] = None
    node_type: Literal["task", "milestone", "decision"] = "task"
    depends_on_labels: List[str] = Field(default_factory=list)
    decision_options: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class GeneratedRoadmapNodes(RootModel[List[GeneratedRoadmapNode]]):
    pass


ROADMAP_NODE_PARSER = PydanticOutputParser(pydantic_object=GeneratedRoadmapNodes)

ROADMAP_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            (
                "You are an expert technical program manager who turns project intents into DAG roadmaps. "
                "Break work into logical phases, add decision nodes where technology choices are needed, "
                "and express sequencing through dependencies. Follow these formatting rules exactly:\n"
                "{format_instructions}"
            ),
        ),
        (
            "human",
            (
                "Intent:\n{intent}\n\n"
                "Existing roadmap ideas or constraints:\n{existing_ideas}\n\n"
                "Generate the roadmap nodes described above."
            ),
        ),
    ]
).partial(format_instructions=ROADMAP_NODE_PARSER.get_format_instructions())


def _roadmap_llm_runnable(project_id: str) -> RunnableLambda:
    def _invoke(prompt_value: Any) -> str:
        prompt_text = prompt_value.to_string() if hasattr(prompt_value, "to_string") else str(prompt_value)
        response = generate_text(
            prompt=prompt_text,
            project_id=project_id,
            temperature=0.3,
            max_tokens=2000,
            json_mode=True,
        )
        return response.response if hasattr(response, "response") else response

    return RunnableLambda(_invoke)


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
        node_type: Optional[str] = None,
        lane_id: Optional[str] = None,
    ) -> PaginatedResponse:
        with db_session() as conn:
            query = "SELECT * FROM roadmap_nodes WHERE project_id = ?"
            params = [project_id]

            if node_type:
                query += " AND node_type = ?"
                params.append(node_type)
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
            if node_type:
                count_query += " AND node_type = ?"
                count_params.append(node_type)
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

        node_type_str = str(node_data.get("node_type", "task")).lower()
        
        node = RoadmapNode(
            id=node_id,
            project_id=project_id,
            label=node_data["label"],
            description=node_data.get("description"),
            node_type=RoadmapNodeType(node_type_str if node_type_str in [nt.value for nt in RoadmapNodeType] else "task"),
            start_date=datetime.fromisoformat(node_data["start_date"]) if node_data.get("start_date") else None,
            target_date=datetime.fromisoformat(node_data["target_date"]) if node_data.get("target_date") else None,
            depends_on_ids=depends_on_ids,
            lane_id=node_data.get("lane_id"),
            idea_id=node_data.get("idea_id"),
            ticket_id=node_data.get("ticket_id"),
            mission_control_task_id=node_data.get("mission_control_task_id"),
            metadata=node_data.get("metadata"),
            created_at=now,
            updated_at=now,
        )

        with db_session() as conn:
            conn.execute(
                """
                INSERT INTO roadmap_nodes
                (id, project_id, label, description, node_type, start_date, target_date,
                 depends_on_ids_json, lane_id, idea_id, ticket_id, mission_control_task_id, metadata_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    node.id,
                    node.project_id,
                    node.label,
                    node.description,
                    node.node_type.value,
                    node.start_date.isoformat() if node.start_date else None,
                    node.target_date.isoformat() if node.target_date else None,
                    json.dumps(node.depends_on_ids),
                    node.lane_id,
                    node.idea_id,
                    node.ticket_id,
                    node.mission_control_task_id,
                    json.dumps(node.metadata) if node.metadata else None,
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
            if "node_type" in updates:
                update_fields.append("node_type = ?")
                params.append(updates["node_type"])
            if "metadata" in updates:
                update_fields.append("metadata_json = ?")
                params.append(json.dumps(updates["metadata"]))
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

    def expand_node(self, project_id: str, node_id: str, intent: str) -> List[RoadmapNode]:
        """
        Expands a given node by generating 5-6 sub-nodes (children) based on an intent.
        """
        logger.info(
            "roadmap_service.expand_node.start",
            extra={"project_id": project_id, "node_id": node_id, "intent": intent},
        )
        parent_node = self.get_node(project_id, node_id)
        if not parent_node:
            raise ValueError("Parent node not found")

        prompt = f"""Given the parent roadmap node:
- Label: {parent_node.label}
- Description: {parent_node.description}

And the user's intent for expansion: "{intent}"

Generate 5-6 detailed sub-tasks to achieve this.
The sub-tasks should be smaller, actionable steps.
For each sub-task, provide a 'label' and a 'description'.
If a sub-task is a 'decision', set 'node_type' to 'decision' and provide 'decision_options' in the 'metadata'.

Return ONLY a valid JSON array of node objects, no markdown formatting, no explanation.
Example format:
[
  {{
    "label": "Sub-task 1",
    "description": "First step to expand the parent node.",
    "node_type": "task"
  }},
  {{
    "label": "Decision point",
    "description": "A choice to be made.",
    "node_type": "decision",
    "metadata": {{
      "decision_options": ["Option A", "Option B"]
    }}
  }}
]"""

        try:
            llm_response = generate_text(
                prompt=prompt,
                project_id=project_id,
                temperature=0.4,
                max_tokens=1500,
                json_mode=True,
            )

            llm_response = llm_response.response.strip().removeprefix("```json").removesuffix("```").strip()
            sub_nodes_data = json.loads(llm_response)
            if not isinstance(sub_nodes_data, list):
                raise ValueError("LLM response is not a JSON array")

            created_nodes = []
            for sub_node_data in sub_nodes_data:
                node_payload = {
                    "label": sub_node_data.get("label", "Untitled Sub-node"),
                    "description": sub_node_data.get("description"),
                    "node_type": sub_node_data.get("node_type", "task"),
                    "metadata": sub_node_data.get("metadata"),
                    "depends_on_ids": [parent_node.id],  # Depend on the parent node
                    "lane_id": parent_node.lane_id,
                }
                new_node = self.create_node(project_id, node_payload)
                
                # Also create an edge for visualization
                self.create_edge(project_id, {
                    "from_node_id": parent_node.id,
                    "to_node_id": new_node.id,
                    "kind": "depends_on",
                })
                created_nodes.append(new_node)
            
            logger.info(
                "roadmap_service.expand_node.success",
                extra={"project_id": project_id, "node_id": node_id, "sub_nodes_created": len(created_nodes)},
            )
            return created_nodes

        except json.JSONDecodeError as e:
            logger.error(
                "roadmap_service.expand_node.json_error",
                extra={"project_id": project_id, "error": str(e), "response": llm_response[:500]},
            )
            raise ValueError(f"Failed to parse LLM response as JSON: {e}")
        except Exception as e:
            logger.exception(
                "roadmap_service.expand_node.error",
                extra={"project_id": project_id, "error": str(e)},
            )
            raise

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
        
        metadata = None
        if row_data.get("metadata_json"):
            try:
                metadata = json.loads(row_data["metadata_json"])
            except (json.JSONDecodeError, ValueError):
                pass

        return RoadmapNode(
            id=row_data["id"],
            project_id=row_data["project_id"],
            label=row_data["label"],
            description=row_data.get("description"),
            node_type=RoadmapNodeType(row_data["node_type"]),
            start_date=datetime.fromisoformat(row_data["start_date"]) if row_data.get("start_date") else None,
            target_date=datetime.fromisoformat(row_data["target_date"]) if row_data.get("target_date") else None,
            depends_on_ids=depends_on_ids,
            lane_id=row_data.get("lane_id"),
            idea_id=row_data.get("idea_id"),
            ticket_id=row_data.get("ticket_id"),
            mission_control_task_id=row_data.get("mission_control_task_id"),
            metadata=metadata,
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
    """
    logger.info(
        "roadmap_service.create_roadmap_nodes_from_intent.start",
        extra={"project_id": project_id, "intent": intent[:100]},
    )
    try:
        chain = ROADMAP_PROMPT | _roadmap_llm_runnable(project_id) | ROADMAP_NODE_PARSER
        parsed_nodes = chain.invoke(
            {
                "intent": intent,
                "existing_ideas": "No existing roadmap nodes provided.",
            }
        )
        nodes_data = parsed_nodes.root

        created_nodes: List[RoadmapNode] = []
        label_to_id_map: dict[str, str] = {}

        for node_schema in nodes_data:
            metadata = dict(node_schema.metadata or {})
            if node_schema.node_type == "decision" and node_schema.decision_options:
                metadata.setdefault("options", node_schema.decision_options)

            node_payload = {
                "label": node_schema.label,
                "description": node_schema.description,
                "node_type": node_schema.node_type,
                "metadata": metadata,
            }

            node = roadmap_service.create_node(project_id, node_payload)
            label_to_id_map[node_schema.label] = node.id
            created_nodes.append(node)

        for node, node_schema in zip(created_nodes, nodes_data):
            depends_on_labels = node_schema.depends_on_labels
            if depends_on_labels:
                depends_on_ids = [label_to_id_map[label] for label in depends_on_labels if label in label_to_id_map]
                if depends_on_ids:
                    roadmap_service.update_node(project_id, node.id, {"depends_on_ids": depends_on_ids})
                    for dep_id in depends_on_ids:
                        try:
                            roadmap_service.create_edge(project_id, {"from_node_id": dep_id, "to_node_id": node.id, "kind": "depends_on"})
                        except ValueError:
                            pass # Edge might already exist
        
        return created_nodes
    except Exception as e:
        logger.exception(
            "roadmap_service.create_roadmap_nodes_from_intent.error",
            extra={"project_id": project_id, "error": str(e)},
        )
        raise


def generate_roadmap_from_project_intent(project_id: str, intent: Optional[str] = None) -> RoadmapGraph:
    """
    Generate a complete roadmap DAG from project intent.
    """
    create_roadmap_nodes_from_intent(project_id, intent or "Generate a roadmap for the project.")
    return roadmap_service.get_graph(project_id)
