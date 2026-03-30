# Copyright (c) 2026 SlotAgent Contributors
# Licensed under the MIT License - see LICENSE file for details.
"""
HookManager - Event subscription and dispatching.

Manages hook event subscriptions and emits events to subscribers.
Thread-safe implementation with exception isolation.
"""

import logging
import threading
from typing import Callable, Dict, List, Optional

from slotagent.types import HookEvent

# Type alias for hook handler
HookHandler = Callable[[HookEvent], None]


class HookManager:
    """
    Hook manager for event subscription and dispatching.

    Provides thread-safe event pub-sub mechanism for observability.
    Subscribers can listen to tool execution lifecycle events.

    Examples:
        >>> manager = HookManager()
        >>> def log_handler(event):
        ...     print(f"Event: {event.event_type}")
        >>> manager.subscribe('before_exec', log_handler)
        >>> manager.emit(BeforeExecEvent(...))
    """

    # Valid event types
    VALID_EVENT_TYPES = {
        "before_schema",
        "after_schema",
        "before_guard",
        "before_exec",
        "after_exec",
        "fail",
        "after_healing",
        "retry_started",
        "after_reflect",
        "guard_block",
        "wait_approval",
        "approval_resolved",
    }

    def __init__(self):
        """Initialize HookManager."""
        # Subscribers dictionary: {event_type: [handler1, handler2, ...]}
        self._subscribers: Dict[str, List[HookHandler]] = {
            "before_schema": [],
            "after_schema": [],
            "before_guard": [],
            "before_exec": [],
            "after_exec": [],
            "fail": [],
            "after_healing": [],
            "retry_started": [],
            "after_reflect": [],
            "guard_block": [],
            "wait_approval": [],
            "approval_resolved": [],
        }
        self._lock = threading.Lock()
        self._logger = logging.getLogger("slotagent.hooks")

    def subscribe(self, event_type: str, handler: HookHandler) -> None:
        """
        Subscribe to a hook event.

        Args:
            event_type: Event type to subscribe
            handler: Callable that handles the event

        Raises:
            ValueError: If event_type is invalid

        Examples:
            >>> def my_handler(event):
            ...     print(event.event_type)
            >>> manager.subscribe('before_exec', my_handler)
        """
        if event_type not in self.VALID_EVENT_TYPES:
            raise ValueError(
                f"Invalid event type: {event_type}. " f"Must be one of: {self.VALID_EVENT_TYPES}"
            )

        with self._lock:
            self._subscribers[event_type].append(handler)

    def unsubscribe(self, event_type: str, handler: HookHandler) -> None:
        """
        Unsubscribe from a hook event.

        Args:
            event_type: Event type to unsubscribe
            handler: Handler to remove

        Raises:
            ValueError: If event_type is invalid

        Examples:
            >>> manager.unsubscribe('before_exec', my_handler)
        """
        if event_type not in self.VALID_EVENT_TYPES:
            raise ValueError(
                f"Invalid event type: {event_type}. " f"Must be one of: {self.VALID_EVENT_TYPES}"
            )

        with self._lock:
            if handler in self._subscribers[event_type]:
                self._subscribers[event_type].remove(handler)

    def emit(self, event: HookEvent) -> None:
        """
        Emit a hook event to all subscribers.

        Calls all subscribers synchronously. If a subscriber raises
        an exception, it is logged but does not affect other subscribers
        or the main flow.

        Args:
            event: Hook event to emit

        Examples:
            >>> event = BeforeExecEvent(...)
            >>> manager.emit(event)
        """
        event_type = event.event_type

        # Get subscribers (thread-safe copy)
        with self._lock:
            subscribers = self._subscribers.get(event_type, []).copy()

        # Dispatch to each subscriber
        for handler in subscribers:
            try:
                handler(event)
            except Exception as e:
                # Log error but don't re-raise
                self._logger.error(
                    f"Hook handler error for {event_type}: {e}",
                    exc_info=True,
                    extra={
                        "event_type": event_type,
                        "execution_id": getattr(event, "execution_id", None),
                        "handler": getattr(handler, "__name__", str(handler)),
                    },
                )

    def clear_subscribers(self, event_type: Optional[str] = None) -> None:
        """
        Clear all subscribers for an event type (or all events).

        Args:
            event_type: Event type to clear (None = all)

        Examples:
            >>> # Clear specific event
            >>> manager.clear_subscribers('before_exec')
            >>> # Clear all events
            >>> manager.clear_subscribers()
        """
        with self._lock:
            if event_type is None:
                # Clear all
                for key in self._subscribers:
                    self._subscribers[key].clear()
            else:
                if event_type in self._subscribers:
                    self._subscribers[event_type].clear()

    def get_subscriber_count(self, event_type: str) -> int:
        """
        Get number of subscribers for an event type.

        Args:
            event_type: Event type

        Returns:
            Number of subscribers

        Examples:
            >>> count = manager.get_subscriber_count('before_exec')
        """
        with self._lock:
            return len(self._subscribers.get(event_type, []))
