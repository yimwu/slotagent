# Copyright (c) 2026 SlotAgent Contributors
# Licensed under the MIT License - see LICENSE file for details.
"""
Unit tests for GuardHumanInLoop plugin.
"""

import time
import uuid

from slotagent.core.approval_manager import ApprovalManager
from slotagent.plugins.guard import GuardHumanInLoop
from slotagent.types import ApprovalStatus, PluginContext


class TestGuardHumanInLoopCreation:
    """Test GuardHumanInLoop plugin creation"""

    def test_plugin_attributes(self):
        """Test GuardHumanInLoop has correct attributes"""
        manager = ApprovalManager()
        plugin = GuardHumanInLoop(approval_manager=manager)

        assert plugin.layer == "guard"
        assert plugin.plugin_id == "guard_human_in_loop"

    def test_plugin_with_custom_timeout(self):
        """Test creating plugin with custom timeout"""
        manager = ApprovalManager()
        plugin = GuardHumanInLoop(approval_manager=manager, timeout=600.0)

        assert plugin.timeout == 600.0


class TestGuardHumanInLoopExecution:
    """Test GuardHumanInLoop execution"""

    def test_execute_creates_approval(self):
        """Test that execute creates approval request"""
        manager = ApprovalManager()
        plugin = GuardHumanInLoop(approval_manager=manager)

        context = PluginContext(
            tool_id="payment_refund",
            tool_name="Payment Refund",
            params={"amount": 100},
            layer="guard",
            execution_id=str(uuid.uuid4()),
            timestamp=time.time(),
        )

        result = plugin.execute(context)

        assert result.success is True
        assert result.should_continue is False
        assert result.data is not None
        assert result.data["pending_approval"] is True
        assert "approval_id" in result.data

    def test_execute_returns_approval_id(self):
        """Test that execute returns valid approval_id"""
        manager = ApprovalManager()
        plugin = GuardHumanInLoop(approval_manager=manager)

        context = PluginContext(
            tool_id="payment_refund",
            tool_name="Payment Refund",
            params={"amount": 100},
            layer="guard",
            execution_id=str(uuid.uuid4()),
            timestamp=time.time(),
        )

        result = plugin.execute(context)

        approval_id = result.data["approval_id"]

        # Verify approval was created in manager
        approval = manager.get_approval(approval_id)
        assert approval is not None
        assert approval.status == ApprovalStatus.PENDING
        assert approval.tool_id == "payment_refund"
        assert approval.tool_name == "Payment Refund"
        assert approval.params == {"amount": 100}

    def test_execute_includes_approval_context(self):
        """Test that execute includes approval context"""
        manager = ApprovalManager()
        plugin = GuardHumanInLoop(approval_manager=manager)

        context = PluginContext(
            tool_id="payment_refund",
            tool_name="Payment Refund",
            params={"order_id": "ORD123", "amount": 100},
            layer="guard",
            execution_id=str(uuid.uuid4()),
            timestamp=time.time(),
        )

        result = plugin.execute(context)

        assert "approval_context" in result.data
        approval_context = result.data["approval_context"]
        assert approval_context["tool_id"] == "payment_refund"
        assert approval_context["tool_name"] == "Payment Refund"
        assert "params_summary" in approval_context

    def test_execute_uses_custom_timeout(self):
        """Test that execute uses custom timeout"""
        manager = ApprovalManager(default_timeout=300.0)
        plugin = GuardHumanInLoop(approval_manager=manager, timeout=600.0)

        context = PluginContext(
            tool_id="test_tool",
            tool_name="Test Tool",
            params={},
            layer="guard",
            execution_id=str(uuid.uuid4()),
            timestamp=time.time(),
        )

        result = plugin.execute(context)
        approval_id = result.data["approval_id"]

        approval = manager.get_approval(approval_id)
        # Should use plugin timeout (600), not manager default (300)
        assert abs((approval.timeout_at - approval.created_at) - 600.0) < 0.1

    def test_validate_returns_true(self):
        """Test that validate returns True"""
        manager = ApprovalManager()
        plugin = GuardHumanInLoop(approval_manager=manager)

        assert plugin.validate() is True


