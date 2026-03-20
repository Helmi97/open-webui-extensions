"""
title: Human Checkpoint
author: Helmi Chaouachi
repo_url: https://github.com/Helmi97/open-webui-extensions/tree/main/human_checkpoint
version: 0.1.0
license: MIT
required_open_webui_version: 0.8.0
description: Collect structured human input in Open WebUI with a browser modal powered by Jedison JSON Schema forms.
"""

import json
import textwrap
from typing import Any, Literal

from pydantic import BaseModel, Field

DEFAULT_JEDISON_CDN_URL = (
    "https://cdn.jsdelivr.net/npm/jedison@latest/dist/umd/jedison.umd.js"
)
DEFAULT_TIMEOUT_MS = 240000
DEFAULT_DIALOG_WIDTH = "92vw"
DEFAULT_DIALOG_MAX_WIDTH = "860px"
THEME_OPTIONS = ["default", "bootstrap5", "bootstrap4", "bootstrap3"]
STATUS_MESSAGES = {
    "submitted": "Structured user input received.",
    "cancelled": "Structured user input cancelled.",
    "timeout": "Structured user input timed out.",
    "error": "Structured user input failed.",
}


class HumanCheckpointValves(BaseModel):
    """Stable browser-side configuration for the human checkpoint modal."""

    submit_label: str = Field(
        default="Submit",
        description="Primary button label shown in the modal footer.",
    )
    cancel_label: str = Field(
        default="Cancel",
        description="Secondary button label shown in the modal footer.",
    )
    timeout_ms: int = Field(
        default=DEFAULT_TIMEOUT_MS,
        description=(
            "Browser-side timeout in milliseconds. Use 0 to disable the "
            "tool timeout. Keep this at or below Open WebUI's "
            "WEBSOCKET_EVENT_CALLER_TIMEOUT unless that server timeout is "
            "also increased."
        ),
    )
    initial_data: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Static JSON object merged over schema defaults before the "
            "form is shown."
        ),
    )
    ui_options: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Additional Jedison options merged into the form "
            "configuration. Reserved keys such as container, schema, "
            "theme, and data are overwritten by this tool."
        ),
    )
    css: str = Field(
        default="",
        description=(
            "Optional extra CSS appended after the base modal styles. "
            "Scope custom rules to the human_checkpoint data attributes or "
            "Jedison's .jedi-* classes."
        ),
    )
    cdn_url: str = Field(
        default=DEFAULT_JEDISON_CDN_URL,
        description=(
            "Browser URL used to load Jedison if window.Jedison is not "
            "already available."
        ),
    )
    dialog_width: str = Field(
        default=DEFAULT_DIALOG_WIDTH,
        description="CSS width value applied to the modal dialog container.",
    )
    dialog_max_width: str = Field(
        default=DEFAULT_DIALOG_MAX_WIDTH,
        description="CSS max-width value applied to the modal dialog container.",
    )
    theme_name: Literal["default", "bootstrap5", "bootstrap4", "bootstrap3"] = (
        Field(
            default="default",
            description=(
                "Jedison theme to instantiate in the browser. Bootstrap "
                "themes attempt to load matching CSS automatically."
            ),
            json_schema_extra={
                "input": {
                    "type": "select",
                    "options": THEME_OPTIONS,
                }
            },
        )
    )
    show_cancel_button: bool = Field(
        default=True,
        description="Whether the modal shows a cancel button.",
    )
    close_on_escape: bool = Field(
        default=True,
        description="Whether pressing Escape closes the modal as cancelled.",
    )
    close_on_overlay_click: bool = Field(
        default=False,
        description="Whether clicking the backdrop closes the modal as cancelled.",
    )



async def _emit_status(
    description: str,
    done: bool,
    __event_emitter__=None,
) -> None:
    """Emit lightweight progress messages when an event emitter is available."""
    if __event_emitter__ is None:
        return

    await __event_emitter__(
        {
            "type": "status",
            "data": {
                "description": description,
                "done": done,
            },
        }
    )

def _get_browser_config(valves: HumanCheckpointValves) -> dict[str, Any]:
    """Translate server-side valves into the browser config payload."""
    return {
        "submitLabel": valves.submit_label,
        "cancelLabel": valves.cancel_label,
        "timeoutMs": valves.timeout_ms,
        "initialData": valves.initial_data,
        "uiOptions": valves.ui_options,
        "css": valves.css,
        "cdnUrl": valves.cdn_url,
        "dialogWidth": valves.dialog_width,
        "dialogMaxWidth": valves.dialog_max_width,
        "themeName": valves.theme_name,
        "showCancelButton": valves.show_cancel_button,
        "closeOnEscape": valves.close_on_escape,
        "closeOnOverlayClick": valves.close_on_overlay_click,
    }

