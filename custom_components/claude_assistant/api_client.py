"""Anthropic API client for Claude Assistant integration."""

import json
import logging
from typing import Any, Optional

from anthropic import AsyncAnthropic, APIError

from .const import CLAUDE_MODELS, DEFAULT_SYSTEM_PROMPT

_LOGGER = logging.getLogger(__name__)


class ClaudeAPIClient:
    """Client for interacting with Anthropic Claude API."""

    def __init__(self, api_key: str, model: str = "claude-opus-4-20250514") -> None:
        """Initialize the Claude API client.

        Note: Does NOT create the AsyncAnthropic client immediately to avoid
        blocking SSL calls in the event loop. Call async_init() before use.

        Args:
            api_key: Anthropic API key
            model: Claude model to use
        """
        self._api_key = api_key
        self.client: Optional[AsyncAnthropic] = None
        self.model = model if model in CLAUDE_MODELS else CLAUDE_MODELS[0]
        self._message_count = 0

    async def async_init(self, hass=None) -> None:
        """Initialize the async client in an executor to avoid blocking calls.

        Args:
            hass: HomeAssistant instance (optional, uses executor if provided)
        """
        if self.client is not None:
            return

        def _create_client():
            return AsyncAnthropic(api_key=self._api_key)

        if hass is not None:
            self.client = await hass.async_add_executor_job(_create_client)
        else:
            import asyncio
            loop = asyncio.get_event_loop()
            self.client = await loop.run_in_executor(None, _create_client)

    def _ensure_client(self) -> AsyncAnthropic:
        """Ensure client is initialized.

        Returns:
            The AsyncAnthropic client

        Raises:
            RuntimeError: If async_init() was not called
        """
        if self.client is None:
            raise RuntimeError(
                "ClaudeAPIClient.async_init() must be called before use"
            )
        return self.client

    async def async_validate_api_key(self) -> bool:
        """Validate the API key by making a test call.

        Returns:
            True if API key is valid, False otherwise
        """
        try:
            client = self._ensure_client()
            await client.messages.create(
                model=self.model,
                max_tokens=10,
                messages=[
                    {
                        "role": "user",
                        "content": "Reply with just 'OK'",
                    }
                ],
            )
            return True
        except APIError as err:
            _LOGGER.error("API key validation failed: %s", err)
            return False

    async def async_send_message(
        self,
        messages: list[dict[str, str]],
        system_prompt: Optional[str] = None,
        tools: Optional[list[dict[str, Any]]] = None,
    ) -> dict[str, Any]:
        """Send a message to Claude and get a response.

        Args:
            messages: List of message dicts with 'role' and 'content'
            system_prompt: System prompt for the conversation
            tools: Optional list of tool definitions

        Returns:
            Response dict with content and metadata
        """
        try:
            self._message_count += 1

            client = self._ensure_client()

            kwargs = {
                "model": self.model,
                "max_tokens": 2048,
                "messages": messages,
            }

            if system_prompt:
                kwargs["system"] = system_prompt

            if tools:
                kwargs["tools"] = tools

            response = await client.messages.create(**kwargs)

            return {
                "success": True,
                "content": response.content,
                "stop_reason": response.stop_reason,
                "usage": {
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                },
            }
        except APIError as err:
            _LOGGER.error("API call failed: %s", err)
            return {
                "success": False,
                "error": str(err),
                "content": None,
            }

    def build_system_prompt(
        self, ha_state: dict[str, Any], custom_instructions: Optional[str] = None
    ) -> str:
        """Build system prompt with current Home Assistant state.

        Args:
            ha_state: Dictionary of Home Assistant state
            custom_instructions: Optional custom instructions to append

        Returns:
            Formatted system prompt
        """
        # Summarize key entities
        entity_summary = self._summarize_entities(ha_state)

        prompt = DEFAULT_SYSTEM_PROMPT.format(ha_state=entity_summary)

        if custom_instructions:
            prompt += f"\n\nAdditional Instructions:\n{custom_instructions}"

        return prompt

    @staticmethod
    def _summarize_entities(ha_state: dict[str, Any]) -> str:
        """Summarize Home Assistant entities for context.

        Args:
            ha_state: Dictionary of Home Assistant state

        Returns:
            Formatted summary of important entities
        """
        summary_parts = []

        # Get important entity types
        important_domains = [
            "light",
            "switch",
            "climate",
            "lock",
            "cover",
            "alarm_control_panel",
            "automation",
            "scene",
        ]

        for domain in important_domains:
            entities_in_domain = {
                eid: state
                for eid, state in ha_state.items()
                if eid.startswith(f"{domain}.")
            }

            if entities_in_domain:
                summary_parts.append(f"\n{domain.upper()}:")
                for eid, state in list(entities_in_domain.items())[:5]:  # Limit to 5 per domain
                    state_str = state.get("state", "unknown")
                    name = state.get("attributes", {}).get("friendly_name", eid)
                    summary_parts.append(f"  - {name}: {state_str}")

                if len(entities_in_domain) > 5:
                    summary_parts.append(f"  ... and {len(entities_in_domain) - 5} more")

        return "\n".join(summary_parts) if summary_parts else "No entities available"

    @staticmethod
    def build_tools() -> list[dict[str, Any]]:
        """Build tool definitions for Claude.

        Returns:
            List of tool definitions in Anthropic format
        """
        return [
            {
                "name": "call_service",
                "description": "Call a Home Assistant service to control a device",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "domain": {
                            "type": "string",
                            "description": "Service domain (e.g., 'light', 'switch')",
                        },
                        "service": {
                            "type": "string",
                            "description": "Service name (e.g., 'turn_on', 'turn_off')",
                        },
                        "entity_id": {
                            "type": "string",
                            "description": "Target entity ID or list of entity IDs",
                        },
                        "data": {
                            "type": "object",
                            "description": "Additional service call data",
                        },
                    },
                    "required": ["domain", "service"],
                },
            },
            {
                "name": "get_state",
                "description": "Get the state of a specific entity",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "entity_id": {
                            "type": "string",
                            "description": "Entity ID to query",
                        },
                    },
                    "required": ["entity_id"],
                },
            },
            {
                "name": "get_history",
                "description": "Get recent state history for an entity",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "entity_id": {
                            "type": "string",
                            "description": "Entity ID to get history for",
                        },
                        "hours": {
                            "type": "integer",
                            "description": "Number of hours of history to retrieve",
                        },
                    },
                    "required": ["entity_id"],
                },
            },
            {
                "name": "analyze_energy",
                "description": "Analyze energy consumption patterns",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "timeframe": {
                            "type": "string",
                            "description": "Time period (daily, weekly, monthly)",
                        },
                    },
                },
            },
            {
                "name": "set_automation",
                "description": "Create or update an automation rule",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Automation name",
                        },
                        "trigger": {
                            "type": "object",
                            "description": "Trigger definition",
                        },
                        "action": {
                            "type": "object",
                            "description": "Action to execute",
                        },
                    },
                    "required": ["name", "trigger", "action"],
                },
            },
        ]

    @staticmethod
    def extract_tool_calls(response: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract tool calls from API response.

        Args:
            response: Response from API

        Returns:
            List of tool calls with name and input
        """
        tool_calls = []

        if not response.get("success") or not response.get("content"):
            return tool_calls

        for content_block in response["content"]:
            if hasattr(content_block, "type") and content_block.type == "tool_use":
                tool_calls.append(
                    {
                        "id": content_block.id,
                        "name": content_block.name,
                        "input": content_block.input,
                    }
                )

        return tool_calls

    @staticmethod
    def extract_text_response(response: dict[str, Any]) -> str:
        """Extract text content from API response.

        Args:
            response: Response from API

        Returns:
            Text response content
        """
        if not response.get("success") or not response.get("content"):
            return "No response received"

        text_parts = []

        for content_block in response["content"]:
            if hasattr(content_block, "type") and content_block.type == "text":
                text_parts.append(content_block.text)

        return "".join(text_parts) if text_parts else "No text response"
