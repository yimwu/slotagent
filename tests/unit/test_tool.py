# Copyright (c) 2026 SlotAgent Contributors
# Licensed under the MIT License - see LICENSE file for details.
"""
Unit tests for Tool class.
"""

import pytest

from slotagent.types import Tool


class TestToolCreation:
    """Test Tool instance creation"""

    def test_tool_minimal_creation(self):
        """Test creating tool with minimal required fields"""
        def dummy_func(params):
            return {"result": "ok"}

        tool = Tool(
            tool_id="test_tool",
            name="Test Tool",
            description="A test tool for testing",
            input_schema={
                "type": "object",
                "properties": {"param1": {"type": "string"}}
            },
            execute_func=dummy_func
        )

        assert tool.tool_id == "test_tool"
        assert tool.name == "Test Tool"
        assert tool.description == "A test tool for testing"
        assert tool.input_schema["type"] == "object"
        assert tool.execute_func == dummy_func
        assert tool.plugins is None
        assert tool.metadata is None

    def test_tool_full_creation(self):
        """Test creating tool with all fields"""
        def dummy_func(params):
            return {"result": "ok"}

        tool = Tool(
            tool_id="payment_refund",
            name="Payment Refund",
            description="Refund payment to customer account",
            input_schema={
                "type": "object",
                "properties": {
                    "order_id": {"type": "string"},
                    "amount": {"type": "number"}
                },
                "required": ["order_id", "amount"]
            },
            execute_func=dummy_func,
            plugins={
                "schema": "schema_strict",
                "guard": "guard_human_in_loop"
            },
            metadata={
                "version": "1.0.0",
                "risk_level": "high",
                "tags": ["payment", "refund"]
            }
        )

        assert tool.tool_id == "payment_refund"
        assert tool.plugins["schema"] == "schema_strict"
        assert tool.plugins["guard"] == "guard_human_in_loop"
        assert tool.metadata["risk_level"] == "high"
        assert "payment" in tool.metadata["tags"]

    def test_tool_execute_func_callable(self):
        """Test that execute_func is callable"""
        def test_func(params):
            return {"value": params.get("x", 0) * 2}

        tool = Tool(
            tool_id="test",
            name="Test",
            description="Test tool",
            input_schema={"type": "object", "properties": {}},
            execute_func=test_func
        )

        result = tool.execute_func({"x": 5})
        assert result == {"value": 10}


class TestToolValidation:
    """Test tool validation rules"""

    def test_valid_tool_id_formats(self):
        """Test valid tool_id formats"""
        valid_ids = [
            "web_search",
            "payment_refund",
            "data_query",
            "test123",
            "a",  # minimum length
            "a" * 64  # maximum length
        ]

        for tool_id in valid_ids:
            tool = Tool(
                tool_id=tool_id,
                name="Test",
                description="Test tool",
                input_schema={"type": "object", "properties": {}},
                execute_func=lambda p: p
            )
            assert tool.tool_id == tool_id
