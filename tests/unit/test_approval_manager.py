# Copyright (c) 2026 SlotAgent Contributors
# Licensed under the MIT License - see LICENSE file for details.
"""
Unit tests for ApprovalManager.
"""

import pytest
import time
import threading

from slotagent.core.approval_manager import ApprovalManager
from slotagent.types import ApprovalStatus, ApprovalRecord


class TestApprovalManagerCreation:
    """Test ApprovalManager initialization"""

    def test_approval_manager_creation(self):
        """Test creating ApprovalManager"""
        manager = ApprovalManager()
        assert manager is not None

    def test_approval_manager_with_custom_timeout(self):
        """Test creating ApprovalManager with custom timeout"""
        manager = ApprovalManager(default_timeout=600.0)
        assert manager._default_timeout == 600.0


class TestCreateApproval:
    """Test approval creation"""

    def test_create_approval_basic(self):
        """Test creating basic approval request"""
        manager = ApprovalManager()

        approval_id = manager.create_approval(
            execution_id="exec-123",
            tool_id="test_tool",
            tool_name="Test Tool",
            params={"key": "value"}
        )

        assert approval_id is not None
        assert isinstance(approval_id, str)
        assert len(approval_id) > 0

    def test_create_approval_returns_record(self):
        """Test that created approval can be retrieved"""
        manager = ApprovalManager()

        approval_id = manager.create_approval(
            execution_id="exec-123",
            tool_id="test_tool",
            tool_name="Test Tool",
            params={"key": "value"}
        )

        record = manager.get_approval(approval_id)
        assert record is not None
        assert record.approval_id == approval_id
        assert record.status == ApprovalStatus.PENDING
        assert record.execution_id == "exec-123"
        assert record.tool_id == "test_tool"
        assert record.tool_name == "Test Tool"
        assert record.params == {"key": "value"}

    def test_create_approval_with_custom_timeout(self):
        """Test creating approval with custom timeout"""
        manager = ApprovalManager(default_timeout=300.0)

        approval_id = manager.create_approval(
            execution_id="exec-123",
            tool_id="test_tool",
            tool_name="Test Tool",
            params={},
            timeout=600.0  # Custom timeout
        )

        record = manager.get_approval(approval_id)
        # timeout_at should be created_at + 600
        assert abs((record.timeout_at - record.created_at) - 600.0) < 0.1

    def test_create_approval_with_metadata(self):
        """Test creating approval with metadata"""
        manager = ApprovalManager()

        approval_id = manager.create_approval(
            execution_id="exec-123",
            tool_id="test_tool",
            tool_name="Test Tool",
            params={},
            metadata={"risk_level": "high", "amount": 1000}
        )

        record = manager.get_approval(approval_id)
        assert record.metadata == {"risk_level": "high", "amount": 1000}


class TestApproveApproval:
    """Test approval operations"""

    def test_approve_pending_approval(self):
        """Test approving a pending approval"""
        manager = ApprovalManager()

        approval_id = manager.create_approval(
            execution_id="exec-123",
            tool_id="test_tool",
            tool_name="Test Tool",
            params={}
        )

        record = manager.approve(approval_id, approver="user@example.com")

        assert record.status == ApprovalStatus.APPROVED
        assert record.approver == "user@example.com"
        assert record.approved_at is not None
        assert record.approved_at >= record.created_at

    def test_approve_nonexistent_approval_raises_error(self):
        """Test approving non-existent approval raises error"""
        manager = ApprovalManager()

        with pytest.raises(ValueError, match="not found"):
            manager.approve("nonexistent-id", approver="user@example.com")

    def test_approve_already_approved_raises_error(self):
        """Test approving already approved request raises error"""
        manager = ApprovalManager()

        approval_id = manager.create_approval(
            execution_id="exec-123",
            tool_id="test_tool",
            tool_name="Test Tool",
            params={}
        )

        manager.approve(approval_id, approver="user1@example.com")

        with pytest.raises(ValueError, match="not in PENDING status"):
            manager.approve(approval_id, approver="user2@example.com")

    def test_approve_rejected_approval_raises_error(self):
        """Test approving rejected request raises error"""
        manager = ApprovalManager()

        approval_id = manager.create_approval(
            execution_id="exec-123",
            tool_id="test_tool",
            tool_name="Test Tool",
            params={}
        )

        manager.reject(approval_id, approver="user@example.com", reason="Test")

        with pytest.raises(ValueError, match="not in PENDING status"):
            manager.approve(approval_id, approver="user@example.com")


class TestRejectApproval:
    """Test rejection operations"""

    def test_reject_pending_approval(self):
        """Test rejecting a pending approval"""
        manager = ApprovalManager()

        approval_id = manager.create_approval(
            execution_id="exec-123",
            tool_id="test_tool",
            tool_name="Test Tool",
            params={}
        )

        record = manager.reject(
            approval_id,
            approver="user@example.com",
            reason="Insufficient justification"
        )

        assert record.status == ApprovalStatus.REJECTED
        assert record.approver == "user@example.com"
        assert record.reject_reason == "Insufficient justification"
        assert record.rejected_at is not None
        assert record.rejected_at >= record.created_at

    def test_reject_nonexistent_approval_raises_error(self):
        """Test rejecting non-existent approval raises error"""
        manager = ApprovalManager()

        with pytest.raises(ValueError, match="not found"):
            manager.reject("nonexistent-id", approver="user@example.com", reason="Test")

    def test_reject_already_approved_raises_error(self):
        """Test rejecting approved request raises error"""
        manager = ApprovalManager()

        approval_id = manager.create_approval(
            execution_id="exec-123",
            tool_id="test_tool",
            tool_name="Test Tool",
            params={}
        )

        manager.approve(approval_id, approver="user@example.com")

        with pytest.raises(ValueError, match="not in PENDING status"):
            manager.reject(approval_id, approver="user@example.com", reason="Test")


