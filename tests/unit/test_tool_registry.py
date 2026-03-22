# Copyright (c) 2026 SlotAgent Contributors
# Licensed under the MIT License - see LICENSE file for details.
"""
Unit tests for ToolRegistry.
"""

import threading

import pytest

from slotagent.core.plugin_pool import PluginPool
from slotagent.core.tool_registry import ToolRegistry
from slotagent.plugins.guard import GuardDefault
from slotagent.plugins.schema import SchemaDefault, SchemaStrict
from slotagent.types import Tool


class TestToolRegistryCreation:
    """Test ToolRegistry initialization"""

    def test_registry_creation_without_plugin_pool(self):
        """Test creating registry without PluginPool"""
        registry = ToolRegistry()
        assert registry is not None
        assert len(registry.list_tools()) == 0

    def test_registry_creation_with_plugin_pool(self):
        """Test creating registry with PluginPool"""
        pool = PluginPool()
        registry = ToolRegistry(plugin_pool=pool)
        assert registry is not None


class TestToolRegistration:
    """Test tool registration"""

    def test_register_simple_tool(self):
        """Test registering a simple tool"""
        registry = ToolRegistry()

        tool = Tool(
            tool_id="test_tool",
            name="Test Tool",
            description="A test tool",
            input_schema={"type": "object", "properties": {}},
            execute_func=lambda p: p,
        )

        registry.register(tool)
        retrieved = registry.get_tool("test_tool")

        assert retrieved is not None
        assert retrieved.tool_id == "test_tool"
        assert retrieved.name == "Test Tool"

    def test_register_duplicate_tool_id_fails(self):
        """Test that registering duplicate tool_id raises error"""
        registry = ToolRegistry()

        tool1 = Tool(
            tool_id="duplicate",
            name="Tool 1",
            description="First tool",
            input_schema={"type": "object", "properties": {}},
            execute_func=lambda p: p,
        )

        tool2 = Tool(
            tool_id="duplicate",
            name="Tool 2",
            description="Second tool",
            input_schema={"type": "object", "properties": {}},
            execute_func=lambda p: p,
        )

        registry.register(tool1)

        with pytest.raises(ValueError, match="already registered"):
            registry.register(tool2)

    def test_register_tool_with_plugins(self):
        """Test registering tool with plugin configuration"""
        pool = PluginPool()
        pool.register_global_plugin(SchemaDefault())
        pool.register_global_plugin(SchemaStrict())
        pool.register_global_plugin(GuardDefault())

        registry = ToolRegistry(plugin_pool=pool)

        tool = Tool(
            tool_id="payment_tool",
            name="Payment Tool",
            description="Payment processing tool",
            input_schema={"type": "object", "properties": {}},
            execute_func=lambda p: p,
            plugins={"schema": "schema_strict", "guard": "guard_default"},
        )

        registry.register(tool)

        # Verify tool registered
        retrieved = registry.get_tool("payment_tool")
        assert retrieved is not None

        # Verify plugins registered in PluginPool
        schema_plugin = pool.get_plugin("schema", "payment_tool")
        assert schema_plugin is not None
        assert schema_plugin.plugin_id == "schema_strict"


