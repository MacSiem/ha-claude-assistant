"""Claude Assistant integration for Home Assistant."""

import asyncio
import json
import logging
from typing import Any, Optional

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.typing import ConfigType
from homeassistant.components import websocket_api

from .action_handler import ActionHandler
from .api_client import ClaudeAPIClient
from .conversation import async_setup_agent
from .const import (
    CONF_API_KEY,
    CONF_MODEL,
    CONF_SAFETY_LEVEL,
    DOMAIN,
    STORAGE_KEY_HISTORY,
    STORAGE_KEY_PENDING,
    WS_TYPE_CHAT,
    WS_TYPE_CONFIRM_ACTION,
    WS_TYPE_GET_PENDING,
    WS_TYPE_GET_ENTITIES,
    WS_TYPE_SETTINGS,
    SAFETY_LEVEL_DANGEROUS,
    DEFAULT_MODEL,
    PANEL_TITLE,
    PANEL_ICON,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS = []


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Claude Assistant integration.

    Args:
        hass: Home Assistant instance
        config: Configuration dictionary

    Returns:
        True if setup was successful
    """
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Claude Assistant from a config entry.

    Args:
        hass: Home Assistant instance
        entry: Configuration entry

    Returns:
        True if setup was successful
    """
    _LOGGER.info("Setting up Claude Assistant")

    # Get configuration
    api_key = entry.data.get(CONF_API_KEY)
    model = entry.data.get(CONF_MODEL, DEFAULT_MODEL)
    safety_level = entry.options.get(CONF_SAFETY_LEVEL, SAFETY_LEVEL_DANGEROUS)

    if not api_key:
        _LOGGER.error("No API key provided")
        return False

    try:
        # Initialize API client (deferred to executor to avoid blocking SSL call)
        api_client = ClaudeAPIClient(api_key, model)
        await api_client.async_init(hass)

        # Validate API key
        is_valid = await api_client.async_validate_api_key()
        if not is_valid:
            _LOGGER.error("Invalid API key")
            return False

        # Initialize action handler
        action_handler = ActionHandler(hass)

        # Store components
        hass.data[DOMAIN] = {
            "api_client": api_client,
            "action_handler": action_handler,
            "config_entry": entry,
            "safety_level": safety_level,
            "conversation_history": [],
            "pending_actions": {},
        }

        # Set up conversation agent
        await async_setup_agent(hass, api_client)

        # Register services
        await _async_register_services(hass)

        # Register WebSocket handlers
        _async_register_websocket_handlers(hass)

        # Register sidebar panel
        _async_register_panel(hass)

        _LOGGER.info("Claude Assistant setup complete")

        return True

    except Exception as err:  # pylint: disable=broad-except
        _LOGGER.error("Error setting up Claude Assistant: %s", err)
        return False


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry.

    Args:
        hass: Home Assistant instance
        entry: Configuration entry

    Returns:
        True if unload was successful
    """
    _LOGGER.info("Unloading Claude Assistant")

    if DOMAIN in hass.data:
        del hass.data[DOMAIN]

    return True


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload a config entry.

    Args:
        hass: Home Assistant instance
        entry: Configuration entry
    """
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)


async def _async_register_services(hass: HomeAssistant) -> None:
    """Register Home Assistant services.

    Args:
        hass: Home Assistant instance
    """

    async def handle_send_message(call: ServiceCall) -> None:
        """Handle send message service call.

        Args:
            call: Service call
        """
        message = call.data.get("message", "")

        if not message:
            _LOGGER.error("No message provided")
            return

        data = hass.data[DOMAIN]
        api_client = data["api_client"]
        history = data.get("conversation_history", [])
        safety_level = data.get("safety_level", SAFETY_LEVEL_DANGEROUS)

        # Add user message to history
        history.append({"role": "user", "content": message})

        # Get Claude response
        ha_state = _get_ha_state(hass)
        system_prompt = api_client.build_system_prompt(ha_state)
        tools = api_client.build_tools()

        response = await api_client.async_send_message(
            messages=history,
            system_prompt=system_prompt,
            tools=tools,
        )

        if not response.get("success"):
            _LOGGER.error("API call failed: %s", response.get("error"))
            return

        # Extract text response
        text_response = api_client.extract_text_response(response)
        history.append({"role": "assistant", "content": text_response})

        # Store updated history
        data["conversation_history"] = history[-20:]  # Keep last 20 messages

        _LOGGER.debug("Message processed: %s", text_response)

    async def handle_execute_action(call: ServiceCall) -> None:
        """Handle execute action service call.

        Args:
            call: Service call
        """
        action_id = call.data.get("action_id")

        if not action_id:
            _LOGGER.error("No action_id provided")
            return

        data = hass.data[DOMAIN]
        action_handler = data["action_handler"]

        success = await action_handler.async_execute_action(action_id)

        if not success:
            _LOGGER.error("Failed to execute action %s", action_id)

    async def handle_get_history(call: ServiceCall) -> None:
        """Handle get history service call.

        Args:
            call: Service call
        """
        data = hass.data[DOMAIN]
        history = data.get("conversation_history", [])

        _LOGGER.info("Conversation history has %d messages", len(history))

    # Register services
    hass.services.async_register(
        DOMAIN,
        "send_message",
        handle_send_message,
        description="Send a message to Claude Assistant",
    )

    hass.services.async_register(
        DOMAIN,
        "execute_action",
        handle_execute_action,
        description="Execute a pending action",
    )

    hass.services.async_register(
        DOMAIN,
        "get_history",
        handle_get_history,
        description="Get conversation history",
    )

    _LOGGER.info("Services registered")


