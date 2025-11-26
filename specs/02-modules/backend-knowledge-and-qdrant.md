## Overview
- Knowledge graph CRUD over SQLite plus optional vector search via Qdrant (`backend/app/services/knowledge_service.py:19-428`).
- Supports listing/creating/updating nodes, listing/creating/deleting edges, graph retrieval with view/focus filters, neighbor lookup, and search combining vector and text.

## Responsibilities & Non-Responsibilities
- Responsibilities: persist knowledge nodes/edges per project; enforce basic existence/duplicate checks; fetch graph subsets; search nodes using Qdrant vector search with text fallback.
- Non-Responsibilities: concurrency control, schema migrations, rich node/edge types, tagging/metadata persistence beyond tags_json, cascade deletes, access control, Qdrant client lifecycle.

## Dependencies & Integration Points
- DB tables: `knowledge_nodes`, `knowledge_edges` (`backend/app/db.py:104-114,310-325`).
- Domain models: `KnowledgeNode`, `KnowledgeEdge`, `KnowledgeGraph`, `KnowledgeSearchRequest`, `PaginatedResponse` (`backend/app/domain/models.py:382-428`).
- Vector store: `qdrant_service.upsert_knowledge_node` and `.search_knowledge_nodes` (`backend/app/services/knowledge_service.py:170-178,324-359`); requires `qdrant_service.client`.
- API router (not shown here) should bind to these service methods; streaming not involved.

## Interfaces & Contracts
- `get_graph(project_id, view?, focus_node_id?) -> KnowledgeGraph` (`backend/app/services/knowledge_service.py:24-58`): loads up to 1000 nodes/edges, filters by view (ideas/tickets/docs), optionally focuses on neighbors of a node.
- `get_node(project_id, node_id) -> KnowledgeNode|None` (`60-68`).
- `get_node_neighbors(project_id, node_id) -> {node, neighbors[], edges[]}` or raises ValueError if not found (`69-109`).
- `list_nodes(project_id, cursor?, limit?) -> PaginatedResponse` (`110-134`); `next_cursor` is id if more rows.
- `create_node(project_id, node_data) -> KnowledgeNode` (`135-180`): inserts DB row (title/summary/tags/type only), stores embedding in Qdrant.
- `update_node(project_id, node_id, updates) -> KnowledgeNode` (`182-227`): validates existence; updates title/summary/tags; upserts embedding if title/summary changed.
- `list_edges(project_id, cursor?, limit?) -> PaginatedResponse` (`228-252`).
- `create_edge(project_id, edge_data) -> KnowledgeEdge` (`253-308`): validates source/target exist; rejects duplicates; inserts edge.
- `delete_edge(project_id, edge_id)` (`310-313`).
- `search(project_id, KnowledgeSearchRequest) -> List[KnowledgeNode]` (`315-393`): tries vector search when `useVectorSearch` truthy and client present; falls back to LIKE search on title/summary; attaches similarity_score to metadata.

## Data Models
- `KnowledgeNode {id, project_id, title, summary?, text?, type, tags[], metadata?, created_at?, updated_at?}`; DB stores `tags_json` only.
- `KnowledgeEdge {id, project_id, source, target, type, weight?, label?, created_at?}`.
- `KnowledgeGraph {nodes[], edges[], generated_at}`.
- `KnowledgeSearchRequest {query, type?, tags?, limit/max_results, use_vector_search}` with aliasing between `limit` and `max_results`.

## Control Flows
- Node creation: generate UUID, build node with title/summary/text/type/tags, insert into DB (metadata not stored), upsert embedding to Qdrant.
- Node update: validate existence, update title/summary/tags, upsert embedding if title/summary changed.
- Edge creation: validate source/target exist, reject duplicate source-target, insert edge.
- Graph retrieval: list nodes/edges (limit 1000), filter by view, optionally focus on node + neighbors.
- Search: attempt Qdrant vector search; order results by vector scores and enrich metadata; fallback text search scores matches in title/summary.

## Config & Runtime Parameters
- Qdrant client endpoint from settings (`Settings.qdrant_url`); not set here but via qdrant_service (see separate spec).
- Result limits: list defaults to 50, graph uses fixed 1000; search uses `request.max_results`.
- No pagination cursor beyond id; no server-side offset for nodes/edges.

## Error & Failure Semantics
- Raises ValueError on missing nodes for neighbor lookup or invalid source/target in edge creation; callers should translate to HTTP errors.
- Duplicate edge raises ValueError.
- Qdrant operations not wrapped in try/except in create/update; failures would raise.
- Search fallback is case-insensitive LIKE; no fuzzy or typo tolerance.

## Observability
- No logging/metrics; Qdrant failures not logged unless exceptions bubble.

## Risks, Gaps, and [ASSUMPTION] Blocks
- Metadata/text fields not persisted to DB (only tags/summary/title), so Qdrant stores text but DB cannot return it; [ASSUMPTION] acceptable for current UI.
- No delete for nodes; edges can reference deleted nodes if removed manually; no cascade.
- Fixed graph fetch cap (1000) may truncate large graphs without warning.
- No authorization checks; relies on global deps.
- Qdrant dependency availability is not checked; lack of client silently falls back to text search.

## Verification Ideas
- API/service tests: create/list/update nodes; ensure tags JSON round-trips; edge creation rejects invalid nodes/duplicates; delete edge works.
- Search tests: with mock qdrant_client returning results, ensure ordering and similarity_score set; fallback search orders by score; useVectorSearch flag honored.
- Graph view/focus tests: view filters nodes by type; focus_node_id returns neighbors and prunes unrelated edges.
