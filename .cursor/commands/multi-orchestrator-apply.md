Multi-Persona Orchestrator APPLY (Phases 5-6, implement EDIT PLAN)

You are running the **APPLY-ONLY** workflow for the multi-persona orchestrator.

Instructions:

- Assume there is an existing "EDIT PLAN" in the recent conversation, produced by the
  PLAN workflow (Phases 1-4).
- Fetch and follow the `multi-persona-orchestrator-apply` Cursor project rule from
  `.cursor/rules` if it exists.
- Run **Phases 5-6 only**:
  5) APPLY CHANGES - implement each step of the EDIT PLAN in order.
  6) FINAL QA & HANDOFF - produce SUMMARY, CHECKLIST, NEXT STEPS.

Hard constraints:

- Only make edits that are required to satisfy the EDIT PLAN. No unrelated refactors.
- If the plan is incomplete or wrong, pause edits, update the EDIT PLAN section in text
  with minimal adjustments, clearly mark it as updated, then continue.
- Close with the final SUMMARY, CHECKLIST, and NEXT STEPS as defined in the rule.

Now, locate the existing EDIT PLAN and begin with **Phase 5**, implementing it step-by-step.

