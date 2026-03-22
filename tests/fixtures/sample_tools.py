# Copyright (c) 2026 SlotAgent Contributors
# Licensed under the MIT License - see LICENSE file for details.
"""
Sample tools for testing.

Provides mock tool definitions and executors.
"""

from typing import Any, Dict


# =============================================================================
# Mock Tool Executors
# =============================================================================


def mock_weather_executor(params: Dict[str, Any]) -> Dict[str, Any]:
    """Mock weather query executor"""
    return {
        'location': params.get('location', 'Unknown'),
        'temperature': 15,
        'weather': 'Sunny'
    }


def mock_payment_executor(params: Dict[str, Any]) -> Dict[str, Any]:
    """Mock payment refund executor"""
    return {
        'order_id': params.get('order_id'),
        'refund_id': 'REF123',
        'status': 'success'
    }


def failing_executor(params: Dict[str, Any]) -> Dict[str, Any]:
    """Executor that always fails"""
    raise RuntimeError("Tool execution failed")


# =============================================================================
# Mock Tool Definitions
# =============================================================================


class MockTool:
    """Simple mock tool for testing"""

    def __init__(self, tool_id: str, name: str, executor=None):
        self.tool_id = tool_id
        self.name = name
        self.executor = executor or mock_weather_executor

    def execute(self, params: Dict[str, Any]) -> Any:
        """Execute the tool"""
        return self.executor(params)


# Predefined tools
WEATHER_TOOL = MockTool('weather_query', 'Weather Query', mock_weather_executor)
PAYMENT_TOOL = MockTool('payment_refund', 'Payment Refund', mock_payment_executor)
FAILING_TOOL = MockTool('failing_tool', 'Failing Tool', failing_executor)