class TestGetApproval:
    """Test getting approval records"""

    def test_get_existing_approval(self):
        """Test getting existing approval"""
        manager = ApprovalManager()

        approval_id = manager.create_approval(
            execution_id="exec-123",
            tool_id="test_tool",
            tool_name="Test Tool",
            params={"key": "value"}
        )

        record = manager.get_approval(approval_id)
        assert record is not None
        assert record.approval_id == approval_id

    def test_get_nonexistent_approval_returns_none(self):
        """Test getting non-existent approval returns None"""
        manager = ApprovalManager()

        record = manager.get_approval("nonexistent-id")
        assert record is None


class TestCheckTimeouts:
    """Test timeout checking"""

    def test_check_timeouts_marks_expired_approvals(self):
        """Test that check_timeouts marks expired approvals"""
        manager = ApprovalManager(default_timeout=0.1)  # 100ms timeout

        approval_id = manager.create_approval(
            execution_id="exec-123",
            tool_id="test_tool",
            tool_name="Test Tool",
            params={}
        )

        # Wait for timeout
        time.sleep(0.2)

        expired_ids = manager.check_timeouts()

        assert approval_id in expired_ids
        record = manager.get_approval(approval_id)
        assert record.status == ApprovalStatus.TIMEOUT

    def test_check_timeouts_does_not_mark_valid_approvals(self):
        """Test that check_timeouts doesn't mark valid approvals"""
        manager = ApprovalManager(default_timeout=10.0)

        approval_id = manager.create_approval(
            execution_id="exec-123",
            tool_id="test_tool",
            tool_name="Test Tool",
            params={}
        )

        expired_ids = manager.check_timeouts()

        assert approval_id not in expired_ids
        record = manager.get_approval(approval_id)
        assert record.status == ApprovalStatus.PENDING

    def test_check_timeouts_does_not_mark_approved(self):
        """Test that check_timeouts doesn't mark approved approvals"""
        manager = ApprovalManager(default_timeout=0.1)

        approval_id = manager.create_approval(
            execution_id="exec-123",
            tool_id="test_tool",
            tool_name="Test Tool",
            params={}
        )

        # Approve before timeout
        manager.approve(approval_id, approver="user@example.com")

        # Wait for would-be timeout
        time.sleep(0.2)

        expired_ids = manager.check_timeouts()

        assert approval_id not in expired_ids
        record = manager.get_approval(approval_id)
        assert record.status == ApprovalStatus.APPROVED


class TestListPending:
    """Test listing pending approvals"""

    def test_list_pending_returns_only_pending(self):
        """Test that list_pending returns only pending approvals"""
        manager = ApprovalManager()

        id1 = manager.create_approval("exec-1", "tool1", "Tool 1", {})
        id2 = manager.create_approval("exec-2", "tool2", "Tool 2", {})
        id3 = manager.create_approval("exec-3", "tool3", "Tool 3", {})

        # Approve one
        manager.approve(id1, approver="user@example.com")

        # Reject one
        manager.reject(id2, approver="user@example.com", reason="Test")

        # List pending
        pending = manager.list_pending()

        assert len(pending) == 1
        assert pending[0].approval_id == id3
        assert pending[0].status == ApprovalStatus.PENDING

    def test_list_pending_empty_when_none(self):
        """Test that list_pending returns empty list when no pending"""
        manager = ApprovalManager()

        pending = manager.list_pending()
        assert len(pending) == 0


class TestThreadSafety:
    """Test thread safety"""

    def test_concurrent_creates(self):
        """Test concurrent approval creates are thread-safe"""
        manager = ApprovalManager()
        created_ids = []
        lock = threading.Lock()

        def create_approval(i):
            approval_id = manager.create_approval(
                execution_id=f"exec-{i}",
                tool_id=f"tool{i}",
                tool_name=f"Tool {i}",
                params={}
            )
            with lock:
                created_ids.append(approval_id)

        threads = []
        for i in range(10):
            t = threading.Thread(target=create_approval, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        assert len(created_ids) == 10
        assert len(set(created_ids)) == 10  # All unique

    def test_concurrent_approve_reject(self):
        """Test concurrent approve/reject operations"""
        manager = ApprovalManager()

        approval_id = manager.create_approval(
            execution_id="exec-123",
            tool_id="test_tool",
            tool_name="Test Tool",
            params={}
        )

        results = []
        lock = threading.Lock()

        def try_approve():
            try:
                manager.approve(approval_id, approver="approver")
                with lock:
                    results.append("approved")
            except ValueError:
                with lock:
                    results.append("error")

        def try_reject():
            try:
                manager.reject(approval_id, approver="rejector", reason="Test")
                with lock:
                    results.append("rejected")
            except ValueError:
                with lock:
                    results.append("error")

        # Start threads simultaneously
        t1 = threading.Thread(target=try_approve)
        t2 = threading.Thread(target=try_reject)

        t1.start()
        t2.start()

        t1.join()
        t2.join()

        # One should succeed, one should fail
        assert len(results) == 2
        assert ("approved" in results and "error" in results) or \
               ("rejected" in results and "error" in results)
