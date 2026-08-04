import unittest

from app.agent.models import AgentRequest
from app.mcp.mcp_client import MCPClient
from app.mcp.mcp_exceptions import MCPTransientException
from app.mcp.mcp_models import MCPRequest, MCPTool
from app.mcp.mcp_registry import MCPRegistry
from app.mcp.mcp_server import MCPServer
from app.mcp.supervisor_integration import MCPSupervisorBridge


class MCPTests(unittest.TestCase):
    def setUp(self):
        self.registry = MCPServer().register_mock_tools()
        self.client = MCPClient(self.registry)

    def test_registration_and_discovery(self):
        tools = self.client.discover_tools("github")
        self.assertEqual({tool.name for tool in tools}, {"search_issues", "create_issue", "list_prs"})
        self.assertEqual(set(self.registry.list_providers()), {"github", "slack", "notion", "google_drive", "jira"})

    def test_mock_execution(self):
        response = self.client.invoke(MCPRequest(tool_name="send_message", parameters={"channel": "general", "message": "hello"}, user_id=1), provider="slack")
        self.assertTrue(response.success)
        self.assertTrue(response.output["mock"])

    def test_retries_transient_handler_once(self):
        calls = []
        tool = MCPTool(id="test.retry", name="retry", description="test", provider="test")
        def handler():
            calls.append(1)
            if len(calls) == 1: raise MCPTransientException("temporary")
            return "ok"
        self.registry.register_tool(tool, handler)

        response = self.client.invoke(MCPRequest(tool_name="retry", user_id=1), provider="test")
        self.assertTrue(response.success)
        self.assertEqual(len(calls), 2)

    def test_falls_back_to_another_provider(self):
        response = self.client.invoke(MCPRequest(tool_name="search_issues", parameters={"query": "bug"}, user_id=1), provider="slack", fallback_providers=["jira"])
        self.assertTrue(response.success)
        self.assertEqual(response.output["provider"], "jira")

    def test_supervisor_bridge_executes_external_tool(self):
        response = MCPSupervisorBridge(self.client).execute_external_tool(AgentRequest(user_message="find notes", user_id=2, conversation_id="c1"), "search_notes", {"query": "review"}, provider="notion")
        self.assertTrue(response.success)
        self.assertEqual(response.output["provider"], "notion")


if __name__ == "__main__":
    unittest.main()
