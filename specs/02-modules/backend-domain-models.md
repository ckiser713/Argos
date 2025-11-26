## Overview
- Shared domain schemas/enums for context, workflows, ingest, agents, ideas/tickets, mission control, roadmap, knowledge graph, streaming events, and simple message responses (`backend/app/domain/models.py`).
- Project domain and execution mode models live in separate files (`backend/app/domain/project.py`, `backend/app/domain/mode.py`).

## Responsibilities & Non-Responsibilities
- Responsibilities: define Pydantic models used by services/APIs; provide validation constraints (enums, ranges) and serialization hints (camel-case in project models).
- Non-Responsibilities: persistence/migration, business logic, API routing, observability.

## Dependencies & Integration Points
- Used across services (context, ingest, agent, workflow, roadmap, knowledge, streaming) and API response models.
- DB schemas in `backend/app/db.py` should align with these models (note: some fields in DB are not surfaced, e.g., workflow node messages/error/timestamps).

## Key Models & Constraints (selected)
- **Context**: `ContextItemType` enum (`pdf|repo|chat|other`), `ContextItem {id,name,type,tokens>=0,pinned?,canonical_document_id?,created_at?}`, `ContextBudget {project_id,total_tokens,used_tokens,available_tokens,items[]}` (`backend/app/domain/models.py:15-47`).
- **Workflow**: `WorkflowNode {id,label,x,y}`, `WorkflowEdge {id,source,target}`, `WorkflowGraph {id,name,description?,nodes[],edges[]}`, `WorkflowRunStatus` enum (`pending|running|completed|failed|cancelled|paused`), `WorkflowRun {id,workflow_id,status,started_at,finished_at?,last_message?,task_id?,paused_at?,cancelled_at?}`, `WorkflowNodeStatus` enum (`idle|running|completed|failed|cancelled`), `WorkflowNodeState {node_id,status,progress 0..1}` (`backend/app/domain/models.py:52-107`).
- **Ingest**: `IngestStatus` enum (`queued|running|completed|failed|cancelled`), `IngestJob {id,project_id?,source_path,original_filename?,byte_size?,mime_type?,stage?,created_at,updated_at?,completed_at?,status,progress 0..1,message?,error_message?,canonical_document_id?}`, `IngestRequest {source_path}` (`backend/app/domain/models.py:111-141`).
- **Agents**: `AgentProfile {id,name,description?,capabilities[]}`, `AgentRunStatus` enum, `AgentRun {id,project_id,workflow_id?,agent_id,status,input_prompt?,output_summary?,context_item_ids[],started_at,finished_at?}`, `AgentRunRequest {project_id,agent_id,input_prompt,context_item_ids[]}`, `AgentStep {id,run_id,step_number,node_id?,status,input?,output?,error?,duration_ms?,started_at,completed_at?}`, `AgentMessage {id,run_id,role user|assistant|system,content,context_item_ids[],created_at}`, `AgentNodeState {run_id,node_id,status,progress,messages[],started_at?,completed_at?,error?}` (`backend/app/domain/models.py:141-225`).
- **Ideas/Tickets**: `IdeaCandidate {id,project_id,type,summary,status active|archived,confidence 0..1,source_log_ids[],source_channel?,source_user?,created_at}`, `IdeaCluster {id,project_id,label,description?,color?,idea_ids[],priority?,created_at,updated_at}`, `IdeaTicket {id,project_id,idea_id?,title,description?,status (active|complete|blocked),priority (low|medium|high),origin_story?,category?,implied_task_summaries[],repo_hints[],source_quotes?,source_channel?,confidence 0..1?,created_at,updated_at}` (`backend/app/domain/models.py:235-294`).
- **Mission Control**: `MissionControlTask {id,project_id,title,origin repo|chat|pdf,confidence 0..1,column backlog|todo|in_progress|done,context[],priority?,idea_id?,ticket_id?,created_at,updated_at}` (`backend/app/domain/models.py:296-321`).
- **Roadmap**: `RoadmapNode {id,project_id,label,description?,status pending|active|complete|blocked,priority?,start_date?,target_date?,depends_on_ids[],lane_id?,idea_id?,ticket_id?,mission_control_task_id?,created_at,updated_at}`, `RoadmapEdge {id,project_id,from_node_id,to_node_id,kind depends_on|relates_to,label?,created_at}`, `RoadmapGraph {nodes[],edges[],generated_at}` (`backend/app/domain/models.py:327-377`).
- **Knowledge graph**: `KnowledgeNode {id,project_id,title,summary?,text?,type,tags[],metadata?,created_at?,updated_at?}`, `KnowledgeEdge {id,project_id,source,target,type,weight?,label?,created_at?}`, `KnowledgeGraph {nodes[],edges[],generated_at}`, `KnowledgeSearchRequest {query,type?,tags?,limit/max_results, use_vector_search}` with aliasing logic syncing limit/max_results (`backend/app/domain/models.py:382-428`).
- **Streaming events**: `IngestJobEvent`, `AgentRunEvent`, `WorkflowNodeEvent` with enums for event types (`backend/app/domain/models.py:439-472`).
- **Misc**: `MessageResponse {message}` (`backend/app/domain/models.py:432-434`).
- **Project/mode**: `CortexProject`, requests, and `ProjectExecutionSettings` detailed in `backend-projects-and-mode.md`.

## Control/Usage Notes
- Pydantic validation ranges: progress and token counts enforce non-negative/<=1 constraints where defined.
- Some DB columns are not represented in models (e.g., workflow node messages/error/timestamps, ingest job stage/progress stored as float); services may return partial data.
- `KnowledgeSearchRequest` dual fields `limit`/`max_results` normalized in `__init__`.

## Config & Runtime Parameters
- Mode defaults drawn from settings (see mode domain).
- No global config hooks in models beyond field defaults/validators.

## Error & Failure Semantics
- Validation errors raised by Pydantic on enum/constraint violations.
- Missing alignment between DB nullable columns and model optionality may cause runtime errors if DB returns NULL for required fields.

## Observability
- None; models do not log.

## Risks, Gaps, and [ASSUMPTION] Blocks
- DB schema vs model mismatches (e.g., workflow node state fields omitted) can hide errors or drop diagnostics.
- Agent/idea/roadmap status lifecycle semantics are not fully specified in code; [ASSUMPTION] consuming services enforce transitions.
- Mission control/task models present but no routes/services documented; potential dead code.
- No versioning for data contracts; changes may break clients silently.

## Verification Ideas
- Contract tests ensuring API responses serialize per these models and include required fields.
- Alignment tests between DB schema columns and model optionality (detect NULLs into non-optional fields).
- Schema evolution tests: add versioning or explicit changelog for model changes.
