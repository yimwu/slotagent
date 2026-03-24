# Copyright (c) 2026 SlotAgent Contributors
# Licensed under the MIT License - see LICENSE file for details.
"""
Unit tests for SlotAgent main class.
"""

import pytest

from slotagent import SlotAgent
from slotagent.core.approval_manager import ApprovalManager
from slotagent.core.hook_manager import HookManager
from slotagent.core.plugin_pool import PluginPool
from slotagent.core.tool_registry import ToolRegistry
from slotagent.llm.mock_llm import MockLLM
from slotagent.plugins.guard import GuardDefault, GuardHumanInLoop
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
# Helpers
# ---------------------------------------------------------------------------

def _make_tool(tool_id: str, func=None):
    if func is None:
        func = lambda p: {"ok": True, "tool_id": tool_id}
    return Tool(
        tool_id=tool_id,
        name=tool_id.replace("_", " ").title(),
        description=f"Test tool {tool_id} - at least 10 characters",
        input_schema={"type": "object", "properties": {}},
        execute_func=func,
    )


# ---------------------------------------------------------------------------
# TestSlotAgentCreation
# ---------------------------------------------------------------------------


class TestSlotAgentCreation:
    def test_default_creation(self):
        agent = SlotAgent()
        assert agent is not None
        assert agent.plugin_pool is not None
        assert agent.tool_registry is not None
        assert agent.hook_manager is not None
        assert agent.approval_manager is not None
        assert agent.llm is None

    def test_creation_with_llm(self):
        llm = MockLLM()
        agent = SlotAgent(llm=llm)
        assert agent.llm is llm

    def test_creation_with_custom_components(self):
        pool = PluginPool()
        registry = ToolRegistry(pool)
        hook_mgr = HookManager()
        approval_mgr = ApprovalManager()

        agent = SlotAgent(
            plugin_pool=pool,
            tool_registry=registry,
            hook_manager=hook_mgr,
            approval_manager=approval_mgr,
        )

        assert agent.plugin_pool is pool
        assert agent.tool_registry is registry
        assert agent.hook_manager is hook_mgr
        assert agent.approval_manager is approval_mgr

    def test_importable_from_package(self):
        from slotagent import SlotAgent as SA  # noqa: F401
        assert SA is SlotAgent


# ---------------------------------------------------------------------------
# TestToolRegistration
# ---------------------------------------------------------------------------


class TestToolRegistration:
    def test_register_tool(self):
        agent = SlotAgent()
        tool = _make_tool("my_tool")
        agent.register_tool(tool)
        assert agent.tool_registry.get_tool("my_tool") is tool

    def test_register_plugin(self):
        agent = SlotAgent()
        plugin = SchemaDefault()
        agent.register_plugin(plugin)
        assert agent.plugin_pool.get_plugin("schema", "any") is plugin


# ---------------------------------------------------------------------------
# TestExecute
# ---------------------------------------------------------------------------


class TestExecute:
    def test_execute_simple_tool(self):
        agent = SlotAgent()
        agent.register_tool(_make_tool("my_tool"))
        ctx = agent.execute("my_tool", {})
        assert ctx.status == ExecutionStatus.COMPLETED
        assert ctx.final_result == {"ok": True, "tool_id": "my_tool"}

    def test_execute_unknown_tool_raises(self):
        from slotagent.interfaces import ToolNotFoundError

        agent = SlotAgent()
        with pytest.raises(ToolNotFoundError):
            agent.execute("no_such_tool", {})

    def test_execute_with_schema_validation(self):
        """Schema failure → FAILED status."""
        agent = SlotAgent()
        schema = {
            "type": "object",
            "properties": {"location": {"type": "string"}},
            "required": ["location"],
        }
        agent.register_plugin(SchemaDefault(schema=schema))
        tool = Tool(
            tool_id="weather_query",
            name="Weather",
            description="Get weather for a location",
            input_schema=schema,
            execute_func=lambda p: {"temp": 25},
        )
        agent.register_tool(tool)

        ctx = agent.execute("weather_query", {})  # missing required param
        assert ctx.status == ExecutionStatus.FAILED

    def test_execute_tool_exception_returns_failed(self):
        def crashing(params):
            raise RuntimeError("boom")

        agent = SlotAgent()
        agent.register_tool(_make_tool("crash_tool", func=crashing))
        ctx = agent.execute("crash_tool", {})
        assert ctx.status == ExecutionStatus.FAILED


