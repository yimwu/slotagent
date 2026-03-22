# Copyright (c) 2026 SlotAgent Contributors
# Licensed under the MIT License - see LICENSE file for details.
"""
Integration tests for complete SlotAgent workflow.

Tests the full execution pipeline: tool registration, plugin chain execution,
hook events, and approval workflows with all components working together.
"""

import threading
import time

import pytest

from slotagent.core.approval_manager import ApprovalManager
from slotagent.core.core_scheduler import CoreScheduler
from slotagent.core.hook_manager import HookManager
from slotagent.core.tool_registry import ToolRegistry
from slotagent.plugins.guard import GuardDefault, GuardHumanInLoop
from slotagent.plugins.observe import LogPlugin
from slotagent.plugins.schema import SchemaDefault
from slotagent.types import (
    AfterExecEvent,
    ApprovalStatus,
    BeforeExecEvent,
    ExecutionStatus,
    FailEvent,
    GuardBlockEvent,
    Tool,
    WaitApprovalEvent,
)

# ---------------------------------------------------------------------------
# Fixtures / shared helpers
# ---------------------------------------------------------------------------


def make_tool(tool_id: str, func=None, schema=None):
    """Build a minimal Tool with sensible defaults."""
    if func is None:

        def default_func(params):
            return {"status": "ok", "tool_id": tool_id}

        func = default_func
    if schema is None:
        schema = {"type": "object", "properties": {}}
    return Tool(
        tool_id=tool_id,
        name=tool_id.replace("_", " ").title(),
        description=f"Test tool {tool_id} (at least 10 chars)",
        input_schema=schema,
        execute_func=func,
    )


WEATHER_SCHEMA = {
    "type": "object",
    "properties": {
        "location": {"type": "string"},
        "unit": {"type": "string"},
    },
    "required": ["location"],
}

PAYMENT_SCHEMA = {
    "type": "object",
    "properties": {
        "amount": {"type": "number", "minimum": 0},
        "order_id": {"type": "string"},
    },
    "required": ["amount", "order_id"],
}


# ---------------------------------------------------------------------------
# 1. Basic end-to-end execution
# ---------------------------------------------------------------------------


class TestBasicExecution:
    """End-to-end execution without plugins."""

    def test_simple_tool_executes_successfully(self):
        """Register a tool and execute it; expect COMPLETED status."""
        scheduler = CoreScheduler()
        tool = make_tool("my_tool")
        scheduler.register_tool(tool)

        ctx = scheduler.execute("my_tool", {})

        assert ctx.status == ExecutionStatus.COMPLETED
        assert ctx.final_result == {"status": "ok", "tool_id": "my_tool"}
        assert ctx.error is None

    def test_unknown_tool_raises_error(self):
        """Executing an unregistered tool raises ToolNotFoundError."""
        from slotagent.interfaces import ToolNotFoundError

        scheduler = CoreScheduler()

        with pytest.raises(ToolNotFoundError, match="Tool 'unknown_tool' not found"):
            scheduler.execute("unknown_tool", {})

    def test_multiple_tools_isolated(self):
        """Two tools registered on the same scheduler execute independently."""
        scheduler = CoreScheduler()

        calls = {"a": 0, "b": 0}
        tool_a = make_tool(
            "tool_a", func=lambda p: calls.update({"a": calls["a"] + 1}) or {"called": "a"}
        )
        tool_b = make_tool(
            "tool_b", func=lambda p: calls.update({"b": calls["b"] + 1}) or {"called": "b"}
        )

        scheduler.register_tool(tool_a)
        scheduler.register_tool(tool_b)

        ctx_a = scheduler.execute("tool_a", {})
        ctx_b = scheduler.execute("tool_b", {})

        assert ctx_a.status == ExecutionStatus.COMPLETED
        assert ctx_b.status == ExecutionStatus.COMPLETED
        assert calls["a"] == 1
        assert calls["b"] == 1


# ---------------------------------------------------------------------------
# 2. Plugin chain execution
# ---------------------------------------------------------------------------


