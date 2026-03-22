# Copyright (c) 2026 SlotAgent Contributors
# Licensed under the MIT License - see LICENSE file for details.
"""
ApprovalManager - Approval lifecycle management.

Manages approval requests, state transitions, and timeout checking.
Thread-safe implementation for concurrent operations.
"""

import threading
import time
import uuid
from typing import Dict, List, Optional

from slotagent.types import ApprovalRecord, ApprovalStatus


class ApprovalManager:
    """
    Approval manager for managing approval lifecycle.

    Thread-safe implementation for concurrent approval operations.

    Examples:
        >>> manager = ApprovalManager(default_timeout=300.0)
        >>> approval_id = manager.create_approval(
        ...     execution_id="exec-123",
        ...     tool_id="payment_refund",
        ...     tool_name="Payment Refund",
        ...     params={"amount": 100}
        ... )
        >>> manager.approve(approval_id, approver="admin@example.com")
    """

    def __init__(self, default_timeout: float = 300.0):
        """
        Initialize ApprovalManager.

        Args:
            default_timeout: Default approval timeout in seconds (default: 5 min)
        """
        self._approvals: Dict[str, ApprovalRecord] = {}
        self._lock = threading.Lock()
        self._default_timeout = default_timeout

    def create_approval(
        self,
        execution_id: str,
        tool_id: str,
        tool_name: str,
        params: Dict,
        timeout: Optional[float] = None,
        metadata: Optional[Dict] = None
    ) -> str:
        """
        Create an approval request.

        Args:
            execution_id: Execution ID
            tool_id: Tool identifier
            tool_name: Tool name
            params: Tool parameters
            timeout: Custom timeout (seconds), uses default if None
            metadata: Additional approval context

        Returns:
            approval_id: Generated approval ID (UUID)

        Postconditions:
            - New ApprovalRecord created with status=PENDING
            - Record stored in _approvals

        Examples:
            >>> approval_id = manager.create_approval(
            ...     execution_id="exec-123",
            ...     tool_id="test_tool",
            ...     tool_name="Test Tool",
            ...     params={"key": "value"}
            ... )
        """
        approval_id = str(uuid.uuid4())
        created_at = time.time()
        timeout_seconds = timeout if timeout is not None else self._default_timeout
        timeout_at = created_at + timeout_seconds

        record = ApprovalRecord(
            approval_id=approval_id,
            status=ApprovalStatus.PENDING,
            execution_id=execution_id,
            tool_id=tool_id,
            tool_name=tool_name,
            params=params.copy() if params else {},
            created_at=created_at,
            timeout_at=timeout_at,
            metadata=metadata.copy() if metadata else None
        )

        with self._lock:
            self._approvals[approval_id] = record

        return approval_id

    def approve(
        self,
        approval_id: str,
        approver: str
    ) -> ApprovalRecord:
        """
        Approve an approval request.

        Args:
            approval_id: Approval ID
            approver: Approver identifier

        Returns:
            Updated ApprovalRecord

        Raises:
            ValueError: If approval_id not found
            ValueError: If approval is not in PENDING status

        Postconditions:
            - status changed to APPROVED
            - approved_at set to current timestamp
            - approver recorded

        Examples:
            >>> record = manager.approve(approval_id, approver="admin@example.com")
        """
        with self._lock:
            if approval_id not in self._approvals:
                raise ValueError(f"Approval {approval_id} not found")

            record = self._approvals[approval_id]

            if record.status != ApprovalStatus.PENDING:
                raise ValueError(
                    f"Approval {approval_id} is not in PENDING status "
                    f"(current: {record.status})"
                )

            # Update record (create new instance for immutability)
            updated_record = ApprovalRecord(
                approval_id=record.approval_id,
                status=ApprovalStatus.APPROVED,
                execution_id=record.execution_id,
                tool_id=record.tool_id,
                tool_name=record.tool_name,
                params=record.params,
                created_at=record.created_at,
                timeout_at=record.timeout_at,
                approved_at=time.time(),
                approver=approver,
                metadata=record.metadata
            )

            self._approvals[approval_id] = updated_record
            return updated_record

    def reject(
        self,
        approval_id: str,
        approver: str,
        reason: str
    ) -> ApprovalRecord:
        """
        Reject an approval request.

        Args:
            approval_id: Approval ID
            approver: Approver identifier
            reason: Rejection reason

        Returns:
            Updated ApprovalRecord

        Raises:
            ValueError: If approval_id not found
            ValueError: If approval is not in PENDING status

        Postconditions:
            - status changed to REJECTED
            - rejected_at set to current timestamp
            - approver and reject_reason recorded

        Examples:
            >>> record = manager.reject(
            ...     approval_id,
            ...     approver="admin@example.com",
            ...     reason="Insufficient justification"
            ... )
        """
        with self._lock:
            if approval_id not in self._approvals:
                raise ValueError(f"Approval {approval_id} not found")

            record = self._approvals[approval_id]

            if record.status != ApprovalStatus.PENDING:
                raise ValueError(
                    f"Approval {approval_id} is not in PENDING status "
                    f"(current: {record.status})"
                )

            # Update record
            updated_record = ApprovalRecord(
                approval_id=record.approval_id,
                status=ApprovalStatus.REJECTED,
                execution_id=record.execution_id,
                tool_id=record.tool_id,
                tool_name=record.tool_name,
                params=record.params,
                created_at=record.created_at,
                timeout_at=record.timeout_at,
                rejected_at=time.time(),
                approver=approver,
                reject_reason=reason,
                metadata=record.metadata
            )

            self._approvals[approval_id] = updated_record
            return updated_record

    def get_approval(self, approval_id: str) -> Optional[ApprovalRecord]:
        """
        Get approval record by ID.

        Args:
            approval_id: Approval ID

        Returns:
            ApprovalRecord if found, None otherwise

        Examples:
            >>> record = manager.get_approval(approval_id)
            >>> if record:
            ...     print(f"Status: {record.status}")
        """
        with self._lock:
            return self._approvals.get(approval_id)

    def check_timeouts(self) -> List[str]:
        """
        Check for timed-out approvals and mark them.

        Returns:
            List of approval_ids that were marked as timeout

        Postconditions:
            - All PENDING approvals past timeout_at are marked TIMEOUT

        Examples:
            >>> expired_ids = manager.check_timeouts()
            >>> for approval_id in expired_ids:
            ...     print(f"Approval {approval_id} timed out")
        """
        current_time = time.time()
        expired_ids = []

        with self._lock:
            for approval_id, record in self._approvals.items():
                # Only mark PENDING approvals that have timed out
                if (record.status == ApprovalStatus.PENDING and
                        current_time > record.timeout_at):

                    # Update to TIMEOUT status
                    updated_record = ApprovalRecord(
                        approval_id=record.approval_id,
                        status=ApprovalStatus.TIMEOUT,
                        execution_id=record.execution_id,
                        tool_id=record.tool_id,
                        tool_name=record.tool_name,
                        params=record.params,
                        created_at=record.created_at,
                        timeout_at=record.timeout_at,
                        rejected_at=current_time,  # Use current time as rejection time
                        reject_reason="Approval request timed out",
                        metadata=record.metadata
                    )

                    self._approvals[approval_id] = updated_record
                    expired_ids.append(approval_id)

        return expired_ids

    def list_pending(self) -> List[ApprovalRecord]:
        """
        List all pending approvals.

        Returns:
            List of ApprovalRecords with status=PENDING

        Examples:
            >>> pending = manager.list_pending()
            >>> for approval in pending:
            ...     print(f"{approval.tool_name}: {approval.approval_id}")
        """
        with self._lock:
            return [
                record for record in self._approvals.values()
                if record.status == ApprovalStatus.PENDING
            ]
