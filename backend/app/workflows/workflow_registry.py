"""In-memory registry managing design templates and custom plugins dynamically."""

import logging
from app.workflows.workflow_models import WorkflowTemplate
from app.workflows.workflow_templates import get_default_templates

logger = logging.getLogger(__name__)


class WorkflowRegistry:
    """Registration registry for versioned automation workflow templates."""

    def __init__(self) -> None:
        self._templates: dict[str, WorkflowTemplate] = {}
        # Load standard defaults on load
        for t in get_default_templates():
            self.register(t)

    def register(self, template: WorkflowTemplate) -> None:
        """Add or update a template inside the registry."""
        self._templates[template.template_id] = template
        logger.info("Registered workflow template: %s (v%s)", template.template_id, template.version)

    def get(self, template_id: str) -> WorkflowTemplate | None:
        """Fetch a template by ID."""
        return self._templates.get(template_id)

    def list(self) -> list[WorkflowTemplate]:
        """Fetch all registered templates."""
        return list(self._templates.values())

    def clear(self) -> None:
        """Clear all templates (useful for resetting during tests)."""
        self._templates.clear()


# Global singleton instance
_workflow_registry = None


def get_workflow_registry() -> WorkflowRegistry:
    """Return the shared WorkflowRegistry singleton."""
    global _workflow_registry
    if _workflow_registry is None:
        _workflow_registry = WorkflowRegistry()
    return _workflow_registry
