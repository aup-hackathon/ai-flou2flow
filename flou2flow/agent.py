"""Agentic system for Flou2Flow."""

import json
import logging
from typing import Any

from .exporters import generate_elsa_workflow
from .llm import llm_client
from .models import AgentResponse, ProcessContext, ProcessEntities, ProcessFlow, QAResponse
from .pipeline import (
    step_context_understanding,
    step_entity_extraction,
    step_flow_construction,
)
from .prompts import QA_SYSTEM_PROMPT, QA_USER_PROMPT

logger = logging.getLogger(__name__)

AGENT_SYSTEM_PROMPT = """You are a Business Process Agent. Your goal is to help users analyze and transform business process descriptions.
You have access to several tools that represent steps in our processing pipeline.

TOOLS:
1. analyze_context(input_text: str): Summarize the process and identify domain/objective.
2. extract_entities(input_text: str, context: dict): Extract actors, tasks, and decisions.
3. construct_flow(context: dict, entities: dict): Build the process flow graph.
4. generate_elsa(context: dict, entities: dict, flow: dict): Generate Elsa-compatible JSON.

PLANNING:
Before taking any action, think step-by-step. Explain what you are going to do.

TOOL CALL FORMAT:
If you want to call a tool, respond with a JSON object containing 'tool' and 'args'.
Example: {"tool": "analyze_context", "args": {"input_text": "..."}}

FINAL ANSWER:
When you have the final result or have completed the task, provide a clear summary and the final data.

Always respond in JSON format with the following structure:
{
  "thought": "your step-by-step reasoning",
  "tool_call": {"tool": "tool_name", "args": {...}} or null,
  "final_result": "your final answer or null"
}
"""

class FlouAgent:
    def __init__(self):
        self.history = []

    async def run(self, task: str, mode: str = "auto", model: str | None = None) -> AgentResponse:
        steps_taken = []
        tool_calls = []
        context = {}

        # Adjust system prompt based on mode
        mode_instruction = ""
        if mode == "interactive":
            mode_instruction = "\nMODE: INTERACTIVE. If you are unsure about something or need more details from the user, you can stop and ask a question using the 'final_result' field."
        else:
            mode_instruction = "\nMODE: AUTO. Try to complete the task autonomously. Make reasonable assumptions if needed."

        current_system_prompt = AGENT_SYSTEM_PROMPT + mode_instruction
        current_input = f"User Task: {task}"

        max_iterations = 10
        for _ in range(max_iterations):
            response_text = await llm_client.chat(
                system_prompt=current_system_prompt,
                user_prompt=current_input,
                json_mode=True,
                model=model
            )

            try:
                data = llm_client.parse_json_response(response_text)
            except Exception as e:
                logger.error(f"Failed to parse agent response: {e}")
                return AgentResponse(result=f"Error parsing agent response: {str(e)}", steps_taken=steps_taken, tool_calls=tool_calls)

            thought = data.get("thought", "")
            if thought:
                steps_taken.append(thought)

            tool_call = data.get("tool_call")
            if tool_call:
                tool_name = tool_call.get("tool")
                args = tool_call.get("args", {})
                tool_calls.append({"tool": tool_name, "args": args})

                logger.info(f"Agent calling tool: {tool_name}")

                try:
                    result = await self.execute_tool(tool_name, args, context, model=model)
                    current_input = f"Tool '{tool_name}' returned: {json.dumps(result, ensure_ascii=False)}"
                    # Store context to pass between tools if needed
                    if tool_name == "analyze_context":
                        context["context"] = result
                    elif tool_name == "extract_entities":
                        context["entities"] = result
                    elif tool_name == "construct_flow":
                        context["flow"] = result
                except Exception as e:
                    logger.error(f"Tool execution failed: {e}")
                    current_input = f"Tool '{tool_name}' failed with error: {str(e)}"

            final_result = data.get("final_result")
            if final_result:
                return AgentResponse(
                    result=final_result,
                    steps_taken=steps_taken,
                    tool_calls=tool_calls
                )

        return AgentResponse(
            result="Agent reached maximum iterations without a final answer.",
            steps_taken=steps_taken,
            tool_calls=tool_calls
        )

    async def generate_questions(self, input_text: str, context: dict | None = None, model: str | None = None) -> QAResponse:
        """Analyze input text for gaps and generate clarifying questions."""
        user_prompt = QA_USER_PROMPT.format(
            input_text=input_text,
            context=json.dumps(context, ensure_ascii=False) if context else "None"
        )

        response_text = await llm_client.chat(
            system_prompt=QA_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            json_mode=True,
            model=model
        )

        data = llm_client.parse_json_response(response_text)

        return QAResponse(
            questions=data.get("questions", []),
            gaps_identified=data.get("gaps_identified", []),
            thought=data.get("thought", "")
        )

    async def execute_tool(self, tool_name: str, args: dict[str, Any], context: dict[str, Any], model: str | None = None) -> Any:
        if tool_name == "analyze_context":
            input_text = args.get("input_text")
            res = await step_context_understanding(input_text, model=model)
            return res.model_dump()

        elif tool_name == "extract_entities":
            input_text = args.get("input_text")
            ctx_data = args.get("context") or context.get("context")
            if not ctx_data:
                raise ValueError("Context is required for extract_entities")
            ctx = ProcessContext(**ctx_data)
            res = await step_entity_extraction(input_text, ctx, model=model)
            return res.model_dump()

        elif tool_name == "construct_flow":
            ctx_data = args.get("context") or context.get("context")
            ent_data = args.get("entities") or context.get("entities")
            if not ctx_data or not ent_data:
                raise ValueError("Context and entities are required for construct_flow")
            ctx = ProcessContext(**ctx_data)
            ent = ProcessEntities(**ent_data)
            res = await step_flow_construction(ctx, ent, model=model)
            return res.model_dump()

        elif tool_name == "generate_elsa":
            ctx_data = args.get("context") or context.get("context")
            ent_data = args.get("entities") or context.get("entities")
            flow_data = args.get("flow") or context.get("flow")
            if not ctx_data or not ent_data or not flow_data:
                raise ValueError("Context, entities, and flow are required for generate_elsa")
            ctx = ProcessContext(**ctx_data)
            ent = ProcessEntities(**ent_data)
            flow = ProcessFlow(**flow_data)
            res = generate_elsa_workflow(ctx, ent, flow)
            return res

        else:
            raise ValueError(f"Unknown tool: {tool_name}")
