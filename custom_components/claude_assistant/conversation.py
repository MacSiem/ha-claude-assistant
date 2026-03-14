"""Conversation platform for Claude Assistant integration."""

import logging
import time
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
from .const import (
    DEFAULT_MAX_TOKENS,
    DEFAULT_SYSTEM_PROMPT,
    DEFAULT_TEMPERATURE,
    DOMAIN,
    MAX_CONVERSATION_HISTORY,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Claude conversation entity from a config entry."""
    data = hass.data[DOMAIN]
    api_client = data["api_client"]

    async_add_entities(
        [ClaudeConversationEntity(hass, config_entry, api_client)]
    )
    _LOGGER.info("Claude conversation entity registered")


class ClaudeConversationEntity(ConversationEntity):
    """Conversation entity for Claude Assistant."""

    _attr_has_entity_name = True
    _attr_name = "Claude Assistant"

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        api_client: ClaudeAPIClient,
    ) -> None:
        """Initialize the conversation entity."""
        self.hass = hass
        self._api_client = api_client
        self._config_entry = config_entry
        self._attr_unique_id = config_entry.entry_id
        self._conversation_history: list[dict] = []

    @property
    def supported_languages(self) -> list[str] | str:
        """Return supported languages (all)."""
        return "*"

    def _get_settings(self) -> dict:
        """Get current settings from integration data."""
        data = self.hass.data.get(DOMAIN, {})
        return data.get("settings", {})

    def _build_system_prompt(self) -> str:
        """Build system prompt including HA entity context."""
        settings = self._get_settings()
        base_prompt = settings.get("system_prompt", DEFAULT_SYSTEM_PROMPT)

        # Gather entity info for context
        entity_summary = []
        for state in self.hass.states.async_all():
            friendly = state.attributes.get("friendly_name", state.entity_id)
            entity_summary.append(
                f"- {friendly} ({state.entity_id}): {state.state}"
            )

        entities_text = "\n".join(entity_summary[:100])

        return (
            f"{base_prompt}\n\n"
            f"## Available Home Assistant Entities:\n{entities_text}\n\n"
            f"Current time: {self.hass.states.get('sensor.date_time_iso', 'unknown')}"
        )

    async def async_process(
        self, user_input: ConversationInput
    ) -> ConversationResult:
        """Process a sentence."""
        settings = self._get_settings()
        temperature = settings.get("temperature", DEFAULT_TEMPERATURE)
        max_tokens = settings.get("max_tokens", DEFAULT_MAX_TOKENS)

        start_time = time.time()

        try:
            # Build system prompt with HA context
            system_prompt = self._build_system_prompt()

            # Add to conversation history
            self._conversation_history.append({
                "role": "user",
                "content": user_input.text,
            })

            # Trim history
            if len(self._conversation_history) > MAX_CONVERSATION_HISTORY:
                self._conversation_history = self._conversation_history[
                    -MAX_CONVERSATION_HISTORY:
                ]

            # Send to Claude
            response = await self._api_client.send_message(
                message=user_input.text,
                system_prompt=system_prompt,
                conversation_history=self._conversation_history[:-1],
                temperature=temperature,
                max_tokens=max_tokens,
            )

            text_response = response.get("text", "Sorry, I could not generate a response.")
            tokens_in = response.get("input_tokens", 0)
            tokens_out = response.get("output_tokens", 0)
            elapsed_ms = int((time.time() - start_time) * 1000)

            # Add assistant response to history
            self._conversation_history.append({
                "role": "assistant",
                "content": text_response,
            })

            # Log and update stats via integration data
            data = self.hass.data.get(DOMAIN, {})
            if data:
                # Import helpers from __init__
                from . import _add_log_entry, _update_stats

                await _add_log_entry(self.hass, {
                    "type": "assist_conversation",
                    "user_message": user_input.text,
                    "assistant_message": text_response[:500],
                    "model": settings.get("model", "unknown"),
                    "tokens_in": tokens_in,
                    "tokens_out": tokens_out,
                    "response_time_ms": elapsed_ms,
                    "language": user_input.language,
                })

                await _update_stats(
                    self.hass,
                    tokens_in,
                    tokens_out,
                    elapsed_ms,
                    settings.get("model", "unknown"),
                )

        except Exception as err:
            _LOGGER.error("Error processing conversation: %s", err)
            text_response = f"Sorry, an error occurred: {str(err)}"

        # Build intent response
        intent_response = intent.IntentResponse(language=user_input.language)
        intent_response.async_set_speech(text_response)

        return ConversationResult(
            response=intent_response,
            conversation_id=user_input.conversation_id,
        )
