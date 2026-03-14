/**
 * Claude Assistant Sidebar Panel
 * Full chat interface with confirmation system, action controls, and settings
 * ~600 lines
 */

customElements.define(
  "claude-assistant-panel",
  class ClaudeAssistantPanel extends HTMLElement {
    constructor() {
      super();
      this.attachShadow({ mode: "open" });

      // State
      this._messages = [];
      this._hass = null;
      this._config = {};
      this._wsConnected = false;
      this._isWaitingResponse = false;
      this._pendingConfirmations = new Map();
      this._voiceEnabled = false;
      this._voiceOutput = false;
      this._recognition = null;
      this._isListening = false;
      this._expandedQuickActions = true;
      this._expandedEntities = true;
      this._expandedSettings = false;
      this._selectedEntities = new Set();
      this._confirmationLevel = "moderate";
      this._exposedDomains = new Set(["light", "switch", "climate", "lock"]);
    }

    set hass(hass) {
      this._hass = hass;
      if (!this._wsConnected && hass) {
        this.initWebSocket();
      }
    }

    set config(config) {
      this._config = config || {};
    }

    initWebSocket() {
      // Placeholder for WebSocket connection to HA
      // In production: hass.connection.subscribeMessage(...)
      this._wsConnected = true;
    }

    initVoiceRecognition() {
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      if (!SpeechRecognition) {
        console.warn("Speech Recognition not supported");
        return;
      }

      this._recognition = new SpeechRecognition();
      this._recognition.continuous = false;
      this._recognition.interimResults = true;

      this._recognition.onstart = () => {
        this._isListening = true;
        this.updateVoiceButton();
      };

      this._recognition.onend = () => {
        this._isListening = false;
        this.updateVoiceButton();
      };

      this._recognition.onresult = (event) => {
        let transcript = "";
        for (let i = event.resultIndex; i < event.results.length; i++) {
          transcript += event.results[i][0].transcript;
        }
        if (event.results[event.results.length - 1].isFinal) {
          this.setInputValue(transcript);
        }
      };

      this._recognition.onerror = (event) => {
        console.error("Speech recognition error:", event.error);
      };
    }

    connectedCallback() {
      this.render();
      this.setupEventListeners();
      this.initVoiceRecognition();
    }

    setupEventListeners() {
      const sendBtn = this.shadowRoot.querySelector(".send-btn");
      const inputField = this.shadowRoot.querySelector(".message-input");
      const voiceBtn = this.shadowRoot.querySelector(".voice-btn");
      const newConvBtn = this.shadowRoot.querySelector(".new-conversation-btn");
      const quickActionChips = this.shadowRoot.querySelectorAll(".quick-action-chip");
      const toggleQuickActions = this.shadowRoot.querySelector(".toggle-quick-actions");
      const toggleEntities = this.shadowRoot.querySelector(".toggle-entities");
      const toggleSettings = this.shadowRoot.querySelector(".toggle-settings");
      const settingsBtn = this.shadowRoot.querySelector(".settings-btn");
      const voiceToggle = this.shadowRoot.querySelector(".voice-toggle");
      const voiceOutputToggle = this.shadowRoot.querySelector(".voice-output-toggle");

      if (sendBtn) {
        sendBtn.addEventListener("click", () => this.sendMessage());
      }

      if (inputField) {
        inputField.addEventListener("keypress", (e) => {
          if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            this.sendMessage();
          }
        });
      }

      if (voiceBtn) {
        voiceBtn.addEventListener("click", () => this.toggleVoiceInput());
      }

      if (newConvBtn) {
        newConvBtn.addEventListener("click", () => this.newConversation());
      }

      if (settingsBtn) {
        settingsBtn.addEventListener("click", () => {
          this._expandedSettings = !this._expandedSettings;
          this.render();
        });
      }

      quickActionChips.forEach((chip) => {
        chip.addEventListener("click", () => {
          const action = chip.dataset.action;
          this.executeQuickAction(action);
        });
      });

      if (toggleQuickActions) {
        toggleQuickActions.addEventListener("click", () => {
          this._expandedQuickActions = !this._expandedQuickActions;
          this.render();
        });
      }

      if (toggleEntities) {
        toggleEntities.addEventListener("click", () => {
          this._expandedEntities = !this._expandedEntities;
          this.render();
        });
      }

      if (voiceToggle) {
        voiceToggle.addEventListener("change", (e) => {
          this._voiceEnabled = e.target.checked;
        });
      }

      if (voiceOutputToggle) {
        voiceOutputToggle.addEventListener("change", (e) => {
          this._voiceOutput = e.target.checked;
        });
      }
    }

    toggleVoiceInput() {
      if (!this._recognition) {
        console.warn("Voice recognition not initialized");
        return;
      }

      if (this._isListening) {
        this._recognition.stop();
      } else {
        this._recognition.start();
      }
    }

    updateVoiceButton() {
      const voiceBtn = this.shadowRoot.querySelector(".voice-btn");
      if (voiceBtn) {
        voiceBtn.style.opacity = this._isListening ? "1" : "0.6";
      }
    }

    setInputValue(value) {
      const inputField = this.shadowRoot.querySelector(".message-input");
      if (inputField) {
        inputField.value = value;
        inputField.focus();
      }
    }

    executeQuickAction(action) {
      const actions = {
        "turn-off-lights": "Turn off all lights",
        "lock-doors": "Lock all doors",
        "temperature": "What's the current temperature?",
        "energy-report": "Give me an energy usage report",
      };

      const message = actions[action] || action;
      this.setInputValue(message);
      this.sendMessage();
    }

    sendMessage() {
      const inputField = this.shadowRoot.querySelector(".message-input");
      const message = inputField.value.trim();

      if (!message || this._isWaitingResponse) return;

      // Add user message
      this._messages.push({
        id: Math.random().toString(36),
        role: "user",
        content: message,
        timestamp: new Date(),
      });

      inputField.value = "";
      inputField.focus();
      this._isWaitingResponse = true;

      this.render();
      this.scrollToBottom();

      // Dispatch event to parent (integration backend)
      this.dispatchEvent(
        new CustomEvent("claude-message-sent", {
          detail: { content: message, timestamp: new Date() },
          bubbles: true,
          composed: true,
        })
      );

      // Simulate response (in production: wait for WebSocket message)
      setTimeout(() => {
        this._messages.push({
          id: Math.random().toString(36),
          role: "claude",
          content: "I'm processing your request...",
          timestamp: new Date(),
        });
        this._isWaitingResponse = false;
        this.render();
        this.scrollToBottom();
      }, 1000);
    }

    newConversation() {
      if (confirm("Start a new conversation? This will clear the current chat history.")) {
        this._messages = [];
        this._pendingConfirmations.clear();
        this.render();
      }
    }

    showConfirmation(confirmationData) {
      const id = Math.random().toString(36);
      this._pendingConfirmations.set(id, {
        ...confirmationData,
        id,
        timestamp: new Date(),
        timeout: setTimeout(() => {
          this._pendingConfirmations.delete(id);
          this.render();
        }, 5 * 60 * 1000), // 5 minutes
      });

      this.render();
    }

    approveConfirmation(id) {
      const confirmation = this._pendingConfirmations.get(id);
      if (!confirmation) return;

      clearTimeout(confirmation.timeout);
      this._pendingConfirmations.delete(id);

      // Add approved message
      this._messages.push({
        id: Math.random().toString(36),
        role: "system",
        content: `✓ Action approved: ${confirmation.action}`,
        timestamp: new Date(),
        status: "approved",
      });

      // Dispatch approval event
      this.dispatchEvent(
        new CustomEvent("claude-confirmation-approved", {
          detail: { id, action: confirmation.action },
          bubbles: true,
          composed: true,
        })
      );

      this.render();
    }

    rejectConfirmation(id) {
      const confirmation = this._pendingConfirmations.get(id);
      if (!confirmation) return;

      clearTimeout(confirmation.timeout);
      this._pendingConfirmations.delete(id);

      // Add rejected message
      this._messages.push({
        id: Math.random().toString(36),
        role: "system",
        content: `✗ Action rejected: ${confirmation.action}`,
        timestamp: new Date(),
        status: "rejected",
      });

      // Dispatch rejection event
      this.dispatchEvent(
        new CustomEvent("claude-confirmation-rejected", {
          detail: { id, action: confirmation.action },
          bubbles: true,
          composed: true,
        })
      );

      this.render();
    }

    scrollToBottom() {
      setTimeout(() => {
        const container = this.shadowRoot.querySelector(".messages-container");
        if (container) {
          container.scrollTop = container.scrollHeight;
        }
      }, 0);
    }

    escapeHtml(text) {
      const div = document.createElement("div");
      div.textContent = text;
      return div.innerHTML;
    }

    formatMarkdown(text) {
      // Simple markdown rendering (bold, code blocks, lists)
      let html = this.escapeHtml(text);

      // Bold
      html = html.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
      html = html.replace(/__(.*?)__/g, "<strong>$1</strong>");

      // Code blocks
      html = html.replace(
        /```(.*?)\n([\s\S]*?)```/g,
        '<pre><code class="code-block">$2</code></pre>'
      );

      // Inline code
      html = html.replace(/`([^`]+)`/g, '<code class="inline-code">$1</code>');

      // Line breaks
      html = html.replace(/\n/g, "<br>");

      // Unordered lists
      html = html.replace(/^- (.*?)$/gm, "<li>$1</li>");
      html = html.replace(/(<li>.*?<\/li>)/s, "<ul>$1</ul>");

      return html;
    }

    getConfirmationRiskColor(level) {
      const colors = {
        safe: "#4CAF50",
        moderate: "#FF9800",
        dangerous: "#F44336",
        critical: "#B71C1C",
      };
      return colors[level] || colors.moderate;
    }

    render() {
      const confirmationsList = Array.from(this._pendingConfirmations.values());

      this.shadowRoot.innerHTML = `
        <style>
          :host {
            --primary-color: var(--ha-primary-color, #03A9F4);
            --text-primary: var(--ha-text-color, #212121);
            --text-secondary: var(--ha-secondary-text-color, #757575);
            --bg-color: var(--ha-card-background-color, #FFFFFF);
            --border-color: var(--ha-divider-color, #E0E0E0);
            --warning-color: #FF9800;
            --danger-color: #F44336;
            --success-color: #4CAF50;
            font-family: var(--ha-font-family, "Roboto", sans-serif);
          }

          .panel {
            display: flex;
            flex-direction: column;
            height: 100%;
            background: var(--bg-color);
            color: var(--text-primary);
          }

          .panel-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 16px;
            background: linear-gradient(135deg, var(--primary-color), var(--primary-color));
            color: white;
            border-bottom: 2px solid var(--border-color);
          }

          .panel-title {
            font-size: 18px;
            font-weight: 600;
            margin: 0;
          }

          .panel-actions {
            display: flex;
            gap: 8px;
          }

          .icon-btn {
            background: none;
            border: none;
            color: white;
            cursor: pointer;
            font-size: 18px;
            padding: 6px;
            opacity: 0.9;
            transition: all 0.2s;
            border-radius: 4px;
          }

          .icon-btn:hover {
            opacity: 1;
            background: rgba(255, 255, 255, 0.1);
          }

          .content {
            flex: 1;
            display: flex;
            flex-direction: column;
            overflow: hidden;
            gap: 12px;
            padding: 12px;
          }

          .messages-container {
            flex: 1;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 8px;
            padding-right: 4px;
          }

          .message-group {
            display: flex;
            margin-bottom: 8px;
            animation: messageAppear 0.3s ease-out;
          }

          @keyframes messageAppear {
            from {
              opacity: 0;
              transform: translateY(10px);
            }
            to {
              opacity: 1;
              transform: translateY(0);
            }
          }

          .message-group.user {
            justify-content: flex-end;
          }

          .message-bubble {
            max-width: 75%;
            padding: 12px 14px;
            border-radius: 12px;
            font-size: 13px;
            line-height: 1.5;
            word-wrap: break-word;
          }

          .message-group.user .message-bubble {
            background: var(--primary-color);
            color: white;
            border-radius: 12px 4px 12px 12px;
          }

          .message-group.claude .message-bubble {
            background: #E8E8E8;
            color: var(--text-primary);
            border-radius: 4px 12px 12px 12px;
          }

          .message-group.system .message-bubble {
            background: rgba(76, 175, 80, 0.1);
            color: var(--text-primary);
            border-left: 3px solid #4CAF50;
            border-radius: 4px;
            font-size: 12px;
          }

          .message-group.system.rejected .message-bubble {
            background: rgba(244, 67, 54, 0.1);
            border-left-color: #F44336;
          }

          .message-timestamp {
            font-size: 11px;
            color: var(--text-secondary);
            margin-top: 4px;
            opacity: 0.7;
          }

          .typing-indicator {
            display: flex;
            gap: 4px;
            padding: 10px 14px;
            background: #E8E8E8;
            border-radius: 12px;
            width: fit-content;
          }

          .typing-dot {
            width: 6px;
            height: 6px;
            border-radius: 50%;
            background: #999;
            animation: typing 1.4s infinite;
          }

          .typing-dot:nth-child(2) {
            animation-delay: 0.2s;
          }

          .typing-dot:nth-child(3) {
            animation-delay: 0.4s;
          }

          @keyframes typing {
            0%,
            60%,
            100% {
              opacity: 0.5;
              transform: translateY(0);
            }
            30% {
              opacity: 1;
              transform: translateY(-10px);
            }
          }

          .confirmation-section {
            background: rgba(255, 152, 0, 0.1);
            border-left: 4px solid var(--warning-color);
            border-radius: 4px;
            padding: 12px;
            margin-bottom: 8px;
          }

          .confirmation-header {
            font-weight: 600;
            color: var(--text-primary);
            margin-bottom: 8px;
            font-size: 13px;
          }

          .confirmation-card {
            background: white;
            border: 1px solid var(--border-color);
            border-radius: 4px;
            padding: 12px;
            margin-bottom: 8px;
          }

          .confirmation-action {
            font-size: 12px;
            color: var(--text-secondary);
            margin-bottom: 8px;
          }

          .confirmation-details {
            background: #f5f5f5;
            padding: 8px;
            border-radius: 4px;
            font-size: 11px;
            font-family: "Courier New", monospace;
            margin-bottom: 8px;
            max-height: 100px;
            overflow-y: auto;
          }

          .confirmation-controls {
            display: flex;
            gap: 8px;
          }

          .confirm-btn,
          .reject-btn {
            flex: 1;
            padding: 8px;
            border: none;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
          }

          .confirm-btn {
            background: var(--success-color);
            color: white;
          }

          .confirm-btn:hover {
            background: #45a049;
          }

          .reject-btn {
            background: var(--danger-color);
            color: white;
          }

          .reject-btn:hover {
            background: #da190b;
          }

          .sidebar-section {
            display: flex;
            flex-direction: column;
            gap: 8px;
            padding: 12px;
            border: 1px solid var(--border-color);
            border-radius: 8px;
            background: var(--bg-color);
          }

          .section-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            cursor: pointer;
            user-select: none;
            font-weight: 600;
            font-size: 13px;
            color: var(--text-primary);
          }

          .section-header:hover {
            opacity: 0.8;
          }

          .section-toggle {
            font-size: 10px;
            opacity: 0.6;
          }

          .section-content {
            display: flex;
            flex-direction: column;
            gap: 8px;
            max-height: 200px;
            overflow-y: auto;
          }

          .quick-action-chip {
            padding: 8px 12px;
            background: var(--primary-color);
            color: white;
            border: none;
            border-radius: 20px;
            font-size: 12px;
            cursor: pointer;
            transition: all 0.2s;
            flex: 1;
          }

          .quick-action-chip:hover {
            background: ${this.getComputedStyle(this).getPropertyValue("--primary-color")};
            box-shadow: 0 2px 8px rgba(3, 169, 244, 0.3);
          }

          .quick-actions-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 8px;
          }

          .entity-item {
            display: flex;
            align-items: center;
            padding: 8px;
            background: #f5f5f5;
            border-radius: 4px;
            font-size: 12px;
          }

          .entity-icon {
            margin-right: 8px;
            opacity: 0.7;
          }

          .entity-name {
            flex: 1;
          }

          .input-area {
            display: flex;
            gap: 8px;
            padding: 12px;
            border-top: 1px solid var(--border-color);
            background: var(--bg-color);
          }

          .message-input {
            flex: 1;
            border: 1px solid var(--border-color);
            border-radius: 20px;
            padding: 10px 16px;
            font-size: 13px;
            font-family: inherit;
            color: var(--text-primary);
            background: white;
            outline: none;
            transition: border-color 0.2s;
          }

          .message-input:focus {
            border-color: var(--primary-color);
          }

          .send-btn,
          .voice-btn,
          .new-conversation-btn {
            background: var(--primary-color);
            color: white;
            border: none;
            border-radius: 50%;
            width: 36px;
            height: 36px;
            cursor: pointer;
            font-size: 16px;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.2s;
            flex-shrink: 0;
          }

          .send-btn:hover,
          .voice-btn:hover,
          .new-conversation-btn:hover {
            box-shadow: 0 2px 8px rgba(3, 169, 244, 0.3);
          }

          .send-btn:active,
          .voice-btn:active {
            transform: scale(0.95);
          }

          .settings-panel {
            background: #f5f5f5;
            border-radius: 4px;
            padding: 12px;
            margin-top: 8px;
          }

          .settings-group {
            margin-bottom: 12px;
          }

          .settings-label {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 12px;
            margin-bottom: 6px;
            cursor: pointer;
          }

          .settings-label input[type="checkbox"] {
            cursor: pointer;
          }

          .settings-select {
            width: 100%;
            padding: 6px;
            border: 1px solid var(--border-color);
            border-radius: 4px;
            font-size: 12px;
          }

          .empty-state {
            flex: 1;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            color: var(--text-secondary);
            text-align: center;
          }

          .empty-icon {
            font-size: 48px;
            margin-bottom: 12px;
            opacity: 0.5;
          }

          ::-webkit-scrollbar {
            width: 6px;
          }

          ::-webkit-scrollbar-track {
            background: transparent;
          }

          ::-webkit-scrollbar-thumb {
            background: var(--border-color);
            border-radius: 3px;
          }

          ::-webkit-scrollbar-thumb:hover {
            background: var(--text-secondary);
          }

          code {
            background: #f5f5f5;
            padding: 2px 4px;
            border-radius: 3px;
            font-family: "Courier New", monospace;
            font-size: 0.9em;
          }

          .inline-code {
            background: rgba(0, 0, 0, 0.05);
            padding: 2px 6px;
            border-radius: 3px;
          }

          .code-block {
            background: #f5f5f5;
            padding: 12px;
            border-radius: 4px;
            overflow-x: auto;
            font-size: 12px;
          }

          strong {
            font-weight: 600;
          }

          ul {
            margin: 6px 0;
            padding-left: 20px;
          }

          li {
            margin: 4px 0;
          }
        </style>

        <div class="panel">
          <div class="panel-header">
            <h2 class="panel-title">Claude Assistant</h2>
            <div class="panel-actions">
              <button class="icon-btn new-conversation-btn" aria-label="New conversation" title="New conversation">
                📝
              </button>
              <button class="icon-btn settings-btn" aria-label="Settings" title="Settings">
                ⚙️
              </button>
            </div>
          </div>

          <div class="content">
            <!-- Quick Actions Section -->
            <div class="sidebar-section">
              <div class="section-header toggle-quick-actions">
                <span>⚡ Quick Actions</span>
                <span class="section-toggle">${this._expandedQuickActions ? "▼" : "▶"}</span>
              </div>
              ${
                this._expandedQuickActions
                  ? `
                <div class="quick-actions-grid">
                  <button class="quick-action-chip" data-action="turn-off-lights">💡 Lights off</button>
                  <button class="quick-action-chip" data-action="lock-doors">🔒 Lock doors</button>
                  <button class="quick-action-chip" data-action="temperature">🌡️ Temperature</button>
                  <button class="quick-action-chip" data-action="energy-report">⚡ Energy</button>
                </div>
              `
                  : ""
              }
            </div>

            <!-- Messages Container -->
            <div class="messages-container">
              ${
                this._messages.length === 0
                  ? `
                <div class="empty-state">
                  <div class="empty-icon">💬</div>
                  <p>Start a conversation with Claude</p>
                </div>
              `
                  : `
                ${this._messages
                  .map((msg) => {
                    if (msg.role === "system") {
                      return `
                      <div class="message-group system ${msg.status || ""}">
                        <div class="message-bubble">${this.escapeHtml(msg.content)}</div>
                      </div>
                    `;
                    }
                    return `
                      <div class="message-group ${msg.role}">
                        <div class="message-bubble">${this.formatMarkdown(msg.content)}</div>
                      </div>
                    `;
                  })
                  .join("")}
                ${
                  this._isWaitingResponse
                    ? `
                  <div class="typing-indicator">
                    <span class="typing-dot"></span>
                    <span class="typing-dot"></span>
                    <span class="typing-dot"></span>
                  </div>
                `
                    : ""
                }
              `
              }
            </div>

            <!-- Pending Confirmations -->
            ${
              confirmationsList.length > 0
                ? `
              <div class="confirmation-section">
                <div class="confirmation-header">⚠️ ${confirmationsList.length} Confirmation${confirmationsList.length > 1 ? "s" : ""} Pending</div>
                ${confirmationsList
                  .map(
                    (conf) => `
                  <div class="confirmation-card">
                    <div class="confirmation-action">
                      <strong>${conf.action}</strong><br>
                      ${conf.description}
                    </div>
                    ${
                      Object.keys(conf.details || {}).length > 0
                        ? `
                      <div class="confirmation-details">
                        ${Object.entries(conf.details || {})
                          .map(([k, v]) => `${k}: ${typeof v === "object" ? JSON.stringify(v) : v}`)
                          .join("<br>")}
                      </div>
                    `
                        : ""
                    }
                    <div class="confirmation-controls">
                      <button class="confirm-btn" data-id="${conf.id}">✓ Approve</button>
                      <button class="reject-btn" data-id="${conf.id}">✗ Reject</button>
                    </div>
                  </div>
                `
                  )
                  .join("")}
              </div>
            `
                : ""
            }

            <!-- Active Entities Section -->
            <div class="sidebar-section">
              <div class="section-header toggle-entities">
                <span>🏠 Active Entities</span>
                <span class="section-toggle">${this._expandedEntities ? "▼" : "▶"}</span>
              </div>
              ${
                this._expandedEntities
                  ? `
                <div class="section-content">
                  ${
                    this._hass && this._hass.states
                      ? Array.from(this._exposedDomains)
                          .flatMap((domain) => {
                            return Object.entries(this._hass.states)
                              .filter(([key]) => key.startsWith(domain + "."))
                              .slice(0, 5)
                              .map(([entityId, state]) => {
                                const icon = {
                                  light: "💡",
                                  switch: "🔘",
                                  lock: "🔒",
                                  climate: "🌡️",
                                  sensor: "📊",
                                }[domain] || "🔧";
                                return `
                            <div class="entity-item">
                              <span class="entity-icon">${icon}</span>
                              <span class="entity-name">${entityId}</span>
                            </div>
                          `;
                              });
                          })
                          .join("")
                      : '<div class="entity-item">No entities available</div>'
                  }
                </div>
              `
                  : ""
              }
            </div>

            <!-- Settings Section -->
            ${
              this._expandedSettings
                ? `
              <div class="settings-panel">
                <div class="settings-group">
                  <label class="settings-label">
                    <input type="checkbox" class="voice-toggle" ${this._voiceEnabled ? "checked" : ""}>
                    Voice Input
                  </label>
                </div>
                <div class="settings-group">
                  <label class="settings-label">
                    <input type="checkbox" class="voice-output-toggle" ${this._voiceOutput ? "checked" : ""}>
                    Voice Output
                  </label>
                </div>
                <div class="settings-group">
                  <label style="font-size: 12px; margin-bottom: 6px;">Confirmation Level</label>
                  <select class="settings-select">
                    <option value="safe">Safe only</option>
                    <option value="moderate" selected>Moderate</option>
                    <option value="all">All actions</option>
                  </select>
                </div>
              </div>
            `
                : ""
            }
          </div>

          <!-- Input Area -->
          <div class="input-area">
            <input
              type="text"
              class="message-input"
              placeholder="Ask Claude..."
              aria-label="Message input"
            />
            <button class="voice-btn" aria-label="Voice input" title="Voice input">🎤</button>
            <button class="send-btn" aria-label="Send message" title="Send">➤</button>
          </div>
        </div>
      `;

      // Re-attach event listeners for confirmation buttons
      this.shadowRoot.querySelectorAll(".confirm-btn").forEach((btn) => {
        btn.addEventListener("click", () => {
          const id = btn.dataset.id;
          this.approveConfirmation(id);
        });
      });

      this.shadowRoot.querySelectorAll(".reject-btn").forEach((btn) => {
        btn.addEventListener("click", () => {
          const id = btn.dataset.id;
          this.rejectConfirmation(id);
        });
      });

      this.setupEventListeners();
    }
  }
);
