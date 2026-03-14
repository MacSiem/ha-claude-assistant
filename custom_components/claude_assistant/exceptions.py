"""Exceptions for Claude Assistant integration."""

from homeassistant.exceptions import HomeAssistantError


class ClaudeAssistantError(HomeAssistantError):
    """Base exception for Claude Assistant."""


class APIError(ClaudeAssistantError):
    """Exception raised for API errors."""


class ActionExecutionError(ClaudeAssistantError):
    """Exception raised when action execution fails."""


class InvalidActionError(ClaudeAssistantError):
    """Exception raised for invalid actions."""


class ActionTimeoutError(ClaudeAssistantError):
    """Exception raised when action confirmation times out."""


class ConfigurationError(ClaudeAssistantError):
    """Exception raised for configuration errors."""
