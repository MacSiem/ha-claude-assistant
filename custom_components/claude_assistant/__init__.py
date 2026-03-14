"""Claude Assistant integration for Home Assistant."""

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Any, Optional

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers.storage import Store
from homeassistant.components import websocket_api

from .action_handler import ActionHandler
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
    DEFAULT_MAX_TOKENS,
    DEFAULT_MODEL,
    DEFAULT_SYSTEM_PROMPT,
    DEFAULT_TEMPERATURE,
    DOMAIN,
    MAX_LOG_ENTRIES,
    STORAGE_KEY_HISTORY,
    STORAGE_KEY_LOGS,
    STORAGE_KEY_PENDING,
    STORAGE_KEY_STATS,
    WS_TYPE_CHAT,
    WS_TYPE_CLEAR_LOGS,
    WS_TYPE_CONFIRM_ACTION,
    WS_TYPE_GET_ENTITIES,
    WS_TYPE_GET_LOGS,
    WS_TYPE_GET_PENDING,
    WS_TYPE_GET_STATS,
    WS_TYPE_SETTINGS,
    WS_TYPE_UPDATE_SETTINGS,
    SAFETY_LEVEL_DANGEROUS,
    PANEL_TITLE,
    PANEL_ICON,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.CONVERSATION]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Claude Assistant component."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Claude Assistant from a config entry."""
    auth_type = entry.data.get(CONF_AUTH_TYPE, AUTH_TYPE_API_KEY)

    if auth_type == AUTH_TYPE_PERSONAL:
        api_key = entry.data.get(CONF_SESSION_KEY, "")
    else:
        api_key = entry.data.get(CONF_API_KEY, "")

    model = entry.data.get(CONF_MODEL, DEFAULT_MODEL)

    # Options override
    if entry.options.get(CONF_MODEL):
        model = entry.options[CONF_MODEL]

    safety_level = entry.data.get(CONF_SAFETY_LEVEL, SAFETY_LEVEL_DANGEROUS)
    if entry.options.get(CONF_SAFETY_LEVEL):
        safety_level = entry.options[CONF_SAFETY_LEVEL]

    temperature = entry.options.get(CONF_TEMPERATURE, DEFAULT_TEMPERATURE)
    max_tokens = entry.options.get(CONF_MAX_TOKENS, DEFAULT_MAX_TOKENS)
    system_prompt = entry.options.get(CONF_SYSTEM_PROMPT, DEFAULT_SYSTEM_PROMPT)

    # Initialize API client
    api_client = ClaudeAPIClient(
        api_key=api_key,
        model=model,
        auth_type=auth_type,
    )
    await api_client.async_init(hass)

    # Validate credentials
    try:
        valid = await api_client.validate_api_key()
        if not valid:
            _LOGGER.error("Claude API key validation failed")
            return False
    except Exception as err:
        _LOGGER.error("Error validating Claude credentials: %s", err)
        return False

    # Initialize action handler
    action_handler = ActionHandler(hass)

    # Initialize storage for logs and stats
    logs_store = Store(hass, 1, STORAGE_KEY_LOGS)
    stats_store = Store(hass, 1, STORAGE_KEY_STATS)

    saved_logs = await logs_store.async_load() or []
    saved_stats = await stats_store.async_load() or {
        "total_conversations": 0,
        "total_tokens_in": 0,
        "total_tokens_out": 0,
        "total_response_time_ms": 0,
        "conversations_today": 0,
        "tokens_today_in": 0,
        "tokens_today_out": 0,
        "last_reset_date": datetime.now().strftime("%Y-%m-%d"),
        "model_usage": {},
        "hourly_usage": {},
        "daily_history": [],
    }

    # Reset daily counters if needed
    today = datetime.now().strftime("%Y-%m-%d")
    if saved_stats.get("last_reset_date") != today:
        # Archive yesterday
        if saved_stats.get("conversations_today", 0) > 0:
            saved_stats.setdefault("daily_history", []).append({
                "date": saved_stats.get("last_reset_date", today),
                "conversations": saved_stats.get("conversations_today", 0),
                "tokens_in": saved_stats.get("tokens_today_in", 0),
                "tokens_out": saved_stats.get("tokens_today_out", 0),
            })
            # Keep last 30 days
            saved_stats["daily_history"] = saved_stats["daily_history"][-30:]
        saved_stats["conversations_today"] = 0
        saved_stats["tokens_today_in"] = 0
        saved_stats["tokens_today_out"] = 0
        saved_stats["hourly_usage"] = {}
        saved_stats["last_reset_date"] = today

    # Store data
    hass.data[DOMAIN] = {
        "api_client": api_client,
        "action_handler": action_handler,
        "safety_level": safety_level,
        "pending_actions": {},
        "conversation_history": [],
        "logs": saved_logs,
        "stats": saved_stats,
        "logs_store": logs_store,
        "stats_store": stats_store,
        "settings": {
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "system_prompt": system_prompt,
            "safety_level": safety_level,
            "auth_type": auth_type,
        },
        "entry": entry,
    }

    # Forward entry setup to conversation platform
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register services
    async def handle_chat(call: ServiceCall) -> None:
        """Handle the chat service call."""
        message = call.data.get("message", "")
        data = hass.data[DOMAIN]
        client = data["api_client"]

        try:
            response = await client.send_message(
                message=message,
                system_prompt=data["settings["]["system_prompt"],
                temperature=data["settings"]["temperature"],
                max_tokens=data["settings["]["max_tokens"],
            )
            _LOGGER.info("Claude response: %s", response.get("text", "")[:100])
        except Exception as err:
            _LOGGER.error("Error in Claude chat: %s", err)

    async def handle_clear_history(call: ServiceCall) -> None:
        """Clear conversation history."""
        data = hass.data[DOMAIN]
        data["conversation_history"] = []
        _LOGGER.info("Conversation history cleared")

    hass.services.async_register(DOMAIN, "chat", handle_chat)
    hass.services.async_register(DOMAIN, "clear_history", handle_clear_history)

    # Register WebSocket handlers
    websocket_api.async_register_command(hass, ws_handle_chat)
    websocket_api.async_register_command(hass, ws_handle_get_entities)
    websocket_api.async_register_command(hass, ws_handle_get_pending)
    websocket_api.async_register_command(hass, ws_handle_confirm_action)
    websocket_api.async_register_command(hass, ws_handle_settings)
    websocket_api.async_register_command(hass, ws_handle_get_logs)
    websocket_api.async_register_command(hass, ws_handle_clear_logs)
    websocket_api.async_register_command(hass, ws_handle_get_stats)
    websocket_api.async_register_command(hass, ws_handle_update_settings)

    # Register panel
    hass.http.register_static_path(
        "/api/panel_custom/claude-assistant",
        hass.config.path("custom_components/claude_assistant/frontend"),
        True,
    )

    hass.components.frontend.async_register_built_in_panel(
        component_name="custom",
        sidebar_title=PANEL_TITLE,
        sidebar_icon=PANEL_ICON,
        frontend_url_path="claude-assistant",
        config={
            "_panel_custom": {
                "name": "claude-assistant-panel",
                "embed_iframe": False,
                "trust_external": False,
                "js_url": "/api/panel_custom/claude-assistant/panel.js",
            }
        },
        require_admin=False,
    )

    # Listen for options updates
    entry.async_on_unload(entry.add_update_listener(async_options_updated))

    _LOGGER.info("Claude Assistant integration loaded successfully")
    return True