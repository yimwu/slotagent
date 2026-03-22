# Copyright (c) 2026 SlotAgent Contributors
# Licensed under the MIT License - see LICENSE file for details.
"""
Unit tests for PluginPool.

Tests plugin registration, query, priority resolution, and plugin chain building.
Following TDD (Test-Driven Development) approach - tests written before implementation.
"""

import pytest

from slotagent.interfaces import PluginConfigError
from tests.fixtures.sample_plugins import (
    AlternativeSchemaPlugin,
    FailingValidationPlugin,
    MockGuardPlugin,
    MockHealingPlugin,
    MockObservePlugin,
    MockReflectPlugin,
    MockSchemaPlugin,
)


class TestPluginPoolRegistration:
    """Test plugin registration functionality"""

    def test_register_global_plugin_success(self):
        """Test successful global plugin registration"""
        from slotagent.core.plugin_pool import PluginPool

        pool = PluginPool()
        plugin = MockSchemaPlugin()

        # Should register without error
        pool.register_global_plugin(plugin)

        # Should be able to retrieve the plugin
        retrieved = pool.get_plugin('schema')
        assert retrieved is not None
        assert retrieved.plugin_id == 'schema_mock'

    def test_register_multiple_plugins_same_layer(self):
        """Test registering multiple plugins in the same layer"""
        from slotagent.core.plugin_pool import PluginPool

        pool = PluginPool()
        plugin1 = MockSchemaPlugin()
        plugin2 = AlternativeSchemaPlugin()

        pool.register_global_plugin(plugin1)
        pool.register_global_plugin(plugin2)

        # Both should be registered
        assert pool.get_plugin('schema') is not None
        assert pool.get_plugin_by_id('schema_mock') is not None
        assert pool.get_plugin_by_id('schema_alternative') is not None

    def test_register_plugin_duplicate_id_raises_error(self):
        """Test that registering duplicate plugin_id raises error"""
        from slotagent.core.plugin_pool import PluginPool

        pool = PluginPool()
        plugin1 = MockSchemaPlugin()
        plugin2 = MockSchemaPlugin()  # Same plugin_id

        pool.register_global_plugin(plugin1)

        with pytest.raises(ValueError, match="already registered"):
            pool.register_global_plugin(plugin2)

    def test_register_plugin_failing_validation(self):
        """Test that plugin failing validation raises error"""
        from slotagent.core.plugin_pool import PluginPool

        pool = PluginPool()
        plugin = FailingValidationPlugin()

        with pytest.raises(PluginConfigError, match="validation failed"):
            pool.register_global_plugin(plugin)

    def test_register_all_layer_plugins(self):
        """Test registering plugins for all 5 layers"""
        from slotagent.core.plugin_pool import PluginPool

        pool = PluginPool()

        pool.register_global_plugin(MockSchemaPlugin())
        pool.register_global_plugin(MockGuardPlugin())
        pool.register_global_plugin(MockHealingPlugin())
        pool.register_global_plugin(MockReflectPlugin())
        pool.register_global_plugin(MockObservePlugin())

        # All layers should have plugins
        assert pool.get_plugin('schema') is not None
        assert pool.get_plugin('guard') is not None
        assert pool.get_plugin('healing') is not None
        assert pool.get_plugin('reflect') is not None
        assert pool.get_plugin('observe') is not None


class TestPluginPoolQuery:
    """Test plugin query functionality"""

    def test_get_plugin_by_layer(self):
        """Test getting plugin by layer name"""
        from slotagent.core.plugin_pool import PluginPool

        pool = PluginPool()
        pool.register_global_plugin(MockSchemaPlugin())

        plugin = pool.get_plugin('schema')
        assert plugin is not None
        assert plugin.layer == 'schema'

    def test_get_plugin_nonexistent_layer_returns_none(self):
        """Test getting plugin from layer with no registered plugin"""
        from slotagent.core.plugin_pool import PluginPool

        pool = PluginPool()

        plugin = pool.get_plugin('schema')
        assert plugin is None

    def test_get_plugin_by_id(self):
        """Test getting plugin by plugin_id"""
        from slotagent.core.plugin_pool import PluginPool

        pool = PluginPool()
        pool.register_global_plugin(MockSchemaPlugin())

        plugin = pool.get_plugin_by_id('schema_mock')
        assert plugin is not None
        assert plugin.plugin_id == 'schema_mock'

    def test_get_plugin_by_id_nonexistent_returns_none(self):
        """Test getting nonexistent plugin by ID returns None"""
        from slotagent.core.plugin_pool import PluginPool

        pool = PluginPool()

        plugin = pool.get_plugin_by_id('nonexistent')
        assert plugin is None

    def test_list_plugins_by_layer(self):
        """Test listing all plugins in a layer"""
        from slotagent.core.plugin_pool import PluginPool

        pool = PluginPool()
        pool.register_global_plugin(MockSchemaPlugin())
        pool.register_global_plugin(AlternativeSchemaPlugin())

        plugins = pool.list_plugins('schema')
        assert len(plugins) == 2
        plugin_ids = [p.plugin_id for p in plugins]
        assert 'schema_mock' in plugin_ids
        assert 'schema_alternative' in plugin_ids


