#!/usr/bin/env python3
# Copyright (c) 2026 SlotAgent Contributors
# Licensed under the MIT License - see LICENSE file for details.
"""
Human-in-the-Loop Approval Workflow Example

This example demonstrates the complete approval workflow for high-risk operations.

Features demonstrated:
- GuardHumanInLoop plugin
- ApprovalManager lifecycle
- Hook-based approval notifications
- Approval, rejection, and timeout handling
- Production-ready approval patterns

Run this example:
    python examples/approval_workflow_example.py
"""

import time
import threading
from datetime import datetime

from slotagent.core import CoreScheduler, ApprovalManager, HookManager
from slotagent.plugins import SchemaDefault, GuardHumanInLoop, LogPlugin
from slotagent.types import Tool, ExecutionStatus, ApprovalStatus


# ============================================================================
# Define High-Risk Tools
# ============================================================================

def process_payment_refund(params):
    """Process a payment refund (high-risk operation)"""
    order_id = params['order_id']
    amount = params['amount']

    print(f"   💰 Processing refund: ${amount} for order {order_id}")

    return {
        'refund_id': 'REFUND-12345',
        'order_id': order_id,
        'amount': amount,
        'status': 'processed',
        'timestamp': time.time()
    }


def delete_user_data(params):
    """Delete user data (irreversible operation)"""
    user_id = params['user_id']

    print(f"   🗑️  Deleting data for user {user_id}")

    return {
        'user_id': user_id,
        'deleted': True,
        'records_deleted': 1234,
        'timestamp': time.time()
    }


def grant_admin_access(params):
    """Grant admin privileges to a user"""
    user_id = params['user_id']

    print(f"   🔐 Granting admin access to user {user_id}")

    return {
        'user_id': user_id,
        'role': 'admin',
        'granted': True,
        'timestamp': time.time()
    }


# ============================================================================
# Tool Definitions
# ============================================================================

PAYMENT_REFUND_TOOL = Tool(
    tool_id='payment_refund',
    name='Payment Refund',
    description='Process a payment refund to customer',
    input_schema={
        'type': 'object',
        'properties': {
            'order_id': {'type': 'string'},
            'amount': {'type': 'number', 'minimum': 0}
        },
        'required': ['order_id', 'amount']
    },
    execute_func=process_payment_refund,
    metadata={'risk_level': 'high', 'category': 'financial'}
)

DELETE_USER_TOOL = Tool(
    tool_id='delete_user_data',
    name='Delete User Data',
    description='Permanently delete all user data (GDPR compliance)',
    input_schema={
        'type': 'object',
        'properties': {
            'user_id': {'type': 'string'},
            'confirmation': {'type': 'string'}
        },
        'required': ['user_id', 'confirmation']
    },
    execute_func=delete_user_data,
    metadata={'risk_level': 'critical', 'category': 'data_management'}
)

GRANT_ADMIN_TOOL = Tool(
    tool_id='grant_admin_access',
    name='Grant Admin Access',
    description='Grant administrator privileges to a user',
    input_schema={
        'type': 'object',
        'properties': {
            'user_id': {'type': 'string'},
            'justification': {'type': 'string'}
        },
        'required': ['user_id']
    },
    execute_func=grant_admin_access,
    metadata={'risk_level': 'high', 'category': 'access_control'}
)


# ============================================================================
# Approval Notification System
# ============================================================================

class ApprovalNotificationSystem:
    """Simulates an approval notification system (email, Slack, etc.)"""

    def __init__(self):
        self.pending_approvals = {}

    def notify_approvers(self, event):
        """
        Notification handler for wait_approval event.

        In production, this would:
        - Send email to approvers
        - Post to Slack channel
        - Create notification in web UI
        - Record in audit log
        """
        approval_id = event.approval_id
        tool_id = event.tool_id
        tool_name = event.tool_name
        params = event.params

        # Store approval request
        self.pending_approvals[approval_id] = {
            'execution_id': event.execution_id,
            'tool_id': tool_id,
            'tool_name': tool_name,
            'params': params,
            'requested_at': datetime.fromtimestamp(event.timestamp).isoformat()
        }

        # Simulate notification
        print(f"\n" + "="*70)
        print("📬 APPROVAL REQUEST NOTIFICATION")
        print("="*70)
        print(f"Approval ID: {approval_id}")
        print(f"Tool: {tool_name} ({tool_id})")
        print(f"Parameters: {params}")
        print(f"Requested at: {self.pending_approvals[approval_id]['requested_at']}")
        print("\nActions:")
        print("  - Approve: approval_manager.approve(approval_id, approver='...')")
        print("  - Reject: approval_manager.reject(approval_id, approver='...', reason='...')")
        print("="*70)

    def get_pending(self):
        """Get list of pending approvals"""
        return list(self.pending_approvals.keys())


