/**
 * Daitsu / TCL Tesla-Style 2D Airflow & Louver Custom Card for Home Assistant
 *
 * Installation:
 * 1. Copy this file to /config/www/daitsu-airflow-card.js
 * 2. In Home Assistant -> Settings -> Dashboards -> (3 dots) -> Resources:
 *    Add URL: /local/daitsu-airflow-card.js   Type: JavaScript Module
 * 3. Use in Dashboard YAML:
 *    - type: custom:daitsu-airflow-card
 *      climate_entity: climate.schlafzimmer_daitsu_artic_plus
 *      vertical_entity: select.schlafzimmer_daitsu_artic_plus_lamelle_vertikal
 *      horizontal_entity: select.schlafzimmer_daitsu_artic_plus_lamelle_horizontal
 */

const VERTICAL_FIXED = ["Ganz oben", "Oben", "Mitte", "Unten", "Ganz unten"];
const HORIZONTAL_FIXED = ["Ganz links", "Leicht links", "Mitte", "Leicht rechts", "Ganz rechts"];

class DaitsuAirflowCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._dragging = false;
    this._normX = 0.5;
    this._normY = 0.5;
    this._displayX = 0.5;
    this._displayY = 0.5;
    this._lockUntil = 0;
    this._optimisticV = null;
    this._optimisticH = null;
    this._animFrame = null;
    this._rendered = false;
  }

  setConfig(config) {
    if (!config.vertical_entity && !config.horizontal_entity) {
      throw new Error("Bitte vertical_entity oder horizontal_entity angeben.");
    }
    this._config = {
      title: "Luftstrom & Lamellen",
      ...config,
    };
    if (this._rendered) {
      this._renderState();
    }
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._rendered) {
      this._buildDom();
      this._rendered = true;
    }
    if (!this._dragging && Date.now() > this._lockUntil) {
      this._optimisticV = null;
      this._optimisticH = null;
      this._syncFromHass();
    }
    this._renderState();
  }

  getCardSize() {
    return 4;
  }

  _getAccent() {
    const cl = this._config.climate_entity
      ? this._hass?.states?.[this._config.climate_entity]?.state
      : null;
    switch (cl) {
      case "heat":
        return "#f97316";
      case "cool":
        return "#06b6d4";
      case "dry":
        return "#38bdf8";
      case "auto":
      case "fan_only":
        return "#14b8a6";
      case "off":
      case "unavailable":
        return "#64748b";
      default:
        return "#06b6d4";
    }
  }

  _getStates() {
    const rawV = this._config.vertical_entity
      ? this._hass?.states?.[this._config.vertical_entity]?.state || "Aus"
      : null;
    const rawH = this._config.horizontal_entity
      ? this._hass?.states?.[this._config.horizontal_entity]?.state || "Aus"
      : null;
    const locked = Date.now() <= this._lockUntil;
    return {
      vState: locked && this._optimisticV ? this._optimisticV : rawV,
      hState: locked && this._optimisticH ? this._optimisticH : rawH,
    };
  }

  _syncFromHass() {
    const { vState, hState } = this._getStates();
    const vIdx = VERTICAL_FIXED.indexOf(vState);
    const hIdx = HORIZONTAL_FIXED.indexOf(hState);
    if (vIdx >= 0) this._normY = vIdx / 4;
    if (hIdx >= 0) this._normX = hIdx / 4;
    this._startAnimation();
  }

  _selectOption(entityId, option) {
    if (!this._hass || !entityId) return;
    this._hass.callService("select", "select_option", {
      entity_id: entityId,
      option: option,
    });
  }

  _commitPosition(nx, ny) {
    const hStep = Math.max(0, Math.min(4, Math.round(nx * 4)));
    const vStep = Math.max(0, Math.min(4, Math.round(ny * 4)));
    const newH = HORIZONTAL_FIXED[hStep];
    const newV = VERTICAL_FIXED[vStep];
    const { vState, hState } = this._getStates();

    this._normX = hStep / 4;
    this._normY = vStep / 4;
    this._lockUntil = Date.now() + 2800;

    if (this._config.horizontal_entity && newH !== hState) {
      this._optimisticH = newH;
      this._selectOption(this._config.horizontal_entity, newH);
    }
    if (this._config.vertical_entity && newV !== vState) {
      this._optimisticV = newV;
      this._selectOption(this._config.vertical_entity, newV);
    }
    this._startAnimation();
    this._renderState();
  }

  _stepVertical(delta) {
    if (!this._config.vertical_entity) return;
    const { vState } = this._getStates();
    const cur = VERTICAL_FIXED.indexOf(vState);
    const next = Math.max(0, Math.min(4, (cur >= 0 ? cur : 2) + delta));
    const newV = VERTICAL_FIXED[next];
    this._normY = next / 4;
    this._lockUntil = Date.now() + 2800;
    this._optimisticV = newV;
    this._selectOption(this._config.vertical_entity, newV);
    this._startAnimation();
    this._renderState();
  }

  _stepHorizontal(delta) {
    if (!this._config.horizontal_entity) return;
    const { hState } = this._getStates();
    const cur = HORIZONTAL_FIXED.indexOf(hState);
    const next = Math.max(0, Math.min(4, (cur >= 0 ? cur : 2) + delta));
    const newH = HORIZONTAL_FIXED[next];
    this._normX = next / 4;
    this._lockUntil = Date.now() + 2800;
    this._optimisticH = newH;
    this._selectOption(this._config.horizontal_entity, newH);
    this._startAnimation();
    this._renderState();
  }

  _startAnimation() {
    if (this._animFrame) return;
    const tick = () => {
      const dx = this._normX - this._displayX;
      const dy = this._normY - this._displayY;
      if (this._dragging) {
        this._displayX = this._normX;
        this._displayY = this._normY;
        this._drawCanvas();
        this._animFrame = null;
        return;
      }
      if (Math.abs(dx) < 0.002 && Math.abs(dy) < 0.002) {
        this._displayX = this._normX;
        this._displayY = this._normY;
        this._drawCanvas();
        this._animFrame = null;
        return;
      }
      this._displayX += dx * 0.24;
      this._displayY += dy * 0.24;
      this._drawCanvas();
      this._animFrame = requestAnimationFrame(tick);
    };
    this._animFrame = requestAnimationFrame(tick);
  }

  _buildDom() {
    this.shadowRoot.innerHTML = `
      <style>
        :host { display: block; }
        ha-card {
          background: linear-gradient(160deg, rgba(30, 35, 50, 0.92), rgba(13, 16, 25, 0.96));
          border: 1px solid rgba(255, 255, 255, 0.08);
          border-radius: 22px;
          box-shadow: 0 10px 26px rgba(0, 0, 0, 0.45), inset 0 1px 0 rgba(255, 255, 255, 0.06);
          padding: 16px;
          color: #f8fafc;
          font-family: var(--primary-font-family, system-ui, -apple-system, sans-serif);
          user-select: none;
          -webkit-user-select: none;
        }
        .header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 12px;
        }
        .title {
          font-size: 15px;
          font-weight: 700;
          letter-spacing: 0.4px;
          color: #f1f5f9;
        }
        .status {
          font-size: 11px;
          font-weight: 700;
          letter-spacing: 0.5px;
          padding: 3px 9px;
          border-radius: 10px;
          background: rgba(255, 255, 255, 0.06);
          border: 1px solid rgba(255, 255, 255, 0.1);
        }
        .pad-wrap {
          position: relative;
          width: 100%;
          height: 210px;
          border-radius: 16px;
          background: #0b0e14;
          border: 1px solid rgba(255, 255, 255, 0.06);
          overflow: hidden;
        }
        canvas {
          width: 100%;
          height: 100%;
          display: block;
          touch-action: none;
          cursor: crosshair;
        }
        .dpad {
          position: absolute;
          width: 34px;
          height: 34px;
          border-radius: 50%;
          border: 1px solid rgba(255, 255, 255, 0.08);
          background: rgba(22, 26, 36, 0.78);
          color: #cbd5e1;
          display: flex;
          align-items: center;
          justify-content: center;
          cursor: pointer;
          font-size: 16px;
          line-height: 1;
          transition: transform 0.12s ease, background 0.15s ease;
          z-index: 2;
        }
        .dpad:active { transform: scale(0.9); background: rgba(255, 255, 255, 0.16); }
        .dpad-up { top: 24px; left: 50%; transform: translateX(-50%); }
        .dpad-down { bottom: 6px; left: 50%; transform: translateX(-50%); }
        .dpad-left { left: 6px; top: 50%; transform: translateY(-50%); }
        .dpad-right { right: 6px; top: 50%; transform: translateY(-50%); }
        .dpad-up:active { transform: translateX(-50%) scale(0.9); }
        .dpad-down:active { transform: translateX(-50%) scale(0.9); }
        .dpad-left:active { transform: translateY(-50%) scale(0.9); }
        .dpad-right:active { transform: translateY(-50%) scale(0.9); }
        .swing-row {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 10px;
          margin-top: 12px;
        }
        .swing-btn {
          border-radius: 12px;
          padding: 10px 12px;
          font-size: 12px;
          font-weight: 700;
          letter-spacing: 0.3px;
          border: 1px solid rgba(255, 255, 255, 0.09);
          background: rgba(24, 28, 42, 0.85);
          color: #94a3b8;
          cursor: pointer;
          transition: all 0.18s ease;
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 6px;
        }
        .swing-btn:active { transform: scale(0.97); }
      </style>
      <ha-card>
        <div class="header">
          <div class="title" id="title"></div>
          <div class="status" id="status">Tippen oder ziehen</div>
        </div>
        <div class="pad-wrap">
          <canvas id="canvas"></canvas>
          <button class="dpad dpad-up" id="btn-up" title="Höher">▲</button>
          <button class="dpad dpad-down" id="btn-down" title="Tiefer">▼</button>
          <button class="dpad dpad-left" id="btn-left" title="Links">◀</button>
          <button class="dpad dpad-right" id="btn-right" title="Rechts">▶</button>
        </div>
        <div class="swing-row">
          <button class="swing-btn" id="btn-vswing">↕ Auf / Ab Schwenken</button>
          <button class="swing-btn" id="btn-hswing">↔ Links / Rechts</button>
        </div>
      </ha-card>
    `;

    this._canvas = this.shadowRoot.getElementById("canvas");
    this._ctx = this._canvas.getContext("2d");

    const mapPointer = (ev) => {
      const rect = this._canvas.getBoundingClientRect();
      const padH = 44;
      const padTop = 44;
      const padBottom = 34;
      const usableW = Math.max(1, rect.width - padH * 2);
      const usableH = Math.max(1, rect.height - padTop - padBottom);
      const nx = Math.max(0, Math.min(1, (ev.clientX - rect.left - padH) / usableW));
      const ny = Math.max(0, Math.min(1, (ev.clientY - rect.top - padTop) / usableH));
      return { nx, ny };
    };

    this._canvas.addEventListener("pointerdown", (ev) => {
      ev.preventDefault();
      this._canvas.setPointerCapture(ev.pointerId);
      this._dragging = true;
      const { nx, ny } = mapPointer(ev);
      this._normX = nx;
      this._normY = ny;
      this._displayX = nx;
      this._displayY = ny;
      this._renderState();
    });

    this._canvas.addEventListener("pointermove", (ev) => {
      if (!this._dragging) return;
      ev.preventDefault();
      const { nx, ny } = mapPointer(ev);
      this._normX = nx;
      this._normY = ny;
      this._displayX = nx;
      this._displayY = ny;
      this._renderState();
    });

    const finishDrag = (ev) => {
      if (!this._dragging) return;
      this._dragging = false;
      const { nx, ny } = mapPointer(ev);
      this._commitPosition(nx, ny);
    };

    this._canvas.addEventListener("pointerup", finishDrag);
    this._canvas.addEventListener("pointercancel", () => {
      this._dragging = false;
      this._syncFromHass();
      this._renderState();
    });

    this.shadowRoot.getElementById("btn-up").addEventListener("click", () => this._stepVertical(-1));
    this.shadowRoot.getElementById("btn-down").addEventListener("click", () => this._stepVertical(1));
    this.shadowRoot.getElementById("btn-left").addEventListener("click", () => this._stepHorizontal(-1));
    this.shadowRoot.getElementById("btn-right").addEventListener("click", () => this._stepHorizontal(1));

    this.shadowRoot.getElementById("btn-vswing").addEventListener("click", () => {
      const { vState } = this._getStates();
      const active = vState && vState.startsWith("Schwenken");
      const next = active ? "Aus" : "Schwenken (Auf/Ab)";
      this._lockUntil = Date.now() + 2800;
      this._optimisticV = next;
      this._selectOption(this._config.vertical_entity, next);
      this._renderState();
    });

    this.shadowRoot.getElementById("btn-hswing").addEventListener("click", () => {
      const { hState } = this._getStates();
      const active = hState && hState.startsWith("Schwenken");
      const next = active ? "Aus" : "Schwenken (Links/Rechts)";
      this._lockUntil = Date.now() + 2800;
      this._optimisticH = next;
      this._selectOption(this._config.horizontal_entity, next);
      this._renderState();
    });

    this._resizeObserver = new ResizeObserver(() => this._drawCanvas());
    this._resizeObserver.observe(this._canvas);
  }

  _renderState() {
    if (!this._rendered) return;
    const accent = this._getAccent();
    const { vState, hState } = this._getStates();

    this.shadowRoot.getElementById("title").textContent = this._config.title;
    const statusEl = this.shadowRoot.getElementById("status");
    const parts = [vState, hState].filter(Boolean);
    statusEl.textContent = parts.length ? parts.join(" · ") : "Tippen oder ziehen";
    statusEl.style.color = accent;
    statusEl.style.borderColor = `${accent}55`;

    const vSwingActive = Boolean(vState && vState.startsWith("Schwenken"));
    const hSwingActive = Boolean(hState && hState.startsWith("Schwenken"));

    const styleBtn = (id, active) => {
      const el = this.shadowRoot.getElementById(id);
      if (active) {
        el.style.background = `${accent}2e`;
        el.style.borderColor = `${accent}88`;
        el.style.color = accent;
      } else {
        el.style.background = "rgba(24, 28, 42, 0.85)";
        el.style.borderColor = "rgba(255, 255, 255, 0.09)";
        el.style.color = "#94a3b8";
      }
    };
    styleBtn("btn-vswing", vSwingActive);
    styleBtn("btn-hswing", hSwingActive);

    this._drawCanvas();
  }

  _drawCanvas() {
    const canvas = this._canvas;
    const ctx = this._ctx;
    if (!canvas || !ctx) return;

    const dpr = window.devicePixelRatio || 1;
    const w = canvas.clientWidth || 320;
    const h = canvas.clientHeight || 210;
    if (canvas.width !== Math.round(w * dpr) || canvas.height !== Math.round(h * dpr)) {
      canvas.width = Math.round(w * dpr);
      canvas.height = Math.round(h * dpr);
    }

    ctx.save();
    ctx.scale(dpr, dpr);
    ctx.clearRect(0, 0, w, h);

    const accent = this._getAccent();
    const { vState, hState } = this._getStates();
    const vSwingActive = Boolean(vState && vState.startsWith("Schwenken"));
    const hSwingActive = Boolean(hState && hState.startsWith("Schwenken"));

    const padH = 44;
    const padTop = 44;
    const padBottom = 34;
    const usableW = Math.max(1, w - padH * 2);
    const usableH = Math.max(1, h - padTop - padBottom);

    // Stylized AC unit vent bar at top center
    const ventW = w * 0.42;
    const ventH = 10;
    const ventLeft = (w - ventW) / 2;
    const ventTop = 9;
    ctx.fillStyle = "#262b34";
    this._roundRect(ctx, ventLeft, ventTop, ventW, ventH, 5);
    ctx.fill();

    ctx.fillStyle = `${accent}b8`;
    this._roundRect(ctx, ventLeft + 10, ventTop + 3, ventW - 20, 4, 2);
    ctx.fill();

    // Subtle 5x5 dot alignment grid
    ctx.fillStyle = "rgba(148, 163, 184, 0.22)";
    for (let gx = 0; gx <= 4; gx++) {
      for (let gy = 0; gy <= 4; gy++) {
        const dx = padH + (gx / 4) * usableW;
        const dy = padTop + (gy / 4) * usableH;
        ctx.beginPath();
        ctx.arc(dx, dy, 2, 0, Math.PI * 2);
        ctx.fill();
      }
    }

    const targetX = padH + this._displayX * usableW;
    const targetY = padTop + this._displayY * usableH;
    const originY = ventTop + ventH + 2;

    // 5 glowing Tesla-style cubic-bezier airflow streams
    const streams = 5;
    for (let i = 0; i < streams; i++) {
      const frac = (i - (streams - 1) / 2) / ((streams - 1) / 2);
      const startX = w / 2 + frac * (ventW * 0.34);
      const spreadX = hSwingActive ? usableW * 0.42 : 22;
      const endX = Math.max(16, Math.min(w - 16, targetX + frac * spreadX));
      const endY = vSwingActive
        ? padTop + usableH * 0.92
        : targetY + Math.abs(frac) * 6;

      const c1x = startX + (endX - startX) * 0.25;
      const c1y = originY + (endY - originY) * 0.45;
      const c2x = endX - (endX - startX) * 0.15;
      const c2y = originY + (endY - originY) * 0.78;

      const weight = 1 - Math.abs(frac) * 0.45;
      const grad = ctx.createLinearGradient(0, originY, 0, endY);
      grad.addColorStop(0, this._withAlpha(accent, 0.8 * weight));
      grad.addColorStop(0.65, this._withAlpha(accent, 0.35 * weight));
      grad.addColorStop(1, this._withAlpha(accent, 0.04));

      ctx.strokeStyle = grad;
      ctx.lineWidth = 3 * weight;
      ctx.lineCap = "round";
      ctx.beginPath();
      ctx.moveTo(startX, originY);
      ctx.bezierCurveTo(c1x, c1y, c2x, c2y, endX, endY);
      ctx.stroke();
    }

    // Target glowing handle
    ctx.fillStyle = this._withAlpha(accent, 0.24);
    ctx.beginPath();
    ctx.arc(targetX, targetY, 16, 0, Math.PI * 2);
    ctx.fill();

    ctx.fillStyle = accent;
    ctx.beginPath();
    ctx.arc(targetX, targetY, 7, 0, Math.PI * 2);
    ctx.fill();

    ctx.fillStyle = "#0b0e14";
    ctx.beginPath();
    ctx.arc(targetX, targetY, 2.8, 0, Math.PI * 2);
    ctx.fill();

    ctx.restore();
  }

  _roundRect(ctx, x, y, w, h, r) {
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.lineTo(x + w - r, y);
    ctx.quadraticCurveTo(x + w, y, x + w, y + r);
    ctx.lineTo(x + w, y + h - r);
    ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
    ctx.lineTo(x + r, y + h);
    ctx.quadraticCurveTo(x, y + h, x, y + h - r);
    ctx.lineTo(x, y + r);
    ctx.quadraticCurveTo(x, y, x + r, y);
    ctx.closePath();
  }

  _withAlpha(hex, alpha) {
    const clean = hex.replace("#", "");
    const r = parseInt(clean.substring(0, 2), 16);
    const g = parseInt(clean.substring(2, 4), 16);
    const b = parseInt(clean.substring(4, 6), 16);
    return `rgba(${r}, ${g}, ${b}, ${alpha.toFixed(2)})`;
  }
}

customElements.define("daitsu-airflow-card", DaitsuAirflowCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "daitsu-airflow-card",
  name: "Daitsu Tesla Airflow Pad",
  description: "Interaktive 2D-Lamellensteuerung per Finger/Maus im Tesla-Style",
});
