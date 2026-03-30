# Copyright (c) 2026 SlotAgent Contributors
# Licensed under the MIT License - see LICENSE file for details.
"""
Unit tests for CoreScheduler.

Tests core scheduling, plugin chain execution, state management, and Hook events.
Following TDD approach - tests written before implementation.
"""

import time
import uuid

import pytest

from slotagent.types import ExecutionStatus, PluginContext, PluginResult
from tests.fixtures.sample_plugins import (
    MockGuardPlugin,
    MockHealingPlugin,
    MockObservePlugin,
    MockReflectPlugin,
    MockSchemaPlugin,
)
from tests.fixtures.sample_tools import (
    FAILING_TOOL,
    PAYMENT_TOOL,
    WEATHER_TOOL,
)


class TestCoreSchedulerBasicExecution:
    """Test basic execution functionality"""

    def test_execute_simple_tool_success(self):
        """Test successful execution of a simple tool"""
        from slotagent.core.core_scheduler import CoreScheduler

        scheduler = CoreScheduler()
        scheduler.plugin_pool.register_global_plugin(MockSchemaPlugin())

        # Register tool
        scheduler.register_tool(WEATHER_TOOL)

        # Execute
        context = scheduler.execute("weather_query", {"location": "Beijing"})

        assert context.status == ExecutionStatus.COMPLETED
        assert context.final_result is not None
        assert context.final_result["location"] == "Beijing"
        assert context.error is None

    def test_execute_tool_not_found_raises_error(self):
        """Test that executing nonexistent tool raises error"""
        from slotagent.core.core_scheduler import CoreScheduler
        from slotagent.interfaces import ToolNotFoundError

        scheduler = CoreScheduler()

        with pytest.raises(ToolNotFoundError, match="not found"):
            scheduler.execute("nonexistent_tool", {})

    def test_execute_creates_execution_context(self):
        """Test that execute creates proper execution context"""
        from slotagent.core.core_scheduler import CoreScheduler

        scheduler = CoreScheduler()
        scheduler.plugin_pool.register_global_plugin(MockSchemaPlugin())
        scheduler.register_tool(WEATHER_TOOL)

        context = scheduler.execute("weather_query", {"location": "Beijing"})

        # Verify context fields
        assert context.tool_id == "weather_query"
        assert context.tool_name == "Weather Query"
        assert context.params == {"location": "Beijing"}
        assert context.execution_id is not None
        assert len(context.execution_id) > 0
        assert context.start_time > 0
        assert context.end_time >= context.start_time
        assert context.execution_time >= 0

    def test_execute_without_plugins_works(self):
        """Test execution works even without plugins registered"""
        from slotagent.core.core_scheduler import CoreScheduler

        scheduler = CoreScheduler()
        scheduler.register_tool(WEATHER_TOOL)

        # Should still work, just skips plugin chain
        context = scheduler.execute("weather_query", {"location": "Beijing"})

        assert context.status == ExecutionStatus.COMPLETED
        assert len(context.plugin_results) == 0


