"""Config flow for Claude Assistant integration."""

import logging
from typing import Any, Optional

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .api_client import ClaudeAPIClient
from .const import (
    CONF_API_KEY,
    CONF_MODEL,
    CONF_SAFETY_LEVEL,
    CLAUDE_MODELS,
    DEFAULT_MODEL,
    DOMAIN,
    SAFETY_LEVELS,
    SAFETY_LEVEL_DANGEROUS,
)

_LOGGER = logging.getLogger(__name__)


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate invalid authentication."""


class ClaudeAssistantConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Claude Assistant integration."""

    VERSION = 1

    async def async_step_user(
        self, user_input: Optional[dict[str, Any]] = None
    ) -> FlowResult:
        """Handle user step (API key input).

        Args:
            user_input: Configuration input from user

        Returns:
            Flow result
        """
        errors = {}

        if user_input is not None:
            try:
                # Validate API key
                api_key = user_input[CONF_API_KEY]
                client = ClaudeAPIClient(api_key)

                is_valid = await client.async_validate_api_key()

                if not is_valid:
                    raise InvalidAuth

                # Check if entry already exists
                await self.async_set_unique_id(DOMAIN)
                self._abort_if_unique_id_configured()

                return await self.async_step_model()

            except InvalidAuth:
                errors["base"] = "invalid_auth"
                _LOGGER.warning("Invalid API key provided")
            except CannotConnect:
                errors["base"] = "cannot_connect"
                _LOGGER.error("Cannot connect to Anthropic API")
            except Exception as err:  # pylint: disable=broad-except
                errors["base"] = "unknown"
                _LOGGER.error("Unexpected error: %s", err)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_API_KEY): str,
                }
            ),
            errors=errors,
            description_placeholders={
                "learn_more": "https://console.anthropic.com/account/keys",
            },
        )

    async def async_step_model(
        self, user_input: Optional[dict[str, Any]] = None
    ) -> FlowResult:
        """Handle model selection step.

        Args:
            user_input: Configuration input from user

        Returns:
            Flow result
        """
        if user_input is not None:
            return await self.async_step_safety()

        return self.async_show_form(
            step_id="model",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_MODEL, default=DEFAULT_MODEL): vol.In(
                        CLAUDE_MODELS
                    ),
                }
            ),
            description_placeholders={
                "models": ", ".join(CLAUDE_MODELS),
            },
        )

    async def async_step_safety(
        self, user_input: Optional[dict[str, Any]] = None
    ) -> FlowResult:
        """Handle safety level configuration step.

        Args:
            user_input: Configuration input from user

        Returns:
            Flow result
        """
        if user_input is not None:
            # Combine all config data
            config_data = {
                CONF_API_KEY: self.hass.config_entries.async_entries(DOMAIN).__iter__().__next__().options.get(
                    CONF_API_KEY,
                    ""
                ) if any(
                    isinstance(x, config_entries.ConfigEntry) for x in [None]
                ) else "",
                CONF_MODEL: self.hass.data.get("claude_model", DEFAULT_MODEL),
                CONF_SAFETY_LEVEL: user_input[CONF_SAFETY_LEVEL],
            }

            # Get the saved API key and model from flow context
            api_key = self.context.get(CONF_API_KEY, "")
            model = self.context.get(CONF_MODEL, DEFAULT_MODEL)

            if not api_key:
                # Retrieve from stored data if available
                for entry in self.hass.config_entries.async_entries(DOMAIN):
                    api_key = entry.data.get(CONF_API_KEY, "")
                    model = entry.data.get(CONF_MODEL, DEFAULT_MODEL)
                    break

            return self.async_create_entry(
                title="Claude Assistant",
                data={
                    CONF_API_KEY: api_key or "",
                    CONF_MODEL: model,
                },
                options={
                    CONF_SAFETY_LEVEL: user_input[CONF_SAFETY_LEVEL],
                },
            )

        return self.async_show_form(
            step_id="safety",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SAFETY_LEVEL, default=SAFETY_LEVEL_DANGEROUS
                    ): vol.In(SAFETY_LEVELS),
                }
            ),
        )

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Get options flow for configuration.

        Args:
            config_entry: Configuration entry

        Returns:
            Options flow instance
        """
        return ClaudeAssistantOptionsFlow(config_entry)


class ClaudeAssistantOptionsFlow(config_entries.OptionsFlow):
    """Options flow for Claude Assistant integration."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow.

        Args:
            config_entry: Configuration entry
        """
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: Optional[dict[str, Any]] = None
    ) -> FlowResult:
        """Handle options step.

        Args:
            user_input: User input

        Returns:
            Flow result
        """
        errors = {}

        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_MODEL,
                        default=self.config_entry.data.get(CONF_MODEL, DEFAULT_MODEL),
                    ): vol.In(CLAUDE_MODELS),
                    vol.Required(
                        CONF_SAFETY_LEVEL,
                        default=self.config_entry.options.get(
                            CONF_SAFETY_LEVEL, SAFETY_LEVEL_DANGEROUS
                        ),
                    ): vol.In(SAFETY_LEVELS),
                }
            ),
            errors=errors,
        )
