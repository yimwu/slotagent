# Copyright (c) 2026 SlotAgent Contributors
# Licensed under the MIT License - see LICENSE file for details.
"""
Unit tests for Schema plugins.

Tests parameter validation logic for SchemaDefault and SchemaStrict.
"""

import pytest

from slotagent.types import PluginContext
import time
import uuid


class TestSchemaDefault:
    """Test SchemaDefault plugin - basic validation"""

    def test_schema_default_validates_required_params(self):
        """Test that SchemaDefault checks required parameters"""
        from slotagent.plugins.schema import SchemaDefault

        plugin = SchemaDefault(
            schema={
                'type': 'object',
                'properties': {
                    'location': {'type': 'string'}
                },
                'required': ['location']
            }
        )

        # Valid params
        context = PluginContext(
            tool_id='test',
            tool_name='Test',
            params={'location': 'Beijing'},
            layer='schema',
            execution_id=str(uuid.uuid4()),
            timestamp=time.time()
        )

        result = plugin.execute(context)
        assert result.success is True
        assert result.should_continue is True

    def test_schema_default_rejects_missing_required(self):
        """Test that SchemaDefault rejects missing required params"""
        from slotagent.plugins.schema import SchemaDefault

        plugin = SchemaDefault(
            schema={
                'type': 'object',
                'properties': {
                    'location': {'type': 'string'}
                },
                'required': ['location']
            }
        )

        context = PluginContext(
            tool_id='test',
            tool_name='Test',
            params={},  # Missing 'location'
            layer='schema',
            execution_id=str(uuid.uuid4()),
            timestamp=time.time()
        )

        result = plugin.execute(context)
        assert result.success is False
        assert result.should_continue is False
        assert 'location' in result.error.lower()
        assert result.error_type == 'ValidationError'

    def test_schema_default_validates_type(self):
        """Test that SchemaDefault validates parameter types"""
        from slotagent.plugins.schema import SchemaDefault

        plugin = SchemaDefault(
            schema={
                'type': 'object',
                'properties': {
                    'count': {'type': 'integer'}
                }
            }
        )

        # Wrong type
        context = PluginContext(
            tool_id='test',
            tool_name='Test',
            params={'count': 'not_an_integer'},
            layer='schema',
            execution_id=str(uuid.uuid4()),
            timestamp=time.time()
        )

        result = plugin.execute(context)
        assert result.success is False
        assert result.should_continue is False
        assert result.error_type == 'ValidationError'

    def test_schema_default_validates_minimum(self):
        """Test that SchemaDefault validates minimum constraint"""
        from slotagent.plugins.schema import SchemaDefault

        plugin = SchemaDefault(
            schema={
                'type': 'object',
                'properties': {
                    'age': {'type': 'integer', 'minimum': 0}
                }
            }
        )

        # Below minimum
        context = PluginContext(
            tool_id='test',
            tool_name='Test',
            params={'age': -5},
            layer='schema',
            execution_id=str(uuid.uuid4()),
            timestamp=time.time()
        )

        result = plugin.execute(context)
        assert result.success is False
        assert result.should_continue is False

    def test_schema_default_allows_empty_schema(self):
        """Test that SchemaDefault works with empty schema (no validation)"""
        from slotagent.plugins.schema import SchemaDefault

        plugin = SchemaDefault(schema={})

        context = PluginContext(
            tool_id='test',
            tool_name='Test',
            params={'any': 'value'},
            layer='schema',
            execution_id=str(uuid.uuid4()),
            timestamp=time.time()
        )

        result = plugin.execute(context)
        assert result.success is True

    def test_schema_default_validation_passes(self):
        """Test that validate() method returns True"""
        from slotagent.plugins.schema import SchemaDefault

        plugin = SchemaDefault(schema={})
        assert plugin.validate() is True


class TestSchemaStrict:
    """Test SchemaStrict plugin - strict validation"""

    def test_schema_strict_rejects_additional_properties(self):
        """Test that SchemaStrict rejects additional properties by default"""
        from slotagent.plugins.schema import SchemaStrict

        plugin = SchemaStrict(
            schema={
                'type': 'object',
                'properties': {
                    'location': {'type': 'string'}
                }
            }
        )

        # Has additional property
        context = PluginContext(
            tool_id='test',
            tool_name='Test',
            params={'location': 'Beijing', 'extra': 'value'},
            layer='schema',
            execution_id=str(uuid.uuid4()),
            timestamp=time.time()
        )

        result = plugin.execute(context)
        assert result.success is False
        assert result.should_continue is False
        assert 'additional' in result.error.lower() or 'extra' in result.error.lower()

    def test_schema_strict_enforces_pattern(self):
        """Test that SchemaStrict enforces pattern matching"""
        from slotagent.plugins.schema import SchemaStrict

        plugin = SchemaStrict(
            schema={
                'type': 'object',
                'properties': {
                    'email': {'type': 'string', 'pattern': r'^[\w\.-]+@[\w\.-]+\.\w+$'}
                }
            }
        )

        # Invalid email pattern
        context = PluginContext(
            tool_id='test',
            tool_name='Test',
            params={'email': 'invalid-email'},
            layer='schema',
            execution_id=str(uuid.uuid4()),
            timestamp=time.time()
        )

        result = plugin.execute(context)
        assert result.success is False
        assert result.should_continue is False

    def test_schema_strict_validates_enum(self):
        """Test that SchemaStrict validates enum values"""
        from slotagent.plugins.schema import SchemaStrict

        plugin = SchemaStrict(
            schema={
                'type': 'object',
                'properties': {
                    'status': {'type': 'string', 'enum': ['active', 'inactive']}
                }
            }
        )

        # Invalid enum value
        context = PluginContext(
            tool_id='test',
            tool_name='Test',
            params={'status': 'pending'},
            layer='schema',
            execution_id=str(uuid.uuid4()),
            timestamp=time.time()
        )

        result = plugin.execute(context)
        assert result.success is False
        assert result.should_continue is False

    def test_schema_strict_validates_nested_objects(self):
        """Test that SchemaStrict validates nested objects"""
        from slotagent.plugins.schema import SchemaStrict

        plugin = SchemaStrict(
            schema={
                'type': 'object',
                'properties': {
                    'user': {
                        'type': 'object',
                        'properties': {
                            'name': {'type': 'string'},
                            'age': {'type': 'integer'}
                        },
                        'required': ['name']
                    }
                }
            }
        )

        # Missing nested required field
        context = PluginContext(
            tool_id='test',
            tool_name='Test',
            params={'user': {'age': 25}},  # Missing 'name'
            layer='schema',
            execution_id=str(uuid.uuid4()),
            timestamp=time.time()
        )

        result = plugin.execute(context)
        assert result.success is False
        assert result.should_continue is False


class TestSchemaPluginAttributes:
    """Test plugin class attributes"""

    def test_schema_default_has_correct_attributes(self):
        """Test SchemaDefault has correct layer and plugin_id"""
        from slotagent.plugins.schema import SchemaDefault

        assert SchemaDefault.layer == 'schema'
        assert SchemaDefault.plugin_id == 'schema_default'

    def test_schema_strict_has_correct_attributes(self):
        """Test SchemaStrict has correct layer and plugin_id"""
        from slotagent.plugins.schema import SchemaStrict

        assert SchemaStrict.layer == 'schema'
        assert SchemaStrict.plugin_id == 'schema_strict'
