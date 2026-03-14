"""Config flow for Claude Assistant integration."""

import logging
from typing import Any, Optional

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .api_client import ClaudeAPIClient
from .const import (
    CONF_API_KEY,
    CONF_AUTH_TYPE,
    CONF_MAX_TOKENS,
    CONF_MODEL,
    CONF_SAFETY_LEVEL,
    CONF_SESSION_KEY,
    CONF_SYSTEM_PROMPT,
    CONF_TEMPERATURE,
    AUTH_TYPE_API_KEY,
    AUTH_TYPE_PERSONAL,
    AUTH_TYPES,
    CLAUDE_MODELS,
    DEFAULT_MAX_TOKENS,
    DEFAULT_MODEL,
    DEFAULT_SYSTEM_PROMPT,
    DEFAULT_TEMPERATURE,
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

    VERSION = 2

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._api_key: Optional[str] = None
        self._session_key: Optional[str] = None
        self._auth_type: str = AUTH_TYPE_API_KEY
        self._model: str = DEFAULT_MODEL

    async def async_step_user(
        self, user_input: Optional[dict[str, Any]] = None
    ) -> FlowResult:
        """Handle the auth type selection step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._auth_type = user_input[CONF_AUTH_TYPE]
            if self._auth_type == AUTH_TYPE_API_KEY:
                return await self.async_step_api_key()
            else:
                return await self.async_step_personal()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_AUTH_TYPE, default=AUTH_TYPE_API_KEY
                    ): vol.In(
                        {
                            AUTH_TYPE_API_KEY: "Klucz API Anthropic",
                            AUTH_TYPE_PERSONAL: "Konto osobiste (Session Key)",
                        }
                    ),
                }
            ),
            errors=errors,
            description_placeholders={
                "api_info": "Wybierz metodę autoryzacji"
            },
        )

    async def async_step_api_key(
        self, user_input: Optional[dict[str, Any]] = None
    ) -> FlowResult:
        """Handle the API key input step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._api_key = user_input[CONF_API_KEY]

            try:
                client = ClaudeAPIClient(api_key=self._api_key)
                await client.async_init(self.hass)
                valid = await client.validate_api_key()
                if not valid:
                    errors["base"] = "invalid_auth"
                else:
                    return await self.async_step_model()
            except Exception:
                _LOGGER.exception("Error validating API key")
                errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="api_key",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_API_KEY): str,
                }
            ),
            errors=errors,
            description_placeholders={
                "api_url": "https://console.anthropic.com/settings/keys"
            },
        )

    async def async_step_personal(
        self, user_input: Optional[dict[str, Any]] = None
    ) -> FlowResult:
        """Handle personal account session key step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._session_key = user_input[CONF_SESSION_KEY]

            try:
                client = ClaudeAPIClient(
                    api_key=self._session_key, auth_type=AUTH_TYPE_PERSONAL
                )
                await client.async_init(self.hass)
                valid = await client.validate_api_key()
                if not valid:
                    errors["base"] = "invalid_session"
                else:
                    return await self.async_step_model()
            except Exception:
                _LOGGER.exception("Error validating session key")
                errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="personal",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_SESSION_KEY): str,
                }
            ),
            errors=errors,
            description_placeholders={
                "session_info": (
                    "Wklej klucz sesji z claude.ai. "
                    "Znajdziesz go w Developer Tools > Application > Cookies > sessionKey"
                )
            },
        )

    async def async_step_model(
        self, user_input: Optional[dict[str, Any]] = None
    ) -> FlowResult:
        """Handle the model selection step."""
        if user_input is not None:
            self._model = user_input[CONF_MODEL]
            return await self.async_step_safety()

        return self.async_show_form(
            step_id="model",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_MODEL, default=DEFAULT_MODEL
                    ): vol.In(CLAUDE_MODELS),
                }
            ),
        )

    async def async_step_safety(
        self, user_input: Optional[dict[str, Any]] = None
    ) -> FlowResult:
        """Handle safety level configuration."""
        if user_input is not None:
            data = {
                CONF_AUTH_TYPE: self._auth_type,
                CONF_MODEL: self._model,
                CONF_SAFETY_LEVEL: user_input[CONF_SAFETY_LEVEL],
            }

            if self._auth_type == AUTH_TYPE_API_KEY:
                data[CONF_API_KEY] = self._api_key
            else:
                data[CONF_SESSION_KEY] = self._session_key

            return self.async_create_entry(
                title="Claude Assistant",
                data=data,
                options={
                    CONF_TEMPERATURE: DEFAULT_TEMPERATURE,
                    CONF_MAX_TOKENS: DEFAULT_MAX_TOKENS,
                    CONF_SYSTEM_PROMPT: DEFAULT_SYSTEM_PROMPT,
                },
            )

        return self.async_show_form(
            step_id="safety",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SAFETY_LEVEL, default=SAFETY_LEVEL_DANGEROUS
                    ): vol.In(
                        {
                            "all_actions": "Potwierdzaj wszystkie akcje",
                            "dangerous_only": "Potwierdzaj tylko niebezpieczne (zalecane)",
                            "none": "Bez potwierdzeń (niebezpieczne)",
                        }
                    ),
                }
            ),
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> "ClaudeAssistantOptionsFlow":
        """Get the options flow for this handler."""
        return ClaudeAssistantOptionsFlow(config_entry)


class ClaudeAssistantOptionsFlow(config_entries.OptionsFlow):
    """Options flow for Claude Assistant."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: Optional[dict[str, Any]] = None
    ) -> FlowResult:
        """Handle the initial step of options flow."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = self.config_entry.options

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_MODEL,
                        default=self.config_entry.data.get(
                            CONF_MODEL, DEFAULT_MODEL
                        ),
                    ): vol.In(CLAUDE_MODELS),
                    vol.Required(
                        CONF_TEMPERATURE,
                        default=current.get(
                            CONF_TEMPERATURE, DEFAULT_TEMPERATURE
                        ),
                    ): vol.All(
                        vol.Coerce(float), vol.Range(min=0.0, max=1.0)
                    ),
                    vol.Required(
                        CONF_MAX_TOKENS,
                        default=current.get(
                            CONF_MAX_TOKENS, DEFAULT_MAX_TOKENS
                        ),
                    ): vol.All(
                        vol.Coerce(int), vol.Range(min=256, max=8192)
                    ),
                    vol.Required(
                        CONF_SAFETY_LEVEL,
                        default=self.config_entry.data.get(
                            CONF_SAFETY_LEVEL, SAFETY_LEVEL_DANGEROUS
                        ),
                    ): vol.In(SAFETY_LEVELS),
                    vol.Optional(
                        CONF_SYSTEM_PROMPT,
                        default=current.get(
                            CONF_SYSTEM_PROMPT, DEFAULT_SYSTEM_PROMPT
                        ),
                    ): str,
                }
            ),
        )
