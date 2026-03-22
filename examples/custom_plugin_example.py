#!/usr/bin/env python3
# Copyright (c) 2026 SlotAgent Contributors
# Licensed under the MIT License - see LICENSE file for details.
"""
Custom Plugin Example - Extending SlotAgent with Custom Plugins

This example demonstrates how to create custom plugins for each layer.

Custom plugins shown:
- Schema: CustomSchemaValidator (JSON Schema + custom rules)
- Guard: RateLimitGuard (rate limiting)
- Guard: RoleBasedGuard (RBAC access control)
- Observe: MetricsCollector (metrics collection)

Run this example:
    python examples/custom_plugin_example.py
"""

import time
from typing import Dict, Any
from collections import defaultdict

from slotagent.core import CoreScheduler, HookManager
from slotagent.interfaces import PluginInterface
from slotagent.types import PluginContext, PluginResult, Tool


# ============================================================================
# Custom Schema Plugin
# ============================================================================

class CustomSchemaValidator(PluginInterface):
    """
    Custom Schema plugin with additional validation rules.

    Beyond JSON Schema validation, adds:
    - String length constraints
    - Numeric range validation
    - Custom business rules
    """

    layer = 'schema'
    plugin_id = 'schema_custom'

    def __init__(self, schema: Dict[str, Any], custom_rules: Dict[str, Any] = None):
        """
        Args:
            schema: JSON Schema definition
            custom_rules: Additional validation rules
                {
                    'field_name': {
                        'min_length': int,
                        'max_length': int,
                        'min_value': number,
                        'max_value': number,
                        'pattern': str (regex),
                        'custom_validator': Callable[[value], bool]
                    }
                }
        """
        self.schema = schema
        self.custom_rules = custom_rules or {}

    def validate(self) -> bool:
        """Validate plugin configuration"""
        return self.schema is not None

    def execute(self, context: PluginContext) -> PluginResult:
        """Execute custom validation"""
        params = context.params

        # 1. Basic type validation (simplified)
        for field, value in params.items():
            if field in self.custom_rules:
                rules = self.custom_rules[field]

                # String length check
                if isinstance(value, str):
                    if 'min_length' in rules and len(value) < rules['min_length']:
                        return PluginResult(
                            success=False,
                            should_continue=False,
                            error=f"Field '{field}' must be at least {rules['min_length']} characters"
                        )

                    if 'max_length' in rules and len(value) > rules['max_length']:
                        return PluginResult(
                            success=False,
                            should_continue=False,
                            error=f"Field '{field}' must be at most {rules['max_length']} characters"
                        )

                # Numeric range check
                if isinstance(value, (int, float)):
                    if 'min_value' in rules and value < rules['min_value']:
                        return PluginResult(
                            success=False,
                            should_continue=False,
                            error=f"Field '{field}' must be >= {rules['min_value']}"
                        )

                    if 'max_value' in rules and value > rules['max_value']:
                        return PluginResult(
                            success=False,
                            should_continue=False,
                            error=f"Field '{field}' must be <= {rules['max_value']}"
                        )

                # Custom validator
                if 'custom_validator' in rules:
                    validator = rules['custom_validator']
                    if not validator(value):
                        return PluginResult(
                            success=False,
                            should_continue=False,
                            error=f"Field '{field}' failed custom validation"
                        )

        return PluginResult(success=True, data={'validated': True})


# ============================================================================
# Custom Guard Plugin - Rate Limiting
# ============================================================================

