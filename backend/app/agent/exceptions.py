"""Domain-specific agent framework errors."""


class AgentException(Exception):
    """Base exception for autonomous-agent framework failures."""


class PlannerException(AgentException):
    """Raised when a plan cannot be created."""


class ToolNotFoundException(AgentException):
    """Raised when a requested tool has not been registered."""
