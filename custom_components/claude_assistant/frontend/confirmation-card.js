/**
 * Confirmation Card Component
 * Standalone card for displaying action confirmations with approve/reject buttons
 * Can be embedded in notifications or dashboard
 */

customElements.define(
  "claude-confirmation-card",
  class ConfirmationCard extends HTMLElement {
    constructor() {
      super();
      this.attachShadow({ mode: "open" });
      this._timeout = null;
      this._remainingSeconds = 300; // 5 minutes
    }

    connectedCallback() {
      this.render();
      this.startCountdown();
    }

    disconnectedCallback() {
      if (this._timeout) {
        clearInterval(this._timeout);
      }
    }

    set data(value) {
      this._data = value;
      this.render();
      this.startCountdown();
    }

    getRiskLevel() {
      const { risk_level } = this._data || {};
      const levels = {
        safe: { color: "#4CAF50", label: "Safe" },
        moderate: { color: "#FF9800", label: "Moderate" },
        dangerous: { color: "#F44336", label: "Dangerous" },
        critical: { color: "#B71C1C", label: "Critical" },
      };
      return levels[risk_level] || levels.moderate;
    }

    startCountdown() {
      if (this._timeout) clearInterval(this._timeout);

      this._remainingSeconds = 300;
      this._timeout = setInterval(() => {
        this._remainingSeconds--;
        const timerEl = this.shadowRoot.querySelector(".timer");
        if (timerEl) {
          timerEl.textContent = `${Math.floor(this._remainingSeconds / 60)}:${(
            this._remainingSeconds % 60
          )
            .toString()
            .padStart(2, "0")}`;
        }

        if (this._remainingSeconds <= 0) {
          clearInterval(this._timeout);
          this.dispatchEvent(
            new CustomEvent("confirmation-timeout", { detail: { id: this._data.id } })
          );
          this.remove();
        }
      }, 1000);
    }

    onApprove() {
      clearInterval(this._timeout);
      this.dispatchEvent(
        new CustomEvent("confirmation-approved", {
          detail: { id: this._data.id, action: this._data.action },
        })
      );
      this.classList.add("approved");
      setTimeout(() => this.remove(), 500);
    }

    onReject() {
      clearInterval(this._timeout);
      this.dispatchEvent(
        new CustomEvent("confirmation-rejected", {
          detail: { id: this._data.id, action: this._data.action },
        })
      );
      this.classList.add("rejected");
      setTimeout(() => this.remove(), 500);
    }

    render() {
      const { action, description, details, risk_level } = this._data || {
        action: "Unknown",
        description: "Unknown action",
        details: {},
        risk_level: "moderate",
      };

      const riskInfo = this.getRiskLevel();

      this.shadowRoot.innerHTML = `
        <style>
          :host {
            display: block;
            font-family: var(--ha-font-family, "Roboto", sans-serif);
            --primary-color: var(--ha-primary-color, #03A9F4);
            --warning-color: #FF9800;
            --danger-color: #F44336;
            --success-color: #4CAF50;
            --text-primary: var(--ha-text-color, #212121);
            --text-secondary: var(--ha-secondary-text-color, #757575);
            --bg-color: var(--ha-card-background-color, #FFFFFF);
            --border-color: var(--ha-divider-color, #E0E0E0);
          }

          .confirmation-card {
            background: linear-gradient(135deg, var(--bg-color) 0%, var(--bg-color) 100%);
            border-left: 4px solid ${riskInfo.color};
            border-radius: 8px;
            padding: 16px;
            margin: 12px 0;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
            animation: slideIn 0.3s ease-out;
            transition: all 0.2s ease;
          }

          @keyframes slideIn {
            from {
              opacity: 0;
              transform: translateX(-20px);
            }
            to {
              opacity: 1;
              transform: translateX(0);
            }
          }

          .confirmation-card.approved {
            border-left-color: var(--success-color);
            background-color: rgba(76, 175, 80, 0.05);
          }

          .confirmation-card.rejected {
            border-left-color: var(--danger-color);
            background-color: rgba(244, 67, 54, 0.05);
          }

          .header {
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 12px;
          }

          .warning-icon {
            font-size: 20px;
          }

          .title {
            font-size: 14px;
            font-weight: 600;
            color: var(--text-primary);
            margin: 0;
          }

          .risk-badge {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 500;
            color: white;
            background-color: ${riskInfo.color};
            margin-left: auto;
          }

          .description {
            font-size: 13px;
            color: var(--text-secondary);
            margin: 0 0 12px 0;
            line-height: 1.4;
          }

          .details {
            background: rgba(0, 0, 0, 0.02);
            border-radius: 4px;
            padding: 10px;
            margin: 12px 0;
            font-size: 12px;
            font-family: "Courier New", monospace;
            color: var(--text-secondary);
            border-left: 2px solid var(--border-color);
            max-height: 120px;
            overflow-y: auto;
          }

          .details-line {
            padding: 4px 0;
            word-break: break-word;
          }

          .controls {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-top: 12px;
          }

          button {
            flex: 1;
            padding: 10px 16px;
            border: none;
            border-radius: 4px;
            font-size: 13px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s ease;
          }

          .approve-btn {
            background-color: var(--success-color);
            color: white;
          }

          .approve-btn:hover {
            background-color: #45a049;
            box-shadow: 0 2px 8px rgba(76, 175, 80, 0.3);
          }

          .approve-btn:active {
            transform: scale(0.98);
          }

          .reject-btn {
            background-color: var(--danger-color);
            color: white;
          }

          .reject-btn:hover {
            background-color: #da190b;
            box-shadow: 0 2px 8px rgba(244, 67, 54, 0.3);
          }

          .reject-btn:active {
            transform: scale(0.98);
          }

          .timer {
            font-size: 12px;
            color: var(--text-secondary);
            font-weight: 500;
            min-width: 40px;
          }

          .status-icon {
            font-size: 18px;
            margin-left: auto;
          }

          .confirmation-card.approved .status-icon {
            color: var(--success-color);
          }

          .confirmation-card.rejected .status-icon {
            color: var(--danger-color);
          }
        </style>

        <div class="confirmation-card">
          <div class="header">
            <span class="warning-icon">⚠️</span>
            <h3 class="title">Action Confirmation Required</h3>
            <span class="risk-badge">${riskInfo.label}</span>
          </div>

          <p class="description">
            <strong>What Claude wants to do:</strong><br>
            ${description}
          </p>

          ${
            Object.keys(details).length > 0
              ? `
            <div class="details">
              ${Object.entries(details)
                .map(([key, value]) => {
                  const displayValue =
                    typeof value === "object" ? JSON.stringify(value, null, 2) : value;
                  return `<div class="details-line"><strong>${key}:</strong> ${displayValue}</div>`;
                })
                .join("")}
            </div>
          `
              : ""
          }

          <div class="controls">
            <button class="approve-btn" aria-label="Approve action">
              ✓ Approve
            </button>
            <button class="reject-btn" aria-label="Reject action">
              ✗ Reject
            </button>
            <span class="timer">5:00</span>
          </div>
        </div>
      `;

      this.shadowRoot
        .querySelector(".approve-btn")
        .addEventListener("click", () => this.onApprove());
      this.shadowRoot
        .querySelector(".reject-btn")
        .addEventListener("click", () => this.onReject());
    }
  }
);
