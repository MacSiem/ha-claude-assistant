# Claude Assistant Integration for Home Assistant

A powerful integration that connects Home Assistant with Anthropic's Claude AI, enabling intelligent voice-controlled smart home automation with built-in safety confirmations.

## Features

- **Natural Language Control**: Control your smart home with Claude AI using natural language
- **Safety Confirmations**: Configurable confirmation system for dangerous actions (locks, alarms, covers, etc.)
- **Conversation Agent**: Registered with Home Assistant's Assist pipeline for voice commands
- **WebSocket API**: Real-time communication panel for chat and action management
- **Entity Access**: Full read/write access to Home Assistant devices
- **Tool Support**: Call services, query states, get history, and more
- **Conversation Memory**: Maintains conversation context across sessions
- **Multiple Models**: Support for Claude Opus, Sonnet, and Haiku
- **Flexible Safety Levels**: all_actions, dangerous_only, or none

## Installation

### Prerequisites

- Home Assistant 2024.1 or later
- Anthropic API key (get one at https://console.anthropic.com/account/keys)

### Setup Steps

1. Copy the integration folder to `custom_components/claude_assistant/`

```bash
cp -r ha-claude-assistant/custom_components/claude_assistant ~/.homeassistant/custom_components/
```

2. Restart Home Assistant

3. Go to Settings â Devices & Services â Integrations

4. Click "Create Integration" and search for "Claude Assistant"

5. Follow the config flow:
   - Enter your Anthropic API key
   - Select preferred Claude model
   - Choose safety level for action confirmations

## Configuration

### Safety Levels

- **all_actions**: Requires confirmation for all Claude-initiated actions
- **dangerous_only**: Confirmation required only for locks, alarms, covers, sirens, climate control
- **none**: No confirmations (use with caution)

### Dangerous Domains

The following entity domains trigger confirmations at "dangerous_only" level:

- `lock` - Smart locks
- `alarm_control_panel` - Alarm systems
- `cover` - Blinds, garage doors, covers
- `camera` - Security cameras
- `siren` - Sirens and emergency alerts
- `climate` - Temperature control
- `water_heater` - Water heaters

### Dangerous Services

High-risk service calls that trigger confirmations:

- `lock.unlock`, `lock.open`
- `alarm_control_panel.alarm_disarm`, `alarm_control_panel.alarm_arm_away`
- `cover.open_cover`, `cover.close_cover`
- `camera.turn_off`
- `switch.turn_off`, `switch.turn_on`
- `light.turn_off`, `light.turn_on`
- `climate.set_temperature`
- `water_heater.set_temperature`
- `siren.turn_on`

## Services

### send_message

Send a message to Claude Assistant for processing.

```yaml
service: claude_assistant.send_message
data:
  message: "Turn on the living room lights"
```

### execute_action

Execute a pending action that was queued for confirmation.

```yaml
service: claude_assistant.execute_action
data:
  action_id: "550e8400-e29b-41d4-a716-446655440000"
```

### get_history

Retrieve conversation history with Claude.

```yaml
service: claude_assistant.get_history
```

## WebSocket API

The integration provides WebSocket endpoints for real-time communication.

### Commands

#### claude_assistant/chat

Send a message and get a response from Claude.

```json
{
  "type": "claude_assistant/chat",
  "id": 1,
  "message": "What devices do I have?"
}
```

#### claude_assistant/confirm_action

Approve or reject a pending action.

```json
{
  "type": "claude_assistant/confirm_action",
  "id": 2,
  "action_id": "550e8400-e29b-41d4-a716-446655440000",
  "confirmed": true
}
```

#### claude_assistant/get_pending

Get all pending actions awaiting confirmation.

```json
{
  "type": "claude_assistant/get_pending",
  "id": 3
}
```

#### claude_assistant/get_entities

Get list of all available entities.

```json
{
  "type": "claude_assistant/get_entities",
  "id": 4
}
```

#### claude_assistant/settings

Get current Claude Assistant settings.

```json
{
  "type": "claude_assistant/settings",
  "id": 5
}
```

## Claude Tools

Claude has access to the following tools for home automation:

### call_service

Execute a Home Assistant service.

```json
{
  "name": "call_service",
  "domain": "light",
  "service": "turn_on",
  "entity_id": "light.living_room",
  "data": {"brightness": 255}
}
```

### get_state

Query the state of an entity.

```json
{
  "name": "get_state",
  "entity_id": "light.living_room"
}
```

### get_history

Get recent state history for an entity.

```json
{
  "name": "get_history",
  "entity_id": "sensor.temperature",
  "hours": 24
}
```

### analyze_energy

Analyze energy consumption patterns.

```json
{
  "name": "analyze_energy",
  "timeframe": "daily"
}
```

### set_automation

Create or update automation rules.

```json
{
  "name": "set_automation",
  "name": "Morning Lights",
  "trigger": {"platform": "time", "at": "07:00:00"},
  "action": {"service": "light.turn_on", "target": {"entity_id": "light.bedroom"}}
}
```

## Claude Models

Supported Claude models:

- **claude-opus-4-20250514** (Default) - Most capable, best for complex tasks
- **claude-sonnet-4-20250514** - Balanced performance and speed
- **claude-haiku-3-5-20241022** - Fast and cost-effective

## Conversation Agent

Claude is registered as a conversation agent and can be used with Home Assistant's Assist:

- Works with the "Assist" voice pipeline
- Understands smart home context
- Can control devices with voice commands
- Provides natural language explanations

## Data Storage

The integration stores:

- **Conversation History**: Last 20 messages (kept in memory)
- **Pending Actions**: Action confirmations with timestamps
- **Configuration**: API key, model selection, safety level

No personal data beyond your Home Assistant entity names is transmitted to Anthropic. Entity data is only sent to Claude in API requests and is not stored.

## Advanced Configuration

### Options Flow

After initial setup, you can change settings via Options:

1. Go to Settings â Devices & Services â Integrations
2. Click on Claude Assistant
3. Click "Options"
4. Change model or safety level
5. Click "Save"

### Custom System Prompt

For advanced users, the system prompt can be customized by modifying the `DEFAULT_SYSTEM_PROMPT` in `const.py`.

## Troubleshooting

### Invalid API Key

- Check that your API key is correct at https://console.anthropic.com/account/keys
- Ensure the key is for the Claude API (not a different Anthropic product)
- Try re-entering the key in the integration options

### Action Confirmation Timeout

- Actions automatically expire after 5 minutes if not confirmed
- Notifications are sent to persistent_notification for confirmations
- Check Home Assistant notifications panel for pending confirmations

### WebSocket Connection Issues

- Ensure your Home Assistant instance is accessible via WebSocket
- Check browser console for connection errors
- Verify firewall isn't blocking WebSocket connections

### Low Response Quality

- Try a different model (e.g., Claude Opus for complex requests)
- Ensure your Home Assistant state is clean (no duplicate entities)
- Provide more context in your queries

## Architecture

### Components

1. **api_client.py**: Handles Anthropic API communication
2. **action_handler.py**: Classifies and manages action confirmations
3. **conversation.py**: Conversation agent for Assist pipeline
4. **config_flow.py**: User-friendly configuration interface
5. **entity_helper.py**: Utilities for entity operations

### Data Flow

```
User Input (Chat/Voice)
    â
Conversation Agent / WebSocket Handler
    â
Claude API Client (with system prompt + tools)
    â
Claude Response
    â
Text Response + Tool Calls
    â
Action Handler (Classification + Confirmation)
    â
Service Execution (if approved)
```

## Security Considerations

- **API Key**: Stored securely in Home Assistant configuration
- **Entity Access**: Claude can see all entity states but respects HA's service restrictions
- **Action Confirmations**: User must explicitly approve dangerous operations
- **Data Transmission**: Only necessary data sent to Anthropic API
- **No Logging**: Sensitive information is not logged

## Development

### Testing Services Locally

```bash
# Start Home Assistant dev environment
hass --config ./test_config

# Trigger a service call
curl -X POST http://localhost:8123/api/services/claude_assistant/send_message \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "Turn on the lights"}'
```

### Building Frontend Panel

The integration supports a custom frontend panel. Create a custom element in:
`www/claude-assistant-panel.js`

Register it by modifying the panel registration in `__init__.py`.

## License

This integration is provided as-is for Home Assistant use.

## Support

For issues, feature requests, or contributions, visit the repository at:
https://github.com/MacSiem/ha-claude-assistant

## Changelog

### Version 1.0.0 (Initial Release)

- Core Claude integration
- Action confirmation system
- Conversation agent for Assist
- WebSocket API for real-time communication
- Configuration flow with model selection
- Safety level configuration
- Entity access and state queries
- Service call execution

---

## Support

If you find this project useful, consider supporting its development:

<a href="https://buymeacoffee.com/macsiem" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" height="50" ></a>
<a href="https://www.paypal.com/donate/?hosted_button_id=Y967H4PLRBN8W" target="_blank"><img src="https://img.shields.io/badge/PayPal-Donate-blue?logo=paypal&logoColor=white" alt="PayPal Donate" height="50" ></a>