class TestToolPluginConfiguration:
    """Test tool-level plugin configuration"""

    def test_register_tool_plugins(self):
        """Test registering tool-specific plugin configuration"""
        from slotagent.core.plugin_pool import PluginPool

        pool = PluginPool()
        pool.register_global_plugin(MockSchemaPlugin())
        pool.register_global_plugin(AlternativeSchemaPlugin())

        # Register tool-specific config
        pool.register_tool_plugins('payment_refund', {
            'schema': 'schema_alternative'
        })

        # Should return tool-specific plugin
        plugin = pool.get_plugin('schema', 'payment_refund')
        assert plugin.plugin_id == 'schema_alternative'

    def test_register_tool_plugins_nonexistent_plugin_raises_error(self):
        """Test that registering nonexistent plugin_id raises error"""
        from slotagent.core.plugin_pool import PluginPool

        pool = PluginPool()

        with pytest.raises(ValueError, match="not found"):
            pool.register_tool_plugins('test_tool', {
                'schema': 'nonexistent_plugin'
            })

    def test_tool_plugin_overrides_global(self):
        """Test that tool-level plugin overrides global plugin"""
        from slotagent.core.plugin_pool import PluginPool

        pool = PluginPool()
        pool.register_global_plugin(MockSchemaPlugin())
        pool.register_global_plugin(AlternativeSchemaPlugin())

        # Register tool-specific config
        pool.register_tool_plugins('special_tool', {
            'schema': 'schema_alternative'
        })

        # Tool-specific should override global
        plugin = pool.get_plugin('schema', 'special_tool')
        assert plugin.plugin_id == 'schema_alternative'

        # Global should still work for other tools
        plugin = pool.get_plugin('schema', 'other_tool')
        assert plugin.plugin_id == 'schema_mock'

        # Global should work when no tool_id specified
        plugin = pool.get_plugin('schema')
        assert plugin.plugin_id == 'schema_mock'


class TestPluginChainBuilding:
    """Test building complete plugin chains for tools"""

    def test_get_plugin_chain_all_layers(self):
        """Test getting complete plugin chain with all 5 layers"""
        from slotagent.core.plugin_pool import PluginPool

        pool = PluginPool()
        pool.register_global_plugin(MockSchemaPlugin())
        pool.register_global_plugin(MockGuardPlugin())
        pool.register_global_plugin(MockHealingPlugin())
        pool.register_global_plugin(MockReflectPlugin())
        pool.register_global_plugin(MockObservePlugin())

        chain = pool.get_plugin_chain('test_tool')

        assert len(chain) == 5
        assert chain[0].layer == 'schema'
        assert chain[1].layer == 'guard'
        assert chain[2].layer == 'healing'
        assert chain[3].layer == 'reflect'
        assert chain[4].layer == 'observe'

    def test_get_plugin_chain_partial_layers(self):
        """Test plugin chain with only some layers configured"""
        from slotagent.core.plugin_pool import PluginPool

        pool = PluginPool()
        pool.register_global_plugin(MockSchemaPlugin())
        pool.register_global_plugin(MockGuardPlugin())
        # No healing, reflect, observe

        chain = pool.get_plugin_chain('test_tool')

        assert len(chain) == 2
        assert chain[0].layer == 'schema'
        assert chain[1].layer == 'guard'

    def test_get_plugin_chain_with_tool_override(self):
        """Test plugin chain with tool-specific overrides"""
        from slotagent.core.plugin_pool import PluginPool

        pool = PluginPool()
        pool.register_global_plugin(MockSchemaPlugin())
        pool.register_global_plugin(AlternativeSchemaPlugin())
        pool.register_global_plugin(MockGuardPlugin())

        # Tool-specific config
        pool.register_tool_plugins('high_risk_tool', {
            'schema': 'schema_alternative'
        })

        chain = pool.get_plugin_chain('high_risk_tool')

        assert len(chain) == 2
        assert chain[0].plugin_id == 'schema_alternative'  # Tool override
        assert chain[1].plugin_id == 'guard_mock'  # Global

    def test_get_plugin_chain_empty(self):
        """Test plugin chain when no plugins registered"""
        from slotagent.core.plugin_pool import PluginPool

        pool = PluginPool()

        chain = pool.get_plugin_chain('test_tool')

        assert len(chain) == 0

    def test_plugin_chain_order_is_correct(self):
        """Test that plugin chain follows correct execution order"""
        from slotagent.core.plugin_pool import PluginPool

        pool = PluginPool()

        # Register in random order
        pool.register_global_plugin(MockObservePlugin())
        pool.register_global_plugin(MockSchemaPlugin())
        pool.register_global_plugin(MockReflectPlugin())
        pool.register_global_plugin(MockGuardPlugin())
        pool.register_global_plugin(MockHealingPlugin())

        chain = pool.get_plugin_chain('test_tool')

        # Should be in correct order: schema, guard, healing, reflect, observe
        layers = [p.layer for p in chain]
        assert layers == ['schema', 'guard', 'healing', 'reflect', 'observe']


class TestPluginPoolEdgeCases:
    """Test edge cases and error handling"""

    def test_register_plugin_with_none_raises_error(self):
        """Test that registering None raises error"""
        from slotagent.core.plugin_pool import PluginPool

        pool = PluginPool()

        with pytest.raises((ValueError, TypeError)):
            pool.register_global_plugin(None)

    def test_get_plugin_with_invalid_layer_raises_error(self):
        """Test that querying with invalid layer raises error"""
        from slotagent.core.plugin_pool import PluginPool

        pool = PluginPool()

        with pytest.raises(ValueError, match="Invalid layer"):
            pool.get_plugin('invalid_layer')

    def test_register_tool_plugins_empty_config(self):
        """Test registering tool with empty plugin config"""
        from slotagent.core.plugin_pool import PluginPool

        pool = PluginPool()

        # Should not raise error
        pool.register_tool_plugins('test_tool', {})

        # Should return None for all layers
        assert pool.get_plugin('schema', 'test_tool') is None
