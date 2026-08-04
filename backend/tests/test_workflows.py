"""Comprehensive unit tests for the Phase 7.4 Workflow Engine and integrations."""

import os
import json
import asyncio
import unittest
import tempfile
import shutil
from datetime import datetime, timezone, timedelta
from typing import Any
from unittest.mock import MagicMock, patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.user import User
from app.models.meeting import Meeting
from app.models.transcript import Transcript
from app.models.action_item import ActionItem
from app.memory.memory_models import Memory
from app.database.base import Base

from app.agent.events.event_bus import EventBus
from app.agent.events.event_models import TranscriptSavedEvent, MeetingStoppedEvent
from app.agent.events.event_types import EventType
from app.copilot.copilot_models import LiveMeetingState, CopilotInsight
from app.copilot.copilot_service import get_live_copilot_service
from app.workflows.workflow_models import Workflow, WorkflowStep
from app.workflows.workflow_engine import get_workflow_engine
from app.workflows.workflow_metrics import get_workflow_metrics
from app.workflows.workflow_state_machine import WorkflowStateMachine
from app.workflows.approval_service import get_approval_service
from app.agent.registry import ToolRegistry

test_engine = create_engine("sqlite:///:memory:")
TestingSessionLocal = sessionmaker(bind=test_engine, autoflush=False, expire_on_commit=False)
Base.metadata.create_all(bind=test_engine)


class MockEmbeddingClient:
    def embed_texts(self, texts):
        return [[0.5] * 1536 for t in texts]


class MockLLMProvider:
    def generate(self, prompt: str) -> Any:
        class Res:
            content = "0.85"
        return Res()