# ---------------------------------------------------------------------------
# TestBatchRun
# ---------------------------------------------------------------------------


class TestBatchRun:
    def test_batch_run_empty_list(self):
        agent = SlotAgent()
        results = agent.batch_run([])
        assert results == []

    def test_batch_run_multiple_tasks(self):
        agent = SlotAgent()
        agent.register_tool(_make_tool("tool_a"))
        agent.register_tool(_make_tool("tool_b"))

        results = agent.batch_run([
            {"tool_id": "tool_a", "params": {}},
            {"tool_id": "tool_b", "params": {}},
        ])

        assert len(results) == 2
        assert results[0].tool_id == "tool_a"
        assert results[1].tool_id == "tool_b"
        assert all(r.status == ExecutionStatus.COMPLETED for r in results)

    def test_batch_run_default_params(self):
        """Tasks without 'params' key should use empty dict."""
        agent = SlotAgent()
        agent.register_tool(_make_tool("simple_tool"))
        results = agent.batch_run([{"tool_id": "simple_tool"}])
        assert len(results) == 1
        assert results[0].status == ExecutionStatus.COMPLETED

    def test_batch_run_mixed_success_and_fail(self):
        def crashing(params):
            raise RuntimeError("fail")

        agent = SlotAgent()
        agent.register_tool(_make_tool("ok_tool"))
        agent.register_tool(_make_tool("bad_tool", func=crashing))

        results = agent.batch_run([
            {"tool_id": "ok_tool"},
            {"tool_id": "bad_tool"},
        ])
        assert results[0].status == ExecutionStatus.COMPLETED
        assert results[1].status == ExecutionStatus.FAILED

    def test_batch_run_returns_results_in_order(self):
        call_order = []

        def make_func(name):
            def func(params):
                call_order.append(name)
                return {"name": name}
            return func

        agent = SlotAgent()
        for i in range(3):
            agent.register_tool(_make_tool(f"tool_{i}", func=make_func(f"tool_{i}")))

        results = agent.batch_run([
            {"tool_id": "tool_0"},
            {"tool_id": "tool_1"},
            {"tool_id": "tool_2"},
        ])

        assert call_order == ["tool_0", "tool_1", "tool_2"]
        assert [r.tool_id for r in results] == ["tool_0", "tool_1", "tool_2"]


# ---------------------------------------------------------------------------
# TestRunIndependentMode
# ---------------------------------------------------------------------------


class TestRunIndependentMode:
    def test_run_requires_llm(self):
        agent = SlotAgent()  # no llm
        agent.register_tool(_make_tool("some_tool"))
        with pytest.raises(ValueError, match="LLM is required"):
            agent.run("do something")

    def test_run_requires_tools(self):
        agent = SlotAgent(llm=MockLLM())
        with pytest.raises(ValueError, match="No tools registered"):
            agent.run("do something")

    def test_run_uses_llm_to_select_tool(self):
        """LLM returns valid JSON → tool executed successfully."""
        import json

        llm_response = json.dumps({
            "tool_id": "weather_query",
            "params": {"location": "Beijing"},
        })
        llm = MockLLM(responses={"weather": llm_response})

        agent = SlotAgent(llm=llm)

        schema = {
            "type": "object",
            "properties": {"location": {"type": "string"}},
            "required": ["location"],
        }
        agent.register_tool(Tool(
            tool_id="weather_query",
            name="Weather Query",
            description="Get weather for a location - at least ten chars",
            input_schema=schema,
            execute_func=lambda p: {"temperature": 20, "city": p["location"]},
        ))

        ctx = agent.run("What is the weather in Beijing?")  # triggers "weather" keyword in LLM

        assert ctx.status == ExecutionStatus.COMPLETED
        assert ctx.final_result["city"] == "Beijing"

    def test_run_invalid_llm_response_raises_value_error(self):
        """Non-JSON LLM response → ValueError."""
        llm = MockLLM(responses={"query": "this is not json"})
        agent = SlotAgent(llm=llm)
        agent.register_tool(_make_tool("my_tool"))

        with pytest.raises(ValueError, match="invalid JSON"):
            agent.run("query something")

    def test_run_missing_tool_id_in_response_raises_value_error(self):
        """JSON without 'tool_id' → ValueError."""
        import json
        llm = MockLLM(responses={"query": json.dumps({"params": {}})})
        agent = SlotAgent(llm=llm)
        agent.register_tool(_make_tool("my_tool"))

        with pytest.raises(ValueError, match="invalid JSON"):
            agent.run("query something")


