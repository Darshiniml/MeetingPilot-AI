from .mcp_client import MCPClient

def discover_available_tools(client: MCPClient, provider: str | None = None):
    return client.discover_tools(provider)