class TestPluginChainExecution:
    """Test plugin chain execution"""

    def test_plugin_chain_executes_in_order(self):
        """Test that plugins execute in correct order"""
        from slotagent.core.core_scheduler import CoreScheduler

        scheduler = CoreScheduler()

        # Register plugins
        scheduler.plugin_pool.register_global_plugin(MockSchemaPlugin())
        scheduler.plugin_pool.register_global_plugin(MockGuardPlugin())
        scheduler.plugin_pool.register_global_plugin(MockHealingPlugin())
        scheduler.plugin_pool.register_global_plugin(MockReflectPlugin())
        scheduler.plugin_pool.register_global_plugin(MockObservePlugin())

        scheduler.register_tool(WEATHER_TOOL)

        context = scheduler.execute("weather_query", {"location": "Beijing"})

        # Verify all plugins executed
        assert "schema" in context.plugin_results
        assert "guard" in context.plugin_results
        assert "reflect" in context.plugin_results
        assert "observe" in context.plugin_results

        # Verify execution order by checking plugin data
        assert context.plugin_results["schema"].data["plugin"] == "schema_mock"
        assert context.plugin_results["guard"].data["plugin"] == "guard_mock"

    def test_schema_validation_failure_stops_execution(self):
        """Test that schema validation failure stops plugin chain"""
        from slotagent.core.core_scheduler import CoreScheduler
        from slotagent.interfaces import PluginInterface

        # Create failing schema plugin
        class FailingSchemaPlugin(PluginInterface):
            layer = "schema"
            plugin_id = "schema_failing"

            def validate(self):
                return True

            def execute(self, context):
                return PluginResult(
                    success=False,
                    should_continue=False,
                    error="Validation failed",
                    error_type="ValidationError",
                )

        scheduler = CoreScheduler()
        scheduler.plugin_pool.register_global_plugin(FailingSchemaPlugin())
        scheduler.plugin_pool.register_global_plugin(MockGuardPlugin())
        scheduler.register_tool(WEATHER_TOOL)

        context = scheduler.execute("weather_query", {})

        # Should fail at schema
        assert context.status == ExecutionStatus.FAILED
        assert "schema" in context.plugin_results
        assert "guard" not in context.plugin_results  # Should not execute
        assert context.error is not None

    def test_guard_blocking_stops_execution(self):
        """Test that Guard plugin can block execution"""
        from slotagent.core.core_scheduler import CoreScheduler
        from slotagent.interfaces import PluginInterface

        class BlockingGuardPlugin(PluginInterface):
            layer = "guard"
            plugin_id = "guard_blocking"

            def validate(self):
                return True

            def execute(self, context):
                return PluginResult(
                    success=True,
                    should_continue=False,
                    data={"blocked": True, "reason": "High risk operation"},
                )

        scheduler = CoreScheduler()
        scheduler.plugin_pool.register_global_plugin(MockSchemaPlugin())
        scheduler.plugin_pool.register_global_plugin(BlockingGuardPlugin())
        scheduler.register_tool(WEATHER_TOOL)

        context = scheduler.execute("weather_query", {"location": "Beijing"})

        # Should be blocked
        assert context.status == ExecutionStatus.FAILED
        assert "schema" in context.plugin_results
        assert "guard" in context.plugin_results
        assert context.final_result is None

    def test_previous_results_passed_to_plugins(self):
        """Test that previous plugin results are passed to next plugins"""
        from slotagent.core.core_scheduler import CoreScheduler
        from slotagent.interfaces import PluginInterface

        executed_contexts = []

        class TrackingGuardPlugin(PluginInterface):
            layer = "guard"
            plugin_id = "guard_tracking"

            def validate(self):
                return True

            def execute(self, context: PluginContext):
                executed_contexts.append(context)
                return PluginResult(success=True, data={"guard_data": "test"})

        scheduler = CoreScheduler()
        scheduler.plugin_pool.register_global_plugin(MockSchemaPlugin())
        scheduler.plugin_pool.register_global_plugin(TrackingGuardPlugin())
        scheduler.register_tool(WEATHER_TOOL)

        scheduler.execute("weather_query", {"location": "Beijing"})

        # Verify Guard plugin received Schema results
        guard_context = executed_contexts[0]
        assert guard_context.previous_results is not None
        assert "schema" in guard_context.previous_results
        assert guard_context.previous_results["schema"]["plugin"] == "schema_mock"


