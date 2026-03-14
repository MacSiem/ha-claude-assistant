"""Conversation platform for Claude Assistant integration."""

import logging
from typing import Any, Optional

from homeassistant.components.conversation import (
    ConversationEntity,
    ConversationInput,
    ConversationResult,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import intent
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api_client import ClaudeAPIClient
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Claude conversation entity from a config entry.

    Args:
        hass: Home Assistant instance
        config_entry: Configuration entry
        async_add_entities: Callback to add entities
    """
    data = hass.data[DOMAIN]
    api_client = data["api_client"]

    async_add_entities(
        [ClaudeConversationEntity(hass, config_entry, api_client)]
    )

    _LOGGER.info("Claude conversation entity registered")


class ClaudeConversationEntity(ConversationEntity):
    """Conversation entity powered by Claude."""

    _attr_has_entity_name = True
    _attr_name = "Claude Assistant"

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        api_client: ClaudeAPIClient,
    ) -> None:
        """Initialize the conversation entity.

        Args:
            hass: Home Assistant instance
            config_entry: Configuration entry
            api_client: Claude API client
        """
        self.hass = hass
        self._api_client = api_client
        self._config_entry = config_entry
        self._attr_unique_id = config_entry.entry_id
        self._conversation_history: list[dict[str, str]] = []

    @property
    def supported_languages(self) -> list[str] | str:
        """Return list of supported languages."""
        return "*"

    async def async_process(
        self,
        user_input: ConversationInput,
    ) -> ConversationResult:
        """Process a user input and generate a response.

        Args:
            user_input: The user input to process

        Returns:
            Conversation result with response
        """
        try:
            # Get Home Assistant state for context
            ha_state = self._get_ha_state()

            # Get safety level
            safety_level = "dangerous_only"
            if self._config_entry:
                safety_level = self._config_entry.options.get(
                    "safety_level", "dangerous_only"
                )

            # Build system prompt
            system_prompt = self._api_client.build_system_prompt(
                ha_state,
                custom_instructions=(
                    "You are assisting via the Home Assistant voice assistant. "
                    "Be concise and direct. Focus on answering the user's question. "
                    f"Respond in the user's language: {user_input.language}."
                ),
            )

            # Add to conversation history
            self._conversation_history.append(
                {
                    "role": "user",
                    "content": user_input.text,
                }
            )

            # Get tools if action execution is needed
            tools = self._api_client.build_tools()

            # Send to Claude
            response = await self._api_client.async_send_message(
                messages=self._conversation_history,
                system_prompt=system_prompt,
                tools=tools,
            )

            if not response.get("success"):
                error_text = f"Error: {response.get('error', 'Unknown error')}"
                intent_response = intent.IntentResponse(language=user_input.language)
                intent_response.async_set_speech(error_text)
                return ConversationResult(
                    response=intent_response,
                    conversation_id=user_input.conversation_id,
                )

            # Extract text response
            text_response = self._api_client.extract_text_response(response)

            # Add Claude's response to history
            self._conversation_history.append(
                {
                    "role": "assistant",
                    "content": text_response,
                }
            )

            # Keep history within limits
            if len(self._conversation_history) > 20:
                self._conversation_history = self._conversation_history[-20:]

            # Process tool calls if any
            tool_calls = self._api_client.extract_tool_calls(response)
            if tool_calls:
                _LOGGER.debug("Claude requested tool calls: %s", tool_calls)

            # Return conversation result
            intent_response = intent.IntentResponse(language=user_input.language)
            intent_response.async_set_speech(text_response)
            return ConversationResult(
                response=intent_response,
                conversation_id=user_input.conversation_id,
            )

        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.error("Error processing conversation: %s", err)
            intent_response = intent.IntentResponse(language=user_input.language)
            intent_response.async_set_speech(
                "I encountered an error processing your request. Please try again."
            )
            return ConversationResult(
                response=intent_response,
                conversation_id=user_input.conversation_id,
            )

    def _get_ha_state(self) -> dict[str, Any]:
        """Get current Home Assistant state.

        Returns:
            Dictionary of entity states
        """
        state_dict = {}

        for entity_id in self.hass.states.async_entity_ids():
            state = self.hass.states.get(entity_id)
            if state:
                state_dict[entity_id] = {
                    "state": state.state,
                    "attributes": dict(state.attributes),
                }

        return state_dict
