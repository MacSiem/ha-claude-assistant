/**
 * Claude Assistant Panel for Home Assistant
 * Features: Chat, Logs, Statistics/Visualizations, Settings
 */

class ClaudeAssistantPanel extends HTMLElement {
  constructor() {
    super();
    this._hass = null;
    this._config = {};
    this._activeTab = "chat";
    this._chatMessages = [];
    this._logs = [];
    this._stats = {};
    this._settings = {};
    this._isLoading = false;
    this._logsTotal = 0;
    this._logsOffset = 0;
  }

  set hass(hass) {
    this._hass = hass;
    if (!this.shadowRoot) {
      this._render();
      this._loadSettings();
      this._loadStats();
    }
  }

  setConfig(config) {
    this._config = config;
  }

  set panel(panel) {
    this._config = panel.config || {};
  }

  // ─── Data Loading ──────────────────────────────────────────
  async _loadSettings() {
    if (!this._hass) return;
    try {
      const result = await this._hass.connection.sendMessagePromise({
        type: "claude_assistant/settings",
      });
      this._settings = result.settings || {};
      this._updateSettings();
    } catch (e) {
      console.error("Failed to load settings:", e);
    }
  }

  async _loadStats() {
    if (!this._hass) return;
    try {
      const result = await this._hass.connection.sendMessagePromise({
        type: "claude_assistant/get_stats",
      });
      this._stats = result.stats || {};
      this._updateStats();
    } catch (e) {
      console.error("Failed to load stats:", e);
    }
  }

  async _loadLogs(reset = false) {
    if (!this._hass) return;
    if (reset) this._logsOffset = 0;
    try {
      const result = await this._hass.connection.sendMessagePromise({
        type: "claude_assistant/get_logs",
        limit: 50,
        offset: this._logsOffset,
      });
      this._logs = result.logs || [];
      this._logsTotal = result.total || 0;
      this._updateLogs();
    } catch (e) {
      console.error("Failed to load logs:", e);
    }
  }

  async _sendMessage(text) {
    if (!this._hass || !text.trim() || this._isLoading) return;
    this._isLoading = true;

    this._chatMessages.push({ role: "user", content: text, time: new Date() });
    this._updateChat();

    try {
      const result = await this._hass.connection.sendMessagePromise({
        type: "claude_assistant/chat",
        message: text,
      });
      this._chatMessages.push({
        role: "assistant",
        content: result.text,
        time: new Date(),
        tokens_in: result.tokens_in,
        tokens_out: result.tokens_out,
        response_time_ms: result.response_time_ms,
        model: result.model,
      });
    } catch (e) {
      this._chatMessages.push({
        role: "error",
        content: "Error: " + (e.message || e),
        time: new Date(),
      });
    }

    this._isLoading = false;
    this._updateChat();
    this._loadStats();
  }

  async _updateSettingsOnServer(key, value) {
    if (!this._hass) return;
    try {
      const msg = { type: "claude_assistant/update_settings" };
      msg[key] = value;
      const result = await this._hass.connection.sendMessagePromise(msg);
      this._settings = result.settings || this._settings;
    } catch (e) {
      console.error("Failed to update setting:", e);
    }
  }

  async _clearLogs() {
    if (!this._hass) return;
    try {
      await this._hass.connection.sendMessagePromise({
        type: "claude_assistant/clear_logs",
      });
      this._logs = [];
      this._logsTotal = 0;
      this._updateLogs();
    } catch (e) {
      console.error("Failed to clear logs:", e);
    }
  }

