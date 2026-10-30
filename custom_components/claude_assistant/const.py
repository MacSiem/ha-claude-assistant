"""Constants for the Claude Assistant integration."""

DOMAIN = "claude_assistant"
VERSION = "1.2.0"

# Config keys
CONF_API_KEY = "api_key"
CONF_MODEL = "model"
CONF_SAFETY_LEVEL = "safety_level"
CONF_AUTH_TYPE = "auth_type"
CONF_TEMPERATURE = "temperature"
CONF_MAX_TOKENS = "max_tokens"
CONF_SYSTEM_PROMPT = "system_prompt"

# Auth types. The claude.ai session-key mode was removed in 1.2.0; the legacy
# identifiers below exist only so the entry migration can find and purge it.
AUTH_TYPE_API_KEY = "api_key"
AUTH_TYPES = [AUTH_TYPE_API_KEY]
LEGACY_AUTH_TYPE_PERSONAL = "personal_account"
LEGACY_CONF_SESSION_KEY = "session_key"

# Retirement (1.2.0 is the final release)
ANTHROPIC_INTEGRATION_URL = "https://www.home-assistant.io/integrations/anthropic/"
ISSUE_INTEGRATION_RETIRED = "integration_retired"
ISSUE_SESSION_MODE_REMOVED = "session_mode_removed"

# Safety levels
SAFETY_LEVEL_ALL = "all_actions"
SAFETY_LEVEL_DANGEROUS = "dangerous_only"
SAFETY_LEVEL_NONE = "none"

SAFETY_LEVELS = [SAFETY_LEVEL_ALL, SAFETY_LEVEL_DANGEROUS, SAFETY_LEVEL_NONE]

# Dangerous domains requiring confirmation
DANGEROUS_DOMAINS = [
    "lock",
    "alarm_control_panel",
    "cover",
    "camera",
    "siren",
    "climate",
    "water_heater",
]

# Dangerous service calls
DANGEROUS_SERVICES = [
    "lock.unlock",
    "lock.open",
    "alarm_control_panel.alarm_disarm",
    "alarm_control_panel.alarm_arm_away",
    "cover.open_cover",
    "cover.close_cover",
    "camera.turn_off",
    "switch.turn_off",
    "switch.turn_on",
    "light.turn_off",
    "light.turn_on",
    "climate.set_temperature",
    "water_heater.set_temperature",
    "siren.turn_on",
    "siren.turn_off",
]

# Claude models
CLAUDE_MODELS = [
    "claude-sonnet-5",
    "claude-opus-4-8",
    "claude-haiku-4-5-20251001",
]

DEFAULT_MODEL = "claude-sonnet-5"
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = 2048

# Default system prompt
DEFAULT_SYSTEM_PROMPT = """You are Claude, an AI assistant integrated with Home Assistant.
You can help users control their smart home devices, check sensor states,
create automations, and answer questions about their home setup.
Be concise, helpful, and proactive in suggesting relevant actions.
When controlling devices, always confirm the action you're about to take."""

# WebSocket types
WS_TYPE_CHAT = f"{DOMAIN}/chat"
WS_TYPE_CONFIRM_ACTION = f"{DOMAIN}/confirm_action"
WS_TYPE_GET_PENDING = f"{DOMAIN}/get_pending"
WS_TYPE_GET_ENTITIES = f"{DOMAIN}/get_entities"
WS_TYPE_SETTINGS = f"{DOMAIN}/settings"
WS_TYPE_GET_LOGS = f"{DOMAIN}/get_logs"
WS_TYPE_CLEAR_LOGS = f"{DOMAIN}/clear_logs"
WS_TYPE_GET_STATS = f"{DOMAIN}/get_stats"
WS_TYPE_UPDATE_SETTINGS = f"{DOMAIN}/update_settings"

# Storage keys
STORAGE_KEY_HISTORY = f"{DOMAIN}_history"
STORAGE_KEY_PENDING = f"{DOMAIN}_pending"
STORAGE_KEY_LOGS = f"{DOMAIN}_logs"
STORAGE_KEY_STATS = f"{DOMAIN}_stats"
STORAGE_KEY_SETTINGS = f"{DOMAIN}_settings"

# Panel
PANEL_TITLE = "Claude Assistant"
PANEL_ICON = "mdi:robot"
PANEL_URL = "/api/panel_custom/claude-assistant"

# Action categories (for action_handler.py)
ACTION_CATEGORY_SAFE = "safe"
ACTION_CATEGORY_MODERATE = "moderate"
ACTION_CATEGORY_DANGEROUS = "dangerous"
ACTION_CATEGORY_CRITICAL = "critical"
ACTION_CONFIRMATION_TIMEOUT = 30

# Limits
MAX_LOG_ENTRIES = 500
MAX_CONVERSATION_HISTORY = 20
