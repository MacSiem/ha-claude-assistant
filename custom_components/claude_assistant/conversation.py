"""Conversation agent for Claude Assistant integration."""

import logging
from typing import Any, Optional

from homeassistant.components import conversation
from homeassistant.core import HomeAssistant
from homeassistant.helpers.intent import IntentHandler

from .api_client import ClaudeAPIClient
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class ClaudeConversationAgent(conversation.AbstractConversationAgent):
    """Conversation agent powered by Claude."""

    def __init__(self, hass: HomeAssistant, api_client: ClaudeAPIClient) -> None:
        """Initialize the conversation agent.

        Args:
            hass: Home Assistant instance
            api_client: Claude API client
        """
        self.hass = hass
        self.api_client = api_client
        self._conversation_history: list[dict[str, str]] = []

    @property
    def supported_languages(self) -> list[str]:
        """Return list of supported languages."""
        return ["en"]

    async def async_process(
        self,
        user_input: conversation.ConversationInput,
    ) -> conversation.ConversationResult:
        """Process a user input and generate a response.

        Args:
            user_input: The user input to process

        Returns:
            Conversation result with response
        """
        try:
            # Get Home Assistant state for context
            ha_state = self._get_ha_state()

            # Get Claude configuration
            config_entry = None
            if DOMAIN in self.hass.data:
                config_entry = self.hass.data[DOMAIN].get("config_entry")

            safety_level = "dangerous_only"
            if config_entry:
                safety_level = config_entry.options.get(
                    "safety_level", "dangerous_only"
                )

            # Build system prompt
            system_prompt = self.api_client.build_system_prompt(
                ha_state,
                custom_instructions=(
                    "You are assisting via the Home Assistant voice assistant. "
                    "Be concise and direct. Focus on answering the user's question."
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
            tools = self.api_client.build_tools()

            # Send to Claude
            response = await self.api_client.async_send_message(
                messages=self._conversation_history,
                system_prompt=system_prompt,
                tools=tools,
            )

            if not response.get("success"):
                return conversation.ConversationResult(
                    response=f"Error: {response.get('error', 'Unknown error')}",
                    conversation_id=user_input.conversation_id,
                )

            # Extract text response
            text_response = self.api_client.extract_text_response(response)

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
            tool_calls = self.api_client.extract_tool_calls(response)
            if tool_calls:
                _LOGGER.debug("Claude requested tool calls: %s", tool_calls)
                # Tool calls will be handled by the action handler

            return conversation.ConversationResult(
                response=text_response,
                conversation_id=user_input.conversation_id,
            )

        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.error("Error processing conversation: %s", err)
            return conversation.ConversationResult(
                response="I encountered an error processing your request. Please try again.",
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


async def async_setup_agent(
    hass: HomeAssistant,
    api_client: ClaudeAPIClient,
) -> None:
    """Set up the Claude conversation agent.

    Args:
        hass: Home Assistant instance
        api_client: Claude API client
    """
    agent = ClaudeConversationAgent(hass, api_client)

    conversation.async_register_agent(
        hass,
        DOMAIN,
        agent,
        name="Claude Assistant",
        description="Control your smart home with Claude AI",
    )

    _LOGGER.info("Claude conversation agent registered")