  // ─── Render ────────────────────────────────────────────────
  _render() {
    const shadow = this.attachShadow({ mode: "open" });
    shadow.innerHTML = `
      <style>
        :host {
          display: block;
          height: 100%;
          --primary: #6C63FF;
          --primary-dark: #5A52D5;
          --bg: #f5f5f5;
          --card-bg: #ffffff;
          --text: #1a1a2e;
          --text-secondary: #6b7280;
          --border: #e5e7eb;
          --success: #10b981;
          --warning: #f59e0b;
          --error: #ef4444;
          --chat-user: #6C63FF;
          --chat-assistant: #f0f0f0;
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }
        @media (prefers-color-scheme: dark) {
          :host {
            --bg: #1a1a2e;
            --card-bg: #16213e;
            --text: #e2e8f0;
            --text-secondary: #94a3b8;
            --border: #334155;
            --chat-assistant: #1e293b;
          }
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        .container {
          display: flex;
          flex-direction: column;
          height: 100vh;
          background: var(--bg);
          color: var(--text);
        }

        /* Header */
        .header {
          display: flex;
          align-items: center;
          padding: 16px 24px;
          background: var(--card-bg);
          border-bottom: 1px solid var(--border);
          gap: 12px;
        }
        .header-icon {
          width: 36px; height: 36px;
          background: var(--primary);
          border-radius: 10px;
          display: flex; align-items: center; justify-content: center;
          color: white; font-size: 20px;
        }
        .header h1 { font-size: 20px; font-weight: 600; }
        .header .subtitle { font-size: 12px; color: var(--text-secondary); }

        /* Tabs */
        .tabs {
          display: flex;
          background: var(--card-bg);
          border-bottom: 1px solid var(--border);
          padding: 0 16px;
        }
        .tab {
          padding: 12px 20px;
          cursor: pointer;
          border-bottom: 2px solid transparent;
          color: var(--text-secondary);
          font-size: 14px;
          font-weight: 500;
          transition: all 0.2s;
          display: flex; align-items: center; gap: 6px;
        }
        .tab:hover { color: var(--text); }
        .tab.active {
          color: var(--primary);
          border-bottom-color: var(--primary);
        }

        /* Tab Content */
        .tab-content { flex: 1; overflow: hidden; display: none; }
        .tab-content.active { display: flex; flex-direction: column; }

        /* ── Chat Tab ── */
        .chat-messages {
          flex: 1;
          overflow-y: auto;
          padding: 20px;
          display: flex;
          flex-direction: column;
          gap: 12px;
        }
        .message {
          max-width: 80%;
          padding: 12px 16px;
          border-radius: 16px;
          font-size: 14px;
          line-height: 1.5;
          word-wrap: break-word;
          white-space: pre-wrap;
        }
        .message.user {
          align-self: flex-end;
          background: var(--chat-user);
          color: white;
          border-bottom-right-radius: 4px;
        }
        .message.assistant {
          align-self: flex-start;
          background: var(--chat-assistant);
          border-bottom-left-radius: 4px;
        }
        .message.error {
          align-self: center;
          background: var(--error);
          color: white;
          font-size: 13px;
        }
        .message-meta {
          font-size: 11px;
          color: var(--text-secondary);
          margin-top: 4px;
          opacity: 0.7;
        }
        .message.user .message-meta { color: rgba(255,255,255,0.7); }
        .typing-indicator {
          align-self: flex-start;
          padding: 12px 16px;
          background: var(--chat-assistant);
          border-radius: 16px;
          font-size: 14px;
          color: var(--text-secondary);
        }
        .typing-indicator span {
          animation: blink 1.4s infinite;
        }
        .typing-indicator span:nth-child(2) { animation-delay: 0.2s; }
        .typing-indicator span:nth-child(3) { animation-delay: 0.4s; }
        @keyframes blink { 0%, 60%, 100% { opacity: 0.2; } 30% { opacity: 1; } }

        .chat-input-area {
          padding: 16px 20px;
          background: var(--card-bg);
          border-top: 1px solid var(--border);
          display: flex;
          gap: 10px;
        }
        .chat-input-area input {
          flex: 1;
          padding: 12px 16px;
          border: 1px solid var(--border);
          border-radius: 24px;
          font-size: 14px;
          background: var(--bg);
          color: var(--text);
          outline: none;
        }
        .chat-input-area input:focus { border-color: var(--primary); }
        .chat-input-area button {
          padding: 12px 20px;
          background: var(--primary);
          color: white;
          border: none;
          border-radius: 24px;
          cursor: pointer;
          font-size: 14px;
          font-weight: 500;
          transition: background 0.2s;
        }
        .chat-input-area button:hover { background: var(--primary-dark); }
        .chat-input-area button:disabled { opacity: 0.5; cursor: not-allowed; }

        .empty-state {
          flex: 1;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          color: var(--text-secondary);
          gap: 8px;
        }
        .empty-state .icon { font-size: 48px; opacity: 0.3; }

        /* ── Logs Tab ── */
        .logs-container { flex: 1; overflow-y: auto; padding: 16px; }
        .logs-toolbar {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 12px 16px;
          background: var(--card-bg);
          border-bottom: 1px solid var(--border);
        }
        .logs-toolbar span { font-size: 13px; color: var(--text-secondary); }
        .btn-sm {
          padding: 6px 12px;
          border: 1px solid var(--border);
          border-radius: 6px;
          background: var(--card-bg);
          color: var(--text);
          cursor: pointer;
          font-size: 12px;
        }
        .btn-sm:hover { background: var(--bg); }
        .btn-danger { border-color: var(--error); color: var(--error); }

        .log-entry {
          padding: 12px 16px;
          border-bottom: 1px solid var(--border);
          font-size: 13px;
        }
        .log-entry:last-child { border-bottom: none; }
        .log-time { color: var(--text-secondary); font-size: 11px; font-family: monospace; }
        .log-type {
          display: inline-block;
          padding: 2px 8px;
          border-radius: 4px;
          font-size: 11px;
          font-weight: 600;
          text-transform: uppercase;
          margin: 0 6px;
        }
        .log-type.conversation { background: #dbeafe; color: #1d4ed8; }
        .log-type.assist_conversation { background: #d1fae5; color: #065f46; }
        .log-type.error { background: #fee2e2; color: #b91c1c; }
        .log-type.action_confirmed { background: #fef3c7; color: #92400e; }
        .log-type.action_rejected { background: #fce7f3; color: #9d174d; }
        .log-type.settings_changed { background: #e0e7ff; color: #4338ca; }
        .log-type.system { background: #f3f4f6; color: #374151; }
        .log-user-msg { margin-top: 4px; color: var(--text); }
        .log-assistant-msg { margin-top: 2px; color: var(--text-secondary); font-style: italic; }
        .log-tokens { font-size: 11px; color: var(--text-secondary); margin-top: 2px; }

        /* ── Stats Tab ── */
        .stats-container { flex: 1; overflow-y: auto; padding: 20px; }
        .stats-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
          gap: 16px;
          margin-bottom: 24px;
        }
        .stat-card {
          background: var(--card-bg);
          border-radius: 12px;
          padding: 20px;
          border: 1px solid var(--border);
        }
        .stat-label { font-size: 12px; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.5px; }
        .stat-value { font-size: 28px; font-weight: 700; margin-top: 4px; color: var(--primary); }
        .stat-sub { font-size: 12px; color: var(--text-secondary); margin-top: 2px; }

        .chart-card {
          background: var(--card-bg);
          border-radius: 12px;
          padding: 20px;
          border: 1px solid var(--border);
          margin-bottom: 16px;
        }
        .chart-card h3 { font-size: 14px; margin-bottom: 12px; }
        .chart-bar-container { display: flex; align-items: flex-end; gap: 4px; height: 120px; }
        .chart-bar {
          flex: 1;
          background: var(--primary);
          border-radius: 4px 4px 0 0;
          min-height: 2px;
          position: relative;
          transition: height 0.3s;
          opacity: 0.8;
        }
        .chart-bar:hover { opacity: 1; }
        .chart-bar-label {
          position: absolute;
          bottom: -18px;
          left: 50%;
          transform: translateX(-50%);
          font-size: 10px;
          color: var(--text-secondary);
        }
        .chart-bar-value {
          position: absolute;
          top: -18px;
          left: 50%;
          transform: translateX(-50%);
          font-size: 10px;
          color: var(--text-secondary);
          white-space: nowrap;
        }

        .model-usage-list { margin-top: 8px; }
        .model-usage-item {
          display: flex;
          align-items: center;
          gap: 8px;
          margin-bottom: 8px;
          font-size: 13px;
        }
        .model-usage-bar {
          height: 8px;
          background: var(--primary);
          border-radius: 4px;
          transition: width 0.3s;
        }

        /* ── Settings Tab ── */
        .settings-container { flex: 1; overflow-y: auto; padding: 20px; }
        .settings-section {
          background: var(--card-bg);
          border-radius: 12px;
          padding: 20px;
          border: 1px solid var(--border);
          margin-bottom: 16px;
        }
        .settings-section h3 {
          font-size: 15px;
          margin-bottom: 16px;
          padding-bottom: 8px;
          border-bottom: 1px solid var(--border);
        }
        .setting-row {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 10px 0;
        }
        .setting-row + .setting-row { border-top: 1px solid var(--border); }
        .setting-label { font-size: 14px; }
        .setting-desc { font-size: 12px; color: var(--text-secondary); }
        .setting-row select,
        .setting-row input[type="number"],
        .setting-row input[type="range"] {
          padding: 8px 12px;
          border: 1px solid var(--border);
          border-radius: 8px;
          background: var(--bg);
          color: var(--text);
          font-size: 14px;
          min-width: 180px;
        }
        .setting-row textarea {
          width: 100%;
          min-height: 100px;
          padding: 12px;
          border: 1px solid var(--border);
          border-radius: 8px;
          background: var(--bg);
          color: var(--text);
          font-size: 13px;
          font-family: inherit;
          resize: vertical;
          margin-top: 8px;
        }
        .setting-full { flex-direction: column; align-items: stretch; gap: 4px; }
        .temp-display { font-size: 14px; font-weight: 600; color: var(--primary); min-width: 40px; text-align: right; }
        .auth-badge {
          display: inline-block;
          padding: 4px 10px;
          border-radius: 6px;
          font-size: 12px;
          font-weight: 600;
        }
        .auth-badge.api_key { background: #dbeafe; color: #1d4ed8; }
        .auth-badge.personal_account { background: #d1fae5; color: #065f46; }
      </style>

      <div class="container">
        <div class="header">
          <div class="header-icon">🤖</div>
          <div>
            <h1>Claude Assistant</h1>
            <div class="subtitle">AI-powered smart home assistant</div>
          </div>
        </div>

        <div class="tabs">
          <div class="tab active" data-tab="chat">💬 Chat</div>
          <div class="tab" data-tab="logs">📋 Logi</div>
          <div class="tab" data-tab="stats">📊 Statystyki</div>
          <div class="tab" data-tab="settings">⚙️ Ustawienia</div>
        </div>

        <!-- Chat Tab -->
        <div class="tab-content active" id="tab-chat">
          <div class="chat-messages" id="chat-messages">
            <div class="empty-state">
              <div class="icon">🤖</div>
              <div>Napisz wiadomość, aby rozpocząć rozmowę z Claude</div>
            </div>
          </div>
          <div class="chat-input-area">
            <input type="text" id="chat-input" placeholder="Napisz wiadomość..." autocomplete="off" />
            <button id="chat-send">Wyślij</button>
          </div>
        </div>

        <!-- Logs Tab -->
        <div class="tab-content" id="tab-logs">
          <div class="logs-toolbar">
            <span id="logs-count">0 wpisów</span>
            <div style="display:flex;gap:8px;">
              <button class="btn-sm" id="logs-refresh">Odśwież</button>
              <button class="btn-sm btn-danger" id="logs-clear">Wyczyść</button>
            </div>
          </div>
          <div class="logs-container" id="logs-list"></div>
        </div>

        <!-- Stats Tab -->
        <div class="tab-content" id="tab-stats">
          <div class="stats-container" id="stats-content"></div>
        </div>

        <!-- Settings Tab -->
        <div class="tab-content" id="tab-settings">
          <div class="settings-container" id="settings-content"></div>
        </div>
      </div>
    `;

    this._setupEvents();
  }