# ============================================================================
# Timeout Monitor
# ============================================================================

class TimeoutMonitor:
    """Background thread to monitor approval timeouts"""

    def __init__(self, approval_manager, check_interval=1.0):
        self.approval_manager = approval_manager
        self.check_interval = check_interval
        self.running = False
        self.thread = None

    def start(self):
        """Start monitoring in background thread"""
        self.running = True
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()
        print(f"⏰ Timeout monitor started (checking every {self.check_interval}s)")

    def stop(self):
        """Stop monitoring"""
        self.running = False
        if self.thread:
            self.thread.join()

    def _monitor_loop(self):
        """Monitor loop (runs in background)"""
        while self.running:
            expired_ids = self.approval_manager.check_timeouts()

            for approval_id in expired_ids:
                record = self.approval_manager.get_approval(approval_id)
                print(f"\n⏱️  TIMEOUT: Approval {approval_id} for tool '{record.tool_id}' timed out")

            time.sleep(self.check_interval)


# ============================================================================
# Examples
# ============================================================================

def example_1_basic_approval_flow():
    """Example 1: Basic approval workflow - approve path"""
    print("\n" + "=" * 70)
    print("Example 1: Basic Approval Flow (Approve)")
    print("=" * 70)

    # Setup
    approval_manager = ApprovalManager(default_timeout=300.0)  # 5 min
    hook_manager = HookManager()
    notification_system = ApprovalNotificationSystem()

    # Subscribe to approval events
    hook_manager.subscribe('wait_approval', notification_system.notify_approvers)

    # Create scheduler with approval plugin
    scheduler = CoreScheduler(hook_manager=hook_manager)
    scheduler.plugin_pool.register_global_plugin(
        GuardHumanInLoop(approval_manager=approval_manager)
    )
    scheduler.plugin_pool.register_global_plugin(LogPlugin())

    scheduler.register_tool(PAYMENT_REFUND_TOOL)

    # Execute tool (triggers approval)
    print("\n--- Executing High-Risk Tool ---")
    context = scheduler.execute('payment_refund', {
        'order_id': 'ORD-98765',
        'amount': 1500.00
    })

    print(f"\nExecution Status: {context.status}")
    print(f"Approval ID: {context.approval_id}")

    # Simulate approver reviewing and approving
    print("\n--- Approver Reviews Request ---")
    time.sleep(1)  # Simulate review time

    approval_id = context.approval_id
    record = approval_manager.approve(approval_id, approver='finance_manager@company.com')

    print(f"\n✅ APPROVED")
    print(f"   Approver: {record.approver}")
    print(f"   Approved at: {datetime.fromtimestamp(record.approved_at).isoformat()}")
    print(f"   Status: {record.status}")