class TestPluginChainExecution:
    """Verify the Schema → Guard → Execute → Healing → Reflect chain."""

    def test_full_plugin_chain_completes(self):
        """All 5 plugin layers fire and the tool executes successfully."""
        execution_order = []

        from slotagent.interfaces import PluginInterface
        from slotagent.types import PluginResult

        def make_tracking_plugin(layer_name):
            class TrackingPlugin(PluginInterface):
                layer = layer_name
                plugin_id = f"{layer_name}_tracker"

                def validate(self):
                    return True

                def execute(self, context):
                    execution_order.append(layer_name)
                    return PluginResult(success=True, data={})

            return TrackingPlugin()

        scheduler = CoreScheduler()

        for layer in ("schema", "guard", "healing", "reflect", "observe"):
            plugin = make_tracking_plugin(layer)
            scheduler.plugin_pool.register_global_plugin(plugin)

        tool = make_tool("full_chain_tool")
        scheduler.register_tool(tool)

        ctx = scheduler.execute("full_chain_tool", {})

        assert ctx.status == ExecutionStatus.COMPLETED
        # Verify relative order of schema, guard, observe
        assert execution_order.index("schema") < execution_order.index("guard")
        assert execution_order.index("guard") < execution_order.index("observe")

    def test_schema_validation_blocks_execution(self):
        """Failing schema validation prevents tool execution."""
        executed = {"value": False}

        def track_execute(params):
            executed["value"] = True
            return {"ok": True}

        tool = make_tool(
            "validated_tool",
            func=track_execute,
            schema=WEATHER_SCHEMA,
        )

        scheduler = CoreScheduler()
        scheduler.plugin_pool.register_global_plugin(SchemaDefault(schema=WEATHER_SCHEMA))
        scheduler.register_tool(tool)

        # Missing required "location" param
        ctx = scheduler.execute("validated_tool", {})

        assert ctx.status == ExecutionStatus.FAILED
        assert executed["value"] is False

    def test_guard_blacklist_blocks_execution(self):
        """Guard plugin blocks blacklisted tools."""
        executed = {"value": False}

        def track_execute(params):
            executed["value"] = True
            return {"ok": True}

        tool = make_tool("dangerous_tool", func=track_execute)
        scheduler = CoreScheduler()
        scheduler.plugin_pool.register_global_plugin(GuardDefault(blacklist=["dangerous_tool"]))
        scheduler.register_tool(tool)

        ctx = scheduler.execute("dangerous_tool", {})

        assert ctx.status == ExecutionStatus.FAILED
        assert executed["value"] is False

    def test_tool_level_plugin_overrides_global(self):
        """Per-tool plugin takes precedence over global plugin."""
        call_counts = {"global_schema": 0, "tool_schema": 0}

        from slotagent.interfaces import PluginInterface
        from slotagent.types import PluginResult

        class GlobalSchema(PluginInterface):
            layer = "schema"
            plugin_id = "schema_global"

            def validate(self):
                return True

            def execute(self, context):
                call_counts["global_schema"] += 1
                return PluginResult(success=True, data={})

        class ToolSchema(PluginInterface):
            layer = "schema"
            plugin_id = "schema_tool_specific"

            def validate(self):
                return True

            def execute(self, context):
                call_counts["tool_schema"] += 1
                return PluginResult(success=True, data={})

        scheduler = CoreScheduler()
        scheduler.plugin_pool.register_global_plugin(GlobalSchema())
        scheduler.plugin_pool.register_global_plugin(ToolSchema())

        # Register tool-level override pointing to tool-specific plugin
        tool = Tool(
            tool_id="specific_tool",
            name="Specific Tool",
            description="Tool with specific plugin config (10+ chars)",
            input_schema={"type": "object", "properties": {}},
            execute_func=lambda p: {"ok": True},
            plugins={"schema": "schema_tool_specific"},
        )
        scheduler.register_tool(tool)

        scheduler.execute("specific_tool", {})

        assert call_counts["tool_schema"] == 1
        assert call_counts["global_schema"] == 0


# ---------------------------------------------------------------------------
# 3. Hook event system
# ---------------------------------------------------------------------------