def _build_execute_code(
    schema: dict[str, Any],
    valves: HumanCheckpointValves,
) -> str:
    """Build the browser-side script executed through `__event_call__`."""
    payload_json = json.dumps(
        {
            "schema": schema,
            "config": _get_browser_config(valves),
        },
        ensure_ascii=False,
    )

    # Keep the browser script split into logical blocks so each concern is readable:
    # shared utilities, asset loading, focus handling, modal markup, and submit flow.
    script_blocks: list[str] = []
    script_blocks.append(
        textwrap.dedent(
            """
            // Shared runtime state, payload, and data helpers.
            const payload = __human_checkpoint_PAYLOAD__;
            const schema = payload.schema || {};
            const config = payload.config || {};
            const STATE_KEY = "__openWebUIHumanCheckpointState__";
            const STYLE_ID = "openwebui-human-checkpoint-style";
            const SCRIPT_SELECTOR = 'script[data-openwebui-human-checkpoint="jedison"]';
            const BOOTSTRAP_LINK_IDS = {
              bootstrap3: "openwebui-human-checkpoint-bootstrap3",
              bootstrap4: "openwebui-human-checkpoint-bootstrap4",
              bootstrap5: "openwebui-human-checkpoint-bootstrap5"
            };
            const BOOTSTRAP_CSS_URLS = {
              bootstrap3: "https://cdn.jsdelivr.net/npm/bootstrap@3.4.1/dist/css/bootstrap.min.css",
              bootstrap4: "https://cdn.jsdelivr.net/npm/bootstrap@4.6.2/dist/css/bootstrap.min.css",
              bootstrap5: "https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css"
            };

            const previousState = window[STATE_KEY];
            if (previousState && typeof previousState.finish === "function") {
              previousState.finish({
                status: "error",
                message: "A previous human_checkpoint dialog was replaced by a new request."
              });
            }

            const isPlainObject = (value) =>
              Object.prototype.toString.call(value) === "[object Object]";

            const safeClone = (value) => {
              if (value === undefined) {
                return undefined;
              }

              try {
                if (typeof structuredClone === "function") {
                  return structuredClone(value);
                }

                return JSON.parse(JSON.stringify(value));
              } catch (error) {
                return value;
              }
            };

            const mergeDeep = (baseValue, overrideValue) => {
              if (!isPlainObject(baseValue)) {
                return safeClone(overrideValue);
              }

              if (!isPlainObject(overrideValue)) {
                return safeClone(overrideValue);
              }

              const merged = safeClone(baseValue) || {};

              for (const [key, value] of Object.entries(overrideValue)) {
                if (isPlainObject(value) && isPlainObject(merged[key])) {
                  merged[key] = mergeDeep(merged[key], value);
                } else {
                  merged[key] = safeClone(value);
                }
              }

              return merged;
            };

            const normalizeInitialValue = (defaultValue, initialData) => {
              if (
                initialData === undefined ||
                initialData === null ||
                (isPlainObject(initialData) && Object.keys(initialData).length === 0)
              ) {
                return safeClone(defaultValue);
              }

              if (isPlainObject(defaultValue) && isPlainObject(initialData)) {
                return mergeDeep(defaultValue, initialData);
              }

              return safeClone(initialData);
            };

            const formatDuration = (milliseconds) => {
              if (!milliseconds || milliseconds <= 0) {
                return "";
              }

              const totalSeconds = Math.ceil(milliseconds / 1000);
              const minutes = Math.floor(totalSeconds / 60);
              const seconds = totalSeconds % 60;

              if (minutes && seconds) {
                return minutes + "m " + seconds + "s";
              }

              if (minutes) {
                return minutes + "m";
              }

              return seconds + "s";
            };

            """
        )
    )
    script_blocks.append(
        textwrap.dedent(
            """
            // Asset and stylesheet loading helpers.
            const ensureStyle = (cssText) => {
              let style = document.getElementById(STYLE_ID);

              if (!style) {
                style = document.createElement("style");
                style.id = STYLE_ID;
                document.head.appendChild(style);
              }

              style.textContent = cssText;
              return style;
            };

            const ensureCssLink = (id, href) =>
              new Promise((resolve) => {
                if (!href) {
                  resolve();
                  return;
                }

                const existing = document.getElementById(id);
                if (existing) {
                  if (existing.dataset.loaded === "true") {
                    resolve();
                    return;
                  }

                  existing.addEventListener("load", () => resolve(), { once: true });
                  existing.addEventListener("error", () => resolve(), { once: true });
                  return;
                }

                const link = document.createElement("link");
                link.id = id;
                link.rel = "stylesheet";
                link.href = href;
                link.dataset.openwebuiHumanCheckpoint = "theme";
                link.addEventListener(
                  "load",
                  () => {
                    link.dataset.loaded = "true";
                    resolve();
                  },
                  { once: true }
                );
                link.addEventListener("error", () => resolve(), { once: true });
                document.head.appendChild(link);
              });

            const ensureThemeAssets = async (themeName) => {
              const id = BOOTSTRAP_LINK_IDS[themeName];
              const href = BOOTSTRAP_CSS_URLS[themeName];

              if (id && href) {
                await ensureCssLink(id, href);
              }
            };

            const loadScriptOnce = (url) => {
              if (window.Jedison && typeof window.Jedison.Create === "function") {
                return Promise.resolve();
              }

              if (!url) {
                return Promise.reject(
                  new Error("Jedison CDN URL is empty.")
                );
              }

              const loaderKey = "__openWebUIHumanCheckpointJedisonLoader__";
              if (window[loaderKey]) {
                return window[loaderKey];
              }

              window[loaderKey] = new Promise((resolve, reject) => {
                const existing = document.querySelector(SCRIPT_SELECTOR);
                if (existing) {
                  if (existing.dataset.loaded === "true") {
                    resolve();
                    return;
                  }

                  existing.addEventListener("load", () => resolve(), { once: true });
                  existing.addEventListener(
                    "error",
                    () => reject(new Error("Failed to load Jedison from the configured CDN URL.")),
                    { once: true }
                  );
                  return;
                }

                const script = document.createElement("script");
                script.src = url;
                script.async = true;
                script.dataset.openwebuiHumanCheckpoint = "jedison";
                script.addEventListener(
                  "load",
                  () => {
                    script.dataset.loaded = "true";
                    resolve();
                  },
                  { once: true }
                );
                script.addEventListener(
                  "error",
                  () => reject(new Error("Failed to load Jedison from the configured CDN URL.")),
                  { once: true }
                );
                document.head.appendChild(script);
              }).finally(() => {
                if (!(window.Jedison && typeof window.Jedison.Create === "function")) {
                  delete window[loaderKey];
                }
              });

              return window[loaderKey];
            };
            """
        )
    )
    script_blocks.append(
        textwrap.dedent(
            """
            // Theme creation and keyboard-focus utilities.
            const createTheme = (themeName) => {
              const Jedison = window.Jedison;

              switch (themeName) {
                case "bootstrap5":
                  if (typeof Jedison.ThemeBootstrap5 === "function") {
                    return new Jedison.ThemeBootstrap5();
                  }
                  break;
                case "bootstrap4":
                  if (typeof Jedison.ThemeBootstrap4 === "function") {
                    return new Jedison.ThemeBootstrap4();
                  }
                  break;
                case "bootstrap3":
                  if (typeof Jedison.ThemeBootstrap3 === "function") {
                    return new Jedison.ThemeBootstrap3();
                  }
                  break;
                default:
                  break;
              }

              if (typeof Jedison.Theme === "function") {
                return new Jedison.Theme();
              }

              throw new Error("Jedison theme constructor is unavailable.");
            };

            const getFocusableElements = (root) =>
              Array.from(
                root.querySelectorAll(
                  'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
                )
              ).filter((element) => {
                if (!(element instanceof HTMLElement)) {
                  return false;
                }

                if (element.hasAttribute("disabled")) {
                  return false;
                }

                if (element.getAttribute("aria-hidden") === "true") {
                  return false;
                }

                const style = window.getComputedStyle(element);
                return style.display !== "none" && style.visibility !== "hidden";
              });

            const focusFirst = (root) => {
              const focusables = getFocusableElements(root);
              if (focusables.length) {
                focusables[0].focus();
              }
            };

            const trapFocus = (event, root) => {
              if (event.key !== "Tab") {
                return;
              }

              const focusables = getFocusableElements(root);
              if (!focusables.length) {
                return;
              }

              const first = focusables[0];
              const last = focusables[focusables.length - 1];

              if (event.shiftKey && document.activeElement === first) {
                event.preventDefault();
                last.focus();
              } else if (!event.shiftKey && document.activeElement === last) {
                event.preventDefault();
                first.focus();
              }
            };

            const focusFirstInvalid = (root) => {
              const candidate =
                root.querySelector('[aria-invalid="true"]') ||
                root.querySelector(".is-invalid") ||
                root.querySelector("input, select, textarea, button");

              if (candidate instanceof HTMLElement) {
                candidate.focus();
                candidate.scrollIntoView({ block: "nearest", behavior: "smooth" });
              }
            };
            """
        )
    )
    script_blocks.append(
        textwrap.dedent(
            """
            // Modal scaffolding and DOM assembly.
            const titleText =
              typeof schema.title === "string" && schema.title.trim()
                ? schema.title.trim()
                : "More input needed";
            const descriptionText =
              typeof schema.description === "string" ? schema.description.trim() : "";
            const timeoutMs = Number.isFinite(Number(config.timeoutMs))
              ? Math.max(0, Number(config.timeoutMs))
              : 0;
            const requestId =
              "human-checkpoint-" +
              Date.now().toString(36) +
              "-" +
              Math.random().toString(36).slice(2, 10);
            const baseStyle = `
            [data-openwebui-human-checkpoint-overlay] {
              position: fixed;
              inset: 0;
              z-index: 2147483000;
              display: flex;
              align-items: center;
              justify-content: center;
              padding: 24px;
              background: rgba(15, 23, 42, 0.68);
              backdrop-filter: blur(10px);
            }

            [data-openwebui-human-checkpoint-dialog] {
              width: 92vw;
              max-width: 860px;
              max-height: 86vh;
              overflow: hidden;
              display: flex;
              flex-direction: column;
              border-radius: 24px;
              border: 1px solid rgba(148, 163, 184, 0.24);
              background:
                linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(248, 250, 252, 0.98));
              box-shadow:
                0 28px 80px rgba(15, 23, 42, 0.38),
                0 6px 24px rgba(15, 23, 42, 0.14);
              color: #0f172a;
            }

            [data-openwebui-human-checkpoint-header] {
              position: relative;
              padding: 24px 74px 18px 28px;
              background:
                radial-gradient(circle at top right, rgba(14, 165, 233, 0.14), transparent 40%),
                linear-gradient(135deg, rgba(226, 232, 240, 0.9), rgba(255, 255, 255, 0.96));
              border-bottom: 1px solid rgba(148, 163, 184, 0.22);
            }

            [data-openwebui-human-checkpoint-countdown] {
              position: absolute;
              top: 20px;
              right: 24px;
              width: 34px;
              height: 34px;
              color: #0f766e;
              pointer-events: none;
              opacity: 0.95;
            }

            [data-openwebui-human-checkpoint-countdown][data-state="warning"] {
              color: #d97706;
            }

            [data-openwebui-human-checkpoint-countdown][data-state="urgent"] {
              color: #dc2626;
            }

            [data-openwebui-human-checkpoint-countdown-svg] {
              display: block;
              width: 34px;
              height: 34px;
              transform: rotate(-90deg);
            }

            [data-openwebui-human-checkpoint-countdown-track],
            [data-openwebui-human-checkpoint-countdown-progress] {
              fill: none;
              stroke-width: 3;
            }

            [data-openwebui-human-checkpoint-countdown-track] {
              stroke: rgba(15, 23, 42, 0.12);
            }

            [data-openwebui-human-checkpoint-countdown-progress] {
              stroke: currentColor;
              stroke-linecap: round;
              transition:
                stroke-dashoffset 180ms linear,
                stroke 180ms ease;
            }

            [data-openwebui-human-checkpoint-eyebrow] {
              margin: 0 0 8px;
              font-size: 12px;
              font-weight: 700;
              letter-spacing: 0.08em;
              text-transform: uppercase;
              color: #0369a1;
            }

            [data-openwebui-human-checkpoint-title] {
              margin: 0;
              font-size: 28px;
              line-height: 1.15;
              font-weight: 700;
              color: #020617;
            }

            [data-openwebui-human-checkpoint-description] {
              margin: 10px 0 0;
              font-size: 14px;
              line-height: 1.6;
              color: #475569;
            }

            [data-openwebui-human-checkpoint-body] {
              padding: 24px 28px 28px;
              overflow: auto;
            }

            [data-openwebui-human-checkpoint-form] {
              display: flex;
              flex-direction: column;
              gap: 18px;
            }

            [data-openwebui-human-checkpoint-form-host] {
              display: flex;
              flex-direction: column;
              gap: 16px;
            }

            [data-openwebui-human-checkpoint-footer] {
              display: flex;
              align-items: center;
              justify-content: space-between;
              gap: 16px;
              padding-top: 18px;
              border-top: 1px solid rgba(148, 163, 184, 0.18);
            }

            [data-openwebui-human-checkpoint-footer-meta] {
              min-width: 0;
              display: flex;
              flex-direction: column;
              gap: 4px;
            }

            [data-openwebui-human-checkpoint-validation] {
              font-size: 13px;
              line-height: 1.4;
              color: #475569;
            }

            [data-openwebui-human-checkpoint-validation][data-state="error"] {
              color: #b91c1c;
            }

            [data-openwebui-human-checkpoint-timeout] {
              font-size: 12px;
              color: #64748b;
            }

            [data-openwebui-human-checkpoint-actions] {
              display: inline-flex;
              align-items: center;
              gap: 12px;
              flex-wrap: wrap;
              justify-content: flex-end;
            }

            [data-openwebui-human-checkpoint-button] {
              appearance: none;
              border: 1px solid transparent;
              border-radius: 999px;
              padding: 11px 18px;
              font-size: 14px;
              font-weight: 600;
              line-height: 1;
              cursor: pointer;
              transition:
                transform 120ms ease,
                box-shadow 120ms ease,
                background-color 120ms ease,
                border-color 120ms ease,
                color 120ms ease;
            }

            [data-openwebui-human-checkpoint-button]:hover:not(:disabled) {
              transform: translateY(-1px);
            }

            [data-openwebui-human-checkpoint-button]:focus-visible {
              outline: 3px solid rgba(14, 165, 233, 0.28);
              outline-offset: 2px;
            }

            [data-openwebui-human-checkpoint-button]:disabled {
              cursor: not-allowed;
              opacity: 0.6;
              transform: none;
              box-shadow: none;
            }

            [data-openwebui-human-checkpoint-button="cancel"] {
              border-color: rgba(148, 163, 184, 0.42);
              background: rgba(255, 255, 255, 0.9);
              color: #334155;
            }

            [data-openwebui-human-checkpoint-button="submit"] {
              background: linear-gradient(135deg, #0284c7, #0f766e);
              color: #ffffff;
              box-shadow: 0 10px 24px rgba(2, 132, 199, 0.22);
            }

            [data-openwebui-human-checkpoint-button="submit"]:disabled {
              background: #94a3b8;
            }
            `;
            """
        )
    )
    script_blocks.append(
        textwrap.dedent(
            """
            const baseStyleExtras = `
            [data-openwebui-human-checkpoint-dialog] .jedi-title,
            [data-openwebui-human-checkpoint-dialog] .jedi-label {
              display: inline-flex;
              align-items: center;
              gap: 8px;
              margin-bottom: 6px;
              font-size: 14px;
              font-weight: 600;
              color: #0f172a;
            }

            [data-openwebui-human-checkpoint-dialog] .jedi-description {
              margin: 6px 0 10px;
              font-size: 13px;
              line-height: 1.55;
              color: #475569;
            }

            [data-openwebui-human-checkpoint-dialog] .jedi-control-slot,
            [data-openwebui-human-checkpoint-dialog] .jedi-children-slot,
            [data-openwebui-human-checkpoint-dialog] .jedi-properties-activators,
            [data-openwebui-human-checkpoint-dialog] .jedi-properties-group {
              display: flex;
              flex-direction: column;
              gap: 12px;
            }

            [data-openwebui-human-checkpoint-dialog] .jedi-messages-slot:empty {
              display: none;
            }

            [data-openwebui-human-checkpoint-dialog] .jedi-error-message,
            [data-openwebui-human-checkpoint-dialog] .jedi-warning-message {
              margin-top: 8px;
              padding: 10px 12px;
              border-radius: 14px;
              font-size: 13px;
              line-height: 1.45;
            }

            [data-openwebui-human-checkpoint-dialog] .jedi-error-message {
              border: 1px solid rgba(220, 38, 38, 0.18);
              background: rgba(254, 226, 226, 0.72);
              color: #991b1b;
            }

            [data-openwebui-human-checkpoint-dialog] .jedi-warning-message {
              border: 1px solid rgba(217, 119, 6, 0.18);
              background: rgba(254, 243, 199, 0.74);
              color: #92400e;
            }

            [data-openwebui-human-checkpoint-dialog] fieldset {
              margin: 0;
              padding: 0;
              border: 0;
              min-width: 0;
            }

            [data-openwebui-human-checkpoint-dialog] .jedi-editor-card,
            [data-openwebui-human-checkpoint-dialog] .jedi-array-item {
              border: 1px solid rgba(148, 163, 184, 0.22);
              border-radius: 18px;
              background: rgba(255, 255, 255, 0.92);
            }

            [data-openwebui-human-checkpoint-dialog] .jedi-editor-card-header,
            [data-openwebui-human-checkpoint-dialog] .jedi-editor-card-body,
            [data-openwebui-human-checkpoint-dialog] .jedi-array-item-body,
            [data-openwebui-human-checkpoint-dialog] .jedi-array-footer {
              padding: 14px 16px;
            }

            [data-openwebui-human-checkpoint-dialog] .jedi-actions-slot,
            [data-openwebui-human-checkpoint-dialog] .jedi-array-actions-slot,
            [data-openwebui-human-checkpoint-dialog] .jedi-btn-group {
              display: inline-flex;
              flex-wrap: wrap;
              align-items: center;
              gap: 8px;
            }

            [data-openwebui-human-checkpoint-dialog] .jedi-btn {
              appearance: none;
              border: 1px solid rgba(148, 163, 184, 0.34);
              border-radius: 999px;
              padding: 8px 12px;
              background: #ffffff;
              color: #334155;
              cursor: pointer;
            }

            [data-openwebui-human-checkpoint-dialog] .jedi-btn:disabled {
              opacity: 0.55;
              cursor: not-allowed;
            }

            [data-openwebui-human-checkpoint-dialog]
            :is(
              input:not([type="checkbox"]):not([type="radio"]):not([type="range"]),
              select,
              textarea
            ) {
              width: 100%;
              min-height: 44px;
              border: 1px solid rgba(148, 163, 184, 0.38);
              border-radius: 14px;
              background: rgba(255, 255, 255, 0.98);
              color: #0f172a;
              padding: 10px 12px;
              font-size: 14px;
              line-height: 1.4;
              box-sizing: border-box;
            }

            [data-openwebui-human-checkpoint-dialog] textarea {
              min-height: 110px;
              resize: vertical;
            }

            [data-openwebui-human-checkpoint-dialog]
            :is(
              input:not([type="checkbox"]):not([type="radio"]):not([type="range"]),
              select,
              textarea
            ):focus {
              outline: none;
              border-color: rgba(2, 132, 199, 0.9);
              box-shadow: 0 0 0 4px rgba(2, 132, 199, 0.12);
            }

            [data-openwebui-human-checkpoint-dialog] input[type="checkbox"],
            [data-openwebui-human-checkpoint-dialog] input[type="radio"] {
              accent-color: #0284c7;
            }

            [data-openwebui-human-checkpoint-dialog] dialog.jedi-json-data,
            [data-openwebui-human-checkpoint-dialog] dialog.jedi-properties-slot,
            [data-openwebui-human-checkpoint-dialog] dialog.jedi-quick-add-property-slot {
              border: 1px solid rgba(148, 163, 184, 0.26);
              border-radius: 18px;
              padding: 16px;
              max-width: min(90vw, 720px);
              background: #ffffff;
              color: #0f172a;
              box-shadow: 0 24px 60px rgba(15, 23, 42, 0.22);
            }

            [data-openwebui-human-checkpoint-dialog] dialog::backdrop {
              background: rgba(15, 23, 42, 0.38);
            }

            @media (max-width: 720px) {
              [data-openwebui-human-checkpoint-overlay] {
                padding: 12px;
              }

              [data-openwebui-human-checkpoint-dialog] {
                max-height: 92vh;
                border-radius: 20px;
              }

              [data-openwebui-human-checkpoint-header] {
                padding: 18px 58px 16px 18px;
              }

              [data-openwebui-human-checkpoint-countdown] {
                top: 16px;
                right: 16px;
                width: 28px;
                height: 28px;
              }

              [data-openwebui-human-checkpoint-countdown-svg] {
                width: 28px;
                height: 28px;
              }

              [data-openwebui-human-checkpoint-body] {
                padding: 18px;
              }

              [data-openwebui-human-checkpoint-footer] {
                flex-direction: column;
                align-items: stretch;
              }

              [data-openwebui-human-checkpoint-actions] {
                width: 100%;
                justify-content: stretch;
              }

              [data-openwebui-human-checkpoint-actions] > button {
                flex: 1 1 auto;
              }
            }
            `;

            return await new Promise(async (resolve) => {
              let overlay = null;
              let dialog = null;
              let form = null;
              let cancelButton = null;
              let submitButton = null;
              let validationMessage = null;
              let timeoutMessage = null;
              let countdownShell = null;
              let countdownProgress = null;
              let timerId = null;
              let countdownIntervalId = null;
              let jedison = null;
              let settled = false;
              let submitting = false;
              let cleanupDone = false;
              const countdownRadius = 18;
              const countdownCircumference = 2 * Math.PI * countdownRadius;
              const countdownWarningThresholdMs =
                timeoutMs > 0 ? Math.min(60000, timeoutMs * 0.25) : 0;
              const deadlineAt = timeoutMs > 0 ? Date.now() + timeoutMs : 0;
              const previousOverflow = document.body ? document.body.style.overflow : "";
              const previousFocus =
                document.activeElement instanceof HTMLElement ? document.activeElement : null;

              const updateCountdown = () => {
                if (!deadlineAt) {
                  return;
                }

                const remainingMs = Math.max(0, deadlineAt - Date.now());
                const remainingRatio = timeoutMs > 0 ? remainingMs / timeoutMs : 0;

                if (countdownProgress) {
                  countdownProgress.style.strokeDashoffset = String(
                    countdownCircumference * (1 - remainingRatio)
                  );
                }

                if (countdownShell) {
                  if (remainingMs <= 10000) {
                    countdownShell.dataset.state = "urgent";
                  } else if (remainingMs <= countdownWarningThresholdMs) {
                    countdownShell.dataset.state = "warning";
                  } else {
                    delete countdownShell.dataset.state;
                  }
                }

                if (timeoutMessage) {
                  timeoutMessage.textContent = remainingMs
                    ? "This request will time out in " + formatDuration(remainingMs) + "."
                    : "This request is about to time out.";
                }
              };

              const cleanup = () => {
                if (cleanupDone) {
                  return;
                }

                cleanupDone = true;

                if (timerId) {
                  window.clearTimeout(timerId);
                }

                if (countdownIntervalId) {
                  window.clearInterval(countdownIntervalId);
                }

                if (form && form.__HumanCheckpointSubmitHandler) {
                  form.removeEventListener("submit", form.__HumanCheckpointSubmitHandler);
                }

                if (cancelButton && cancelButton.__HumanCheckpointCancelHandler) {
                  cancelButton.removeEventListener("click", cancelButton.__HumanCheckpointCancelHandler);
                }

                if (overlay && overlay.__HumanCheckpointOverlayClickHandler) {
                  overlay.removeEventListener("click", overlay.__HumanCheckpointOverlayClickHandler);
                }

                if (document.__HumanCheckpointKeydownHandler) {
                  document.removeEventListener(
                    "keydown",
                    document.__HumanCheckpointKeydownHandler,
                    true
                  );
                  delete document.__HumanCheckpointKeydownHandler;
                }

                if (jedison && typeof jedison.destroy === "function") {
                  try {
                    jedison.destroy();
                  } catch (error) {
                  }
                }

                if (overlay) {
                  overlay.remove();
                }

                if (document.body) {
                  document.body.style.overflow = previousOverflow;
                }
              };

              const finish = (result) => {
                if (settled) {
                  return;
                }

                settled = true;

                if (window[STATE_KEY] && window[STATE_KEY].id === requestId) {
                  delete window[STATE_KEY];
                }

                cleanup();

                if (previousFocus && document.contains(previousFocus)) {
                  previousFocus.focus();
                }

                resolve(result);
              };

              window[STATE_KEY] = {
                id: requestId,
                finish
              };

              try {
                if (!document.body) {
                  throw new Error("Document body is unavailable.");
                }

                await ensureThemeAssets(config.themeName);
                await loadScriptOnce(config.cdnUrl);

                if (!(window.Jedison && typeof window.Jedison.Create === "function")) {
                  throw new Error("Jedison loaded but window.Jedison.Create is unavailable.");
                }

                ensureStyle(baseStyle + "\\n" + baseStyleExtras + "\\n" + (config.css || ""));

                overlay = document.createElement("div");
                overlay.setAttribute("data-openwebui-human-checkpoint-overlay", "true");

                dialog = document.createElement("section");
                dialog.setAttribute("data-openwebui-human-checkpoint-dialog", "true");
                dialog.setAttribute("role", "dialog");
                dialog.setAttribute("aria-modal", "true");
                dialog.setAttribute("aria-labelledby", requestId + "-title");
                dialog.setAttribute("aria-describedby", requestId + "-description");
                dialog.style.width = String(config.dialogWidth || "92vw");
                dialog.style.maxWidth = String(config.dialogMaxWidth || "860px");

                const header = document.createElement("header");
                header.setAttribute("data-openwebui-human-checkpoint-header", "true");

                const eyebrow = document.createElement("p");
                eyebrow.setAttribute("data-openwebui-human-checkpoint-eyebrow", "true");
                eyebrow.textContent = "Structured Input";

                const title = document.createElement("h2");
                title.id = requestId + "-title";
                title.setAttribute("data-openwebui-human-checkpoint-title", "true");
                title.textContent = titleText;

                const description = document.createElement("p");
                description.id = requestId + "-description";
                description.setAttribute("data-openwebui-human-checkpoint-description", "true");
                description.textContent =
                  descriptionText || "Please complete the requested fields and submit the form.";

                header.appendChild(eyebrow);
                header.appendChild(title);
                header.appendChild(description);

                if (timeoutMs > 0) {
                  countdownShell = document.createElement("div");
                  countdownShell.setAttribute(
                    "data-openwebui-human-checkpoint-countdown",
                    "true"
                  );
                  countdownShell.setAttribute("aria-hidden", "true");

                  const countdownSvg = document.createElementNS(
                    "http://www.w3.org/2000/svg",
                    "svg"
                  );
                  countdownSvg.setAttribute(
                    "data-openwebui-human-checkpoint-countdown-svg",
                    "true"
                  );
                  countdownSvg.setAttribute("viewBox", "0 0 60 60");

                  const countdownTrack = document.createElementNS(
                    "http://www.w3.org/2000/svg",
                    "circle"
                  );
                  countdownTrack.setAttribute(
                    "data-openwebui-human-checkpoint-countdown-track",
                    "true"
                  );
                  countdownTrack.setAttribute("cx", "30");
                  countdownTrack.setAttribute("cy", "30");
                  countdownTrack.setAttribute("r", String(countdownRadius));

                  countdownProgress = document.createElementNS(
                    "http://www.w3.org/2000/svg",
                    "circle"
                  );
                  countdownProgress.setAttribute(
                    "data-openwebui-human-checkpoint-countdown-progress",
                    "true"
                  );
                  countdownProgress.setAttribute("cx", "30");
                  countdownProgress.setAttribute("cy", "30");
                  countdownProgress.setAttribute("r", String(countdownRadius));
                  countdownProgress.style.strokeDasharray = String(countdownCircumference);
                  countdownProgress.style.strokeDashoffset = "0";

                  countdownSvg.appendChild(countdownTrack);
                  countdownSvg.appendChild(countdownProgress);
                  countdownShell.appendChild(countdownSvg);
                  header.appendChild(countdownShell);
                }

                const body = document.createElement("div");
                body.setAttribute("data-openwebui-human-checkpoint-body", "true");

                form = document.createElement("form");
                form.noValidate = true;
                form.setAttribute("data-openwebui-human-checkpoint-form", "true");

                const formHost = document.createElement("div");
                formHost.setAttribute("data-openwebui-human-checkpoint-form-host", "true");

                const footer = document.createElement("div");
                footer.setAttribute("data-openwebui-human-checkpoint-footer", "true");

                const footerMeta = document.createElement("div");
                footerMeta.setAttribute("data-openwebui-human-checkpoint-footer-meta", "true");

                validationMessage = document.createElement("div");
                validationMessage.setAttribute("data-openwebui-human-checkpoint-validation", "ready");
                validationMessage.textContent = "Complete the required fields to continue.";

                timeoutMessage = document.createElement("div");
                timeoutMessage.setAttribute("data-openwebui-human-checkpoint-timeout", "true");
                timeoutMessage.textContent = timeoutMs
                  ? "This request will time out in " + formatDuration(timeoutMs) + "."
                  : "";

                footerMeta.appendChild(validationMessage);
                if (timeoutMessage.textContent) {
                  footerMeta.appendChild(timeoutMessage);
                }

                const actions = document.createElement("div");
                actions.setAttribute("data-openwebui-human-checkpoint-actions", "true");

                if (config.showCancelButton !== false) {
                  cancelButton = document.createElement("button");
                  cancelButton.type = "button";
                  cancelButton.setAttribute("data-openwebui-human-checkpoint-button", "cancel");
                  cancelButton.textContent = String(config.cancelLabel || "Cancel");
                  actions.appendChild(cancelButton);
                }

                submitButton = document.createElement("button");
                submitButton.type = "submit";
                submitButton.setAttribute("data-openwebui-human-checkpoint-button", "submit");
                submitButton.textContent = String(config.submitLabel || "Submit");
                submitButton.disabled = true;
                actions.appendChild(submitButton);

                footer.appendChild(footerMeta);
                footer.appendChild(actions);
                form.appendChild(formHost);
                form.appendChild(footer);
                body.appendChild(form);
                dialog.appendChild(header);
                dialog.appendChild(body);
                overlay.appendChild(dialog);
                document.body.appendChild(overlay);
                document.body.style.overflow = "hidden";
            """
        )
    )
    script_blocks.append(
        textwrap.dedent(
            """
                // Jedison initialization, validation, and submission lifecycle.
                const theme = createTheme(config.themeName);
                const uiOptions = isPlainObject(config.uiOptions)
                  ? safeClone(config.uiOptions)
                  : {};

                jedison = new window.Jedison.Create(
                  Object.assign({}, uiOptions, {
                    container: formHost,
                    theme,
                    schema,
                    showErrors:
                      typeof uiOptions.showErrors === "string"
                        ? uiOptions.showErrors
                        : "change"
                  })
                );

                const initialValue = normalizeInitialValue(
                  jedison.getValue(),
                  config.initialData
                );

                if (initialValue !== undefined) {
                  jedison.setValue(initialValue, false, "api");
                }

                const updateValidation = (forceErrors = false) => {
                  const errors =
                    typeof jedison.getErrors === "function"
                      ? jedison.getErrors(["error"])
                      : [];
                  const errorCount = Array.isArray(errors) ? errors.length : 0;

                  if (forceErrors && typeof jedison.showValidationErrors === "function") {
                    jedison.showValidationErrors(errors);
                  }

                  if (errorCount > 0) {
                    validationMessage.dataset.state = "error";
                    validationMessage.textContent =
                      errorCount +
                      (errorCount === 1
                        ? " validation error still needs attention."
                        : " validation errors still need attention.");
                  } else {
                    delete validationMessage.dataset.state;
                    validationMessage.textContent = "Form is valid and ready to submit.";
                  }

                  submitButton.disabled = submitting || errorCount > 0;
                  return errorCount;
                };

                const submitHandler = (event) => {
                  event.preventDefault();

                  if (submitting) {
                    return;
                  }

                  const errorCount = updateValidation(true);
                  if (errorCount > 0) {
                    focusFirstInvalid(dialog);
                    return;
                  }

                  submitting = true;
                  submitButton.disabled = true;
                  submitButton.textContent = "Submitting...";

                  if (cancelButton) {
                    cancelButton.disabled = true;
                  }

                  const value = safeClone(jedison.getValue());
                  finish({
                    status: "submitted",
                    data: value === undefined ? null : value
                  });
                };

                form.__HumanCheckpointSubmitHandler = submitHandler;
                form.addEventListener("submit", submitHandler);

                if (cancelButton) {
                  const cancelHandler = () => {
                    finish({ status: "cancelled" });
                  };
                  cancelButton.__HumanCheckpointCancelHandler = cancelHandler;
                  cancelButton.addEventListener("click", cancelHandler);
                }

                const overlayClickHandler = (event) => {
                  if (
                    config.closeOnOverlayClick === true &&
                    event.target === overlay
                  ) {
                    finish({ status: "cancelled" });
                  }
                };

                overlay.__HumanCheckpointOverlayClickHandler = overlayClickHandler;
                overlay.addEventListener("click", overlayClickHandler);

                const keydownHandler = (event) => {
                  if (event.key === "Escape" && config.closeOnEscape === true) {
                    event.preventDefault();
                    finish({ status: "cancelled" });
                    return;
                  }

                  trapFocus(event, dialog);
                };

                document.__HumanCheckpointKeydownHandler = keydownHandler;
                document.addEventListener("keydown", keydownHandler, true);

                if (timeoutMs > 0) {
                  updateCountdown();
                  countdownIntervalId = window.setInterval(() => {
                    updateCountdown();
                  }, 250);

                  timerId = window.setTimeout(() => {
                    finish({ status: "timeout" });
                  }, timeoutMs);
                }

                if (typeof jedison.on === "function") {
                  jedison.on("change", () => {
                    updateValidation(false);
                  });
                }

                updateValidation(false);
                window.requestAnimationFrame(() => {
                  focusFirst(dialog);
                });
              } catch (error) {
                finish({
                  status: "error",
                  message:
                    error && error.message ? error.message : String(error || "Unknown error")
                });
              }
            });
            """
        )
    )
    code = "".join(script_blocks).strip()
    return code.replace("__human_checkpoint_PAYLOAD__", payload_json)