class WorkflowSystemTests(unittest.TestCase):
    def setUp(self) -> None:
        # Create temp dir for state isolation
        self.test_dir = tempfile.mkdtemp()
        self.state_file_path = os.path.join(self.test_dir, "test_workflows_state.json")
        
        # Override the STATE_FILE path dynamically
        import app.workflows.workflow_engine
        self._orig_state_file = app.workflows.workflow_engine.STATE_FILE
        app.workflows.workflow_engine.STATE_FILE = self.state_file_path

        # Clear test memories
        with TestingSessionLocal() as session:
            session.query(Memory).delete()
            session.commit()

        # Set up memory manager with test DB session factory
        from app.memory.memory_manager import MemoryManager
        self.mgr = MemoryManager(use_mock_store=False, session_factory=TestingSessionLocal)
        import app.memory.memory_manager
        app.memory.memory_manager._memory_manager = self.mgr

        # Global mocks for Ollama and embeddings
        self.mock_emb = MockEmbeddingClient()
        self.mock_llm = MockLLMProvider()
        self.patchers = [
            patch("app.memory.embedding_service.get_embedding_service", return_value=self.mock_emb),
            patch("app.copilot.decision_detector.get_llm_provider", return_value=self.mock_llm),
            patch("app.copilot.risk_detector.get_llm_provider", return_value=self.mock_llm),
            patch("app.copilot.deadline_detector.get_llm_provider", return_value=self.mock_llm),
            patch("app.memory.memory_indexer.get_llm_provider", return_value=self.mock_llm),
            patch("app.ai.providers.get_llm_provider", return_value=self.mock_llm),
        ]
        for p in self.patchers:
            p.start()

        # Retrieve and clear the workflow engine states & metrics
        self.engine = get_workflow_engine()
        self.engine._workflows.clear()
        
        # Reset Metrics
        metrics = get_workflow_metrics()
        metrics.workflow_count = 0
        metrics.completed_count = 0
        metrics.failed_count = 0
        metrics.retry_count = 0
        metrics.compensations_run = 0
        metrics.approvals_requested = 0
        metrics.approvals_approved = 0
        metrics.approvals_rejected = 0
        metrics.total_duration_ms = 0.0
        metrics.duration_runs_count = 0

    def tearDown(self) -> None:
        for p in self.patchers:
            p.stop()
        
        # Restore state path and remove temp directory
        import app.workflows.workflow_engine
        app.workflows.workflow_engine.STATE_FILE = self._orig_state_file
        shutil.rmtree(self.test_dir)

        # Clear global memory singleton
        import app.memory.memory_manager
        app.memory.memory_manager._memory_manager = None

    def test_workflow_state_transitions(self) -> None:
        workflow = Workflow(name="Test State Machine", steps=[])
        
        # Test valid transitions
        WorkflowStateMachine.transition(workflow, "VALIDATING")
        self.assertEqual(workflow.status, "VALIDATING")

        WorkflowStateMachine.transition(workflow, "VALIDATED")
        self.assertEqual(workflow.status, "VALIDATED")

        WorkflowStateMachine.transition(workflow, "RUNNING")
        self.assertEqual(workflow.status, "RUNNING")

        WorkflowStateMachine.transition(workflow, "COMPLETED")
        self.assertEqual(workflow.status, "COMPLETED")

    def test_workflow_validation_cycles(self) -> None:
        from app.workflows.workflow_validator import WorkflowValidator
        validator = WorkflowValidator()

        # Build cycle: step A depends on B, step B depends on A
        s1 = WorkflowStep(name="Step A", tool="summary")
        s2 = WorkflowStep(name="Step B", tool="summary", depends_on=[s1.step_id])
        s1.depends_on = [s2.step_id]

        wf = Workflow(name="Cycle Test", steps=[s1, s2])
        is_valid = validator.validate(wf)
        self.assertFalse(is_valid)
        self.assertEqual(wf.status, "FAILED")

    def test_approval_service_extended_actions(self) -> None:
        app_service = get_approval_service()
        app_service._approvals.clear()
        
        # Request approval
        app_id = app_service.request_step_approval(
            workflow_id="wf-1",
            step_id="step-1",
            tool="gmail",
            parameters={"to": "user@test.com"},
            reason="Verify email release"
        )
        
        approval = app_service.get_approval(app_id)
        self.assertIsNotNone(approval)
        self.assertEqual(approval.status, "pending")

        # Modify parameters
        app_service.modify_parameters(app_id, {"to": "admin@test.com"})
        self.assertEqual(approval.status, "modified")

        # Postpone
        future_time = datetime.now(timezone.utc) + timedelta(hours=1)
        app_service.postpone(app_id, future_time)
        self.assertEqual(approval.status, "postponed")
        self.assertEqual(approval.postpone_until, future_time)

        # Delegate
        app_service.delegate(app_id, "Manager")
        self.assertEqual(approval.status, "delegated")
        self.assertEqual(approval.delegate_to, "Manager")

        # Approve
        app_service.approve(app_id, user_id=9)
        self.assertEqual(approval.status, "approved")

    def test_workflow_executor_compensations(self) -> None:
        # Step 1: Successful step with compensating action
        s1 = WorkflowStep(
            name="Create Draft", 
            tool="gmail", 
            parameters={"op": "draft"},
            compensating_action={"tool": "gmail", "parameters": {"op": "delete_draft"}}
        )
        # Step 2: Fails, triggering compensation
        s2 = WorkflowStep(
            name="Send Invitation",
            tool="gmail",
            parameters={"op": "send"},
            depends_on=[s1.step_id],
            max_retries=1
        )
        
        wf = Workflow(name="Compensations Test", steps=[s1, s2])
        
        # Mock executor tool invocations
        # s1 succeeds, s2 fails
        async def mock_invoke(step: WorkflowStep) -> bool:
            if step.name == "Create Draft":
                step.result = "Draft created"
                return True
            return False

        async def mock_compensate(tool: str, params: dict) -> bool:
            return True

        self.engine.executor._invoke_tool = mock_invoke
        self.engine.executor._invoke_compensating_action = mock_compensate
        
        # Run execution
        success = asyncio.run(self.engine.executor.execute(wf))
        
        self.assertFalse(success)
        self.assertEqual(wf.status, "FAILED")
        
        # Verify s1 was compensated
        self.assertEqual(s1.status, "COMPLETED")
        self.assertEqual(s2.status, "FAILED")
        
        # Check audit trail has compensation log
        trail_events = [event["event"] for event in s1.audit_trail]
        self.assertIn("compensation_executed", trail_events)

    def test_supervisor_agent_tool_integration(self) -> None:
        # Registry has WorkflowTool loaded from initializer hook automatically
        reg = ToolRegistry()
        self.assertIn("workflow", reg.list_tools())
        
        # Trigger create action via registry tool
        ctx = MagicMock()
        res = reg.execute_tool("workflow", ctx, {
            "action": "create",
            "template_id": "meeting_stopped",
            "payload": {"meeting_id": 42}
        })
        
        self.assertEqual(res["status"], "success")
        wf_id = res["workflow_id"]
        
        # Trigger list action
        res_list = reg.execute_tool("workflow", ctx, {"action": "list"})
        active_ids = [w["workflow_id"] for w in res_list["active_workflows"]]
        self.assertIn(wf_id, active_ids)

    def test_copilot_insights_workflow_generation(self) -> None:
        # Start meeting
        copilot_service = get_live_copilot_service()
        copilot_service.handle_meeting_started(meeting_id=100, user_id=1)
        
        # We hook handle_transcript_saved to generate draft workflows.
        # Generating a 'risk' insight should automatically trigger the Customer Escalation workflow!
        copilot_service.handle_transcript_saved(meeting_id=100, payload={
            "text": "The server room is blocked by water leaks. This is a huge risk.",
            "speaker_name": "Bob",
            "start_seconds": 0.0,
            "end_seconds": 10.0
        })
        
        # Verify a Customer Escalation workflow was created
        escalation_wfs = [w for w in self.engine._workflows.values() if w.name == "Customer Escalation Workflow"]
        self.assertTrue(len(escalation_wfs) >= 1)
        self.assertEqual(escalation_wfs[0].trigger_event, "insight_risk")


if __name__ == "__main__":
    unittest.main()
