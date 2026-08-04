"""Versioned built-in workflow template definitions and design catalogs."""

from app.workflows.workflow_models import WorkflowStep, WorkflowTemplate


def create_meeting_finished_template() -> WorkflowTemplate:
    """Build the 'Meeting Finished' summary and index pipeline template."""
    s1 = WorkflowStep(name="Generate Summary", tool="summary", max_retries=3)
    s2 = WorkflowStep(name="Extract Action Items", tool="action_items", depends_on=[s1.step_id], max_retries=3)
    s3 = WorkflowStep(name="Refresh Memory", tool="rag_chat", depends_on=[s2.step_id], max_retries=3)
    s4 = WorkflowStep(name="Refresh Embeddings", tool="rag_chat", depends_on=[s3.step_id], max_retries=2)
    s5 = WorkflowStep(name="Generate Recommendations", tool="rag_chat", depends_on=[s4.step_id], max_retries=2)

    return WorkflowTemplate(
        template_id="meeting_finished",
        name="Meeting Finished Summary Pipeline",
        version="1.0.0",
        steps=[s1, s2, s3, s4, s5]
    )


def create_meeting_scheduled_template() -> WorkflowTemplate:
    """Build the 'Meeting Scheduled' calendar invite drafting and send template."""
    s1 = WorkflowStep(name="Generate Invitation", tool="calendar", parameters={"operation": "create"}, max_retries=3)
    s2 = WorkflowStep(name="Prepare Gmail Draft", tool="gmail", parameters={"operation": "draft"}, depends_on=[s1.step_id], max_retries=3)
    # Send Invitation requires explicit user approval
    s3 = WorkflowStep(
        name="Send Invitation",
        tool="gmail",
        parameters={"operation": "send"},
        depends_on=[s2.step_id],
        approval_required=True,
        max_retries=2,
        compensating_action={"tool": "gmail", "parameters": {"operation": "delete_draft"}}
    )

    return WorkflowTemplate(
        template_id="meeting_scheduled",
        name="Meeting Scheduled Invite Automation",
        version="1.0.0",
        steps=[s1, s2, s3]
    )


def create_decision_detected_template() -> WorkflowTemplate:
    """Build the 'Decision Detected' logging and reflection template."""
    s1 = WorkflowStep(name="Create Decision Record", tool="action_items", parameters={"operation": "create"}, max_retries=3)
    s2 = WorkflowStep(name="Notify Planner", tool="rag_chat", depends_on=[s1.step_id], max_retries=2)
    s3 = WorkflowStep(name="Update Memory", tool="rag_chat", depends_on=[s2.step_id], max_retries=3)

    return WorkflowTemplate(
        template_id="decision_detected",
        name="Decision Sync Pipeline",
        version="1.0.0",
        steps=[s1, s2, s3]
    )


def create_deadline_detected_template() -> WorkflowTemplate:
    """Build the 'Deadline Detected' calendar integration template."""
    s1 = WorkflowStep(name="Create Reminder", tool="calendar", parameters={"operation": "create_reminder"}, max_retries=3)
    s2 = WorkflowStep(name="Suggest Calendar Follow-up", tool="calendar", parameters={"operation": "suggest"}, depends_on=[s1.step_id], max_retries=2)

    return WorkflowTemplate(
        template_id="deadline_detected",
        name="Deadline Alert Pipeline",
        version="1.1.0",
        steps=[s1, s2]
    )


def create_commitment_detected_template() -> WorkflowTemplate:
    """Build the 'Commitment Detected' logging template."""
    s1 = WorkflowStep(name="Create Follow-up Recommendation", tool="action_items", max_retries=3)

    return WorkflowTemplate(
        template_id="commitment_detected",
        name="Speaker Commitment Tracking",
        version="1.0.0",
        steps=[s1]
    )


def create_customer_escalation_template() -> WorkflowTemplate:
    """Build the 'Customer Escalation' blocker and report template."""
    s1 = WorkflowStep(name="Generate Executive Summary", tool="summary", max_retries=3)
    s2 = WorkflowStep(name="Draft Escalation Email", tool="gmail", parameters={"operation": "draft"}, depends_on=[s1.step_id], max_retries=3)
    # Send Escalation requires explicit user approval
    s3 = WorkflowStep(
        name="Send Email",
        tool="gmail",
        parameters={"operation": "send"},
        depends_on=[s2.step_id],
        approval_required=True,
        max_retries=2,
        compensating_action={"tool": "gmail", "parameters": {"operation": "delete_draft"}}
    )

    return WorkflowTemplate(
        template_id="customer_escalation",
        name="Customer Escalation Workflow",
        version="1.0.0",
        steps=[s1, s2, s3]
    )


def get_default_templates() -> list[WorkflowTemplate]:
    """Return all built-in template instances."""
    return [
        create_meeting_finished_template(),
        create_meeting_scheduled_template(),
        create_decision_detected_template(),
        create_deadline_detected_template(),
        create_commitment_detected_template(),
        create_customer_escalation_template()
    ]