def _build_execute_request(
    schema: dict[str, Any],
    valves: HumanCheckpointValves,
) -> dict[str, Any]:
    """Build the single browser execution request sent through `__event_call__`."""
    return {
        "type": "execute",
        "data": {
            "code": _build_execute_code(schema, valves),
        },
    }


def _error_result(message: str) -> dict[str, Any]:
    """Return the canonical error result shape."""
    return {
        "status": "error",
        "message": message,
    }


def _normalize_result(result: Any) -> dict[str, Any]:
    """Normalize browser responses into one predictable JSON object shape."""
    if isinstance(result, str):
        try:
            result = json.loads(result)
        except json.JSONDecodeError:
            return _error_result(
                "human_checkpoint returned a non-JSON string from the browser "
                "execution channel."
            )

    if not isinstance(result, dict):
        return _error_result(
            "human_checkpoint returned an unexpected response type from the "
            "browser execution channel."
        )

    status = str(result.get("status", "")).strip().lower()

    if status == "submitted":
        return {
            "status": "submitted",
            "data": result.get("data"),
        }

    if status == "cancelled":
        return {"status": "cancelled"}

    if status == "timeout":
        return {"status": "timeout"}

    if status == "error":
        return _error_result(
            str(result.get("message") or "Unknown browser-side error.")
        )

    return _error_result(
        "human_checkpoint returned an unknown result status from the browser "
        "execution channel."
    )

