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

PLATFORMS = [Platform.CONVERSATION]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Claude Assistant integration."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Claude Assistant from a config entry."""
    _LOGGER.info("Setting up Claude Assistant")

    api_key = entry.data.get(CONF_API_KEY)
    model = entry.data.get(CONF_MODEL, DEFAULT_MODEL)
    safety_level = entry.options.get(CONF_SAFETY_LEVEL, SAFETY_LEVEL_DANGEROUS)

    if not api_key:
        _LOGGER.error("No API key provided")
        return False

    try:
        api_client = ClaudeAPIClient(api_key, model)
        await api_client.async_init(hass)

        is_valid = await api_client.async_validate_api_key()
        if not is_valid:
            _LOGGER.error("Invalid API key")
            return False

        action_handler = ActionHandler(hass)

        hass.data[DOMAIN] = {
            "api_client": api_client,
            "action_handler": action_handler,
            "config_entry": entry,
            "safety_level": safety_level,
            "conversation_history": [],
            "pending_actions": {},
        }

        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

        await _async_register_services(hass)
        _async_register_websocket_handlers(hass)
        _async_register_panel(hass)

        _LOGGER.info("Claude Assistant setup complete")
        return True

    except Exception as err:
        _LOGGER.error("Error setting up Claude Assistant: %s", err)
        return False


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.info("Unloading Claude Assistant")
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok and DOMAIN in hass.data:
        del hass.data[DOMAIN]
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload a config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)


async def _async_register_services(hass: HomeAssistant) -> None:
    """Register Home Assistant services."""

    async def handle_send_message(call: ServiceCall) -> None:
        message = call.data.get("message", "")
        if not message:
            _LOGGER.error("No message provided")
            return
        data = hass.data[DOMAIN]
        api_client = data["api_client"]
        history = data.get("conversation_history", [])
        history.append({"role": "user", "content": message})
        ha_state = _get_ha_state(hass)
        system_prompt = api_client.build_system_prompt(ha_state)
        tools = api_client.build_tools()
        response = await api_client.async_send_message(
            messages=history, system_prompt=system_prompt, tools=tools)
        if not response.get("success"):
            _LOGGER.error("API call failed: %s", response.get("error"))
            return
        text_response = api_client.extract_text_response(response)
        history.append({"role": "assistant", "content": text_response})
        data["conversation_history"] = history[-20:]

    async def handle_execute_action(call: ServiceCall) -> None:
        action_id = call.data.get("action_id")
        if not action_id:
            _LOGGER.error("No action_id provided")
            return
        data = hass.data[DOMAIN]
        success = await data["action_handler"].async_execute_action(action_id)
        if not success:
            _LOGGER.error("Failed to execute action %s", action_id)

    async def handle_get_history(call: ServiceCall) -> None:
        data = hass.data[DOMAIN]
        history = data.get("conversation_history", [])
        _LOGGER.info("Conversation history has %d messages", len(history))

    hass.services.async_register(DOMAIN, "send_message", handle_send_message)
    hass.services.async_register(DOMAIN, "execute_action", handle_execute_action)
    hass.services.async_register(DOMAIN, "get_history", handle_get_history)
    _LOGGER.info("Services registered")


def _async_register_websocket_handlers(hass: HomeAssistant) -> None:
    """Register WebSocket handlers."""

    @websocket_api.websocket_command({"type": WS_TYPE_CHAT, "message": str})
    @callback
    async def websocket_chat(hass_ws, msg):
        message = msg.get("message", "")
        if not message:
            websocket_api.error_message(msg, "message_required")
            return
        try:
            data = hass.data[DOMAIN]
            api_client = data["api_client"]
            history = data.get("conversation_history", [])
            history.append({"role": "user", "content": message})
            ha_state = _get_ha_state(hass)
            system_prompt = api_client.build_system_prompt(ha_state)
            tools = api_client.build_tools()
            response = await api_client.async_send_message(
                messages=history, system_prompt=system_prompt, tools=tools)
            if not response.get("success"):
                websocket_api.error_message(msg, response.get("error", "Unknown error"))
                return
            text_response = api_client.extract_text_response(response)
            history.append({"role": "assistant", "content": text_response})
            data["conversation_history"] = history[-20:]
            websocket_api.result_message(msg, {
                "response": text_response,
                "tool_calls": api_client.extract_tool_calls(response)})
        except Exception as err:
            _LOGGER.error("WebSocket chat error: %s", err)
            websocket_api.error_message(msg, str(err))

    @websocket_api.websocket_command(
        {"type": WS_TYPE_CONFIRM_ACTION, "action_id": str, "confirmed": bool})
    @callback
    async def websocket_confirm_action(hass_ws, msg):
        action_id = msg.get("action_id", "")
        confirmed = msg.get("confirmed", False)
        data = hass.data[DOMAIN]
        ah = data["action_handler"]
        if confirmed:
            success = await ah.async_execute_action(action_id)
        else:
            success = await ah.async_reject_action(action_id, "User rejected")
        websocket_api.result_message(msg, {"success": success})

    @websocket_api.websocket_command({"type": WS_TYPE_GET_PENDING})
    @callback
    async def websocket_get_pending(hass_ws, msg):
        data = hass.data[DOMAIN]
        pending = await data["action_handler"].async_get_pending_actions()
        websocket_api.result_message(msg, {"pending_actions": pending})

    @websocket_api.websocket_command({"type": WS_TYPE_GET_ENTITIES})
    @callback
    async def websocket_get_entities(hass_ws, msg):
        entities = {}
        for eid in hass.states.async_entity_ids():
            state = hass.states.get(eid)
            if state:
                entities[eid] = {
                    "state": state.state,
                    "friendly_name": state.attributes.get("friendly_name", eid)}
        websocket_api.result_message(msg, {"entities": entities})

    @websocket_api.websocket_command({"type": WS_TYPE_SETTINGS})
    @callback
    async def websocket_settings(hass_ws, msg):
        data = hass.data[DOMAIN]
        websocket_api.result_message(msg, {
            "model": data["api_client"].model,
            "safety_level": data.get("safety_level", SAFETY_LEVEL_DANGEROUS)})

    websocket_api.async_register_command(hass, websocket_chat)
    websocket_api.async_register_command(hass, websocket_confirm_action)
    websocket_api.async_register_command(hass, websocket_get_pending)
    websocket_api.async_register_command(hass, websocket_get_entities)
    websocket_api.async_register_command(hass, websocket_settings)
    _LOGGER.info("WebSocket handlers registered")


def _async_register_panel(hass: HomeAssistant) -> None:
    _LOGGER.info("Frontend panel registration queued (requires custom element)")


def _get_ha_state(hass: HomeAssistant) -> dict[str, Any]:
    state_dict = {}
    for eid in hass.states.async_entity_ids():
        state = hass.states.get(eid)
        if state:
            state_dict[eid] = {
                "state": state.state,
                "attributes": dict(state.attributes)}
    return state_dict
