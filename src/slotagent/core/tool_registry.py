# Copyright (c) 2026 SlotAgent Contributors
# Licensed under the MIT License - see LICENSE file for details.
"""
Tool registry for managing all available tools.

Provides thread-safe tool registration, lookup, and validation.
"""

import re
import threading
from typing import TYPE_CHECKING, Dict, List, Optional

from slotagent.types import Tool

if TYPE_CHECKING:
    from slotagent.core.plugin_pool import PluginPool


class ToolRegistry:
    """
    Tool registry for managing all available tools.

    Thread-safe singleton implementation for registering and querying tools.

    Examples:
        >>> registry = ToolRegistry()
        >>> tool = Tool(...)
        >>> registry.register(tool)
        >>> retrieved = registry.get_tool("my_tool")
    """

    # Valid tool_id pattern: ^[a-z][a-z0-9_]{1,63}$
    TOOL_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]{1,63}$")

    # Valid plugin layers
    VALID_LAYERS = {"schema", "guard", "healing", "reflect", "observe"}

    def __init__(self, plugin_pool: Optional["PluginPool"] = None):
        """
        Initialize ToolRegistry.

        Args:
            plugin_pool: Optional PluginPool instance for validation

        Postconditions:
            - Empty tool registry created
            - Thread lock initialized
        """
        self._tools: Dict[str, Tool] = {}
        self._plugin_pool = plugin_pool
        self._lock = threading.Lock()

    def register(self, tool: Tool) -> None:
        """
        Register a tool.

        Preconditions:
            - tool.tool_id not already registered
            - tool passes validation (validate_tool returns True)

        Args:
            tool: Tool instance to register

        Postconditions:
            - Tool stored in registry
            - Tool-level plugins registered in PluginPool (if configured)

        Raises:
            ValueError: If tool_id already exists
            ValueError: If tool validation fails
        """
        # Validate tool
        self.validate_tool(tool)

        # Check uniqueness
        with self._lock:
            if tool.tool_id in self._tools:
                raise ValueError(f"Tool {tool.tool_id} already registered")

            # Store tool
            self._tools[tool.tool_id] = tool

        # Register tool-level plugins to PluginPool
        if tool.plugins and self._plugin_pool:
            self._plugin_pool.register_tool_plugins(tool.tool_id, tool.plugins)

    def get_tool(self, tool_id: str) -> Optional[Tool]:
        """
        Get tool by ID.

        Preconditions:
            - None (tool_id can be any string)

        Args:
            tool_id: Tool identifier

        Returns:
            Tool instance if found, None otherwise

        Postconditions:
            - Registry state unchanged
        """
        return self._tools.get(tool_id)

    def list_tools(self, tags: Optional[List[str]] = None) -> List[Tool]:
        """
        List all registered tools, optionally filtered by tags.

        Preconditions:
            - None

        Args:
            tags: Optional list of tags to filter
                  (checks metadata['tags'])

        Returns:
            List of Tool instances
            Empty list if no tools or no matches

        Postconditions:
            - Registry state unchanged
        """
        # Get all tools
        with self._lock:
            all_tools = list(self._tools.values())

        # Filter by tags if specified
        if tags:
            filtered_tools = []
            for tool in all_tools:
                # Check if tool has tags in metadata
                if tool.metadata and "tags" in tool.metadata:
                    tool_tags = tool.metadata["tags"]
                    # Check if any requested tag matches
                    if any(tag in tool_tags for tag in tags):
                        filtered_tools.append(tool)
            return filtered_tools

        return all_tools

    def unregister(self, tool_id: str) -> None:
        """
        Unregister a tool.

        Preconditions:
            - tool_id exists in registry

        Args:
            tool_id: Tool identifier

        Postconditions:
            - Tool removed from registry
            - Tool-level plugins remain in PluginPool (not removed)

        Raises:
            KeyError: If tool_id not found
        """
        with self._lock:
            if tool_id not in self._tools:
                raise KeyError(f"Tool {tool_id} not found")
            del self._tools[tool_id]

    def validate_tool(self, tool: Tool) -> bool:
        """
        Validate tool configuration.

        Preconditions:
            - tool is a Tool instance

        Args:
            tool: Tool instance to validate

        Returns:
            True if valid (never returns False - raises instead)

        Postconditions:
            - Registry state unchanged

        Raises:
            ValueError: If validation fails with detailed reason
        """
        # 1. Validate tool_id format
        if not self.TOOL_ID_PATTERN.match(tool.tool_id):
            raise ValueError(
                f"Invalid tool_id format: {tool.tool_id}. " f"Must match: ^[a-z][a-z0-9_]{{1,63}}$"
            )

        # 2. Validate name
        if not tool.name or len(tool.name) < 1 or len(tool.name) > 128:
            raise ValueError(f"Invalid name length: {len(tool.name)}. Must be 1-128 characters")

        # 3. Validate description
        if not tool.description or len(tool.description) < 10 or len(tool.description) > 1000:
            raise ValueError(
                f"Invalid description length: {len(tool.description)}. Must be 10-1000 characters"
            )

        # 4. Validate input_schema
        if not isinstance(tool.input_schema, dict):
            raise ValueError("Invalid input_schema: must be a dictionary")

        if tool.input_schema.get("type") != "object":
            raise ValueError("Invalid input_schema: must have type=object")

        if "properties" not in tool.input_schema:
            raise ValueError("Invalid input_schema: must have properties")

        # 5. Validate execute_func
        if not callable(tool.execute_func):
            raise ValueError("execute_func is not callable")

        # 6. Validate plugins (if configured and plugin_pool exists)
        if tool.plugins:
            for layer, plugin_id in tool.plugins.items():
                # Check layer validity
                if layer not in self.VALID_LAYERS:
                    raise ValueError(
                        f"Invalid plugin layer: {layer}. " f"Must be one of: {self.VALID_LAYERS}"
                    )

                # Check plugin exists in PluginPool
                if self._plugin_pool:
                    # Get plugin by ID from pool
                    plugin = self._plugin_pool.get_plugin_by_id(plugin_id)
                    if plugin is None:
                        raise ValueError(f"Plugin {plugin_id} not found in PluginPool")

        return True
