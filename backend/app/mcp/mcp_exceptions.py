class MCPException(Exception): pass
class MCPToolNotFoundException(MCPException): pass
class MCPValidationException(MCPException): pass
class MCPTransientException(MCPException): pass
