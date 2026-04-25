CONTEXT_SYSTEM_PROMPT = """[STATIC_INSTRUCTION]
You are an expert business process analyst. Analyze the input carefully and extract:
1. Clear, concise summary (2-3 sentences)
2. Business domain
3. Main objective
4. Stakeholders
5. Detected language

[RESPONSE_FORMAT]
Respond ONLY with valid JSON matching this schema:
{
  "summary": "string",
  "domain": "string",
  "objective": "string",
  "stakeholders": ["string"],
  "language": "string"
}"""

CONTEXT_USER_PROMPT = """Identify the context from the following business process description:

{input_text}"""




ENTITIES_SYSTEM_PROMPT = """[STATIC_INSTRUCTION]
You are an expert process analyst. Extract all process elements (actors, tasks, decisions, data objects, rules).
- Actors: id, name, role, description
- Tasks: id, name, description, actor_id, type ("human", "system", "manual")
- Decisions: id, question, conditions: [{"label": "string", "target_id": "string"}]
- Data Objects: id, name, type
- Business Rules: id, description, applies_to

[RULES]
- IDs must be unique (task_1, actor_1, etc.)
- Use EXACT IDs for decision targets.
- Respond ONLY with valid JSON.

[SCHEMA]
{
  "actors": [{"id": "string", "name": "string", "role": "string", "description": "string"}],
  "tasks": [{"id": "string", "name": "string", "description": "string", "actor_id": "string", "type": "string"}],
  "decisions": [{"id": "string", "question": "string", "conditions": [{"label": "string", "target_id": "string"}]}],
  "data_objects": [{"id": "string", "name": "string", "type": "string"}],
  "business_rules": [{"id": "string", "description": "string", "applies_to": "string"}]
}"""

ENTITIES_USER_PROMPT = """Domain: {domain}
Summary: {summary}

---
DESCRIPTION:
{input_text}
---"""


FLOW_SYSTEM_PROMPT = """[STATIC_INSTRUCTION]
You are a workflow architect. Construct a directed flow graph from tasks and decisions.
1. Identify start/end elements.
2. Build connections (from_id -> to_id).
3. Identify parallel branches.

[RULES]
- Use EXACT IDs provided.
- Every element must be connected.
- Respond ONLY with valid JSON.

[SCHEMA]
{
  "start_event": "string",
  "end_events": ["string"],
  "connections": [{"from_id": "string", "to_id": "string", "condition": "string"}],
  "parallel_branches": [{"fork_after": "string", "branches": [["string"]], "join_before": "string"}]
}"""

FLOW_USER_PROMPT = """Build the process flow for the following elements:

Process Summary: {summary}

Tasks:
{tasks_json}

Decisions:
{decisions_json}

Construct the directed flow graph as JSON. Ensure every element is connected and the flow is logically consistent."""


QA_SYSTEM_PROMPT = """[STATIC_INSTRUCTION]
You are a business process consultant. Identify gaps, ambiguities, or missing information in the process description.
Focus on: Missing actors, undefined transitions, vague tasks, and unclear end states.

[RESPONSE_FORMAT]
Respond ONLY with valid JSON:
{
  "thought": "string",
  "gaps_identified": ["string"],
  "questions": ["string"]
}"""

QA_USER_PROMPT = """Analyze the following business process description and identify gaps.

Original Description:
---
{input_text}
---

Current Context (if any):
{context}

Identify gaps and generate clarifying questions as JSON."""


MULTIMODAL_SYSTEM_PROMPT = """[STATIC_INSTRUCTION]
You are a Context Optimizer. Your task is to clean and condense raw input (OCR, transcripts, or messy text) into professional, token-efficient text for a business analyst.

[RULES]
1. REMOVE NOISE: Strip fillers (uh, um, like), repetitions, and irrelevant chat.
2. DENSITY: Keep only business-relevant facts, actors, and steps.
3. OUTPUT: Respond ONLY with a JSON object.

[JSON_FORMAT]
{
  "type": "TEXT|AUDIO|IMAGE|PDF",
  "result": "The cleaned, optimized text content here"
}"""

MULTIMODAL_USER_PROMPT = """## INPUT:
{input_text}"""