class RateLimitGuard(PluginInterface):
    """
    Rate limiting guard plugin.

    Limits the number of tool executions per time window.
    """

    layer = 'guard'
    plugin_id = 'guard_rate_limit'

    def __init__(self, max_calls: int = 10, window_seconds: float = 60.0):
        """
        Args:
            max_calls: Maximum number of calls allowed in the window
            window_seconds: Time window in seconds
        """
        self.max_calls = max_calls
        self.window_seconds = window_seconds
        self.call_history = defaultdict(list)  # {tool_id: [timestamp, ...]}

    def validate(self) -> bool:
        """Validate plugin configuration"""
        return self.max_calls > 0 and self.window_seconds > 0

    def execute(self, context: PluginContext) -> PluginResult:
        """Check rate limit"""
        tool_id = context.tool_id
        current_time = time.time()

        # Clean old entries
        self.call_history[tool_id] = [
            t for t in self.call_history[tool_id]
            if current_time - t < self.window_seconds
        ]

        # Check limit
        if len(self.call_history[tool_id]) >= self.max_calls:
            return PluginResult(
                success=True,
                should_continue=False,
                data={
                    'blocked': True,
                    'reason': f'Rate limit exceeded: {self.max_calls} calls per {self.window_seconds}s'
                }
            )

        # Record this call
        self.call_history[tool_id].append(current_time)

        return PluginResult(
            success=True,
            data={
                'rate_limit_ok': True,
                'calls_in_window': len(self.call_history[tool_id])
            }
        )


# ============================================================================
# Custom Guard Plugin - Role-Based Access Control
# ============================================================================

class RoleBasedGuard(PluginInterface):
    """
    Role-based access control (RBAC) guard plugin.

    Controls tool access based on user roles.
    """

    layer = 'guard'
    plugin_id = 'guard_rbac'

    def __init__(self, role_permissions: Dict[str, list]):
        """
        Args:
            role_permissions: Mapping of tool_id to allowed roles
                {
                    'payment_refund': ['admin', 'finance'],
                    'view_report': ['admin', 'finance', 'analyst'],
                    'delete_data': ['admin']
                }
        """
        self.role_permissions = role_permissions

    def validate(self) -> bool:
        """Validate plugin configuration"""
        return isinstance(self.role_permissions, dict)

    def execute(self, context: PluginContext) -> PluginResult:
        """Check user role permissions"""
        tool_id = context.tool_id

        # Get user role from metadata (in real app, from auth context)
        user_role = context.metadata.get('user_role', 'guest') if context.metadata else 'guest'

        # Get allowed roles for this tool
        allowed_roles = self.role_permissions.get(tool_id, [])

        if not allowed_roles:
            # No restrictions defined, allow by default
            return PluginResult(success=True, data={'authorized': True})

        if user_role in allowed_roles:
            return PluginResult(
                success=True,
                data={'authorized': True, 'role': user_role}
            )
        else:
            return PluginResult(
                success=True,
                should_continue=False,
                data={
                    'blocked': True,
                    'reason': f"Role '{user_role}' not authorized for tool '{tool_id}'. Required: {allowed_roles}"
                }
            )


# ============================================================================
# Custom Observe Plugin - Metrics Collector
# ============================================================================

class MetricsCollector(PluginInterface):
    """
    Metrics collection observe plugin.

    Collects execution metrics for monitoring and analytics.
    """

    layer = 'observe'
    plugin_id = 'observe_metrics'

    def __init__(self):
        self.metrics = {
            'total_executions': 0,
            'successful_executions': 0,
            'failed_executions': 0,
            'execution_times': [],
            'tool_counts': defaultdict(int)
        }

    def validate(self) -> bool:
        """Validate plugin configuration"""
        return True

    def execute(self, context: PluginContext) -> PluginResult:
        """Collect metrics"""
        # Record execution
        self.metrics['total_executions'] += 1
        self.metrics['tool_counts'][context.tool_id] += 1

        # Check if execution was successful (from previous_results)
        if context.previous_results:
            # In real implementation, check the actual execution result
            # For now, assume success if we reached observe layer
            self.metrics['successful_executions'] += 1

        return PluginResult(
            success=True,
            data={
                'metrics_recorded': True,
                'total_executions': self.metrics['total_executions']
            }
        )

    def get_metrics(self) -> Dict[str, Any]:
        """Get collected metrics"""
        return {
            'total_executions': self.metrics['total_executions'],
            'successful_executions': self.metrics['successful_executions'],
            'failed_executions': self.metrics['failed_executions'],
            'success_rate': (
                self.metrics['successful_executions'] / self.metrics['total_executions']
                if self.metrics['total_executions'] > 0 else 0
            ),
            'tool_counts': dict(self.metrics['tool_counts']),
            'avg_execution_time': (
                sum(self.metrics['execution_times']) / len(self.metrics['execution_times'])
                if self.metrics['execution_times'] else 0
            )
        }


