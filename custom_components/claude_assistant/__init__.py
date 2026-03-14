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
from homeassistant.components.frontend import async_register_built_in_panel
from homeassistant.components.frontend import async_register_built_in_panel

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
    PANEL_ICON,
    PANEL_TITLE,
    SAFETY_LEVEL_ALL,
    SAFETY_LEVEL_DANGEROUS,
    SAFETY_LEVEL_NONE,
    STORAGE_KEY_LOGS,
    STORAGE_KEY_STATS,
    MAX_LOG_ENTRIES,
    WS_TYPE_CHAT,
    WS_TYPE_CONFIRM_ACTION,
    WS_TYPE_GET_PENDING,
    WS_TYPE_GET_ENTITIES,
    WS_TYPE_SETTINGS,
    WS_TYPE_GET_LOGS,
    WS_TYPE_CLEAR_LOGS,
    WS_TYPE_GET_STATS,
    WS_TYPE_UPDATE_SETTINGS,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.CONVERSATION]


# ââ Helper Functions âââââââââââââââââââââââââââââââââââââââââââââââââ


async def _add_log_entry(hass: HomeAssistant, log_type: str, message: str, details: dict | None = None) -> None:
    """Add a log entry and persist."""
    data = hass.data.get(DOMAIN, {})
    logs = data.get("logs", [])
    entry = {
        "timestamp": datetime.now().isoformat(),
        "type": log_type,
        "message": message,
    }
    if details:
        entry["details"] = details
    logs.insert(0, entry)
    if len(logs) > MAX_LOG_ENTRIES:
        logs = logs[:MAX_LOG_ENTRIES]
    data["logs"] = logs
    log_store = data.get("log_store")
    if log_store:
        await log_store.async_save(logs)


async def _update_stats(hass: HomeAssistant, tokens_in: int, tokens_out: int, response_time_ms: int, model: str) -> None:
    """Update stats and persist."""
    data = hass.data.get(DOMAIN, {})
    stats = data.get("stats", {})
    stats["conversations_total"] = stats.get("conversations_total", 0) + 1
    stats["conversations_today"] = stats.get("conversations_today", 0) + 1
    stats["tokens_total_in"] = stats.get("tokens_total_in", 0) + tokens_in
    stats["tokens_total_out"] = stats.get("tokens_total_out", 0) + tokens_out
    stats["tokens_today_in"] = stats.get("tokens_today_in", 0) + tokens_in
    stats["tokens_today_out"] = stats.get("tokens_today_out", 0) + tokens_out

    total = stats.get("conversations_total", 1)
    old_avg = stats.get("avg_response_time_ms", 0)
    stats["avg_response_time_ms"] = int(old_avg + (response_time_ms - old_avg) / total)

    model_usage = stats.get("model_usage", {})
    model_usage[model] = model_usage.get(model, 0) + 1
    stats["model_usage"] = model_usage

    hour = datetime.now().strftime("%H")
    hourly = stats.get("hourly_usage", {})
    hourly[hour] = hourly.get(hour, 0) + 1
    stats["hourly_usage"] = hourly

    data["stats"] = stats
    stat_store = data.get("stat_store")
    if stat_store:
        await stat_store.async_save(stats)


# ââ WebSocket Handlers âââââââââââââââââââââââââââââââââââââââââââââââ


@websocket_api.websocket_command({
    vol.Required("type"): WS_TYPE_CHAT,
    vol.Required("message"): str,
    vol.Optional("conversation_id"): str,
})
@websocket_api.async_response
async def ws_handle_chat(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict) -> None:
    """Handle WebSocket chat."""
    data = hass.data.get(DOMAIN, {})
    message = msg["message"]
    start_time = time.time()

    try:
        entity_context = []
        for state in hass.states.async_all():
            domain = state.entity_id.split(".")[0]
            if domain in ("light", "switch", "climate", "cover", "lock", "sensor", "binary_sensor", "media_player"):
                entity_context.append(f"- {state.entity_id}: {state.state}")

        system = data["settings"]["system_prompt"]
        if entity_context:
            system += "\n\nAvailable entities:\n" + "\n".join(entity_context[:50])

        response = await data["api_client"].send_message(
            message=message,
            conversation_history=data["conversation_history"],
            system_prompt=system,
            temperature=data["settings"]["temperature"],
            max_tokens=data["settings"]["max_tokens"],
        )

        elapsed_ms = int((time.time() - start_time) * 1000)

        data["conversation_history"].append({"role": "user", "content": message})
        data["conversation_history"].append({"role": "assistant", "content": response.get("text", "")})
        if len(data["conversation_history"]) > 40:
            data["conversation_history"] = data["conversation_history"][-40:]

        await _add_log_entry(hass, "chat", message[:100], {
            "response": response.get("text", "")[:200],
            "tokens_in": response.get("input_tokens", 0),
            "tokens_out": response.get("output_tokens", 0),
            "time_ms": elapsed_ms,
        })
        await _update_stats(
            hass,
            response.get("input_tokens", 0),
            response.get("output_tokens", 0),
            elapsed_ms,
            response.get("model", data["settings"]["model"]),
        )

        connection.send_result(msg["id"], {
            "text": response.get("text", ""),
            "input_tokens": response.get("input_tokens", 0),
            "output_tokens": response.get("output_tokens", 0),
            "model": response.get("model", ""),
            "time_ms": elapsed_ms,
        })
    except Exception as err:
        _LOGGER.error("WS chat error: %s", err)
        await _add_log_entry(hass, "error", f"Chat error: {err}")
        connection.send_error(msg["id"], "chat_error", str(err))


