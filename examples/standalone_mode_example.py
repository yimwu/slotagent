#!/usr/bin/env python3
# Copyright (c) 2026 SlotAgent Contributors
# Licensed under the MIT License - see LICENSE file for details.
"""
Standalone Mode Example - Basic SlotAgent Usage

This example demonstrates how to use SlotAgent as a standalone agent execution engine.

Features demonstrated:
- Tool registration and execution
- Schema validation
- Guard access control
- Hook event monitoring
- Error handling

Run this example:
    python examples/standalone_mode_example.py
"""

from slotagent.core import CoreScheduler, HookManager
from slotagent.plugins import SchemaDefault, GuardDefault, LogPlugin
from slotagent.types import Tool, ExecutionStatus


# ============================================================================
# Define Tools
# ============================================================================

def get_weather(params):
    """Simulate weather query API"""
    location = params['location']
    unit = params.get('unit', 'celsius')

    # Simulate API call
    temperature = 25 if unit == 'celsius' else 77

    return {
        'location': location,
        'temperature': temperature,
        'unit': unit,
        'condition': 'sunny',
        'humidity': 65
    }


def calculate_sum(params):
    """Calculate sum of numbers"""
    numbers = params['numbers']
    return {'result': sum(numbers), 'count': len(numbers)}


def send_email(params):
    """Simulate sending email (dangerous operation)"""
    recipient = params['recipient']
    subject = params['subject']
    body = params.get('body', '')

    # Simulate email sending
    print(f"[EMAIL] Sending to {recipient}: {subject}")

    return {
        'sent': True,
        'recipient': recipient,
        'message_id': 'msg-12345'
    }


# ============================================================================
# Define Tool Schemas
# ============================================================================

WEATHER_TOOL = Tool(
    tool_id='weather_query',
    name='Weather Query',
    description='Get current weather information for a location',
    input_schema={
        'type': 'object',
        'properties': {
            'location': {'type': 'string'},
            'unit': {'type': 'string', 'enum': ['celsius', 'fahrenheit']}
        },
        'required': ['location']
    },
    execute_func=get_weather
)

CALCULATOR_TOOL = Tool(
    tool_id='calculator_sum',
    name='Calculator - Sum',
    description='Calculate the sum of a list of numbers',
    input_schema={
        'type': 'object',
        'properties': {
            'numbers': {
                'type': 'array',
                'items': {'type': 'number'}
            }
        },
        'required': ['numbers']
    },
    execute_func=calculate_sum
)

EMAIL_TOOL = Tool(
    tool_id='send_email',
    name='Send Email',
    description='Send an email to a recipient (dangerous operation)',
    input_schema={
        'type': 'object',
        'properties': {
            'recipient': {'type': 'string'},
            'subject': {'type': 'string'},
            'body': {'type': 'string'}
        },
        'required': ['recipient', 'subject']
    },
    execute_func=send_email
)


# ============================================================================
# Setup Hook Monitoring
# ============================================================================

def setup_hooks(hook_manager):
    """Setup hook event listeners for monitoring"""

    def on_before_exec(event):
        print(f"\n[HOOK] 🚀 Starting execution: {event.tool_name}")
        print(f"       Execution ID: {event.execution_id}")
        print(f"       Parameters: {event.params}")

    def on_after_exec(event):
        print(f"\n[HOOK] ✅ Execution completed: {event.tool_name}")
        print(f"       Result: {event.result}")
        print(f"       Execution time: {event.execution_time:.4f}s")

    def on_fail(event):
        print(f"\n[HOOK] ❌ Execution failed: {event.tool_name}")
        print(f"       Error: {event.error}")
        print(f"       Failed at: {event.failed_at}")

    def on_guard_block(event):
        print(f"\n[HOOK] 🚫 Execution blocked: {event.tool_name}")
        print(f"       Reason: {event.reason}")

    # Subscribe to all events
    hook_manager.subscribe('before_exec', on_before_exec)
    hook_manager.subscribe('after_exec', on_after_exec)
    hook_manager.subscribe('fail', on_fail)
    hook_manager.subscribe('guard_block', on_guard_block)


# ============================================================================
# Main Examples
# ============================================================================

def example_1_basic_execution():
    """Example 1: Basic tool execution without plugins"""
    print("\n" + "=" * 70)
    print("Example 1: Basic Tool Execution")
    print("=" * 70)

    scheduler = CoreScheduler()
    scheduler.register_tool(CALCULATOR_TOOL)

    # Execute tool
    context = scheduler.execute('calculator_sum', {'numbers': [1, 2, 3, 4, 5]})

    print(f"\nExecution Status: {context.status}")
    print(f"Result: {context.final_result}")
    print(f"Execution Time: {context.execution_time:.4f}s")


