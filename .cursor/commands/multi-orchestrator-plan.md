Multi-Persona Orchestrator PLAN (Phases 1-4, no edits)

You are running the **PLAN-ONLY** workflow for the multi-persona orchestrator.

Instructions:

- Treat the full user message (including any text after this snippet) plus recent context
  as the TASK you must analyze.
- Fetch and follow the `multi-persona-orchestrator-plan` Cursor project rule from
  `.cursor/rules` if it exists.
- Run **Phases 1-4 only**:
  1) Scope & Scan
  2) Specialist Reviews ([FE], [BE], [INFRA], [QA])
  3) Round Table & Decisions
  4) EDIT PLAN

Hard constraints:

- Do NOT edit any files or propose concrete patches.
- Produce an **EDIT PLAN** section exactly as defined in the rule, with numbered steps
  by file.
- End with the Phase 4 status line and the question:
  "Shall I proceed to apply this EDIT PLAN now (in a separate APPLY phase)?"

Now, interpret the user's task and begin with **Phase 1**.

Invoke it in chat by typing /multi-orchestrator-plan and then adding your task description (e.g. "fix the deployment startup failure in FastAPI for non-local envs").

