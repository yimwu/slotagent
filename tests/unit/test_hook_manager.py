# Copyright (c) 2026 SlotAgent Contributors
# Licensed under the MIT License - see LICENSE file for details.
"""
Unit tests for HookManager.
"""

import threading
import time

import pytest

from slotagent.core.hook_manager import HookManager
from slotagent.types import (
    AfterExecEvent,
    BeforeExecEvent,
    FailEvent,
    GuardBlockEvent,
    WaitApprovalEvent,
)


class TestHookManagerCreation:
    """Test HookManager initialization"""

    def test_hook_manager_creation(self):
        """Test creating HookManager"""
        manager = HookManager()
        assert manager is not None

    def test_initial_subscriber_counts_are_zero(self):
        """Test all event types start with zero subscribers"""
        manager = HookManager()
        assert manager.get_subscriber_count("before_exec") == 0
        assert manager.get_subscriber_count("after_exec") == 0
        assert manager.get_subscriber_count("fail") == 0
        assert manager.get_subscriber_count("guard_block") == 0
        assert manager.get_subscriber_count("wait_approval") == 0


class TestSubscription:
    """Test subscription operations"""

    def test_subscribe_single_handler(self):
        """Test subscribing a single handler"""
        manager = HookManager()
        events = []

        def handler(event):
            events.append(event)

        manager.subscribe("before_exec", handler)
        assert manager.get_subscriber_count("before_exec") == 1

    def test_subscribe_multiple_handlers_same_event(self):
        """Test subscribing multiple handlers to same event"""
        manager = HookManager()
        events1 = []
        events2 = []

        def handler1(event):
            events1.append(event)

        def handler2(event):
            events2.append(event)

        manager.subscribe("before_exec", handler1)
        manager.subscribe("before_exec", handler2)

        assert manager.get_subscriber_count("before_exec") == 2

    def test_subscribe_same_handler_multiple_events(self):
        """Test subscribing same handler to multiple events"""
        manager = HookManager()
        events = []

        def handler(event):
            events.append(event)

        manager.subscribe("before_exec", handler)
        manager.subscribe("after_exec", handler)

        assert manager.get_subscriber_count("before_exec") == 1
        assert manager.get_subscriber_count("after_exec") == 1

    def test_subscribe_invalid_event_type_raises_error(self):
        """Test subscribing to invalid event type raises ValueError"""
        manager = HookManager()

        def handler(event):
            pass

        with pytest.raises(ValueError, match="Invalid event type"):
            manager.subscribe("invalid_event", handler)


class TestUnsubscription:
    """Test unsubscription operations"""

    def test_unsubscribe_existing_handler(self):
        """Test unsubscribing an existing handler"""
        manager = HookManager()

        def handler(event):
            pass

        manager.subscribe("before_exec", handler)
        assert manager.get_subscriber_count("before_exec") == 1

        manager.unsubscribe("before_exec", handler)
        assert manager.get_subscriber_count("before_exec") == 0

    def test_unsubscribe_nonexistent_handler_does_nothing(self):
        """Test unsubscribing non-existent handler does nothing"""
        manager = HookManager()

        def handler(event):
            pass

        # Should not raise error
        manager.unsubscribe("before_exec", handler)
        assert manager.get_subscriber_count("before_exec") == 0

    def test_unsubscribe_invalid_event_type_raises_error(self):
        """Test unsubscribing from invalid event type raises ValueError"""
        manager = HookManager()

        def handler(event):
            pass

        with pytest.raises(ValueError, match="Invalid event type"):
            manager.unsubscribe("invalid_event", handler)


class TestEventEmission:
    """Test event emission"""

    def test_emit_before_exec_event(self):
        """Test emitting before_exec event"""
        manager = HookManager()
        received_events = []

        def handler(event):
            received_events.append(event)

        manager.subscribe("before_exec", handler)

        event = BeforeExecEvent(
            execution_id="test-123",
            tool_id="test_tool",
            tool_name="Test Tool",
            timestamp=time.time(),
            params={"key": "value"},
        )

        manager.emit(event)

        assert len(received_events) == 1
        assert received_events[0].event_type == "before_exec"
        assert received_events[0].execution_id == "test-123"

    def test_emit_after_exec_event(self):
        """Test emitting after_exec event"""
        manager = HookManager()
        received_events = []

        def handler(event):
            received_events.append(event)

        manager.subscribe("after_exec", handler)

        event = AfterExecEvent(
            execution_id="test-123",
            tool_id="test_tool",
            tool_name="Test Tool",
            timestamp=time.time(),
            params={"key": "value"},
            result={"status": "success"},
            execution_time=1.5,
        )

        manager.emit(event)

        assert len(received_events) == 1
        assert received_events[0].event_type == "after_exec"
        assert received_events[0].result == {"status": "success"}
        assert received_events[0].execution_time == 1.5

    def test_emit_fail_event(self):
        """Test emitting fail event"""
        manager = HookManager()
        received_events = []

        def handler(event):
            received_events.append(event)

        manager.subscribe("fail", handler)

        event = FailEvent(
            execution_id="test-123",
            tool_id="test_tool",
            tool_name="Test Tool",
            timestamp=time.time(),
            params={"key": "value"},
            error="Something went wrong",
            error_type="RuntimeError",
            failed_stage="execute",
        )

        manager.emit(event)

        assert len(received_events) == 1
        assert received_events[0].event_type == "fail"
        assert received_events[0].error == "Something went wrong"
        assert received_events[0].failed_stage == "execute"

    def test_emit_guard_block_event(self):
        """Test emitting guard_block event"""
        manager = HookManager()
        received_events = []

        def handler(event):
            received_events.append(event)

        manager.subscribe("guard_block", handler)

        event = GuardBlockEvent(
            execution_id="test-123",
            tool_id="test_tool",
            tool_name="Test Tool",
            timestamp=time.time(),
            params={"key": "value"},
            reason="Permission denied",
            guard_plugin_id="guard_default",
        )

        manager.emit(event)

        assert len(received_events) == 1
        assert received_events[0].event_type == "guard_block"
        assert received_events[0].reason == "Permission denied"

    def test_emit_wait_approval_event(self):
        """Test emitting wait_approval event"""
        manager = HookManager()
        received_events = []

        def handler(event):
            received_events.append(event)

        manager.subscribe("wait_approval", handler)

        event = WaitApprovalEvent(
            execution_id="test-123",
            tool_id="test_tool",
            tool_name="Test Tool",
            timestamp=time.time(),
            params={"key": "value"},
            approval_id="approval-456",
            approval_context={"risk_level": "high"},
        )

        manager.emit(event)

        assert len(received_events) == 1
        assert received_events[0].event_type == "wait_approval"
        assert received_events[0].approval_id == "approval-456"

    def test_emit_to_multiple_subscribers(self):
        """Test emitting to multiple subscribers"""
        manager = HookManager()
        events1 = []
        events2 = []

        def handler1(event):
            events1.append(event)

        def handler2(event):
            events2.append(event)

        manager.subscribe("before_exec", handler1)
        manager.subscribe("before_exec", handler2)

        event = BeforeExecEvent(
            execution_id="test-123",
            tool_id="test_tool",
            tool_name="Test Tool",
            timestamp=time.time(),
            params={},
        )

        manager.emit(event)

        assert len(events1) == 1
        assert len(events2) == 1

    def test_emit_without_subscribers_does_nothing(self):
        """Test emitting without subscribers does nothing"""
        manager = HookManager()

        event = BeforeExecEvent(
            execution_id="test-123",
            tool_id="test_tool",
            tool_name="Test Tool",
            timestamp=time.time(),
            params={},
        )

        # Should not raise error
        manager.emit(event)