class TestHookEvents:
    """Verify Hook events are emitted at correct points in execution."""

    def test_before_and_after_exec_emitted_on_success(self):
        """Both before_exec and after_exec events fire on success."""
        hook_manager = HookManager()
        scheduler = CoreScheduler(hook_manager=hook_manager)

        before_events = []
        after_events = []

        hook_manager.subscribe("before_exec", lambda e: before_events.append(e))
        hook_manager.subscribe("after_exec", lambda e: after_events.append(e))

        tool = make_tool("hook_tool")
        scheduler.register_tool(tool)

        ctx = scheduler.execute("hook_tool", {})

        assert ctx.status == ExecutionStatus.COMPLETED
        assert len(before_events) == 1
        assert len(after_events) == 1
        assert isinstance(before_events[0], BeforeExecEvent)
        assert isinstance(after_events[0], AfterExecEvent)
        assert before_events[0].execution_id == ctx.execution_id
        assert after_events[0].execution_id == ctx.execution_id

    def test_fail_event_emitted_on_tool_error(self):
        """FailEvent is emitted when tool execution raises an exception."""
        hook_manager = HookManager()
        scheduler = CoreScheduler(hook_manager=hook_manager)

        fail_events = []
        hook_manager.subscribe("fail", lambda e: fail_events.append(e))

        def crashing_func(params):
            raise RuntimeError("Intentional failure")

        tool = make_tool("crash_tool", func=crashing_func)
        scheduler.register_tool(tool)

        ctx = scheduler.execute("crash_tool", {})

        assert ctx.status == ExecutionStatus.FAILED
        assert len(fail_events) >= 1
        assert isinstance(fail_events[-1], FailEvent)

    def test_guard_block_event_emitted_on_blocked_tool(self):
        """GuardBlockEvent fires when Guard blocks execution."""
        hook_manager = HookManager()
        scheduler = CoreScheduler(hook_manager=hook_manager)

        block_events = []
        hook_manager.subscribe("guard_block", lambda e: block_events.append(e))

        scheduler.plugin_pool.register_global_plugin(GuardDefault(blacklist=["blocked_tool"]))
        tool = make_tool("blocked_tool")
        scheduler.register_tool(tool)

        ctx = scheduler.execute("blocked_tool", {})

        assert ctx.status == ExecutionStatus.FAILED
        assert len(block_events) == 1
        assert isinstance(block_events[0], GuardBlockEvent)
        assert block_events[0].tool_id == "blocked_tool"

    def test_wait_approval_event_emitted_on_pending_approval(self):
        """WaitApprovalEvent fires when GuardHumanInLoop triggers approval."""
        approval_manager = ApprovalManager()
        hook_manager = HookManager()
        scheduler = CoreScheduler(hook_manager=hook_manager)

        wait_events = []
        hook_manager.subscribe("wait_approval", lambda e: wait_events.append(e))

        scheduler.plugin_pool.register_global_plugin(
            GuardHumanInLoop(approval_manager=approval_manager)
        )
        tool = make_tool("sensitive_tool")
        scheduler.register_tool(tool)

        ctx = scheduler.execute("sensitive_tool", {})

        assert ctx.status == ExecutionStatus.PENDING_APPROVAL
        assert len(wait_events) == 1
        assert isinstance(wait_events[0], WaitApprovalEvent)
        assert wait_events[0].approval_id == ctx.approval_id

    def test_subscriber_exception_does_not_affect_execution(self):
        """A failing hook subscriber must not break tool execution."""
        hook_manager = HookManager()
        scheduler = CoreScheduler(hook_manager=hook_manager)

        def bad_subscriber(event):
            raise ValueError("Subscriber error")

        hook_manager.subscribe("before_exec", bad_subscriber)

        tool = make_tool("resilient_tool")
        scheduler.register_tool(tool)

        ctx = scheduler.execute("resilient_tool", {})

        # Tool should still complete successfully
        assert ctx.status == ExecutionStatus.COMPLETED


# ---------------------------------------------------------------------------
# 4. Approval workflow
# ---------------------------------------------------------------------------