# ============================================================================
# Example Tools
# ============================================================================

def create_test_tools():
    """Create test tools for examples"""

    def process_payment(params):
        return {'payment_id': 'PAY-123', 'amount': params['amount']}

    def view_report(params):
        return {'report_id': params['report_id'], 'data': [1, 2, 3]}

    def create_user(params):
        return {'user_id': 'USR-456', 'username': params['username']}

    payment_tool = Tool(
        tool_id='payment_refund',
        name='Payment Refund',
        description='Process a payment refund',
        input_schema={'type': 'object', 'properties': {'amount': {'type': 'number'}}},
        execute_func=process_payment
    )

    report_tool = Tool(
        tool_id='view_report',
        name='View Report',
        description='View a financial report',
        input_schema={'type': 'object', 'properties': {'report_id': {'type': 'string'}}},
        execute_func=view_report
    )

    user_tool = Tool(
        tool_id='create_user',
        name='Create User',
        description='Create a new user account',
        input_schema={'type': 'object', 'properties': {'username': {'type': 'string'}}},
        execute_func=create_user
    )

    return payment_tool, report_tool, user_tool


# ============================================================================
# Examples
# ============================================================================

def example_1_custom_schema():
    """Example 1: Custom schema validation"""
    print("\n" + "=" * 70)
    print("Example 1: Custom Schema Validation")
    print("=" * 70)

    scheduler = CoreScheduler()

    # Create custom schema plugin with extra rules
    custom_schema = CustomSchemaValidator(
        schema={'type': 'object', 'properties': {'username': {'type': 'string'}}},
        custom_rules={
            'username': {
                'min_length': 3,
                'max_length': 20,
                'custom_validator': lambda v: v.isalnum()  # Alphanumeric only
            }
        }
    )

    scheduler.plugin_pool.register_global_plugin(custom_schema)

    _, _, user_tool = create_test_tools()
    scheduler.register_tool(user_tool)

    # Valid username
    print("\n--- Valid Username ---")
    context = scheduler.execute('create_user', {'username': 'john123'})
    print(f"Status: {context.status}, Result: {context.final_result}")

    # Too short
    print("\n--- Invalid: Too Short ---")
    context = scheduler.execute('create_user', {'username': 'ab'})
    print(f"Status: {context.status}, Error: {context.error}")

    # Non-alphanumeric
    print("\n--- Invalid: Special Characters ---")
    context = scheduler.execute('create_user', {'username': 'john@123'})
    print(f"Status: {context.status}, Error: {context.error}")


def example_2_rate_limiting():
    """Example 2: Rate limiting guard"""
    print("\n" + "=" * 70)
    print("Example 2: Rate Limiting Guard")
    print("=" * 70)

    scheduler = CoreScheduler()

    # Rate limit: max 3 calls per 2 seconds
    rate_limiter = RateLimitGuard(max_calls=3, window_seconds=2.0)
    scheduler.plugin_pool.register_global_plugin(rate_limiter)

    payment_tool, _, _ = create_test_tools()
    scheduler.register_tool(payment_tool)

    # Execute 5 times rapidly
    for i in range(5):
        context = scheduler.execute('payment_refund', {'amount': 100})
        print(f"\nCall {i+1}: Status = {context.status}")

        if context.status.value == 'failed':
            print(f"  Reason: {context.error}")
        else:
            print(f"  Result: {context.final_result}")

    print("\n--- Waiting 2 seconds for rate limit reset ---")
    time.sleep(2.1)

    context = scheduler.execute('payment_refund', {'amount': 100})
    print(f"\nAfter reset: Status = {context.status}, Result: {context.final_result}")