class TestToolQuery:
    """Test tool query operations"""

    def test_get_tool_exists(self):
        """Test getting existing tool"""
        registry = ToolRegistry()

        tool = Tool(
            tool_id="existing",
            name="Existing Tool",
            description="An existing tool",
            input_schema={"type": "object", "properties": {}},
            execute_func=lambda p: p,
        )

        registry.register(tool)
        retrieved = registry.get_tool("existing")

        assert retrieved is not None
        assert retrieved.tool_id == "existing"

    def test_get_tool_not_exists(self):
        """Test getting non-existent tool returns None"""
        registry = ToolRegistry()
        retrieved = registry.get_tool("nonexistent")
        assert retrieved is None

    def test_list_all_tools(self):
        """Test listing all tools"""
        registry = ToolRegistry()

        tool1 = Tool(
            tool_id="tool1",
            name="Tool 1",
            description="First tool",
            input_schema={"type": "object", "properties": {}},
            execute_func=lambda p: p,
        )

        tool2 = Tool(
            tool_id="tool2",
            name="Tool 2",
            description="Second tool",
            input_schema={"type": "object", "properties": {}},
            execute_func=lambda p: p,
        )

        registry.register(tool1)
        registry.register(tool2)

        tools = registry.list_tools()
        assert len(tools) == 2
        tool_ids = [t.tool_id for t in tools]
        assert "tool1" in tool_ids
        assert "tool2" in tool_ids

    def test_list_tools_with_tag_filter(self):
        """Test listing tools filtered by tags"""
        registry = ToolRegistry()

        tool1 = Tool(
            tool_id="payment_tool",
            name="Payment Tool",
            description="Payment processing",
            input_schema={"type": "object", "properties": {}},
            execute_func=lambda p: p,
            metadata={"tags": ["payment", "high-risk"]},
        )

        tool2 = Tool(
            tool_id="query_tool",
            name="Query Tool",
            description="Data query",
            input_schema={"type": "object", "properties": {}},
            execute_func=lambda p: p,
            metadata={"tags": ["query", "low-risk"]},
        )

        tool3 = Tool(
            tool_id="refund_tool",
            name="Refund Tool",
            description="Refund processing",
            input_schema={"type": "object", "properties": {}},
            execute_func=lambda p: p,
            metadata={"tags": ["payment", "high-risk"]},
        )

        registry.register(tool1)
        registry.register(tool2)
        registry.register(tool3)

        # Filter by "payment" tag
        payment_tools = registry.list_tools(tags=["payment"])
        assert len(payment_tools) == 2
        payment_ids = [t.tool_id for t in payment_tools]
        assert "payment_tool" in payment_ids
        assert "refund_tool" in payment_ids

        # Filter by "query" tag
        query_tools = registry.list_tools(tags=["query"])
        assert len(query_tools) == 1
        assert query_tools[0].tool_id == "query_tool"

    def test_list_tools_no_tags_returns_all(self):
        """Test listing tools with no tag filter returns all"""
        registry = ToolRegistry()

        tool1 = Tool(
            tool_id="tool1",
            name="Tool 1",
            description="First tool",
            input_schema={"type": "object", "properties": {}},
            execute_func=lambda p: p,
            metadata={"tags": ["tag1"]},
        )

        tool2 = Tool(
            tool_id="tool2",
            name="Tool 2",
            description="Second tool",
            input_schema={"type": "object", "properties": {}},
            execute_func=lambda p: p,
        )

        registry.register(tool1)
        registry.register(tool2)

        all_tools = registry.list_tools()
        assert len(all_tools) == 2


class TestToolUnregistration:
    """Test tool unregistration"""

    def test_unregister_existing_tool(self):
        """Test unregistering an existing tool"""
        registry = ToolRegistry()

        tool = Tool(
            tool_id="to_remove",
            name="To Remove",
            description="Tool to be removed",
            input_schema={"type": "object", "properties": {}},
            execute_func=lambda p: p,
        )

        registry.register(tool)
        assert registry.get_tool("to_remove") is not None

        registry.unregister("to_remove")
        assert registry.get_tool("to_remove") is None

    def test_unregister_nonexistent_tool_fails(self):
        """Test unregistering non-existent tool raises error"""
        registry = ToolRegistry()

        with pytest.raises(KeyError):
            registry.unregister("nonexistent")