def _format_event_call_error(error: Exception) -> str:
    """Make transport failures readable and actionable for the caller."""
    message = str(error).strip() or error.__class__.__name__
    lower_message = message.lower()

    if "timeout" in lower_message or "timed out" in lower_message:
        return (
            "human_checkpoint did not complete before Open WebUI's event-call "
            "timeout expired. Lower the tool's timeout_ms valve or raise "
            "WEBSOCKET_EVENT_CALLER_TIMEOUT on the server."
        )

    return f"human_checkpoint browser execution failed: {message}"

class Tools:
    async def human_checkpoint(
        self,
        schema: dict[str, Any],
        __event_call__=None,
        __event_emitter__=None,
    ) -> dict[str, Any]:
        """
        Open a browser modal that asks the human for structured input using a JSON Schema form.

        Use this when the task needs accurate informations from the user.

        Calling guidance:
        - Provide exactly one runtime argument: `schema`.
        - Put titles, descriptions, defaults, enums, required fields, and validation rules inside
          the schema itself.
        - Prefer one complete schema that captures everything needed in a single interaction.
        - Most calls should use `type: "object"` with `properties` and `required`.
        - Add a schema `title` and `description` so the modal is self-explanatory to the user.
        - Use enums, numeric bounds, string lengths, patterns, and formats whenever the value
          shape matters.
        - When collecting secrets, use the password or secret conventions supported by Jedison so
          the browser can mask the field where available.
        - After the call returns, inspect `status` before using any data.

        Return shapes:
        - `{"status": "submitted", "data": {...}}`
        - `{"status": "cancelled"}`
        - `{"status": "timeout"}`
        - `{"status": "error", "message": "..."}`
        """
        if not isinstance(schema, dict):
            return _error_result(
                "human_checkpoint requires the `schema` argument to be a JSON "
                "Schema object."
            )

        if __event_call__ is None:
            return _error_result(
                "human_checkpoint requires an active Open WebUI browser session "
                "because it opens a client-side modal through __event_call__."
            )

        await _emit_status(
            "Waiting for structured user input...",
            done=False,
            __event_emitter__=__event_emitter__,
        )

        try:
            raw_result = await __event_call__(_build_execute_request(schema, self.valves))
            result = _normalize_result(raw_result)
        except Exception as error:
            result = _error_result(_format_event_call_error(error))

        await _emit_status(
            STATUS_MESSAGES.get(result["status"], "Structured user input finished."),
            done=True,
            __event_emitter__=__event_emitter__,
        )

        return result


def _tools_init(self):
    """Attach the runtime configuration that Open WebUI expects."""
    self.valves = HumanCheckpointValves()
    self.citation = False


Tools.__init__ = _tools_init
Tools.Valves = HumanCheckpointValves
Tools.citation = False
