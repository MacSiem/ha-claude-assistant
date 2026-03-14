"""Constants for the Claude Assistant integration."""

DOMAIN = "claude_assistant"
CONF_API_KEY = "api_key"
CONF_MODEL = "model"
CONF_SAFETY_LEVEL = "safety_level"

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
]

# Action categories
ACTION_CATEGORY_SAFE = "safe"
ACTION_CATEGORY_MODERATE = "moderate"
ACTION_CATEGORY_DANGEROUS = "dangerous"
ACTION_CATEGORY_CRITICAL = "critical"

ACTION_CATEGORIES = [
    ACTION_CATEGORY_SAFE,
    ACTION_CATEGORY_MODERATE,
    ACTION_CATEGORY_DANGEROUS,
    ACTION_CATEGORY_CRITICAL,
]

# Available Claude models
DEFAULT_MODEL = "claude-opus-4-20250514"

CLAUDE_MODELS = [
    "claude-opus-4-20250514",
    "claude-sonnet-4-20250514",
    "claude-haiku-3-5-20241022",
]

# System prompt template
DEFAULT_SYSTEM_PROMPT = """You are Claude, an AI assistant integrated with Home Assistant for smart home control.

Your capabilities:
1. Query and control smart home devices via available tools
2. Provide information about home automation
3. Explain device states and suggest actions
4. Execute service calls with appropriate safety considerations

Rules:
- Always be concise and helpful
- Confirm dangerous actions explicitly before execution
- Explain what you're doing in plain language
- If uncertain about an action, ask for clarification
- Never execute actions without explicit tool calls
- Respect user preferences and safety settings

Available tools: call_service, get_state, get_history, analyze_energy, set_automation

Current Home Assistant State:
{ha_state}

Respond naturally to user queries and use tools as needed."""

# WebSocket commands
WS_TYPE_CHAT = "claude_assistant/chat"
WS_TYPE_CONFIRM_ACTION = "claude_assistant/confirm_action"
WS_TYPE_GET_PENDING = "claude_assistant/get_pending"
WS_TYPE_GET_ENTITIES = "claude_assistant/get_entities"
WS_TYPE_SETTINGS = "claude_assistant/settings"

# Storage keys
STORAGE_KEY_HISTORY = f"{DOMAIN}_history"
STORAGE_KEY_PENDING = f"{DOMAIN}_pending"

# Limits
MAX_HISTORY_ITEMS = 100
ACTION_CONFIRMATION_TIMEOUT = 300  # 5 minutes
RATE_LIMIT_CALLS_PER_MINUTE = 30

# Panel info
PANEL_TITLE = "Claude Assistant"
PANEL_ICON = "mdi:robot"