class TestApprovalWorkflow:
    """Verify complete approval lifecycle through the engine."""

    def test_approval_pending_then_approved(self):
        """
        Full approval flow:
        execute → PENDING_APPROVAL → approve → record APPROVED.
        """
        approval_manager = ApprovalManager()
        hook_manager = HookManager()
        scheduler = CoreScheduler(hook_manager=hook_manager)

        scheduler.plugin_pool.register_global_plugin(
            GuardHumanInLoop(approval_manager=approval_manager)
        )
        tool = make_tool("payment_tool")
        scheduler.register_tool(tool)

        ctx = scheduler.execute("payment_tool", {"amount": 100})

        assert ctx.status == ExecutionStatus.PENDING_APPROVAL
        assert ctx.approval_id is not None

        # Approve the request
        record = approval_manager.approve(ctx.approval_id, approver="admin")
        assert record.status == ApprovalStatus.APPROVED
        assert record.approver == "admin"

    def test_approval_pending_then_rejected(self):
        """
        Full rejection flow:
        execute → PENDING_APPROVAL → reject → record REJECTED.
        """
        approval_manager = ApprovalManager()
        hook_manager = HookManager()
        scheduler = CoreScheduler(hook_manager=hook_manager)

        scheduler.plugin_pool.register_global_plugin(
            GuardHumanInLoop(approval_manager=approval_manager)
        )
        tool = make_tool("risky_tool")
        scheduler.register_tool(tool)

        ctx = scheduler.execute("risky_tool", {})

        assert ctx.status == ExecutionStatus.PENDING_APPROVAL

        record = approval_manager.reject(
            ctx.approval_id, approver="security_admin", reason="Insufficient justification"
        )
        assert record.status == ApprovalStatus.REJECTED
        assert record.reject_reason == "Insufficient justification"

    def test_approval_timeout(self):
        """Pending approval expires and is marked TIMEOUT by check_timeouts."""
        approval_manager = ApprovalManager(default_timeout=0.1)
        hook_manager = HookManager()
        scheduler = CoreScheduler(hook_manager=hook_manager)

        scheduler.plugin_pool.register_global_plugin(
            GuardHumanInLoop(approval_manager=approval_manager, timeout=0.1)
        )
        tool = make_tool("timed_tool")
        scheduler.register_tool(tool)

        ctx = scheduler.execute("timed_tool", {})
        assert ctx.status == ExecutionStatus.PENDING_APPROVAL

        # Wait for timeout
        time.sleep(0.3)
        expired = approval_manager.check_timeouts()

        assert ctx.approval_id in expired
        record = approval_manager.get_approval(ctx.approval_id)
        assert record.status == ApprovalStatus.TIMEOUT

    def test_multiple_pending_approvals_listed(self):
        """All pending approvals are returned by list_pending()."""
        approval_manager = ApprovalManager()
        hook_manager = HookManager()
        scheduler = CoreScheduler(hook_manager=hook_manager)

        scheduler.plugin_pool.register_global_plugin(
            GuardHumanInLoop(approval_manager=approval_manager)
        )

        for i in range(3):
            scheduler.register_tool(make_tool(f"tool_{i}"))

        # Schedule tool_1 and tool_2; approve tool_0 later
        ctx0 = scheduler.execute("tool_0", {})
        ctx1 = scheduler.execute("tool_1", {})
        ctx2 = scheduler.execute("tool_2", {})

        # Approve one
        approval_manager.approve(ctx0.approval_id, approver="admin")

        pending = approval_manager.list_pending()
        pending_ids = {r.approval_id for r in pending}

        assert ctx0.approval_id not in pending_ids
        assert ctx1.approval_id in pending_ids
        assert ctx2.approval_id in pending_ids


# ---------------------------------------------------------------------------
# 5. Multi-layer plugin combination
# ---------------------------------------------------------------------------


class TestMultiLayerPluginCombination:
    """Tests combining multiple plugin types in realistic configurations."""

    def test_schema_and_guard_and_log_combination(self):
        """Schema + Guard + LogPlugin all cooperate on a successful execution."""
        hook_manager = HookManager()
        scheduler = CoreScheduler(hook_manager=hook_manager)

        # Register plugins
        weather_schema = SchemaDefault(schema=WEATHER_SCHEMA)
        guard = GuardDefault(whitelist=["weather_api"])
        log_plugin = LogPlugin()

        scheduler.plugin_pool.register_global_plugin(weather_schema)
        scheduler.plugin_pool.register_global_plugin(guard)
        scheduler.plugin_pool.register_global_plugin(log_plugin)

        tool = Tool(
            tool_id="weather_api",
            name="Weather API",
            description="Get weather information for a location",
            input_schema=WEATHER_SCHEMA,
            execute_func=lambda p: {"temperature": 25, "city": p["location"]},
        )
        scheduler.register_tool(tool)

        ctx = scheduler.execute("weather_api", {"location": "Beijing"})

        assert ctx.status == ExecutionStatus.COMPLETED
        assert ctx.final_result["temperature"] == 25
        assert ctx.final_result["city"] == "Beijing"

    def test_payment_tool_with_strict_schema_and_human_approval(self):
        """
        Payment tool uses strict schema validation + human approval.
        Valid params → PENDING_APPROVAL (not FAILED).
        """
        approval_manager = ApprovalManager()
        hook_manager = HookManager()
        scheduler = CoreScheduler(hook_manager=hook_manager)

        # Payment tool uses strict schema validation + human in loop guard
        payment_schema = SchemaDefault(schema=PAYMENT_SCHEMA)
        guard = GuardHumanInLoop(approval_manager=approval_manager)

        scheduler.plugin_pool.register_global_plugin(payment_schema)
        scheduler.plugin_pool.register_global_plugin(guard)

        tool = Tool(
            tool_id="payment_refund",
            name="Payment Refund",
            description="Process a payment refund for an order",
            input_schema=PAYMENT_SCHEMA,
            execute_func=lambda p: {"refunded": p["amount"]},
        )
        scheduler.register_tool(tool)

        ctx = scheduler.execute("payment_refund", {"amount": 500, "order_id": "ORD-001"})

        assert ctx.status == ExecutionStatus.PENDING_APPROVAL
        assert ctx.approval_id is not None

        record = approval_manager.get_approval(ctx.approval_id)
        assert record.tool_id == "payment_refund"
        assert record.params["amount"] == 500

    def test_schema_validation_fails_before_human_approval(self):
        """Invalid params fail schema validation before reaching Guard."""
        approval_manager = ApprovalManager()
        hook_manager = HookManager()
        scheduler = CoreScheduler(hook_manager=hook_manager)

        payment_schema = SchemaDefault(schema=PAYMENT_SCHEMA)
        guard = GuardHumanInLoop(approval_manager=approval_manager)

        scheduler.plugin_pool.register_global_plugin(payment_schema)
        scheduler.plugin_pool.register_global_plugin(guard)

        tool = Tool(
            tool_id="payment_refund2",
            name="Payment Refund",
            description="Process a payment refund for an order",
            input_schema=PAYMENT_SCHEMA,
            execute_func=lambda p: {"refunded": p["amount"]},
        )
        scheduler.register_tool(tool)

        # Missing "order_id" – should fail schema, not reach guard
        ctx = scheduler.execute("payment_refund2", {"amount": 500})

        assert ctx.status == ExecutionStatus.FAILED
        # No approvals should have been created
        assert len(approval_manager.list_pending()) == 0


