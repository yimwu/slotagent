# Copyright (c) 2026 SlotAgent Contributors
# Licensed under the MIT License - see LICENSE file for details.
"""
Schema layer plugins - Parameter validation.

Provides JSON Schema-based parameter validation with different strictness levels.
"""

from typing import Any, Dict

from slotagent.interfaces import PluginInterface
from slotagent.types import PluginContext, PluginResult


def _validate_simple_schema(params: Dict[str, Any], schema: Dict[str, Any]) -> tuple[bool, str]:
    """
    Simple JSON Schema validation implementation.

    Args:
        params: Parameters to validate
        schema: JSON Schema definition

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not schema or schema == {}:
        return True, ""

    # Validate required fields
    required = schema.get("required", [])
    for field in required:
        if field not in params:
            return False, f"Required field '{field}' is missing"

    # Validate properties
    properties = schema.get("properties", {})
    for key, value in params.items():
        if key not in properties:
            continue

        prop_schema = properties[key]
        expected_type = prop_schema.get("type")

        # Type validation
        if expected_type:
            if expected_type == "string" and not isinstance(value, str):
                return False, f"Field '{key}' must be string, got {type(value).__name__}"
            elif expected_type == "integer" and not isinstance(value, int):
                return False, f"Field '{key}' must be integer, got {type(value).__name__}"
            elif expected_type == "number" and not isinstance(value, (int, float)):
                return False, f"Field '{key}' must be number, got {type(value).__name__}"
            elif expected_type == "boolean" and not isinstance(value, bool):
                return False, f"Field '{key}' must be boolean, got {type(value).__name__}"
            elif expected_type == "object" and not isinstance(value, dict):
                return False, f"Field '{key}' must be object, got {type(value).__name__}"
            elif expected_type == "array" and not isinstance(value, list):
                return False, f"Field '{key}' must be array, got {type(value).__name__}"

        # Minimum validation
        if "minimum" in prop_schema:
            if isinstance(value, (int, float)) and value < prop_schema["minimum"]:
                return False, f"Field '{key}' must be >= {prop_schema['minimum']}"

        # Maximum validation
        if "maximum" in prop_schema:
            if isinstance(value, (int, float)) and value > prop_schema["maximum"]:
                return False, f"Field '{key}' must be <= {prop_schema['maximum']}"

        # Enum validation
        if "enum" in prop_schema:
            if value not in prop_schema["enum"]:
                return False, f"Field '{key}' must be one of {prop_schema['enum']}"

        # Pattern validation (simple)
        if "pattern" in prop_schema and isinstance(value, str):
            import re

            if not re.match(prop_schema["pattern"], value):
                return False, f"Field '{key}' does not match pattern {prop_schema['pattern']}"

        # Nested object validation
        if expected_type == "object" and isinstance(value, dict):
            is_valid, error = _validate_simple_schema(value, prop_schema)
            if not is_valid:
                return False, f"Field '{key}': {error}"

    return True, ""


class SchemaDefault(PluginInterface):
    """
    Default Schema validation plugin - basic JSON Schema validation.

    Validates parameters against JSON Schema but allows additional properties.
    Suitable for lightweight tools where strict validation is not required.

    Examples:
        >>> plugin = SchemaDefault(schema={
        ...     'type': 'object',
        ...     'properties': {'location': {'type': 'string'}},
        ...     'required': ['location']
        ... })
        >>> result = plugin.execute(context)
    """

    layer = "schema"
    plugin_id = "schema_default"

    def __init__(self, schema: Dict[str, Any] = None):
        """
        Initialize SchemaDefault plugin.

        Args:
            schema: JSON Schema definition
        """
        self.schema = schema or {}

    def validate(self) -> bool:
        """Validate plugin configuration"""
        return True

    def execute(self, context: PluginContext) -> PluginResult:
        """
        Execute schema validation.

        Args:
            context: Plugin execution context

        Returns:
            PluginResult with validation status
        """
        # Use tool's input_schema if no explicit schema was set
        schema = self.schema
        if not schema and context.tool_schema:
            schema = context.tool_schema

        is_valid, error_msg = _validate_simple_schema(context.params, schema)

        if not is_valid:
            return PluginResult(
                success=False, should_continue=False, error=error_msg, error_type="ValidationError"
            )

        return PluginResult(success=True, data={"validated": True, "params": context.params})


class SchemaStrict(PluginInterface):
    """
    Strict Schema validation plugin - enforces additional properties restriction.

    Validates parameters against JSON Schema and rejects additional properties
    not defined in the schema. Suitable for high-security tools.

    Examples:
        >>> plugin = SchemaStrict(schema={
        ...     'type': 'object',
        ...     'properties': {'location': {'type': 'string'}}
        ... })
        >>> result = plugin.execute(context)
    """

    layer = "schema"
    plugin_id = "schema_strict"

    def __init__(self, schema: Dict[str, Any] = None):
        """
        Initialize SchemaStrict plugin.

        Args:
            schema: JSON Schema definition
        """
        self.schema = schema or {}

    def validate(self) -> bool:
        """Validate plugin configuration"""
        return True

    def execute(self, context: PluginContext) -> PluginResult:
        """
        Execute strict schema validation.

        Args:
            context: Plugin execution context

        Returns:
            PluginResult with validation status
        """
        # Check for additional properties not in schema
        properties = self.schema.get("properties", {})
        for key in context.params.keys():
            if key not in properties:
                return PluginResult(
                    success=False,
                    should_continue=False,
                    error=f"Additional property '{key}' not allowed in strict mode",
                    error_type="ValidationError",
                )

        # Run standard validation
        is_valid, error_msg = _validate_simple_schema(context.params, self.schema)

        if not is_valid:
            return PluginResult(
                success=False, should_continue=False, error=error_msg, error_type="ValidationError"
            )

        return PluginResult(success=True, data={"validated": True, "params": context.params})
