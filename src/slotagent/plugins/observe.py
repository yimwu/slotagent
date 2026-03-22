# Copyright (c) 2026 SlotAgent Contributors
# Licensed under the MIT License - see LICENSE file for details.
"""
Observe layer plugins - Lifecycle observation.

Provides logging and monitoring capabilities.
"""

import logging

from slotagent.interfaces import PluginInterface
from slotagent.types import PluginContext, PluginResult


class LogPlugin(PluginInterface):
    """
    Log plugin - standard logging output.

    Logs execution information at various log levels.

    Examples:
        >>> plugin = LogPlugin(level='INFO')
    """

    layer = "observe"
    plugin_id = "observe_log"

    def __init__(self, level: str = "INFO", logger_name: str = "slotagent"):
        """
        Initialize LogPlugin.

        Args:
            level: Log level (DEBUG/INFO/WARNING/ERROR)
            logger_name: Logger name
        """
        self.level = getattr(logging, level.upper())
        self.logger = logging.getLogger(logger_name)
        self.logger.setLevel(self.level)

        # Add handler if not exists
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def validate(self) -> bool:
        """Validate plugin configuration"""
        return True

    def execute(self, context: PluginContext) -> PluginResult:
        """
        Execute logging.

        Args:
            context: Plugin execution context

        Returns:
            PluginResult with logged status
        """
        # Log execution info
        self.logger.info(
            f"Tool execution: {context.tool_id} " f"(execution_id={context.execution_id})"
        )

        # Get previous results for logging
        if context.previous_results:
            for layer, data in context.previous_results.items():
                self.logger.debug(f"  {layer}: {data}")

        return PluginResult(
            success=True, data={"logged": True, "execution_id": context.execution_id}
        )