class TestToolValidation:
    """Test tool validation"""

    def test_validate_valid_tool(self):
        """Test validating a valid tool"""
        registry = ToolRegistry()

        tool = Tool(
            tool_id="valid_tool",
            name="Valid Tool",
            description="A valid tool for testing validation",
            input_schema={"type": "object", "properties": {"param": {"type": "string"}}},
            execute_func=lambda p: p,
        )

        assert registry.validate_tool(tool) is True

    def test_validate_invalid_tool_id_format(self):
        """Test validation fails for invalid tool_id format"""
        registry = ToolRegistry()

        # Invalid: starts with uppercase
        tool = Tool(
            tool_id="Invalid",
            name="Test",
            description="Test tool",
            input_schema={"type": "object", "properties": {}},
            execute_func=lambda p: p,
        )

        with pytest.raises(ValueError, match="Invalid tool_id format"):
            registry.validate_tool(tool)

    def test_validate_invalid_tool_id_too_long(self):
        """Test validation fails for too long tool_id"""
        registry = ToolRegistry()

        tool = Tool(
            tool_id="a" * 65,  # 65 characters, exceeds 64 limit
            name="Test",
            description="Test tool",
            input_schema={"type": "object", "properties": {}},
            execute_func=lambda p: p,
        )

        with pytest.raises(ValueError, match="Invalid tool_id format"):
            registry.validate_tool(tool)

    def test_validate_invalid_name_empty(self):
        """Test validation fails for empty name"""
        registry = ToolRegistry()

        tool = Tool(
            tool_id="test",
            name="",
            description="Test tool",
            input_schema={"type": "object", "properties": {}},
            execute_func=lambda p: p,
        )

        with pytest.raises(ValueError, match="Invalid name"):
            registry.validate_tool(tool)

    def test_validate_invalid_description_too_short(self):
        """Test validation fails for too short description"""
        registry = ToolRegistry()

        tool = Tool(
            tool_id="test",
            name="Test",
            description="Short",  # Less than 10 characters
            input_schema={"type": "object", "properties": {}},
            execute_func=lambda p: p,
        )

        with pytest.raises(ValueError, match="Invalid description"):
            registry.validate_tool(tool)

    def test_validate_invalid_input_schema_no_type(self):
        """Test validation fails for input_schema without type"""
        registry = ToolRegistry()

        tool = Tool(
            tool_id="test",
            name="Test",
            description="Test tool for validation testing purposes",
            input_schema={"properties": {}},  # Missing "type"
            execute_func=lambda p: p,
        )

        with pytest.raises(ValueError, match="Invalid input_schema"):
            registry.validate_tool(tool)

    def test_validate_invalid_input_schema_no_properties(self):
        """Test validation fails for input_schema without properties"""
        registry = ToolRegistry()

        tool = Tool(
            tool_id="test",
            name="Test",
            description="Test tool for validation testing purposes",
            input_schema={"type": "object"},  # Missing "properties"
            execute_func=lambda p: p,
        )

        with pytest.raises(ValueError, match="Invalid input_schema"):
            registry.validate_tool(tool)

    def test_validate_non_callable_execute_func(self):
        """Test validation fails for non-callable execute_func"""
        registry = ToolRegistry()

        tool = Tool(
            tool_id="test",
            name="Test",
            description="Test tool for validation testing purposes",
            input_schema={"type": "object", "properties": {}},
            execute_func="not_callable",  # String instead of function
        )

        with pytest.raises(ValueError, match="execute_func is not callable"):
            registry.validate_tool(tool)

    def test_validate_invalid_plugin_layer(self):
        """Test validation fails for invalid plugin layer"""
        pool = PluginPool()
        registry = ToolRegistry(plugin_pool=pool)

        tool = Tool(
            tool_id="test",
            name="Test",
            description="Test tool for validation testing purposes",
            input_schema={"type": "object", "properties": {}},
            execute_func=lambda p: p,
            plugins={"invalid_layer": "some_plugin"},
        )

        with pytest.raises(ValueError, match="Invalid plugin layer"):
            registry.validate_tool(tool)

    def test_validate_plugin_not_found(self):
        """Test validation fails when plugin not in PluginPool"""
        pool = PluginPool()
        pool.register_global_plugin(SchemaDefault())

        registry = ToolRegistry(plugin_pool=pool)

        tool = Tool(
            tool_id="test",
            name="Test",
            description="Test tool for validation testing purposes",
            input_schema={"type": "object", "properties": {}},
            execute_func=lambda p: p,
            plugins={"schema": "nonexistent_plugin"},
        )

        with pytest.raises(ValueError, match="Plugin .* not found"):
            registry.validate_tool(tool)


class TestThreadSafety:
    """Test thread safety of ToolRegistry"""

    def test_concurrent_registration(self):
        """Test concurrent tool registration is thread-safe"""
        registry = ToolRegistry()
        errors = []

        def register_tool(tool_id):
            try:
                tool = Tool(
                    tool_id=tool_id,
                    name=f"Tool {tool_id}",
                    description="Concurrent registration test tool",
                    input_schema={"type": "object", "properties": {}},
                    execute_func=lambda p: p,
                )
                registry.register(tool)
            except Exception as e:
                errors.append(e)

        threads = []
        for i in range(10):
            t = threading.Thread(target=register_tool, args=(f"tool_{i}",))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(registry.list_tools()) == 10