class TestExceptionHandling:
    """Test exception handling in subscribers"""

    def test_subscriber_exception_does_not_stop_other_subscribers(self):
        """Test that one subscriber's exception doesn't affect others"""
        manager = HookManager()
        events1 = []
        events2 = []

        def failing_handler(event):
            raise RuntimeError("Handler failed")

        def success_handler1(event):
            events1.append(event)

        def success_handler2(event):
            events2.append(event)

        # Subscribe in order: success, fail, success
        manager.subscribe("before_exec", success_handler1)
        manager.subscribe("before_exec", failing_handler)
        manager.subscribe("before_exec", success_handler2)

        event = BeforeExecEvent(
            execution_id="test-123",
            tool_id="test_tool",
            tool_name="Test Tool",
            timestamp=time.time(),
            params={},
        )

        # Should not raise exception
        manager.emit(event)

        # Both success handlers should have received the event
        assert len(events1) == 1
        assert len(events2) == 1

    def test_subscriber_exception_is_logged(self, caplog):
        """Test that subscriber exceptions are logged"""
        manager = HookManager()

        def failing_handler(event):
            raise ValueError("Test error")

        manager.subscribe("before_exec", failing_handler)

        event = BeforeExecEvent(
            execution_id="test-123",
            tool_id="test_tool",
            tool_name="Test Tool",
            timestamp=time.time(),
            params={},
        )

        manager.emit(event)

        # Check that error was logged
        assert any("Hook handler error" in record.message for record in caplog.records)


class TestClearSubscribers:
    """Test clearing subscribers"""

    def test_clear_subscribers_for_specific_event(self):
        """Test clearing subscribers for specific event type"""
        manager = HookManager()

        def handler(event):
            pass

        manager.subscribe("before_exec", handler)
        manager.subscribe("after_exec", handler)

        assert manager.get_subscriber_count("before_exec") == 1
        assert manager.get_subscriber_count("after_exec") == 1

        manager.clear_subscribers("before_exec")

        assert manager.get_subscriber_count("before_exec") == 0
        assert manager.get_subscriber_count("after_exec") == 1

    def test_clear_all_subscribers(self):
        """Test clearing all subscribers"""
        manager = HookManager()

        def handler(event):
            pass

        manager.subscribe("before_exec", handler)
        manager.subscribe("after_exec", handler)
        manager.subscribe("fail", handler)

        manager.clear_subscribers()

        assert manager.get_subscriber_count("before_exec") == 0
        assert manager.get_subscriber_count("after_exec") == 0
        assert manager.get_subscriber_count("fail") == 0


class TestThreadSafety:
    """Test thread safety"""

    def test_concurrent_subscriptions(self):
        """Test concurrent subscriptions are thread-safe"""
        manager = HookManager()
        errors = []

        def subscribe_handler(i):
            try:

                def handler(event):
                    pass

                handler.__name__ = f"handler_{i}"
                manager.subscribe("before_exec", handler)
            except Exception as e:
                errors.append(e)

        threads = []
        for i in range(10):
            t = threading.Thread(target=subscribe_handler, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        assert len(errors) == 0
        assert manager.get_subscriber_count("before_exec") == 10

    def test_concurrent_emissions(self):
        """Test concurrent emissions are thread-safe"""
        manager = HookManager()
        received_count = []
        lock = threading.Lock()

        def handler(event):
            with lock:
                received_count.append(1)

        manager.subscribe("before_exec", handler)

        def emit_event(i):
            event = BeforeExecEvent(
                execution_id=f"test-{i}",
                tool_id="test_tool",
                tool_name="Test Tool",
                timestamp=time.time(),
                params={},
            )
            manager.emit(event)

        threads = []
        for i in range(10):
            t = threading.Thread(target=emit_event, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        assert len(received_count) == 10