# ---------------------------------------------------------------------------
# 6. Concurrent executions
# ---------------------------------------------------------------------------


class TestConcurrentExecution:
    """Verify thread safety during concurrent executions."""

    def test_concurrent_tool_executions(self):
        """Multiple threads executing the same tool concurrently produce no corruption."""
        scheduler = CoreScheduler()

        call_count = {"n": 0}
        lock = threading.Lock()

        def counting_func(params):
            with lock:
                call_count["n"] += 1
            time.sleep(0.01)
            return {"n": call_count["n"]}

        tool = make_tool("concurrent_tool", func=counting_func)
        scheduler.register_tool(tool)

        results = []
        errors = []

        def run():
            try:
                ctx = scheduler.execute("concurrent_tool", {})
                results.append(ctx.status)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=run) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert all(s == ExecutionStatus.COMPLETED for s in results)
        assert call_count["n"] == 10

    def test_concurrent_approvals(self):
        """Multiple executions waiting for approval are all tracked correctly."""
        approval_manager = ApprovalManager()
        scheduler = CoreScheduler()

        scheduler.plugin_pool.register_global_plugin(
            GuardHumanInLoop(approval_manager=approval_manager)
        )

        # Create 5 different tools
        for i in range(5):
            scheduler.register_tool(make_tool(f"concurrent_sensitive_tool_{i}"))

        contexts = []
        lock = threading.Lock()

        def run(i):
            ctx = scheduler.execute(f"concurrent_sensitive_tool_{i}", {})
            with lock:
                contexts.append(ctx)

        threads = [threading.Thread(target=run, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(contexts) == 5
        assert all(c.status == ExecutionStatus.PENDING_APPROVAL for c in contexts)

        pending = approval_manager.list_pending()
        assert len(pending) == 5


# ---------------------------------------------------------------------------
# 7. ToolRegistry integration
# ---------------------------------------------------------------------------


class TestToolRegistryIntegration:
    """Verify CoreScheduler works correctly with an external ToolRegistry."""

    def test_scheduler_uses_external_registry(self):
        """Tools registered in an external ToolRegistry are accessible to scheduler."""
        registry = ToolRegistry()
        scheduler = CoreScheduler(tool_registry=registry)

        tool = make_tool("external_registry_tool")
        registry.register(tool)

        ctx = scheduler.execute("external_registry_tool", {})
        assert ctx.status == ExecutionStatus.COMPLETED

    def test_registry_unregister_removes_tool_from_scheduler(self):
        """After unregistering a tool, scheduler raises ToolNotFoundError."""
        from slotagent.interfaces import ToolNotFoundError

        registry = ToolRegistry()
        scheduler = CoreScheduler(tool_registry=registry)

        tool = make_tool("removable_tool")
        registry.register(tool)

        ctx1 = scheduler.execute("removable_tool", {})
        assert ctx1.status == ExecutionStatus.COMPLETED

        registry.unregister("removable_tool")

        with pytest.raises(ToolNotFoundError, match="Tool 'removable_tool' not found"):
            scheduler.execute("removable_tool", {})