def example_2_with_schema_validation():
    """Example 2: Tool execution with schema validation"""
    print("\n" + "=" * 70)
    print("Example 2: Schema Validation")
    print("=" * 70)

    hook_manager = HookManager()
    setup_hooks(hook_manager)

    scheduler = CoreScheduler(hook_manager=hook_manager)

    # Register schema plugin
    weather_schema = SchemaDefault(schema=WEATHER_TOOL.input_schema)
    scheduler.plugin_pool.register_global_plugin(weather_schema)

    scheduler.register_tool(WEATHER_TOOL)

    # Valid execution
    print("\n--- Valid Parameters ---")
    context = scheduler.execute('weather_query', {
        'location': 'Beijing',
        'unit': 'celsius'
    })

    if context.status == ExecutionStatus.COMPLETED:
        print(f"\n✅ Success: {context.final_result}")

    # Invalid execution (missing required field)
    print("\n\n--- Invalid Parameters (missing 'location') ---")
    context = scheduler.execute('weather_query', {'unit': 'celsius'})

    if context.status == ExecutionStatus.FAILED:
        print(f"\n❌ Failed: {context.error}")


def example_3_with_guard_control():
    """Example 3: Access control with Guard plugin"""
    print("\n" + "=" * 70)
    print("Example 3: Guard Access Control")
    print("=" * 70)

    hook_manager = HookManager()
    setup_hooks(hook_manager)

    scheduler = CoreScheduler(hook_manager=hook_manager)

    # Register guard plugin with blacklist
    guard = GuardDefault(blacklist=['send_email'])
    scheduler.plugin_pool.register_global_plugin(guard)

    # Also register LogPlugin for visibility
    scheduler.plugin_pool.register_global_plugin(LogPlugin())

    scheduler.register_tool(EMAIL_TOOL)
    scheduler.register_tool(CALCULATOR_TOOL)

    # Allowed tool
    print("\n--- Allowed Tool (calculator_sum) ---")
    context = scheduler.execute('calculator_sum', {'numbers': [10, 20, 30]})
    print(f"Status: {context.status}")

    # Blocked tool
    print("\n\n--- Blocked Tool (send_email) ---")
    context = scheduler.execute('send_email', {
        'recipient': 'user@example.com',
        'subject': 'Test Email'
    })
    print(f"Status: {context.status}")


def example_4_full_plugin_stack():
    """Example 4: Complete plugin stack (Schema + Guard + Log)"""
    print("\n" + "=" * 70)
    print("Example 4: Full Plugin Stack")
    print("=" * 70)

    hook_manager = HookManager()
    setup_hooks(hook_manager)

    scheduler = CoreScheduler(hook_manager=hook_manager)

    # Register all plugins
    scheduler.plugin_pool.register_global_plugin(
        SchemaDefault(schema=WEATHER_TOOL.input_schema)
    )
    scheduler.plugin_pool.register_global_plugin(
        GuardDefault(whitelist=['weather_query'], whitelist_only=True)
    )
    scheduler.plugin_pool.register_global_plugin(LogPlugin())

    scheduler.register_tool(WEATHER_TOOL)

    # Execute
    print("\n--- Executing with Full Plugin Stack ---")
    context = scheduler.execute('weather_query', {
        'location': 'Shanghai',
        'unit': 'celsius'
    })

    print(f"\n📊 Final Result:")
    print(f"   Status: {context.status}")
    print(f"   Result: {context.final_result}")
    print(f"   Plugin Results: {context.plugin_results}")


def example_5_error_handling():
    """Example 5: Graceful error handling"""
    print("\n" + "=" * 70)
    print("Example 5: Error Handling")
    print("=" * 70)

    def failing_tool(params):
        """Tool that always fails"""
        raise ValueError("Intentional failure for demonstration")

    FAILING_TOOL = Tool(
        tool_id='failing_tool',
        name='Failing Tool',
        description='A tool that demonstrates error handling',
        input_schema={'type': 'object', 'properties': {}},
        execute_func=failing_tool
    )

    hook_manager = HookManager()
    setup_hooks(hook_manager)

    scheduler = CoreScheduler(hook_manager=hook_manager)
    scheduler.register_tool(FAILING_TOOL)

    # Execute failing tool
    context = scheduler.execute('failing_tool', {})

    print(f"\n📊 Execution Result:")
    print(f"   Status: {context.status}")
    print(f"   Error: {context.error}")
    print(f"   Execution Time: {context.execution_time:.4f}s")


# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    """Run all examples"""
    print("\n")
    print("█" * 70)
    print("█" + " " * 68 + "█")
    print("█" + " " * 18 + "SlotAgent Standalone Mode" + " " * 25 + "█")
    print("█" + " " * 22 + "Usage Examples" + " " * 32 + "█")
    print("█" + " " * 68 + "█")
    print("█" * 70)

    try:
        example_1_basic_execution()
        example_2_with_schema_validation()
        example_3_with_guard_control()
        example_4_full_plugin_stack()
        example_5_error_handling()

        print("\n" + "=" * 70)
        print("✅ All examples completed successfully!")
        print("=" * 70 + "\n")

    except Exception as e:
        print(f"\n❌ Error running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