@websocket_api.websocket_command({
    vol.Required("type"): WS_TYPE_GET_ENTITIES,
})
@websocket_api.async_response
async def ws_handle_get_entities(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict) -> None:
    """Return all entities grouped by domain."""
    entities = {}
    for state in hass.states.async_all():
        domain = state.entity_id.split(".")[0]
        entities.setdefault(domain, []).append({
            "entity_id": state.entity_id,
            "state": state.state,
            "name": state.attributes.get("friendly_name", state.entity_id),
        })
    connection.send_result(msg["id"], entities)


@websocket_api.websocket_command({
    vol.Required("type"): WS_TYPE_GET_PENDING,
})
@websocket_api.async_response
async def ws_handle_get_pending(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict) -> None:
    """Return pending actions."""
    data = hass.data.get(DOMAIN, {})
    connection.send_result(msg["id"], data.get("pending_actions", {}))


@websocket_api.websocket_command({
    vol.Required("type"): WS_TYPE_CONFIRM_ACTION,
    vol.Required("action_id"): str,
    vol.Required("confirmed"): bool,
})
@websocket_api.async_response
async def ws_handle_confirm_action(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict) -> None:
    """Confirm or reject a pending action."""
    data = hass.data.get(DOMAIN, {})
    action_id = msg["action_id"]
    confirmed = msg["confirmed"]
    pending = data.get("pending_actions", {})

    if action_id not in pending:
        connection.send_error(msg["id"], "not_found", "Action not found")
        return

    action = pending.pop(action_id)
    if confirmed:
        try:
            await hass.services.async_call(
                action["domain"], action["service"],
                action.get("data", {}),
                blocking=True,
            )
            await _add_log_entry(hass, "action", f"Executed: {action['domain']}.{action['service']}")
            connection.send_result(msg["id"], {"status": "executed"})
        except Exception as err:
            connection.send_error(msg["id"], "execution_error", str(err))
    else:
        await _add_log_entry(hass, "action", f"Rejected: {action['domain']}.{action['service']}")
        connection.send_result(msg["id"], {"status": "rejected"})


@websocket_api.websocket_command({
    vol.Required("type"): WS_TYPE_SETTINGS,
})
@websocket_api.async_response
async def ws_handle_settings(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict) -> None:
    """Return current settings."""
    data = hass.data.get(DOMAIN, {})
    connection.send_result(msg["id"], data.get("settings", {}))


@websocket_api.websocket_command({
    vol.Required("type"): WS_TYPE_GET_LOGS,
})
@websocket_api.async_response
async def ws_handle_get_logs(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict) -> None:
    """Return logs."""
    data = hass.data.get(DOMAIN, {})
    connection.send_result(msg["id"], data.get("logs", []))


@websocket_api.websocket_command({
    vol.Required("type"): WS_TYPE_CLEAR_LOGS,
})
@websocket_api.async_response
async def ws_handle_clear_logs(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict) -> None:
    """Clear all logs."""
    data = hass.data.get(DOMAIN, {})
    data["logs"] = []
    log_store = data.get("log_store")
    if log_store:
        await log_store.async_save([])
    connection.send_result(msg["id"], {"status": "cleared"})


@websocket_api.websocket_command({
    vol.Required("type"): WS_TYPE_GET_STATS,
})
@websocket_api.async_response
async def ws_handle_get_stats(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict) -> None:
    """Return stats."""
    data = hass.data.get(DOMAIN, {})
    connection.send_result(msg["id"], data.get("stats", {}))


