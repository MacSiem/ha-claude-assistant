# Changelog

## 1.1.3 (2026-07-12)

- The `claude_assistant.chat` service now uses the same pipeline as the
  sidebar panel: entity-state context is included, the exchange is written to
  the panel's log store and stats, and with `response_variable` the reply
  (`response`, `tokens_in`, `tokens_out`, `response_time_ms`, `model`) is
  returned to the calling automation or script (`SupportsResponse.OPTIONAL`).
  Previously the service bypassed logging/stats entirely and discarded the
  reply (found by a real-use-case test on production).

## 1.1.2 (2026-07-12)

- Fixed sidebar-panel WebSocket contract bugs where the backend response
  shape didn't match what `frontend/panel.js` reads, breaking Logs pagination,
  Settings, Stats, and per-message chat metadata:
  - `claude_assistant/get_logs` now accepts the `limit`/`offset` the panel
    sends (previously rejected by the schema) and returns
    `{"logs": [...], "total": N}` instead of a bare list.
  - `claude_assistant/settings` now returns `{"settings": {...}}` instead of
    an unwrapped dict.
  - `claude_assistant/get_stats` now returns `{"stats": {...}}` and includes
    `total_conversations` / `total_tokens_in` / `total_tokens_out` alongside
    the existing `conversations_total` / `tokens_total_in` / `tokens_total_out`
    keys for backward compat.
  - `claude_assistant/chat` responses now include `tokens_in` / `tokens_out` /
    `response_time_ms` alongside the existing `input_tokens` / `output_tokens`
    / `time_ms` keys, so per-message token/timing metadata renders in the
    Chat tab.
- Fixed a `TypeError`/zombie-card bug in `frontend/confirmation-card.js`:
  the approve/reject buttons and the countdown-expiry handler read
  `this._data.id` unguarded, which threw if the card rendered (or its
  countdown expired) before `data` was ever set. Approve/Reject buttons are
  now disabled until `data` is set, and all three code paths guard against
  a missing `_data`.
- Added a comment in `frontend/card.js` marking the hardcoded `setTimeout`
  chat reply as experimental/not wired to the backend (kept intentionally;
  matches the README's existing "Is there a working Lovelace dashboard
  card?" answer — the card is not registered as a Lovelace resource
  anywhere in this integration).

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