def _async_register_websocket_handlers(hass: HomeAssistant) -> None:
    """Register WebSocket handlers.

    Args:
        hass: Home Assistant instance
    """

    @websocket_api.websocket_command({"type": WS_TYPE_CHAT, "message": str})
    @callback
    async def websocket_chat(hass_ws: HomeAssistant, msg: dict) -> None:
        """Handle WebSocket chat command.

        Args:
            hass_ws: Home Assistant instance
            msg: Message dict
        """
        message = msg.get("message", "")

        if not message:
            websocket_api.error_message(msg, "message_required")
            return

        try:
            data = hass.data[DOMAIN]
            api_client = data["api_client"]
            history = data.get("conversation_history", [])
            safety_level = data.get("safety_level", SAFETY_LEVEL_DANGEROUS)

            # Add user message
            history.append({"role": "user", "content": message})

            # Get response
            ha_state = _get_ha_state(hass)
            system_prompt = api_client.build_system_prompt(ha_state)
            tools = api_client.build_tools()

            response = await api_client.async_send_message(
                messages=history,
                system_prompt=system_prompt,
                tools=tools,
            )

            if not response.get("success"):
                websocket_api.error_message(msg, response.get("error", "Unknown error"))
                return

            text_response = api_client.extract_text_response(response)
            history.append({"role": "assistant", "content": text_response})
            data["conversation_history"] = history[-20:]

            websocket_api.result_message(
                msg,
                {
                    "response": text_response,
                    "tool_calls": api_client.extract_tool_calls(response),
                },
            )

        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.error("WebSocket chat error: %s", err)
            websocket_api.error_message(msg, str(err))

    @websocket_api.websocket_command(
        {"type": WS_TYPE_CONFIRM_ACTION, "action_id": str, "confirmed": bool}
    )
    @callback
    async def websocket_confirm_action(hass_ws: HomeAssistant, msg: dict) -> None:
        """Handle WebSocket confirm action command.

        Args:
            hass_ws: Home Assistant instance
            msg: Message dict
        """
        action_id = msg.get("action_id", "")
        confirmed = msg.get("confirmed", False)

        data = hass.data[DOMAIN]
        action_handler = data["action_handler"]

        if confirmed:
            success = await action_handler.async_execute_action(action_id)
            websocket_api.result_message(msg, {"success": success})
        else:
            success = await action_handler.async_reject_action(action_id, "User rejected")
            websocket_api.result_message(msg, {"success": success})

    @websocket_api.websocket_command({"type": WS_TYPE_GET_PENDING})
    @callback
    async def websocket_get_pending(hass_ws: HomeAssistant, msg: dict) -> None:
        """Handle WebSocket get pending command.

        Args:
            hass_ws: Home Assistant instance
            msg: Message dict
        """
        data = hass.data[DOMAIN]
        action_handler = data["action_handler"]

        pending = await action_handler.async_get_pending_actions()
        websocket_api.result_message(msg, {"pending_actions": pending})

    @websocket_api.websocket_command({"type": WS_TYPE_GET_ENTITIES})
    @callback
    async def websocket_get_entities(hass_ws: HomeAssistant, msg: dict) -> None:
        """Handle WebSocket get entities command.

        Args:
            hass_ws: Home Assistant instance
            msg: Message dict
        """
        entities = {}

        for entity_id in hass.states.async_entity_ids():
            state = hass.states.get(entity_id)
            if state:
                entities[entity_id] = {
                    "state": state.state,
                    "friendly_name": state.attributes.get("friendly_name", entity_id),
                }

        websocket_api.result_message(msg, {"entities": entities})

    @websocket_api.websocket_command({"type": WS_TYPE_SETTINGS})
    @callback
    async def websocket_settings(hass_ws: HomeAssistant, msg: dict) -> None:
        """Handle WebSocket settings command.

        Args:
            hass_ws: Home Assistant instance
            msg: Message dict
        """
        data = hass.data[DOMAIN]

        settings = {
            "model": data["api_client"].model,
            "safety_level": data.get("safety_level", SAFETY_LEVEL_DANGEROUS),
        }

        websocket_api.result_message(msg, settings)

    # Register commands
    websocket_api.async_register_command(hass, websocket_chat)
    websocket_api.async_register_command(hass, websocket_confirm_action)
    websocket_api.async_register_command(hass, websocket_get_pending)
    websocket_api.async_register_command(hass, websocket_get_entities)
    websocket_api.async_register_command(hass, websocket_settings)

    _LOGGER.info("WebSocket handlers registered")


def _async_register_panel(hass: HomeAssistant) -> None:
    """Register frontend panel.

    Args:
        hass: Home Assistant instance
    """
    # For production, this would register a custom panel
    # Here we just log that it would be done
    _LOGGER.info("Frontend panel registration queued (requires custom element)")


def _get_ha_state(hass: HomeAssistant) -> dict[str, Any]:
    """Get current Home Assistant state.

    Args:
        hass: Home Assistant instance

    Returns:
        Dictionary of entity states
    """
    state_dict = {}

    for entity_id in hass.states.async_entity_ids():
        state = hass.states.get(entity_id)
        if state:
            state_dict[entity_id] = {
                "state": state.state,
                "attributes": dict(state.attributes),
            }

    return state_dict
