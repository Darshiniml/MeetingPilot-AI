import pytest
from unittest.mock import MagicMock, patch
from app.background import BackgroundService
from app.autonomy import AutonomyEngine, AutonomyGoal, AutonomyDecision
from app.agent.events.event_types import EventType

@pytest.fixture
def clean_autonomy_engine():
    srv = BackgroundService.get_instance()
    # Reset singleton mapping if already created to ensure clean tests runs
    AutonomyEngine._instance = None
    engine = AutonomyEngine.get_instance(srv.event_bus)
    engine.loop.approval_engine._queue.clear()
    engine.metrics.__init__()
    return engine

def test_goal_prioritization(clean_autonomy_engine):
    engine = clean_autonomy_engine
    
    # 1. Base context with no deadlines/risks
    context = {"copilot_insights": []}
    goals = engine.loop.goal_manager.get_goals(context)
    
    # Monitor deadlines should be MEDIUM priority by default
    deadline_goal = next(g for g in goals if g.name == "Monitor deadlines")
    assert deadline_goal.priority == "MEDIUM"
    
    # 2. Elevate deadline priority context
    context = {"copilot_insights": [{"insight_type": "deadline"}]}
    goals = engine.loop.goal_manager.get_goals(context)
    deadline_goal = next(g for g in goals if g.name == "Monitor deadlines")
    assert deadline_goal.priority == "HIGH"
    
    # 3. Elevate risks to HIGHEST priority
    context = {"copilot_insights": [{"insight_type": "risk"}]}
    goals = engine.loop.goal_manager.get_goals(context)
    risk_goal = next(g for g in goals if g.name == "Resolve unanswered questions")
    assert risk_goal.priority == "HIGHEST"

def test_policy_engine_tier_filtering():
    from app.autonomy.policy_engine import PolicyEngine
    
    # 1. Observation Mode - all actions blocked
    pe = PolicyEngine(mode="Observation")
    assert pe.evaluate_policy("generate_reminder") == "BLOCKED"
    assert pe.evaluate_policy("calendar_creation") == "BLOCKED"
    
    # 2. Recommendation Mode - recommend actions
    pe = PolicyEngine(mode="Recommendation")
    assert pe.evaluate_policy("generate_reminder") == "RECOMMEND"
    assert pe.evaluate_policy("calendar_creation") == "RECOMMEND"
    
    # 3. Semi-Autonomous Mode - Safe auto-executes, unsafe queues for approval
    pe = PolicyEngine(mode="Semi-Autonomous")
    assert pe.evaluate_policy("generate_reminder") == "AUTO_EXECUTE"
    assert pe.evaluate_policy("calendar_creation") == "QUEUE_APPROVAL"
    
    # 4. Fully Autonomous Mode - auto-executes all
    pe = PolicyEngine(mode="Fully Autonomous")
    assert pe.evaluate_policy("generate_reminder") == "AUTO_EXECUTE"
    assert pe.evaluate_policy("calendar_creation") == "AUTO_EXECUTE"

def test_explainable_decisions_generation(clean_autonomy_engine):
    engine = clean_autonomy_engine
    
    context = {"copilot_insights": [{"insight_type": "deadline"}]}
    goals = engine.loop.goal_manager.get_goals(context)
    
    decisions = engine.loop.decision_engine.evaluate_decisions(context, goals)
    
    # Verify decision structure and explainability values
    deadline_dec = next(d for d in decisions if d.goal == "Monitor deadlines")
    assert deadline_dec.confidence > 0.8
    assert deadline_dec.trigger == "Copilot deadline insight detected."
    assert deadline_dec.reasoning != ""
    assert deadline_dec.selected_action["action_name"] == "generate_reminder"
    assert deadline_dec.expected_outcome != ""

def test_safe_unsafe_action_routing(clean_autonomy_engine):
    engine = clean_autonomy_engine
    
    # Set policy to Semi-Autonomous
    engine.loop.set_policy_mode("Semi-Autonomous")
    
    # Track EventBus triggers
    received_events = []
    def on_event(event):
        received_events.append(event.event_type)
        
    engine.event_bus.subscribe(EventType.ACTION_EXECUTED, on_event)
    engine.event_bus.subscribe(EventType.APPROVAL_REQUIRED, on_event)
    
    # We trigger a single reasoning cycle. It generates:
    # 1. Track commitments -> create_workflow (safe action -> AUTO_EXECUTE)
    # 2. Maintain memory -> refresh_embeddings (safe action -> AUTO_EXECUTE)
    # 3. Assist scheduling -> calendar_creation (unsafe action -> QUEUE_APPROVAL)
    
    context = {
        "copilot_insights": [{"insight_type": "commitment"}],
        "provider_status": {"calendar": "healthy", "email": "healthy", "notification": "healthy"}
    }
    
    # Override goals to active list
    goals = [
        AutonomyGoal(name="Track commitments", description="Extract and structure meeting action items.", status="ACTIVE"),
        AutonomyGoal(name="Assist scheduling", description="Verify availability and suggest calendar slots.", status="ACTIVE")
    ]

    with patch("app.autonomy.execution_engine.TaskPlanner.plan_and_delegate") as mock_delegate, \
         patch("app.autonomy.context_builder.ContextBuilder.build_context") as mock_context_builder, \
         patch("app.autonomy.goal_manager.GoalManager.get_goals") as mock_get_goals:
        mock_delegate.return_value = True
        mock_context_builder.return_value = context
        mock_get_goals.return_value = goals
        
        # Run one reasoning cycle
        engine.loop.run_single_reasoning_cycle()
        
        # Verify event dispatches
        assert EventType.ACTION_EXECUTED in received_events
        assert EventType.APPROVAL_REQUIRED in received_events
        
        # Verify unsafe action is queued in approval engine
        pending = engine.loop.approval_engine.get_pending_approvals()
        assert len(pending) == 1
        assert pending[0].action_name == "calendar_creation"
        
        # Resolve approval manually
        approval_id = pending[0].approval_id
        engine.loop.trigger_approval_resolution(approval_id, approve=True)
        
        # Verify status is EXECUTED
        history = engine.loop.approval_engine.get_history()
        exec_item = next(h for h in history if h.approval_id == approval_id)
        assert exec_item.status == "EXECUTED"
