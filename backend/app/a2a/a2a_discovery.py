from __future__ import annotations

import logging
from app.a2a.a2a_models import AgentCapability, AgentState
from app.a2a.a2a_registry import get_a2a_registry

logger = logging.getLogger(__name__)

def discover_enterprise_agents() -> None:
    """Pre-register all external enterprise mock agents in the global registry."""
    registry = get_a2a_registry()
    
    # 1. GitHub Agent
    registry.register_agent(
        agent_name="github",
        endpoint_url="http://mock-github-agent/api/a2a",
        capabilities=[
            AgentCapability(
                capability_id="github.search_issues",
                name="search_issues",
                version="1.0.0",
                provider="github",
                required_permissions=["repo"],
                supported_input_schema={"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
                supported_output_schema={"type": "object"}
            ),
            AgentCapability(
                capability_id="github.create_issue",
                name="create_issue",
                version="1.0.0",
                provider="github",
                required_permissions=["repo"],
                supported_input_schema={"type": "object", "properties": {"title": {"type": "string"}}, "required": ["title"]},
                supported_output_schema={"type": "object"}
            )
        ],
        version="1.0.0"
    )
    registry.heartbeat("github", AgentState.ACTIVE, {"load": 0, "latency_ms": 120.0, "success_rate": 0.99})

    # 2. Slack Agent
    registry.register_agent(
        agent_name="slack",
        endpoint_url="http://mock-slack-agent/api/a2a",
        capabilities=[
            AgentCapability(
                capability_id="slack.send_message",
                name="send_message",
                version="1.0.0",
                provider="slack",
                required_permissions=["chat:write"],
                supported_input_schema={"type": "object", "properties": {"channel": {"type": "string"}, "message": {"type": "string"}}, "required": ["channel", "message"]},
                supported_output_schema={"type": "object"}
            )
        ],
        version="1.0.0"
    )
    registry.heartbeat("slack", AgentState.ACTIVE, {"load": 0, "latency_ms": 80.0, "success_rate": 0.99})

    # 3. Notion Agent
    registry.register_agent(
        agent_name="notion",
        endpoint_url="http://mock-notion-agent/api/a2a",
        capabilities=[
            AgentCapability(
                capability_id="notion.create_page",
                name="create_page",
                version="1.0.0",
                provider="notion",
                required_permissions=["write"],
                supported_input_schema={"type": "object", "properties": {"title": {"type": "string"}}, "required": ["title"]},
                supported_output_schema={"type": "object"}
            )
        ],
        version="1.0.0"
    )
    registry.heartbeat("notion", AgentState.ACTIVE, {"load": 0, "latency_ms": 150.0, "success_rate": 0.98})

    # 4. Jira Agent
    registry.register_agent(
        agent_name="jira",
        endpoint_url="http://mock-jira-agent/api/a2a",
        capabilities=[
            AgentCapability(
                capability_id="jira.create_task",
                name="create_task",
                version="1.0.0",
                provider="jira",
                required_permissions=["write"],
                supported_input_schema={"type": "object", "properties": {"project_key": {"type": "string"}, "summary": {"type": "string"}}, "required": ["project_key", "summary"]},
                supported_output_schema={"type": "object"}
            )
        ],
        version="1.0.0"
    )
    registry.heartbeat("jira", AgentState.ACTIVE, {"load": 0, "latency_ms": 140.0, "success_rate": 0.98})

    # 5. Salesforce Agent
    registry.register_agent(
        agent_name="salesforce",
        endpoint_url="http://mock-salesforce-agent/api/a2a",
        capabilities=[
            AgentCapability(
                capability_id="salesforce.create_lead",
                name="create_lead",
                version="1.0.0",
                provider="salesforce",
                required_permissions=["crm"],
                supported_input_schema={"type": "object", "properties": {"last_name": {"type": "string"}, "company": {"type": "string"}}, "required": ["last_name", "company"]},
                supported_output_schema={"type": "object"}
            )
        ],
        version="1.0.0"
    )
    registry.heartbeat("salesforce", AgentState.ACTIVE, {"load": 0, "latency_ms": 200.0, "success_rate": 0.97})

    # 6. MS Teams Agent
    registry.register_agent(
        agent_name="teams",
        endpoint_url="http://mock-teams-agent/api/a2a",
        capabilities=[
            AgentCapability(
                capability_id="teams.send_chat",
                name="send_chat",
                version="1.0.0",
                provider="teams",
                required_permissions=["chat:write"],
                supported_input_schema={"type": "object", "properties": {"team_id": {"type": "string"}, "content": {"type": "string"}}, "required": ["team_id", "content"]},
                supported_output_schema={"type": "object"}
            )
        ],
        version="1.0.0"
    )
    registry.heartbeat("teams", AgentState.ACTIVE, {"load": 0, "latency_ms": 90.0, "success_rate": 0.99})

    # 7. Google Drive Agent
    registry.register_agent(
        agent_name="google_drive",
        endpoint_url="http://mock-drive-agent/api/a2a",
        capabilities=[
            AgentCapability(
                capability_id="google_drive.search_files",
                name="search_files",
                version="1.0.0",
                provider="google_drive",
                required_permissions=["drive.readonly"],
                supported_input_schema={"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
                supported_output_schema={"type": "object"}
            )
        ],
        version="1.0.0"
    )
    registry.heartbeat("google_drive", AgentState.ACTIVE, {"load": 0, "latency_ms": 110.0, "success_rate": 0.99})

    # 8. ServiceNow Agent
    registry.register_agent(
        agent_name="servicenow",
        endpoint_url="http://mock-servicenow-agent/api/a2a",
        capabilities=[
            AgentCapability(
                capability_id="servicenow.create_incident",
                name="create_incident",
                version="1.0.0",
                provider="servicenow",
                required_permissions=["itil"],
                supported_input_schema={"type": "object", "properties": {"short_description": {"type": "string"}}, "required": ["short_description"]},
                supported_output_schema={"type": "object"}
            )
        ],
        version="1.0.0"
    )
    registry.heartbeat("servicenow", AgentState.ACTIVE, {"load": 0, "latency_ms": 180.0, "success_rate": 0.97})
    
    logger.info("Enterprise mock agents discovered and initialized.")