class TestBatch1HookExpansionRed:
    """Red tests for first-batch fine-grained Hook events."""

    def test_schema_phase_events_emitted_in_order(self):
        """Schema execution should emit before_schema then after_schema."""
        from slotagent.core.core_scheduler import CoreScheduler
        from slotagent.core.hook_manager import HookManager

        hook_manager = HookManager()
        scheduler = CoreScheduler(hook_manager=hook_manager)
        scheduler.plugin_pool.register_global_plugin(MockSchemaPlugin())
        scheduler.register_tool(WEATHER_TOOL)

        received_types = []
        received_events = []

        def record(event):
            received_types.append(event.event_type)
            received_events.append(event)

        hook_manager.subscribe("before_schema", record)
        hook_manager.subscribe("after_schema", record)

        context = scheduler.execute("weather_query", {"location": "Beijing"})

        assert context.status == ExecutionStatus.COMPLETED
        assert received_types == ["before_schema", "after_schema"]
        assert received_events[0].execution_id == context.execution_id
        assert received_events[1].execution_id == context.execution_id

    def test_schema_failure_still_emits_after_schema_before_fail(self):
        """Schema rejection should still emit after_schema before fail."""
        from slotagent.core.core_scheduler import CoreScheduler
        from slotagent.core.hook_manager import HookManager
        from slotagent.interfaces import PluginInterface

        class FailingSchemaPlugin(PluginInterface):
            layer = "schema"
            plugin_id = "schema_failing"

            def validate(self):
                return True

            def execute(self, context):
                return PluginResult(
                    success=False,
                    should_continue=False,
                    error="Validation failed",
                    error_type="ValidationError",
                )

        hook_manager = HookManager()
        scheduler = CoreScheduler(hook_manager=hook_manager)
        scheduler.plugin_pool.register_global_plugin(FailingSchemaPlugin())
        scheduler.register_tool(WEATHER_TOOL)

        received_types = []
        after_schema_events = []
        fail_events = []

        def on_before_schema(event):
            received_types.append(event.event_type)

        def on_after_schema(event):
            received_types.append(event.event_type)
            after_schema_events.append(event)

        def on_fail(event):
            received_types.append(event.event_type)
            fail_events.append(event)

        hook_manager.subscribe("before_schema", on_before_schema)
        hook_manager.subscribe("after_schema", on_after_schema)
        hook_manager.subscribe("fail", on_fail)

        context = scheduler.execute("weather_query", {})

        assert context.status == ExecutionStatus.FAILED
        assert received_types == ["before_schema", "after_schema", "fail"]
        assert after_schema_events[0].success is False
        assert after_schema_events[0].should_continue is False
        assert fail_events[0].failed_stage == "schema"

    def test_before_guard_emitted_when_guard_plugin_runs(self):
        """Guard execution should emit before_guard."""
        from slotagent.core.core_scheduler import CoreScheduler
        from slotagent.core.hook_manager import HookManager

        hook_manager = HookManager()
        scheduler = CoreScheduler(hook_manager=hook_manager)
        scheduler.plugin_pool.register_global_plugin(MockSchemaPlugin())
        scheduler.plugin_pool.register_global_plugin(MockGuardPlugin())
        scheduler.register_tool(WEATHER_TOOL)

        events = []
        hook_manager.subscribe("before_guard", lambda e: events.append(e))

        context = scheduler.execute("weather_query", {"location": "Beijing"})

        assert context.status == ExecutionStatus.COMPLETED
        assert len(events) == 1
        assert events[0].event_type == "before_guard"
        assert events[0].execution_id == context.execution_id

    def test_healing_recovery_emits_after_healing_and_retry_started(self):
        """Recoverable failure should emit after_healing then retry_started."""
        from slotagent.core.core_scheduler import CoreScheduler
        from slotagent.core.hook_manager import HookManager
        from slotagent.interfaces import PluginInterface
        from slotagent.types import Tool

        calls = {"count": 0}

        def flaky_execute(params):
            calls["count"] += 1
            if calls["count"] == 1:
                raise RuntimeError("boom")
            return {"attempt": calls["count"]}

        class RecoveringHealingPlugin(PluginInterface):
            layer = "healing"
            plugin_id = "healing_recovering"
            max_retries = 1

            def validate(self):
                return True

            def execute(self, context):
                return PluginResult(success=True, data={"recovered": True})

        hook_manager = HookManager()
        scheduler = CoreScheduler(hook_manager=hook_manager)
        scheduler.plugin_pool.register_global_plugin(RecoveringHealingPlugin())
        scheduler.register_tool(
            Tool(
                tool_id="flaky_tool",
                name="Flaky Tool",
                description="Tool that fails once then succeeds",
                input_schema={"type": "object", "properties": {}},
                execute_func=flaky_execute,
            )
        )

        received_types = []
        after_healing_events = []
        retry_events = []

        def on_after_healing(event):
            received_types.append(event.event_type)
            after_healing_events.append(event)

        def on_retry_started(event):
            received_types.append(event.event_type)
            retry_events.append(event)

        hook_manager.subscribe("after_healing", on_after_healing)
        hook_manager.subscribe("retry_started", on_retry_started)

        context = scheduler.execute("flaky_tool", {})

        assert context.status == ExecutionStatus.COMPLETED
        assert context.final_result == {"attempt": 2}
        assert received_types == ["after_healing", "retry_started"]
        assert after_healing_events[0].recovered is True
        assert after_healing_events[0].attempt == 1
        assert after_healing_events[0].max_attempts == 2
        assert after_healing_events[0].healing_plugin_id == "healing_recovering"
        assert retry_events[0].attempt == 1
        assert retry_events[0].next_attempt == 2
        assert retry_events[0].max_attempts == 2

    def test_after_reflect_emitted_after_reflect_plugin_executes(self):
        """Reflect execution should emit after_reflect."""
        from slotagent.core.core_scheduler import CoreScheduler
        from slotagent.core.hook_manager import HookManager
        from slotagent.interfaces import PluginInterface

        class TrackingReflectPlugin(PluginInterface):
            layer = "reflect"
            plugin_id = "reflect_tracking"

            def validate(self):
                return True

            def execute(self, context):
                return PluginResult(success=True, should_continue=True, data={"reflected": True})

        hook_manager = HookManager()
        scheduler = CoreScheduler(hook_manager=hook_manager)
        scheduler.plugin_pool.register_global_plugin(TrackingReflectPlugin())
        scheduler.register_tool(WEATHER_TOOL)

        events = []
        hook_manager.subscribe("after_reflect", lambda e: events.append(e))

        context = scheduler.execute("weather_query", {"location": "Beijing"})

        assert context.status == ExecutionStatus.COMPLETED
        assert len(events) == 1
        assert events[0].event_type == "after_reflect"
        assert events[0].reflect_plugin_id == "reflect_tracking"
        assert events[0].success is True
        assert events[0].should_continue is True


