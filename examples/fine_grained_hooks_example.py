#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) 2026 SlotAgent Contributors
# Licensed under the MIT License - see LICENSE file for details.
"""
Fine-Grained Hook Events Example

Demonstrates the Batch 1 + Batch 2 hook events added in the hook expansion plan:

  Batch 1 - Scheduling lifecycle events:
    before_schema, after_schema, before_guard,
    after_healing, retry_started, after_reflect

  Batch 2 - Approval resolution event:
    approval_resolved (approved / rejected / timeout)

Run this example:
    python examples/fine_grained_hooks_example.py
"""

import sys
import time

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

from slotagent import SlotAgent
from slotagent.core import ApprovalManager
from slotagent.plugins import SchemaDefault, GuardDefault, GuardHumanInLoop
from slotagent.plugins.reflect import ReflectSimple
from slotagent.types import Tool, ExecutionStatus


# ============================================================================
# Helpers
# ============================================================================

def _log(event):
    print(f"  [HOOK] {event.event_type}")


def _make_tool(name, fn, schema=None):
    return Tool(tool_id=name, name=name, description=f"{name} tool for demo",
                input_schema=schema or {"type": "object", "properties": {}},
                execute_func=fn)


# ============================================================================
# Demo 1: Batch 1 - full success flow
#   before_schema -> after_schema -> before_guard -> before_exec
#   -> after_exec -> after_reflect
# ============================================================================

def demo_batch1_success():
    print("\n=== Demo 1: Batch 1 success flow ===")

    agent = SlotAgent()
    events = []

    for et in ("before_schema", "after_schema", "before_guard",
               "before_exec", "after_exec", "after_reflect"):
        agent.hook_manager.subscribe(et, lambda e, t=et: events.append(t))

    # Schema plugin validates params; Guard allows all; Reflect verifies result
    agent.register_plugin(SchemaDefault())
    agent.register_plugin(GuardDefault())
    agent.register_plugin(ReflectSimple())

    agent.register_tool(_make_tool(
        "query_tool",
        lambda p: {"answer": 42},
        schema={"type": "object", "properties": {}, "required": []},
    ))

    ctx = agent.execute("query_tool", {})
    assert ctx.status == ExecutionStatus.COMPLETED, f"Unexpected: {ctx.status}"

    print(f"  Event order: {events}")
    assert events == ["before_schema", "after_schema", "before_guard",
                      "before_exec", "after_exec", "after_reflect"], \
        f"Unexpected order: {events}"
    print("  PASSED")


# ============================================================================
# Demo 2: Batch 1 - schema failure
#   before_schema -> after_schema(success=False) -> fail
#   (before_guard / before_exec must NOT fire)
# ============================================================================

def demo_batch1_schema_failure():
    print("\n=== Demo 2: Batch 1 schema failure ===")

    agent = SlotAgent()
    events = []

    for et in ("before_schema", "after_schema", "before_guard",
               "before_exec", "fail"):
        agent.hook_manager.subscribe(et, lambda e, t=et: events.append(t))

    from slotagent.plugins.schema import SchemaDefault
    agent.register_plugin(SchemaDefault())

    # Tool requires "amount" field; we pass nothing -> schema rejects
    agent.register_tool(_make_tool(
        "strict_tool",
        lambda p: {},
        schema={
            "type": "object",
            "properties": {"amount": {"type": "number"}},
            "required": ["amount"],
        },
    ))

    ctx = agent.execute("strict_tool", {})
    assert ctx.status == ExecutionStatus.FAILED

    print(f"  Event order: {events}")
    assert "before_schema" in events
    assert "after_schema" in events
    assert "fail" in events
    assert "before_guard" not in events
    assert "before_exec" not in events
    print("  PASSED")


# ============================================================================
# Demo 3: Batch 1 - healing + retry
#   fail -> after_healing -> retry_started -> (retry) -> after_exec
# ============================================================================

