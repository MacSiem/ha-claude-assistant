"""Anthropic API client for Claude Assistant integration."""

import json
import logging
from typing import Any, Optional

from anthropic import AsyncAnthropic, APIError

from .const import (
    AUTH_TYPE_API_KEY,
    AUTH_TYPE_PERSONAL,
    CLAUDE_MODELS,
    DEFAULT_MAX_TOKENS,
    DEFAULT_SYSTEM_PROMPT,
    DEFAULT_TEMPERATURE,
)

_LOGGER = logging.getLogger(__name__)


class ClaudeAPIClient:
    """Client for interacting with Anthropic Claude API."""

    def __init__(
        self,
        api_key: str,
        model: str = "claude-opus-4-20250514",
        auth_type: str = AUTH_TYPE_API_KEY,
    ) -> None:
        """Initialize the Claude API client.

        Note: Does NOT create the AsyncAnthropic client immediately to avoid
        blocking SSL calls in the event loop. Call async_init() before use.
        """
        self._api_key = api_key
        self._auth_type = auth_type
        self.client: Optional[AsyncAnthropic] = None
        self.model = model if model in CLAUDE_MODELS else CLAUDE_MODELS[0]
        self._message_count = 0

    async def async_init(self, hass) -> None:
        """Initialize the async client (must be called from event loop).

        Creates the AsyncAnthropic client in an executor to avoid blocking
        the event loop with SSL initialization.
        """
        def _create_client():
            if self._auth_type == AUTH_TYPE_PERSONAL:
                # For personal accounts, use session key as API key
                # This works if user provides an API-compatible key
                return AsyncAnthropic(api_key=self._api_key)
            else:
                return AsyncAnthropic(api_key=self._api_key)

        self.client = await hass.async_add_executor_job(_create_client)
        _LOGGER.debug("AsyncAnthropic client initialized (auth: %s)", self._auth_type)

    def _ensure_client(self) -> AsyncAnthropic:
        """Ensure the client is initialized."""
        if self.client is None:
            raise RuntimeError(
                "API client not initialized. Call async_init() first."
            )
        return self.client

    async def validate_api_key(self) -> bool:
        """Validate the API key by making a minimal request."""
        client = self._ensure_client()
        try:
            response = await client.messages.create(
                model=self.model,
                max_tokens=10,
                messages=[{"role": "user", "content": "Hi"}],
            )
            return True
        except APIError as err:
            if err.status_code == 401:
                _LOGGER.error("Invalid API key: authentication failed")
                return False
            _LOGGER.error("API error during validation: %s", err)
            return False
        except Exception as err:
            _LOGGER.error("Unexpected error validating API key: %s", err)
            return False

    async def send_message(
        self,
        message: str,
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
        conversation_history: Optional[list[dict]] = None,
        temperature: float = DEFAULT_TEMPERATURE,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ) -> dict[str, Any]:
        """Send a message to Claude and return the response with metadata.

        Returns:
            dict with keys: text, input_tokens, output_tokens, model, stop_reason
        """
        client = self._ensure_client()

        # Build messages list
        messages = []
        if conversation_history:
            messages.extend(conversation_history)
        messages.append({"role": "user", "content": message})

        try:
            response = await client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt,
                messages=messages,
            )

            self._message_count += 1

            # Extract text from response
            text = ""
            for block in response.content:
                if hasattr(block, "text"):
                    text += block.text

            # Extract usage info
            input_tokens = getattr(response.usage, "input_tokens", 0)
            output_tokens = getattr(response.usage, "output_tokens", 0)

            return {
                "text": text,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "model": response.model,
                "stop_reason": response.stop_reason,
                "message_count": self._message_count,
            }

        except APIError as err:
            _LOGGER.error("Anthropic API error: %s (status: %s)", err.message, err.status_code)
            raise
        except Exception as err:
            _LOGGER.error("Error sending message to Claude: %s", err)
            raise

    async def send_message_stream(
        self,
        message: str,
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
        conversation_history: Optional[list[dict]] = None,
        temperature: float = DEFAULT_TEMPERATURE,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ):
        """Send a message and stream the response (generator).

        Yields partial text chunks as they arrive.
        """
        client = self._ensure_client()

        messages = []
        if conversation_history:
            messages.extend(conversation_history)
        messages.append({"role": "user", "content": message})

        try:
            async with client.messages.stream(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt,
                messages=messages,
            ) as stream:
                async for text in stream.text_stream:
                    yield text

            self._message_count += 1

        except APIError as err:
            _LOGGER.error("Streaming API error: %s", err.message)
            raise
        except Exception as err:
            _LOGGER.error("Streaming error: %s", err)
            raise

    @property
    def message_count(self) -> int:
        """Return total messages sent."""
        return self._message_count