@websocket_api.websocket_command({
    vol.Required("type"): WS_TYPE_UPDATE_SETTINGS,
    vol.Optional("model"): str,
    vol.Optional("temperature"): float,
    vol.Optional("max_tokens"): int,
    vol.Optional("safety_level"): str,
    vol.Optional("system_prompt"): str,
})
@websocket_api.async_response
async def ws_handle_update_settings(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict) -> None:
    """Update settings at runtime."""
    data = hass.data.get(DOMAIN, {})
    settings = data.get("settings", {})

    for key in ("model", "temperature", "max_tokens", "safety_level", "system_prompt"):
        if key in msg:
            settings[key] = msg[key]

    data["settings"] = settings
    await _add_log_entry(hass, "settings", "Settings updated")
    connection.send_result(msg["id"], {"status": "ok", "settings": settings})


# ââ Setup / Unload âââââââââââââââââââââââââââââââââââââââââââââââââââ


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up Claude Assistant from configuration.yaml."""
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

    # Initialize action handler
    action_handler = ActionHandler(hass)

    # Load logs from storage
    log_store = Store(hass, 1, STORAGE_KEY_LOGS)
    saved_logs = await log_store.async_load() or []

    # Load stats from storage
    stat_store = Store(hass, 1, STORAGE_KEY_STATS)
    saved_stats = await stat_store.async_load() or {
        "conversations_total": 0,
        "conversations_today": 0,
        "tokens_total_in": 0,
        "tokens_total_out": 0,
        "tokens_today_in": 0,
        "tokens_today_out": 0,
        "avg_response_time_ms": 0,
        "model_usage": {},
        "hourly_usage": {},
        "daily_history": [],
        "last_reset_date": datetime.now().strftime("%Y-%m-%d"),
    }

    # Reset daily stats if needed
    today = datetime.now().strftime("%Y-%m-%d")
    if saved_stats.get("last_reset_date") != today:
        if saved_stats.get("conversations_today", 0) > 0:
            saved_stats.setdefault("daily_history", []).append({
                "date": saved_stats.get("last_reset_date", today),
                "conversations": saved_stats.get("conversations_today", 0),
                "tokens_in": saved_stats.get("tokens_today_in", 0),
                "tokens_out": saved_stats.get("tokens_today_out", 0),
            })
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
        "conversation_history": [],
        "pending_actions": {},
        "settings": {
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "safety_level": safety_level,
            "system_prompt": system_prompt,
            "auth_type": auth_type,
        },
        "logs": saved_logs,
        "stats": saved_stats,
        "log_store": log_store,
        "stat_store": stat_store,
    }

    # Forward to conversation platform
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Services
    async def handle_chat(call: ServiceCall) -> None:
        """Handle chat service call."""
        message = call.data.get("message", "")
        data = hass.data[DOMAIN]
        try:
            response = await data["api_client"].send_message(
                message=message,
                conversation_history=data["conversation_history"],
                system_prompt=data["settings"]["system_prompt"],
                temperature=data["settings"]["temperature"],
                max_tokens=data["settings"]["max_tokens"],
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
    from homeassistant.components.http import StaticPathConfig
    await hass.http.async_register_static_paths(
        [StaticPathConfig(
            "/api/panel_custom/claude-assistant",
            hass.config.path("custom_components/claude_assistant/frontend"),
            True,
        )]
    )

    try:
        async_register_built_in_panel(hass,
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
    except ValueError:
        pass  # Panel already registered

    # Listen for options updates
    entry.async_on_unload(entry.add_update_listener(async_options_updated))

    _LOGGER.info("Claude Assistant integration loaded successfully")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data.pop(DOMAIN, None)
    return unload_ok


async def async_options_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    data = hass.data.get(DOMAIN, {})
    settings = data.get("settings", {})
    settings["model"] = entry.options.get(CONF_MODEL, settings.get("model"))
    settings["temperature"] = entry.options.get(CONF_TEMPERATURE, DEFAULT_TEMPERATURE)
    settings["max_tokens"] = entry.options.get(CONF_MAX_TOKENS, DEFAULT_MAX_TOKENS)
    settings["safety_level"] = entry.options.get(CONF_SAFETY_LEVEL, settings.get("safety_level"))
    settings["system_prompt"] = entry.options.get(CONF_SYSTEM_PROMPT, DEFAULT_SYSTEM_PROMPT)
    _LOGGER.info("Claude Assistant options updated")
