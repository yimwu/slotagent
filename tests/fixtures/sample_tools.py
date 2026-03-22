# Copyright (c) 2026 SlotAgent Contributors
# Licensed under the MIT License - see LICENSE file for details.
"""
Sample tools for testing.

Provides mock tool definitions and executors.
"""

from typing import Any, Dict

from slotagent.types import Tool

# =============================================================================
# Mock Tool Executors
# =============================================================================


def mock_weather_executor(params: Dict[str, Any]) -> Dict[str, Any]:
    """Mock weather query executor"""
    return {"location": params.get("location", "Unknown"), "temperature": 15, "weather": "Sunny"}


def mock_payment_executor(params: Dict[str, Any]) -> Dict[str, Any]:
    """Mock payment refund executor"""
    return {"order_id": params.get("order_id"), "refund_id": "REF123", "status": "success"}


def failing_executor(params: Dict[str, Any]) -> Dict[str, Any]:
    """Executor that always fails"""
    raise RuntimeError("Tool execution failed")


# =============================================================================
# Mock Tool Definitions (using Tool dataclass)
# =============================================================================

# Predefined tools
WEATHER_TOOL = Tool(
    tool_id="weather_query",
    name="Weather Query",
    description="Query weather information for a location",
    input_schema={
        "type": "object",
        "properties": {"location": {"type": "string"}},
        "required": ["location"],
    },
    execute_func=mock_weather_executor,
)

PAYMENT_TOOL = Tool(
    tool_id="payment_refund",
    name="Payment Refund",
    description="Process payment refund for an order",
    input_schema={
        "type": "object",
        "properties": {"order_id": {"type": "string"}, "amount": {"type": "number"}},
        "required": ["order_id", "amount"],
    },
    execute_func=mock_payment_executor,
)

FAILING_TOOL = Tool(
    tool_id="failing_tool",
    name="Failing Tool",
    description="A tool that always fails for testing error handling",
    input_schema={"type": "object", "properties": {}},
    execute_func=failing_executor,
)