def example_2_rejection_flow():
    """Example 2: Approval workflow - reject path"""
    print("\n" + "=" * 70)
    print("Example 2: Approval Flow (Reject)")
    print("=" * 70)

    # Setup
    approval_manager = ApprovalManager(default_timeout=300.0)
    hook_manager = HookManager()
    notification_system = ApprovalNotificationSystem()

    hook_manager.subscribe('wait_approval', notification_system.notify_approvers)

    scheduler = CoreScheduler(hook_manager=hook_manager)
    scheduler.plugin_pool.register_global_plugin(
        GuardHumanInLoop(approval_manager=approval_manager)
    )

    scheduler.register_tool(GRANT_ADMIN_TOOL)

    # Execute tool
    print("\n--- Requesting Admin Access Grant ---")
    context = scheduler.execute('grant_admin_access', {
        'user_id': 'user@example.com',
        'justification': 'Need temporary access for testing'
    })

    print(f"\nExecution Status: {context.status}")

    # Approver rejects
    print("\n--- Approver Rejects Request ---")
    time.sleep(0.5)

    approval_id = context.approval_id
    record = approval_manager.reject(
        approval_id,
        approver='security_admin@company.com',
        reason='Insufficient justification; permanent access not appropriate for testing'
    )

    print(f"\n❌ REJECTED")
    print(f"   Approver: {record.approver}")
    print(f"   Reason: {record.reject_reason}")
    print(f"   Rejected at: {datetime.fromtimestamp(record.rejected_at).isoformat()}")


def example_3_timeout_handling():
    """Example 3: Approval timeout handling"""
    print("\n" + "=" * 70)
    print("Example 3: Approval Timeout")
    print("=" * 70)

    # Setup with short timeout for demonstration
    approval_manager = ApprovalManager(default_timeout=2.0)  # 2 seconds
    hook_manager = HookManager()
    notification_system = ApprovalNotificationSystem()

    hook_manager.subscribe('wait_approval', notification_system.notify_approvers)

    # Start timeout monitor
    monitor = TimeoutMonitor(approval_manager, check_interval=0.5)
    monitor.start()

    scheduler = CoreScheduler(hook_manager=hook_manager)
    scheduler.plugin_pool.register_global_plugin(
        GuardHumanInLoop(approval_manager=approval_manager, timeout=2.0)
    )

    scheduler.register_tool(DELETE_USER_TOOL)

    # Execute tool
    print("\n--- Requesting User Data Deletion ---")
    context = scheduler.execute('delete_user_data', {
        'user_id': 'user123',
        'confirmation': 'DELETE'
    })

    print(f"\nExecution Status: {context.status}")
    print(f"Approval ID: {context.approval_id}")

    # Wait for timeout
    print("\n--- Waiting for timeout (2 seconds) ---")
    time.sleep(2.5)

    # Check status
    record = approval_manager.get_approval(context.approval_id)
    print(f"\n⏱️  TIMED OUT")
    print(f"   Status: {record.status}")
    print(f"   Reason: {record.reject_reason}")

    monitor.stop()


def example_4_multiple_pending_approvals():
    """Example 4: Managing multiple pending approvals"""
    print("\n" + "=" * 70)
    print("Example 4: Multiple Pending Approvals")
    print("=" * 70)

    # Setup
    approval_manager = ApprovalManager(default_timeout=300.0)
    hook_manager = HookManager()
    notification_system = ApprovalNotificationSystem()

    hook_manager.subscribe('wait_approval', notification_system.notify_approvers)

    scheduler = CoreScheduler(hook_manager=hook_manager)
    scheduler.plugin_pool.register_global_plugin(
        GuardHumanInLoop(approval_manager=approval_manager)
    )

    # Register multiple tools
    scheduler.register_tool(PAYMENT_REFUND_TOOL)
    scheduler.register_tool(DELETE_USER_TOOL)
    scheduler.register_tool(GRANT_ADMIN_TOOL)

    # Execute multiple tools
    print("\n--- Executing Multiple High-Risk Operations ---")

    contexts = []

    # Operation 1
    ctx1 = scheduler.execute('payment_refund', {'order_id': 'ORD-001', 'amount': 500})
    contexts.append(ctx1)

    # Operation 2
    ctx2 = scheduler.execute('delete_user_data', {'user_id': 'user456', 'confirmation': 'DELETE'})
    contexts.append(ctx2)

    # Operation 3
    ctx3 = scheduler.execute('grant_admin_access', {'user_id': 'newadmin@company.com'})
    contexts.append(ctx3)

    # List all pending approvals
    print(f"\n--- Pending Approvals ---")
    pending = approval_manager.list_pending()
    print(f"Total pending: {len(pending)}")

    for i, record in enumerate(pending, 1):
        print(f"\n{i}. Approval ID: {record.approval_id}")
        print(f"   Tool: {record.tool_name}")
        print(f"   Params: {record.params}")
        print(f"   Created: {datetime.fromtimestamp(record.created_at).isoformat()}")

    # Approve first two, reject third
    print("\n--- Processing Approvals ---")

    approval_manager.approve(pending[0].approval_id, approver='finance@company.com')
    print(f"✅ Approved: {pending[0].tool_name}")

    approval_manager.approve(pending[1].approval_id, approver='data_admin@company.com')
    print(f"✅ Approved: {pending[1].tool_name}")

    approval_manager.reject(
        pending[2].approval_id,
        approver='security@company.com',
        reason='Approval process incomplete'
    )
    print(f"❌ Rejected: {pending[2].tool_name}")

    # Check final state
    remaining_pending = approval_manager.list_pending()
    print(f"\nRemaining pending approvals: {len(remaining_pending)}")