# ---------------------------------------------------------------------------
# TestHookSubscriptions
# ---------------------------------------------------------------------------


class TestHookSubscriptions:
    def test_on_before_exec(self):
        agent = SlotAgent()
        events = []
        agent.on_before_exec(lambda e: events.append(e))
        agent.register_tool(_make_tool("my_tool"))
        agent.execute("my_tool", {})
        assert len(events) == 1
        assert isinstance(events[0], BeforeExecEvent)

    def test_on_after_exec(self):
        agent = SlotAgent()
        events = []
        agent.on_after_exec(lambda e: events.append(e))
        agent.register_tool(_make_tool("my_tool"))
        agent.execute("my_tool", {})
        assert len(events) == 1
        assert isinstance(events[0], AfterExecEvent)

    def test_on_fail(self):
        agent = SlotAgent()
        events = []
        agent.on_fail(lambda e: events.append(e))
        agent.register_tool(_make_tool("crash", func=lambda p: (_ for _ in ()).throw(RuntimeError("x"))))
        agent.execute("crash", {})
        assert len(events) >= 1
        assert isinstance(events[0], FailEvent)

    def test_on_guard_block(self):
        agent = SlotAgent()
        events = []
        agent.on_guard_block(lambda e: events.append(e))
        agent.register_plugin(GuardDefault(blacklist=["blocked"]))
        agent.register_tool(_make_tool("blocked"))
        agent.execute("blocked", {})
        assert len(events) == 1
        assert isinstance(events[0], GuardBlockEvent)

    def test_on_wait_approval(self):
        approval_mgr = ApprovalManager()
        agent = SlotAgent(approval_manager=approval_mgr)
        events = []
        agent.on_wait_approval(lambda e: events.append(e))
        agent.register_plugin(GuardHumanInLoop(approval_manager=approval_mgr))
        agent.register_tool(_make_tool("sensitive"))
        ctx = agent.execute("sensitive", {})
        assert ctx.status == ExecutionStatus.PENDING_APPROVAL
        assert len(events) == 1
        assert isinstance(events[0], WaitApprovalEvent)

    def test_multiple_subscribers_for_same_event(self):
        agent = SlotAgent()
        received_1, received_2 = [], []
        agent.on_before_exec(lambda e: received_1.append(e))
        agent.on_before_exec(lambda e: received_2.append(e))
        agent.register_tool(_make_tool("my_tool"))
        agent.execute("my_tool", {})
        assert len(received_1) == 1
        assert len(received_2) == 1


# ---------------------------------------------------------------------------
# TestApprovalManagement
# ---------------------------------------------------------------------------


class TestApprovalManagement:
    def _setup_approval_agent(self):
        approval_mgr = ApprovalManager()
        agent = SlotAgent(approval_manager=approval_mgr)
        agent.register_plugin(GuardHumanInLoop(approval_manager=approval_mgr))
        agent.register_tool(_make_tool("payment_tool"))
        return agent

    def test_approve_pending_execution(self):
        agent = self._setup_approval_agent()
        ctx = agent.execute("payment_tool", {})
        assert ctx.status == ExecutionStatus.PENDING_APPROVAL

        record = agent.approve(ctx.approval_id, approver="admin")
        assert record.status == ApprovalStatus.APPROVED
        assert record.approver == "admin"

    def test_reject_pending_execution(self):
        agent = self._setup_approval_agent()
        ctx = agent.execute("payment_tool", {})

        record = agent.reject(ctx.approval_id, approver="security", reason="Too risky")
        assert record.status == ApprovalStatus.REJECTED
        assert record.reject_reason == "Too risky"

    def test_list_pending_approvals(self):
        approval_mgr = ApprovalManager()
        agent = SlotAgent(approval_manager=approval_mgr)
        agent.register_plugin(GuardHumanInLoop(approval_manager=approval_mgr))

        for i in range(3):
            agent.register_tool(_make_tool(f"tool_{i}"))
            agent.execute(f"tool_{i}", {})

        pending = agent.list_pending_approvals()
        assert len(pending) == 3

    def test_approve_removes_from_pending(self):
        agent = self._setup_approval_agent()
        ctx = agent.execute("payment_tool", {})

        agent.approve(ctx.approval_id, approver="admin")

        pending = agent.list_pending_approvals()
        pending_ids = {r.approval_id for r in pending}
        assert ctx.approval_id not in pending_ids
