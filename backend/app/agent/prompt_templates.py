"""Prompts for the LLM-backed agent planner."""

from __future__ import annotations

from typing import Any


TOOL_CATALOG: tuple[dict[str, Any], ...] = (
    {"name": "summary", "purpose": "Generate a meeting summary.", "required_parameters": ["meeting_id"], "expected_output": "Generated summary."},
    {"name": "transcript", "purpose": "Persist transcription output.", "required_parameters": ["meeting_id", "meeting_started_at", "audio_chunk", "whisper_result"], "expected_output": "Persisted transcript rows."},
    {"name": "meeting_history", "purpose": "Retrieve a meeting or a page of history.", "required_parameters": [], "expected_output": "Meeting history data."},
    {"name": "action_items", "purpose": "Extract action items for a meeting.", "required_parameters": ["meeting_id"], "expected_output": "Action items."},
    {"name": "scheduler", "purpose": "Plan a meeting.", "required_parameters": ["request_text"], "expected_output": "Scheduling plan."},
    {"name": "calendar", "purpose": "Read or create calendar events.", "required_parameters": ["operation"], "expected_output": "Calendar event or events."},
    {"name": "gmail", "purpose": "Send email or list sent messages.", "required_parameters": ["operation"], "expected_output": "Email result."},
    {"name": "contacts", "purpose": "Search contacts.", "required_parameters": ["query"], "expected_output": "Matching contacts."},
    {"name": "rag_chat", "purpose": "Answer a question from meeting content.", "required_parameters": ["meeting_id", "question"], "expected_output": "Grounded answer."},
    {"name": "vision", "purpose": "Inspect the active meeting display.", "required_parameters": [], "expected_output": "Vision inspection result."},
)


def build_planner_prompt(user_message: str, memory_context: dict[str, Any] | None = None) -> str:
    """Return a strict JSON-only planning prompt with all agent tool metadata."""
    tool_lines = "\n".join(
        f"- name: {tool['name']}\n  purpose: {tool['purpose']}\n  required_parameters: {tool['required_parameters']}\n  expected_output: {tool['expected_output']}"
        for tool in TOOL_CATALOG
    )
    return f"""You are the MeetingPilot planning engine. Choose zero or more tools in execution order.
Available tools:
{tool_lines}

Return ONLY valid JSON, with no markdown and no extra text. Use exactly this shape:
{{"intent":"one supported intent or MULTI_TOOL","confidence":0.0,"reasoning":"brief explanation","tools":["tool_name"],"parameters":{{}}}}
Supported intents: SUMMARIZE_MEETING, LIST_ACTION_ITEMS, SCHEDULE_MEETING, GOOGLE_CALENDAR, SEND_EMAIL, CONTACT_SEARCH, SEARCH_HISTORY, SEARCH_TRANSCRIPT, GENERAL_CHAT, MULTI_TOOL.
Only select tool names listed above. Use parameters for user-supplied values. Later tools may reference prior output using {{{{tool_outputs.tool_name.key}}}}.

Memory context (use only when relevant): {memory_context or {}}
User message: {user_message}"""


def build_repair_prompt(invalid_response: str) -> str:
    """Ask the model once to repair a malformed planner response."""
    return f"""Repair the following planner output. Return ONLY valid JSON with keys intent, confidence, reasoning, tools, and parameters. Do not add markdown or commentary.
Invalid output:
{invalid_response}"""
