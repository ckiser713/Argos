Goal: The prompt engineering and logic to turn text into a visualized roadmap.

Markdown

# SPEC-006: Roadmap Generation Logic

## Context
Cortex needs to visualize projects as a DAG (Directed Acyclic Graph), not just text. The `RoadmapService` needs a structured generation method.

## Requirements
- **Output Format:** JSON strictly matching `WorkflowGraph` (nodes with x/y coordinates, edges).
- **Layout Algorithm:** Simple heuristic to assign (x, y) coordinates based on dependency depth (Phases).

## Implementation Guide

### 1. The Prompt (System Message)
```text
You are a Senior Technical Program Manager.
Goal: Convert the user's intent into a structured Project Roadmap.
Output: JSON object with 'nodes' and 'edges'.
Rules:
1. Break work into Phases (Phase 1, Phase 2, etc.).
2. Identify Decision Points (Diamond shape nodes) where the user must choose a path (e.g., "SQL vs NoSQL").
3. Nodes must have 'id', 'label', 'type' (task/decision), and 'phase_index'.
2. The Service Logic (app/services/roadmap_service.py)
Python

import json
from app.services.llm_service import generate_text

def generate_roadmap_from_intent(project_id: str, intent: str) -> dict:
    prompt = f"Generate a roadmap for: {intent}"
    # Force JSON mode in LLM (if supported) or parse text
    response_json = generate_text(prompt, json_mode=True) 
    data = json.loads(response_json)
    
    # Auto-Layout Logic
    # Assign X,Y based on 'phase_index'
    for node in data['nodes']:
        phase = node.get('phase_index', 0)
        node['y'] = phase * 150
        node['x'] = 250 + (node.get('sibling_index', 0) * 200)
        
    # Save to DB (using Repo from SPEC-001)
    return data