def demo_batch1_healing_retry():
    print("\n=== Demo 3: Batch 1 healing + retry ===")

    from slotagent.interfaces import PluginInterface
    from slotagent.types import PluginResult

    class RecoveringHealingPlugin(PluginInterface):
        """Healing plugin that always signals recovery (for demo purposes)."""
        layer = "healing"
        plugin_id = "healing_recovering"

        def validate(self):
            return True

        def execute(self, context):
            return PluginResult(success=True, data={"recovered": True})

    agent = SlotAgent()
    events = []

    for et in ("fail", "after_healing", "retry_started", "after_exec"):
        agent.hook_manager.subscribe(et, lambda e, t=et: events.append(t))

    agent.register_plugin(RecoveringHealingPlugin())

    call_count = {"n": 0}

    def flaky(params):
        call_count["n"] += 1
        if call_count["n"] < 2:
            raise RuntimeError("transient error")
        return {"ok": True}

    agent.register_tool(_make_tool("flaky_tool", flaky))

    ctx = agent.execute("flaky_tool", {})
    assert ctx.status == ExecutionStatus.COMPLETED, f"Unexpected: {ctx.status}"

    print(f"  Event order: {events}")
    assert "fail" in events
    assert "after_healing" in events
    assert "retry_started" in events
    assert "after_exec" in events
    print("  PASSED")


# ============================================================================
# Demo 4: Batch 2 - approval_resolved (approved)
# ============================================================================

def demo_batch2_approved():
    print("\n=== Demo 4: Batch 2 approval_resolved (approved) ===")

    approval_manager = ApprovalManager()
    agent = SlotAgent(approval_manager=approval_manager)

    resolved_events = []
    agent.on_approval_resolved(resolved_events.append)
    agent.on_wait_approval(lambda e: print(f"  [HOOK] wait_approval: {e.approval_id}"))

    agent.register_plugin(GuardHumanInLoop(approval_manager=approval_manager))
    agent.register_tool(_make_tool("pay_tool", lambda p: {"paid": True}))

    ctx = agent.execute("pay_tool", {"amount": 100})
    assert ctx.status == ExecutionStatus.PENDING_APPROVAL

    # Simulate external approver
    approval_manager.approve(ctx.approval_id, approver="admin@example.com")

    assert len(resolved_events) == 1
    e = resolved_events[0]
    print(f"  [HOOK] approval_resolved: resolution={e.resolution}, approver={e.approver}")
    assert e.resolution == "approved"
    assert e.approver == "admin@example.com"
    assert e.approval_id == ctx.approval_id
    print("  PASSED")


# ============================================================================
# Demo 5: Batch 2 - approval_resolved (rejected)
# ============================================================================

def demo_batch2_rejected():
    print("\n=== Demo 5: Batch 2 approval_resolved (rejected) ===")

    approval_manager = ApprovalManager()
    agent = SlotAgent(approval_manager=approval_manager)

    resolved_events = []
    agent.on_approval_resolved(resolved_events.append)

    agent.register_plugin(GuardHumanInLoop(approval_manager=approval_manager))
    agent.register_tool(_make_tool("delete_tool", lambda p: {"deleted": True}))

    ctx = agent.execute("delete_tool", {})
    approval_manager.reject(ctx.approval_id, approver="security@example.com",
                            reason="Insufficient justification")

    assert len(resolved_events) == 1
    e = resolved_events[0]
    print(f"  [HOOK] approval_resolved: resolution={e.resolution}, reason={e.reason}")
    assert e.resolution == "rejected"
    assert e.reason == "Insufficient justification"
    print("  PASSED")


# ============================================================================
# Demo 6: Batch 2 - approval_resolved (timeout)
# ============================================================================

def demo_batch2_timeout():
    print("\n=== Demo 6: Batch 2 approval_resolved (timeout) ===")

    approval_manager = ApprovalManager(default_timeout=0.01)
    agent = SlotAgent(approval_manager=approval_manager)

    resolved_events = []
    agent.on_approval_resolved(resolved_events.append)

    agent.register_plugin(GuardHumanInLoop(approval_manager=approval_manager))
    agent.register_tool(_make_tool("risky_tool", lambda p: {}))

    ctx = agent.execute("risky_tool", {})
    time.sleep(0.05)
    approval_manager.check_timeouts()

    assert len(resolved_events) == 1
    e = resolved_events[0]
    print(f"  [HOOK] approval_resolved: resolution={e.resolution}")
    assert e.resolution == "timeout"
    print("  PASSED")


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    demo_batch1_success()
    demo_batch1_schema_failure()
    demo_batch1_healing_retry()
    demo_batch2_approved()
    demo_batch2_rejected()
    demo_batch2_timeout()
    print("\nAll demos passed.")