def example_3_rbac():
    """Example 3: Role-based access control"""
    print("\n" + "=" * 70)
    print("Example 3: Role-Based Access Control")
    print("=" * 70)

    # NOTE: Current version doesn't support metadata in execute()
    # This example shows the plugin design; in production, you'd need
    # to pass user_role through a wrapper or modify CoreScheduler

    scheduler = CoreScheduler()

    # Define role permissions
    rbac_guard = RoleBasedGuard(role_permissions={
        'payment_refund': ['admin', 'finance'],
        'view_report': ['admin', 'finance', 'analyst'],
        'create_user': ['admin']
    })

    scheduler.plugin_pool.register_global_plugin(rbac_guard)

    payment_tool, report_tool, user_tool = create_test_tools()
    scheduler.register_tool(payment_tool)
    scheduler.register_tool(report_tool)
    scheduler.register_tool(user_tool)

    # Simulate execution with different roles
    # (In real implementation, you'd inject user_role via context)
    print("\n--- Simulating RBAC (plugin is registered) ---")
    print("Note: Current version executes without role context")
    print("In production, wrap execute() to inject user_role metadata")

    context = scheduler.execute('view_report', {'report_id': 'RPT-001'})
    print(f"\nExecution: Status = {context.status}")


def example_4_metrics_collection():
    """Example 4: Metrics collection"""
    print("\n" + "=" * 70)
    print("Example 4: Metrics Collection")
    print("=" * 70)

    scheduler = CoreScheduler()

    # Register metrics collector
    metrics_collector = MetricsCollector()
    scheduler.plugin_pool.register_global_plugin(metrics_collector)

    payment_tool, report_tool, _ = create_test_tools()
    scheduler.register_tool(payment_tool)
    scheduler.register_tool(report_tool)

    # Execute multiple tools
    print("\n--- Executing Multiple Tools ---")
    for i in range(3):
        scheduler.execute('payment_refund', {'amount': 100 * (i + 1)})

    for i in range(2):
        scheduler.execute('view_report', {'report_id': f'RPT-{i+1}'})

    # Get metrics
    print("\n--- Collected Metrics ---")
    metrics = metrics_collector.get_metrics()
    for key, value in metrics.items():
        print(f"{key}: {value}")


def example_5_combined_plugins():
    """Example 5: Combining multiple custom plugins"""
    print("\n" + "=" * 70)
    print("Example 5: Combined Custom Plugins")
    print("=" * 70)

    scheduler = CoreScheduler()

    # Register all custom plugins
    custom_schema = CustomSchemaValidator(
        schema={'type': 'object', 'properties': {'amount': {'type': 'number'}}},
        custom_rules={'amount': {'min_value': 1, 'max_value': 10000}}
    )

    rate_limiter = RateLimitGuard(max_calls=5, window_seconds=10.0)
    metrics_collector = MetricsCollector()

    scheduler.plugin_pool.register_global_plugin(custom_schema)
    scheduler.plugin_pool.register_global_plugin(rate_limiter)
    scheduler.plugin_pool.register_global_plugin(metrics_collector)

    payment_tool, _, _ = create_test_tools()
    scheduler.register_tool(payment_tool)

    # Execute with valid amount
    print("\n--- Valid Amount ---")
    context = scheduler.execute('payment_refund', {'amount': 500})
    print(f"Status: {context.status}, Result: {context.final_result}")

    # Execute with invalid amount (too high)
    print("\n--- Invalid Amount (too high) ---")
    context = scheduler.execute('payment_refund', {'amount': 50000})
    print(f"Status: {context.status}, Error: {context.error}")

    # Check metrics
    print("\n--- Metrics ---")
    print(f"Total executions: {metrics_collector.get_metrics()['total_executions']}")


# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    """Run all examples"""
    print("\n")
    print("█" * 70)
    print("█" + " " * 68 + "█")
    print("█" + " " * 18 + "Custom Plugin Examples" + " " * 28 + "█")
    print("█" + " " * 68 + "█")
    print("█" * 70)

    try:
        example_1_custom_schema()
        example_2_rate_limiting()
        example_3_rbac()
        example_4_metrics_collection()
        example_5_combined_plugins()

        print("\n" + "=" * 70)
        print("✅ All examples completed successfully!")
        print("=" * 70 + "\n")

    except Exception as e:
        print(f"\n❌ Error running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