def example_5_production_pattern():
    """Example 5: Production-ready approval pattern"""
    print("\n" + "=" * 70)
    print("Example 5: Production Pattern (Simulated)")
    print("=" * 70)

    print("""
This example demonstrates a production-ready approval pattern:

1. Approval request created → stored in database
2. Notification sent to approvers (email/Slack/etc.)
3. Approver reviews in web UI
4. Approval/rejection triggers callback → updates execution
5. Audit log records all actions
6. Background task monitors timeouts

Code structure:
    """)

    code = """
# Production setup
approval_manager = ApprovalManager(default_timeout=600.0)  # 10 min
hook_manager = HookManager()

# Hook: Store in database
def store_approval_request(event):
    db.approvals.insert({
        'approval_id': event.approval_id,
        'tool_id': event.tool_id,
        'params': event.params,
        'status': 'pending',
        'created_at': event.timestamp
    })

# Hook: Send notifications
def notify_approvers(event):
    approvers = get_approvers_for_tool(event.tool_id)
    for approver in approvers:
        send_email(approver, event.approval_id, event.tool_id)
        send_slack_notification(approver, event.approval_id)

# Hook: Audit logging
def audit_log_approval(event):
    audit_logger.info({
        'event': 'approval_requested',
        'approval_id': event.approval_id,
        'tool_id': event.tool_id,
        'params': event.params
    })

# Subscribe hooks
hook_manager.subscribe('wait_approval', store_approval_request)
hook_manager.subscribe('wait_approval', notify_approvers)
hook_manager.subscribe('wait_approval', audit_log_approval)

# Background timeout checker (Celery/APScheduler)
@celery.task
def check_approval_timeouts():
    expired = approval_manager.check_timeouts()
    for approval_id in expired:
        db.approvals.update(approval_id, {'status': 'timeout'})
        notify_timeout(approval_id)

# Web API endpoint for approvers
@app.post('/api/approvals/{approval_id}/approve')
def approve_request(approval_id: str, approver: str):
    record = approval_manager.approve(approval_id, approver)
    db.approvals.update(approval_id, {'status': 'approved', 'approver': approver})
    audit_logger.info({'event': 'approved', 'approval_id': approval_id})
    return {'status': 'success', 'record': record}
    """

    print(code)

    print("\nKey components:")
    print("  ✓ Database persistence (PostgreSQL/MongoDB)")
    print("  ✓ Notification system (Email/Slack/Teams)")
    print("  ✓ Web UI for approvers")
    print("  ✓ Audit logging")
    print("  ✓ Background timeout monitoring")
    print("  ✓ RESTful API for approval actions")


# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    """Run all examples"""
    print("\n")
    print("█" * 70)
    print("█" + " " * 68 + "█")
    print("█" + " " * 14 + "Human-in-the-Loop Approval Workflow" + " " * 19 + "█")
    print("█" + " " * 68 + "█")
    print("█" * 70)

    try:
        example_1_basic_approval_flow()
        example_2_rejection_flow()
        example_3_timeout_handling()
        example_4_multiple_pending_approvals()
        example_5_production_pattern()

        print("\n" + "=" * 70)
        print("✅ All examples completed successfully!")
        print("=" * 70 + "\n")

    except Exception as e:
        print(f"\n❌ Error running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