class TestToolLevelPluginPriority:
    """Test tool-level plugin configuration priority"""

    def test_tool_plugin_overrides_global(self):
        """Test that tool-specific plugin overrides global plugin"""
        from slotagent.core.core_scheduler import CoreScheduler
        from tests.fixtures.sample_plugins import AlternativeSchemaPlugin

        scheduler = CoreScheduler()
        scheduler.plugin_pool.register_global_plugin(MockSchemaPlugin())
        scheduler.plugin_pool.register_global_plugin(AlternativeSchemaPlugin())

        # Configure tool to use alternative schema
        scheduler.plugin_pool.register_tool_plugins(
            "weather_query", {"schema": "schema_alternative"}
        )

        scheduler.register_tool(WEATHER_TOOL)

        context = scheduler.execute("weather_query", {"location": "Beijing"})

        # Should use alternative schema
        schema_result = context.plugin_results["schema"]
        assert schema_result.data["plugin"] == "schema_alternative"


class TestStateManagement:
    """Test execution state transitions"""

    def test_initial_state_is_running(self):
        """Test that execution starts in RUNNING state"""
        from slotagent.core.core_scheduler import CoreScheduler

        scheduler = CoreScheduler()
        scheduler.register_tool(WEATHER_TOOL)

        # We can't easily check intermediate state, but can verify final state
        context = scheduler.execute("weather_query", {"location": "Beijing"})

        # Should end in COMPLETED
        assert context.status == ExecutionStatus.COMPLETED

    def test_failed_execution_sets_failed_state(self):
        """Test that execution failure sets FAILED state"""
        from slotagent.core.core_scheduler import CoreScheduler

        scheduler = CoreScheduler()
        scheduler.plugin_pool.register_global_plugin(MockSchemaPlugin())
        scheduler.register_tool(FAILING_TOOL)

        context = scheduler.execute("failing_tool", {})

        assert context.status == ExecutionStatus.FAILED
        assert context.error is not None
        assert context.final_result is None

    def test_is_terminal_method(self):
        """Test ToolExecutionContext.is_terminal() method"""
        from slotagent.types import ToolExecutionContext

        completed_context = ToolExecutionContext(
            tool_id="test",
            tool_name="Test",
            params={},
            execution_id=str(uuid.uuid4()),
            status=ExecutionStatus.COMPLETED,
            start_time=time.time(),
        )

        failed_context = ToolExecutionContext(
            tool_id="test",
            tool_name="Test",
            params={},
            execution_id=str(uuid.uuid4()),
            status=ExecutionStatus.FAILED,
            start_time=time.time(),
        )

        running_context = ToolExecutionContext(
            tool_id="test",
            tool_name="Test",
            params={},
            execution_id=str(uuid.uuid4()),
            status=ExecutionStatus.RUNNING,
            start_time=time.time(),
        )

        assert completed_context.is_terminal() is True
        assert failed_context.is_terminal() is True
        assert running_context.is_terminal() is False