  _setupEvents() {
    const shadow = this.shadowRoot;

    // Tab switching
    shadow.querySelectorAll(".tab").forEach((tab) => {
      tab.addEventListener("click", () => {
        shadow.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
        shadow.querySelectorAll(".tab-content").forEach((c) => c.classList.remove("active"));
        tab.classList.add("active");
        const tabId = tab.dataset.tab;
        shadow.getElementById("tab-" + tabId).classList.add("active");
        this._activeTab = tabId;

        if (tabId === "logs") this._loadLogs(true);
        if (tabId === "stats") this._loadStats();
        if (tabId === "settings") this._loadSettings();
      });
    });

    // Chat
    const chatInput = shadow.getElementById("chat-input");
    const chatSend = shadow.getElementById("chat-send");

    chatSend.addEventListener("click", () => {
      this._sendMessage(chatInput.value);
      chatInput.value = "";
    });
    chatInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        this._sendMessage(chatInput.value);
        chatInput.value = "";
      }
    });

    // Logs
    shadow.getElementById("logs-refresh").addEventListener("click", () => this._loadLogs(true));
    shadow.getElementById("logs-clear").addEventListener("click", () => {
      if (confirm("Czy na pewno chcesz wyczyścić wszystkie logi?")) {
        this._clearLogs();
      }
    });
  }

  // ─── UI Updates ────────────────────────────────────────────
  _updateChat() {
    const container = this.shadowRoot.getElementById("chat-messages");
    if (!container) return;

    let html = "";
    if (this._chatMessages.length === 0) {
      html = `<div class="empty-state">
        <div class="icon">🤖</div>
        <div>Napisz wiadomość, aby rozpocząć rozmowę z Claude</div>
      </div>`;
    } else {
      for (const msg of this._chatMessages) {
        const time = msg.time ? new Date(msg.time).toLocaleTimeString("pl-PL") : "";
        const meta = [];
        if (msg.tokens_in) meta.push(msg.tokens_in + "→ tok");
        if (msg.tokens_out) meta.push(msg.tokens_out + "← tok");
        if (msg.response_time_ms) meta.push(msg.response_time_ms + "ms");
        if (msg.model) meta.push(msg.model.split("-").slice(0, 2).join("-"));

        html += `<div class="message ${msg.role}">
          ${this._escapeHtml(msg.content)}
          <div class="message-meta">${time}${meta.length ? " · " + meta.join(" · ") : ""}</div>
        </div>`;
      }
      if (this._isLoading) {
        html += `<div class="typing-indicator"><span>●</span><span>●</span><span>●</span></div>`;
      }
    }

    container.innerHTML = html;
    container.scrollTop = container.scrollHeight;

    const sendBtn = this.shadowRoot.getElementById("chat-send");
    if (sendBtn) sendBtn.disabled = this._isLoading;
  }

  _updateLogs() {
    const container = this.shadowRoot.getElementById("logs-list");
    const counter = this.shadowRoot.getElementById("logs-count");
    if (!container) return;

    counter.textContent = this._logsTotal + " wpisów";

    if (this._logs.length === 0) {
      container.innerHTML = `<div class="empty-state" style="padding:40px"><div>Brak logów</div></div>`;
      return;
    }

    let html = "";
    for (const log of this._logs) {
      const time = log.timestamp
        ? new Date(log.timestamp).toLocaleString("pl-PL")
        : "—";
      const type = log.type || "unknown";

      html += `<div class="log-entry">
        <span class="log-time">${time}</span>
        <span class="log-type ${type}">${type.replace("_", " ")}</span>`;

      if (log.user_message) {
        html += `<div class="log-user-msg">👤 ${this._escapeHtml(log.user_message.substring(0, 200))}</div>`;
      }
      if (log.assistant_message) {
        html += `<div class="log-assistant-msg">🤖 ${this._escapeHtml(log.assistant_message.substring(0, 200))}</div>`;
      }
      if (log.error) {
        html += `<div class="log-user-msg" style="color:var(--error)">❌ ${this._escapeHtml(log.error)}</div>`;
      }
      if (log.message) {
        html += `<div class="log-user-msg">${this._escapeHtml(log.message)}</div>`;
      }
      if (log.changes) {
        html += `<div class="log-user-msg">Zmieniono: ${this._escapeHtml(JSON.stringify(log.changes))}</div>`;
      }
      if (log.tokens_in || log.tokens_out) {
        html += `<div class="log-tokens">Tokeny: ${log.tokens_in || 0}→ / ${log.tokens_out || 0}← | ${log.response_time_ms || 0}ms${log.model ? " | " + log.model : ""}</div>`;
      }

      html += `</div>`;
    }

    container.innerHTML = html;
  }

  _updateStats() {
    const container = this.shadowRoot.getElementById("stats-content");
    if (!container) return;

    const s = this._stats;
    const avgTime = s.avg_response_time_ms || 0;
    const totalTokens = (s.total_tokens_in || 0) + (s.total_tokens_out || 0);
    const todayTokens = (s.tokens_today_in || 0) + (s.tokens_today_out || 0);

    // Hourly chart
    let hourlyBars = "";
    const hourly = s.hourly_usage || {};
    const maxHourly = Math.max(...Object.values(hourly), 1);
    for (let h = 0; h < 24; h++) {
      const key = String(h).padStart(2, "0");
      const val = hourly[key] || 0;
      const height = Math.max((val / maxHourly) * 100, 2);
      hourlyBars += `<div class="chart-bar" style="height:${height}%">
        ${val > 0 ? `<div class="chart-bar-value">${val}</div>` : ""}
        <div class="chart-bar-label">${key}</div>
      </div>`;
    }

    // Daily history chart
    let dailyBars = "";
    const daily = s.daily_history || [];
    const maxDaily = Math.max(...daily.map((d) => d.conversations), 1);
    for (const d of daily.slice(-14)) {
      const height = Math.max((d.conversations / maxDaily) * 100, 2);
      const label = d.date ? d.date.slice(5) : "?";
      dailyBars += `<div class="chart-bar" style="height:${height}%">
        ${d.conversations > 0 ? `<div class="chart-bar-value">${d.conversations}</div>` : ""}
        <div class="chart-bar-label">${label}</div>
      </div>`;
    }

    // Model usage
    let modelHtml = "";
    const models = s.model_usage || {};
    const totalModelUse = Object.values(models).reduce((a, b) => a + b, 0) || 1;
    for (const [model, count] of Object.entries(models)) {
      const pct = Math.round((count / totalModelUse) * 100);
      const shortName = model.split("-").slice(0, 2).join("-");
      modelHtml += `<div class="model-usage-item">
        <span style="min-width:120px">${shortName}</span>
        <div style="flex:1;background:var(--border);border-radius:4px;height:8px;">
          <div class="model-usage-bar" style="width:${pct}%"></div>
        </div>
        <span>${count} (${pct}%)</span>
      </div>`;
    }

    container.innerHTML = `
      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-label">Rozmowy dzisiaj</div>
          <div class="stat-value">${s.conversations_today || 0}</div>
          <div class="stat-sub">Łącznie: ${s.total_conversations || 0}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Tokeny dzisiaj</div>
          <div class="stat-value">${this._formatNumber(todayTokens)}</div>
          <div class="stat-sub">↗ ${s.tokens_today_in || 0} / ↙ ${s.tokens_today_out || 0}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Łączne tokeny</div>
          <div class="stat-value">${this._formatNumber(totalTokens)}</div>
          <div class="stat-sub">↗ ${this._formatNumber(s.total_tokens_in || 0)} / ↙ ${this._formatNumber(s.total_tokens_out || 0)}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Śr. czas odpowiedzi</div>
          <div class="stat-value">${this._formatNumber(avgTime)}<span style="font-size:14px">ms</span></div>
          <div class="stat-sub">Na podstawie ${s.total_conversations || 0} rozmów</div>
        </div>
      </div>

      <div class="chart-card">
        <h3>Aktywność godzinowa (dzisiaj)</h3>
        <div class="chart-bar-container" style="margin-bottom:24px;">
          ${hourlyBars || '<div style="color:var(--text-secondary);font-size:13px;">Brak danych</div>'}
        </div>
      </div>

      ${daily.length > 0 ? `
      <div class="chart-card">
        <h3>Historia dzienna (ostatnie 14 dni)</h3>
        <div class="chart-bar-container" style="margin-bottom:24px;">
          ${dailyBars}
        </div>
      </div>` : ""}

      <div class="chart-card">
        <h3>Użycie modeli</h3>
        <div class="model-usage-list">
          ${modelHtml || '<div style="color:var(--text-secondary);font-size:13px;">Brak danych</div>'}
        </div>
      </div>
    `;
  }

  _updateSettings() {
    const container = this.shadowRoot.getElementById("settings-content");
    if (!container) return;

    const s = this._settings;
    const models = ["claude-opus-4-20250514", "claude-sonnet-4-20250514", "claude-haiku-3-5-20241022"];
    const safetyLevels = {
      all_actions: "Potwierdzaj wszystkie",
      dangerous_only: "Tylko niebezpieczne",
      none: "Bez potwierdzeń",
    };

    const modelOptions = models.map((m) => {
      const sel = m === s.model ? "selected" : "";
      return `<option value="${m}" ${sel}>${m.split("-").slice(0, 2).join("-")}</option>`;
    }).join("");

    const safetyOptions = Object.entries(safetyLevels).map(([k, v]) => {
      const sel = k === s.safety_level ? "selected" : "";
      return `<option value="${k}" ${sel}>${v}</option>`;
    }).join("");

    const authLabel = s.auth_type === "personal_account" ? "Konto osobiste" : "Klucz API";
    const authClass = s.auth_type || "api_key";

    container.innerHTML = `
      <div class="settings-section">
        <h3>Autoryzacja</h3>
        <div class="setting-row">
          <div>
            <div class="setting-label">Metoda logowania</div>
            <div class="setting-desc">Zmiana wymaga rekonfiguracji integracji</div>
          </div>
          <span class="auth-badge ${authClass}">${authLabel}</span>
        </div>
      </div>

      <div class="settings-section">
        <h3>Model AI</h3>
        <div class="setting-row">
          <div>
            <div class="setting-label">Model Claude</div>
            <div class="setting-desc">Wpływa na jakość i szybkość odpowiedzi</div>
          </div>
          <select id="set-model">${modelOptions}</select>
        </div>
      </div>

      <div class="settings-section">
        <h3>Parametry generowania</h3>
        <div class="setting-row">
          <div>
            <div class="setting-label">Temperatura</div>
            <div class="setting-desc">Niższa = bardziej precyzyjne, wyższa = bardziej kreatywne</div>
          </div>
          <div style="display:flex;align-items:center;gap:8px;">
            <input type="range" id="set-temperature" min="0" max="1" step="0.05" value="${s.temperature || 0.7}" style="min-width:120px" />
            <span class="temp-display" id="temp-val">${s.temperature || 0.7}</span>
          </div>
        </div>
        <div class="setting-row">
          <div>
            <div class="setting-label">Maksymalna liczba tokenów</div>
            <div class="setting-desc">Limit długości odpowiedzi (256 - 8192)</div>
          </div>
          <input type="number" id="set-max-tokens" min="256" max="8192" step="256" value="${s.max_tokens || 2048}" />
        </div>
      </div>

      <div class="settings-section">
        <h3>Bezpieczeństwo</h3>
        <div class="setting-row">
          <div>
            <div class="setting-label">Poziom potwierdzeń</div>
            <div class="setting-desc">Kiedy pytać o potwierdzenie akcji smart home</div>
          </div>
          <select id="set-safety">${safetyOptions}</select>
        </div>
      </div>

      <div class="settings-section">
        <h3>Prompt systemowy</h3>
        <div class="setting-row setting-full">
          <div>
            <div class="setting-label">Instrukcje dla Claude</div>
            <div class="setting-desc">Określ zachowanie i rolę asystenta</div>
          </div>
          <textarea id="set-prompt">${this._escapeHtml(s.system_prompt || "")}</textarea>
        </div>
      </div>
    `;

    // Bind events
    const self = this;

    container.querySelector("#set-model").addEventListener("change", function () {
      self._updateSettingsOnServer("model", this.value);
    });

    const tempSlider = container.querySelector("#set-temperature");
    const tempVal = container.querySelector("#temp-val");
    tempSlider.addEventListener("input", function () {
      tempVal.textContent = this.value;
    });
    tempSlider.addEventListener("change", function () {
      self._updateSettingsOnServer("temperature", parseFloat(this.value));
    });

    container.querySelector("#set-max-tokens").addEventListener("change", function () {
      self._updateSettingsOnServer("max_tokens", parseInt(this.value));
    });

    container.querySelector("#set-safety").addEventListener("change", function () {
      self._updateSettingsOnServer("safety_level", this.value);
    });

    let promptTimeout;
    container.querySelector("#set-prompt").addEventListener("input", function () {
      clearTimeout(promptTimeout);
      const val = this.value;
      promptTimeout = setTimeout(() => {
        self._updateSettingsOnServer("system_prompt", val);
      }, 1000);
    });
  }

  // ─── Helpers ───────────────────────────────────────────────
  _escapeHtml(str) {
    if (!str) return "";
    return str
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  _formatNumber(n) {
    if (n >= 1000000) return (n / 1000000).toFixed(1) + "M";
    if (n >= 1000) return (n / 1000).toFixed(1) + "K";
    return String(n);
  }
}

customElements.define("claude-assistant-panel", ClaudeAssistantPanel);
