"""Constants for the Claude Assistant integration."""

DOMAIN = "claude_assistant"

# Config keys
CONF_API_KEY = "api_key"
CONF_MODEL = "model"
CONF_SAFETY_LEVEL = "safety_level"
CONF_AUTH_TYPE = "auth_type"
CONF_SESSION_KEY = "session_key"
CONF_TEMPERATURE = "temperature"
CONF_MAX_TOKENS = "max_tokens"
CONF_SYSTEM_PROMPT = "system_prompt"

# Auth types
AUTH_TYPE_API_KEY = "api_key"
AUTH_TYPE_PERSONAL = "personal_account"
AUTH_TYPES = [AUTH_TYPE_API_KEY, AUTH_TYPE_PERSONAL]

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
    "claude-opus-4-20250514",
    "claude-sonnet-4-20250514",
    "claude-haiku-3-5-20241022",
]

DEFAULT_MODEL = "claude-opus-4-20250514"
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