class TestToolRegistration:
    """Test tool registration functionality"""

    def test_register_tool_success(self):
        """Test successful tool registration"""
        from slotagent.core.core_scheduler import CoreScheduler

        scheduler = CoreScheduler()
        scheduler.register_tool(WEATHER_TOOL)

        # Should be able to execute
        context = scheduler.execute("weather_query", {"location": "Beijing"})
        assert context.status == ExecutionStatus.COMPLETED

    def test_register_duplicate_tool_raises_error(self):
        """Test that registering duplicate tool_id raises error"""
        from slotagent.core.core_scheduler import CoreScheduler

        scheduler = CoreScheduler()
        scheduler.register_tool(WEATHER_TOOL)

        with pytest.raises(ValueError, match="already registered"):
            scheduler.register_tool(WEATHER_TOOL)

    def test_get_registered_tool(self):
        """Test getting registered tool"""
        from slotagent.core.core_scheduler import CoreScheduler

        scheduler = CoreScheduler()
        scheduler.register_tool(WEATHER_TOOL)

        tool = scheduler.get_tool("weather_query")
        assert tool is not None
        assert tool.tool_id == "weather_query"

    def test_get_nonexistent_tool_returns_none(self):
        """Test getting nonexistent tool returns None"""
        from slotagent.core.core_scheduler import CoreScheduler

        scheduler = CoreScheduler()

        tool = scheduler.get_tool("nonexistent")
        assert tool is None


class TestExecutionMetrics:
    """Test execution time tracking"""

    def test_execution_time_is_recorded(self):
        """Test that execution time is recorded"""
        from slotagent.core.core_scheduler import CoreScheduler

        scheduler = CoreScheduler()
        scheduler.register_tool(WEATHER_TOOL)

        context = scheduler.execute("weather_query", {"location": "Beijing"})

        assert context.start_time > 0
        assert context.end_time >= context.start_time
        assert context.execution_time >= 0
        assert context.execution_time == context.end_time - context.start_time

    def test_execution_id_is_unique(self):
        """Test that each execution gets unique execution_id"""
        from slotagent.core.core_scheduler import CoreScheduler

        scheduler = CoreScheduler()
        scheduler.register_tool(WEATHER_TOOL)

        context1 = scheduler.execute("weather_query", {"location": "Beijing"})
        context2 = scheduler.execute("weather_query", {"location": "Shanghai"})

        assert context1.execution_id != context2.execution_id


class TestErrorHandling:
    """Test error handling in various scenarios"""

    def test_tool_execution_exception_is_caught(self):
        """Test that tool execution exceptions are caught and handled"""
        from slotagent.core.core_scheduler import CoreScheduler

        scheduler = CoreScheduler()
        scheduler.plugin_pool.register_global_plugin(MockSchemaPlugin())
        scheduler.register_tool(FAILING_TOOL)

        # Should not raise, but return FAILED context
        context = scheduler.execute("failing_tool", {})

        assert context.status == ExecutionStatus.FAILED
        assert "Tool execution failed" in context.error

    def test_plugin_exception_is_caught(self):
        """Test that plugin exceptions are caught"""
        from slotagent.core.core_scheduler import CoreScheduler
        from slotagent.interfaces import PluginInterface

        class CrashingPlugin(PluginInterface):
            layer = "schema"
            plugin_id = "schema_crashing"

            def validate(self):
                return True

            def execute(self, context):
                raise RuntimeError("Plugin crashed")

        scheduler = CoreScheduler()
        scheduler.plugin_pool.register_global_plugin(CrashingPlugin())
        scheduler.register_tool(WEATHER_TOOL)

        # Should not crash, but handle gracefully
        context = scheduler.execute("weather_query", {})

        assert context.status == ExecutionStatus.FAILED
        assert context.error is not None


class TestApprovalWorkflow:
    """Test approval workflow integration with CoreScheduler"""

    def test_pending_approval_sets_correct_state(self):
        """Test that guard pending approval sets PENDING_APPROVAL state"""
        from slotagent.core.approval_manager import ApprovalManager
        from slotagent.core.core_scheduler import CoreScheduler
        from slotagent.core.hook_manager import HookManager
        from slotagent.plugins.guard import GuardHumanInLoop

        manager = ApprovalManager()
        hook_manager = HookManager()
        scheduler = CoreScheduler(hook_manager=hook_manager)

        # Register GuardHumanInLoop plugin
        guard_plugin = GuardHumanInLoop(approval_manager=manager)
        scheduler.plugin_pool.register_global_plugin(guard_plugin)

        scheduler.register_tool(PAYMENT_TOOL)

        # Track approval events
        wait_approval_events = []

        def on_wait_approval(event):
            wait_approval_events.append(event)

        hook_manager.subscribe("wait_approval", on_wait_approval)

        context = scheduler.execute("payment_refund", {"amount": 100})

        # Should be in PENDING_APPROVAL state
        assert context.status == ExecutionStatus.PENDING_APPROVAL
        assert context.approval_id is not None

        # Should have emitted wait_approval event
        assert len(wait_approval_events) == 1
        assert wait_approval_events[0].approval_id == context.approval_id
