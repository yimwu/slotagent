# Copyright (c) 2026 SlotAgent Contributors
# Licensed under the MIT License - see LICENSE file for details.
"""
PluginPool - Plugin management and registry.

Manages all registered plugins, supports layer-based organization,
and implements tool-level plugin priority resolution.
"""

from typing import Dict, List, Optional

from slotagent.interfaces import PluginConfigError, PluginInterface


class PluginPool:
    """
    Plugin pool for managing all registered plugins.

    Responsibilities:
    - Manage global plugin registration
    - Manage tool-level plugin configurations
    - Resolve plugin priority (tool-level > global)
    - Build plugin chains for tools

    Usage:
        >>> pool = PluginPool()
        >>> pool.register_global_plugin(SchemaDefault())
        >>> pool.register_tool_plugins('payment', {'schema': 'schema_strict'})
        >>> plugin = pool.get_plugin('schema', 'payment')  # Returns schema_strict
    """

    def __init__(self):
        """Initialize empty plugin pool"""
        # Global plugins: {layer: {plugin_id: plugin_instance}}
        self._global_plugins: Dict[str, Dict[str, PluginInterface]] = {
            "schema": {},
            "guard": {},
            "healing": {},
            "reflect": {},
            "observe": {},
        }

        # Tool-specific plugin configs: {tool_id: {layer: plugin_id}}
        self._tool_plugins: Dict[str, Dict[str, str]] = {}

        # Quick lookup: {plugin_id: plugin_instance}
        self._plugin_by_id: Dict[str, PluginInterface] = {}

    def register_global_plugin(self, plugin: PluginInterface) -> None:
        """
        Register a global plugin.

        Args:
            plugin: Plugin instance implementing PluginInterface

        Raises:
            ValueError: If plugin_id already registered
            PluginConfigError: If plugin validation fails
            TypeError: If plugin is None or invalid

        Examples:
            >>> pool = PluginPool()
            >>> pool.register_global_plugin(SchemaDefault())
        """
        if plugin is None:
            raise TypeError("Plugin cannot be None")

        if not isinstance(plugin, PluginInterface):
            raise TypeError(f"Plugin must implement PluginInterface, got {type(plugin)}")

        # Validate plugin
        if not plugin.validate():
            raise PluginConfigError(f"Plugin '{plugin.plugin_id}' validation failed")

        # Check for duplicate plugin_id
        if plugin.plugin_id in self._plugin_by_id:
            raise ValueError(f"Plugin '{plugin.plugin_id}' already registered")

        # Register
        layer = plugin.layer
        self._global_plugins[layer][plugin.plugin_id] = plugin
        self._plugin_by_id[plugin.plugin_id] = plugin

    def register_tool_plugins(self, tool_id: str, plugins: Dict[str, str]) -> None:
        """
        Register tool-specific plugin configuration.

        Args:
            tool_id: Tool identifier
            plugins: Plugin config mapping {layer: plugin_id}

        Raises:
            ValueError: If plugin_id not found

        Examples:
            >>> pool.register_tool_plugins('payment_refund', {
            ...     'schema': 'schema_strict',
            ...     'guard': 'guard_human_in_loop'
            ... })
        """
        # Validate all plugin_ids exist
        for layer, plugin_id in plugins.items():
            if plugin_id not in self._plugin_by_id:
                raise ValueError(f"Plugin '{plugin_id}' not found. " f"Register it globally first.")

        # Register tool config
        self._tool_plugins[tool_id] = plugins

    def get_plugin(self, layer: str, tool_id: Optional[str] = None) -> Optional[PluginInterface]:
        """
        Get plugin for a specific layer (with tool-level override support).

        Priority: tool-level config > global config

        Args:
            layer: Plugin layer name
            tool_id: Optional tool ID for tool-specific lookup

        Returns:
            Plugin instance or None if not found

        Raises:
            ValueError: If layer is invalid

        Examples:
            >>> # Get global plugin
            >>> plugin = pool.get_plugin('schema')
            >>>
            >>> # Get tool-specific plugin (with override)
            >>> plugin = pool.get_plugin('schema', 'payment_refund')
        """
        # Validate layer
        valid_layers = {"schema", "guard", "healing", "reflect", "observe"}
        if layer not in valid_layers:
            raise ValueError(f"Invalid layer '{layer}'. Must be one of: {valid_layers}")

        # Check tool-level config first
        if tool_id and tool_id in self._tool_plugins:
            tool_config = self._tool_plugins[tool_id]
            if layer in tool_config:
                plugin_id = tool_config[layer]
                return self._plugin_by_id.get(plugin_id)

        # Fallback to global config
        layer_plugins = self._global_plugins[layer]
        if not layer_plugins:
            return None

        # Return first plugin in the layer (for simplicity)
        # In practice, could be configurable which plugin is "default"
        return next(iter(layer_plugins.values()))

    def get_plugin_by_id(self, plugin_id: str) -> Optional[PluginInterface]:
        """
        Get plugin by plugin_id.

        Args:
            plugin_id: Plugin identifier

        Returns:
            Plugin instance or None if not found

        Examples:
            >>> plugin = pool.get_plugin_by_id('schema_default')
        """
        return self._plugin_by_id.get(plugin_id)

    def list_plugins(self, layer: str) -> List[PluginInterface]:
        """
        List all plugins in a specific layer.

        Args:
            layer: Plugin layer name

        Returns:
            List of plugin instances

        Examples:
            >>> plugins = pool.list_plugins('schema')
            >>> for p in plugins:
            ...     print(p.plugin_id)
        """
        valid_layers = {"schema", "guard", "healing", "reflect", "observe"}
        if layer not in valid_layers:
            raise ValueError(f"Invalid layer '{layer}'. Must be one of: {valid_layers}")

        return list(self._global_plugins[layer].values())

    def get_plugin_chain(self, tool_id: str) -> List[PluginInterface]:
        """
        Build complete plugin chain for a tool.

        Returns plugins in execution order: schema, guard, healing, reflect, observe

        Args:
            tool_id: Tool identifier

        Returns:
            List of plugins in execution order

        Examples:
            >>> chain = pool.get_plugin_chain('payment_refund')
            >>> assert chain[0].layer == 'schema'
            >>> assert chain[1].layer == 'guard'
        """
        chain = []
        layers = ["schema", "guard", "healing", "reflect", "observe"]

        for layer in layers:
            plugin = self.get_plugin(layer, tool_id)
            if plugin:
                chain.append(plugin)

        return chain