class TestParamsSummarization:
    """Test parameter summarization for approval context"""

    def test_summarize_simple_params(self):
        """Test summarizing simple parameter types"""
        manager = ApprovalManager()
        plugin = GuardHumanInLoop(approval_manager=manager)

        context = PluginContext(
            tool_id="test_tool",
            tool_name="Test Tool",
            params={
                "string_param": "value",
                "int_param": 42,
                "float_param": 3.14,
                "bool_param": True,
            },
            layer="guard",
            execution_id=str(uuid.uuid4()),
            timestamp=time.time(),
        )

        result = plugin.execute(context)
        summary = result.data["approval_context"]["params_summary"]

        assert "string_param=value" in summary
        assert "int_param=42" in summary
        assert "float_param=3.14" in summary
        assert "bool_param=True" in summary

    def test_summarize_dict_params(self):
        """Test summarizing dict parameters"""
        manager = ApprovalManager()
        plugin = GuardHumanInLoop(approval_manager=manager)

        context = PluginContext(
            tool_id="test_tool",
            tool_name="Test Tool",
            params={"nested_dict": {"key1": "value1", "key2": "value2"}},
            layer="guard",
            execution_id=str(uuid.uuid4()),
            timestamp=time.time(),
        )

        result = plugin.execute(context)
        summary = result.data["approval_context"]["params_summary"]

        assert "nested_dict={...}" in summary

    def test_summarize_list_params(self):
        """Test summarizing list parameters"""
        manager = ApprovalManager()
        plugin = GuardHumanInLoop(approval_manager=manager)

        context = PluginContext(
            tool_id="test_tool",
            tool_name="Test Tool",
            params={"items": [1, 2, 3, 4, 5]},
            layer="guard",
            execution_id=str(uuid.uuid4()),
            timestamp=time.time(),
        )

        result = plugin.execute(context)
        summary = result.data["approval_context"]["params_summary"]

        assert "items=[5 items]" in summary

    def test_summarize_empty_params(self):
        """Test summarizing empty parameters"""
        manager = ApprovalManager()
        plugin = GuardHumanInLoop(approval_manager=manager)

        context = PluginContext(
            tool_id="test_tool",
            tool_name="Test Tool",
            params={},
            layer="guard",
            execution_id=str(uuid.uuid4()),
            timestamp=time.time(),
        )

        result = plugin.execute(context)
        summary = result.data["approval_context"]["params_summary"]

        assert summary == "No parameters"

    def test_summarize_many_params(self):
        """Test summarizing more than 5 parameters"""
        manager = ApprovalManager()
        plugin = GuardHumanInLoop(approval_manager=manager)

        context = PluginContext(
            tool_id="test_tool",
            tool_name="Test Tool",
            params={
                "param1": "value1",
                "param2": "value2",
                "param3": "value3",
                "param4": "value4",
                "param5": "value5",
                "param6": "value6",
                "param7": "value7",
            },
            layer="guard",
            execution_id=str(uuid.uuid4()),
            timestamp=time.time(),
        )

        result = plugin.execute(context)
        summary = result.data["approval_context"]["params_summary"]

        # Should show "(+ 2 more)"
        assert "(+ 2 more)" in summary

    def test_summarize_custom_object_params(self):
        """Test summarizing custom object parameters"""
        manager = ApprovalManager()
        plugin = GuardHumanInLoop(approval_manager=manager)

        class CustomObj:
            pass

        context = PluginContext(
            tool_id="test_tool",
            tool_name="Test Tool",
            params={"obj": CustomObj()},
            layer="guard",
            execution_id=str(uuid.uuid4()),
            timestamp=time.time(),
        )

        result = plugin.execute(context)
        summary = result.data["approval_context"]["params_summary"]

        assert "obj=<CustomObj>" in summary
