# Changelog

## 1.1.1 (2026-07-12)

- Panel UI translated to English (tabs, chat, logs, stats, settings — previously
  hardcoded Polish labels).
- `services.yaml` now documents the services that are actually registered
  (`chat`, `clear_history`); removed `send_message` / `execute_action` /
  `get_history`, which were never implemented.
- Unit tests (manifest/const consistency, model-selection logic) + `tests` CI
  workflow.

## 1.1.0 (2026-07-12)

- Home Assistant 2026.3.1 compatibility.
- hassfest fixes.

## 1.0.1

- Initial public release: conversation agent, sidebar panel (chat, logs,
  stats, settings), `chat` / `clear_history` services.
