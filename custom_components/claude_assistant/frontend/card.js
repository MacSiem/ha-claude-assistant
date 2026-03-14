/**
 * Claude Assistant Lovelace Card
 * Compact chat widget for Home Assistant dashboard
 * Expandable to full height, HACS compatible
 */

customElements.define(
  "claude-assistant-card",
  class ClaudeAssistantCard extends HTMLElement {
    static getConfigElement() {
      const element = document.createElement("claude-assistant-card-editor");
      return element;
    }

    static getStubConfig() {
      return {
        type: "custom:claude-assistant-card",
        title: "Claude Assistant",
        show_quick_actions: true,
        max_messages: 5,
      };
    }

    constructor() {
      super();
      this.attachShadow({ mode: "open" });
      this._messages = [];
      this._config = {};
      this._hass = null;
      this._wsConnected = false;
      this._isExpanded = false;
      this._pendingConfirmations = 0;
      this._voiceEnabled = false;
    }

    setConfig(config) {
      this._config = config;
    }

    set hass(hass) {
      this._hass = hass;
      if (!this._wsConnected) {
        this.initWebSocket();
      }
    }

    initWebSocket() {
      // Placeholder for WebSocket connection
      // In production: connect to HA websocket for chat events
      this._wsConnected = true;
    }

    connectedCallback() {
      this.render();
      this.setupEventListeners();
    }

    setupEventListeners() {
      const sendBtn = this.shadowRoot.querySelector(".send-btn");
      const inputField = this.shadowRoot.querySelector(".message-input");
      const expandBtn = this.shadowRoot.querySelector(".expand-btn");

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

      if (expandBtn) {
        expandBtn.addEventListener("click", () => this.toggleExpand());
      }
    }

    sendMessage() {
      const inputField = this.shadowRoot.querySelector(".message-input");
      const message = inputField.value.trim();

      if (!message) return;

      this._messages.push({ role: "user", content: message, timestamp: new Date() });
      inputField.value = "";

      // Dispatch event to parent (panel)
      this.dispatchEvent(
        new CustomEvent("claude-message", {
          detail: { content: message, timestamp: new Date() },
          bubbles: true,
          composed: true,
        })
      );

      // Simulate Claude response
      setTimeout(() => {
        this._messages.push({
          role: "claude",
          content: "Working on your request...",
          timestamp: new Date(),
        });
        this.render();
      }, 800);

      this.render();
    }

    toggleExpand() {
      this._isExpanded = !this._isExpanded;
      this.render();
    }

    render() {
      const maxMessages = this._config.max_messages || 5;
      const displayMessages = this._messages.slice(-maxMessages);
      const title = this._config.title || "Claude Assistant";

      this.shadowRoot.innerHTML = `
        <style>
          :host {
            --primary-color: var(--ha-primary-color, #03A9F4);
            --text-primary: var(--ha-text-color, #212121);
            --text-secondary: var(--ha-secondary-text-color, #757575);
            --bg-color: var(--ha-card-background-color, #FFFFFF);
            --border-color: var(--ha-divider-color, #E0E0E0);
            --warning-color: #FF9800;
          }

          .card {
            display: flex;
            flex-direction: column;
            height: 100%;
            background: var(--bg-color);
            border-radius: 12px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
            overflow: hidden;
          }

          .card.expanded {
            height: 100vh;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            z-index: 1000;
            border-radius: 0;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
          }

          .card-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 16px;
            border-bottom: 1px solid var(--border-color);
            background: linear-gradient(135deg, var(--primary-color), var(--primary-color));
            color: white;
          }

          .card-title {
            font-size: 16px;
            font-weight: 600;
            margin: 0;
          }

          .header-controls {
            display: flex;
            gap: 8px;
            align-items: center;
          }

          .confirmation-badge {
            background: var(--warning-color);
            color: white;
            border-radius: 12px;
            padding: 4px 8px;
            font-size: 12px;
            font-weight: 600;
          }

          .expand-btn,
          .close-btn {
            background: none;
            border: none;
            color: white;
            cursor: pointer;
            font-size: 20px;
            padding: 4px;
            opacity: 0.9;
            transition: opacity 0.2s;
          }

          .expand-btn:hover,
          .close-btn:hover {
            opacity: 1;
          }

          .messages-container {
            flex: 1;
            overflow-y: auto;
            padding: 16px;
            display: flex;
            flex-direction: column;
            gap: 8px;
          }

          .message {
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

          .message.user {
            justify-content: flex-end;
          }

          .message-bubble {
            max-width: 80%;
            padding: 10px 14px;
            border-radius: 12px;
            font-size: 13px;
            line-height: 1.4;
            word-wrap: break-word;
          }

          .message.user .message-bubble {
            background: var(--primary-color);
            color: white;
            border-radius: 12px 4px 12px 12px;
          }

          .message.claude .message-bubble {
            background: #E8E8E8;
            color: var(--text-primary);
            border-radius: 4px 12px 12px 12px;
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

          .input-area {
            padding: 12px;
            border-top: 1px solid var(--border-color);
            display: flex;
            gap: 8px;
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
            outline: none;
            transition: border-color 0.2s;
          }

          .message-input:focus {
            border-color: var(--primary-color);
          }

          .send-btn,
          .voice-btn {
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
          }

          .send-btn:hover,
          .voice-btn:hover {
            background: ${this.adjustColor(
              getComputedStyle(this).getPropertyValue("--primary-color"),
              -10
            )};
            box-shadow: 0 2px 8px rgba(3, 169, 244, 0.3);
          }

          .send-btn:active,
          .voice-btn:active {
            transform: scale(0.95);
          }

          .empty-state {
            flex: 1;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            color: var(--text-secondary);
            text-align: center;
            padding: 24px;
          }

          .empty-icon {
            font-size: 48px;
            margin-bottom: 16px;
            opacity: 0.5;
          }

          .empty-text {
            font-size: 14px;
            margin: 0;
          }

          .card.expanded .card-title {
            font-size: 20px;
          }

          .card:not(.expanded) .close-btn {
            display: none;
          }

          @media (max-width: 768px) {
            .message-bubble {
              max-width: 90%;
            }
          }
        </style>

        <div class="card ${this._isExpanded ? "expanded" : ""}">
          <div class="card-header">
            <h2 class="card-title">${title}</h2>
            <div class="header-controls">
              ${
                this._pendingConfirmations > 0
                  ? `<span class="confirmation-badge">${this._pendingConfirmations}</span>`
                  : ""
              }
              ${
                !this._isExpanded
                  ? `<button class="expand-btn" aria-label="Expand" title="Expand">⤢</button>`
                  : `<button class="close-btn" aria-label="Close" title="Close">✕</button>`
              }
            </div>
          </div>

          <div class="messages-container">
            ${
              displayMessages.length === 0
                ? `
              <div class="empty-state">
                <div class="empty-icon">💬</div>
                <p class="empty-text">Start a conversation with Claude</p>
              </div>
            `
                : displayMessages
                    .map(
                      (msg) => `
              <div class="message ${msg.role}">
                <div class="message-bubble">${this.escapeHtml(msg.content)}</div>
              </div>
            `
                    )
                    .join("")
            }
          </div>

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

      this.setupEventListeners();
    }

    escapeHtml(text) {
      const div = document.createElement("div");
      div.textContent = text;
      return div.innerHTML;
    }

    adjustColor(color, percent) {
      // Simple color adjustment (returns same color for now)
      return color;
    }
  }
);

/**
 * Card Editor (HACS compatible configuration UI)
 */
customElements.define(
  "claude-assistant-card-editor",
  class ClaudeAssistantCardEditor extends HTMLElement {
    constructor() {
      super();
      this._config = {};
    }

    setConfig(config) {
      this._config = config;
    }

    render() {
      this.innerHTML = `
        <style>
          .editor-form {
            padding: 16px;
          }
          .form-group {
            margin-bottom: 16px;
          }
          label {
            display: block;
            margin-bottom: 4px;
            font-weight: 500;
            font-size: 13px;
          }
          input,
          select {
            width: 100%;
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-family: inherit;
            font-size: 13px;
          }
        </style>
        <div class="editor-form">
          <div class="form-group">
            <label>Title</label>
            <input
              type="text"
              value="${this._config.title || "Claude Assistant"}"
              @change=${(e) => this.updateConfig("title", e.target.value)}
            />
          </div>
          <div class="form-group">
            <label>Max Messages to Display</label>
            <input
              type="number"
              value="${this._config.max_messages || 5}"
              min="1"
              max="20"
              @change=${(e) => this.updateConfig("max_messages", parseInt(e.target.value))}
            />
          </div>
          <div class="form-group">
            <label>
              <input type="checkbox" ${this._config.show_quick_actions ? "checked" : ""}
                @change=${(e) => this.updateConfig("show_quick_actions", e.target.checked)}
              />
              Show Quick Actions
            </label>
          </div>
        </div>
      `;
    }

    updateConfig(key, value) {
      this._config = { ...this._config, [key]: value };
      this.dispatchEvent(
        new CustomEvent("config-changed", {
          detail: { config: this._config },
          bubbles: true,
          composed: true,
        })
      );
    }
  }
);
