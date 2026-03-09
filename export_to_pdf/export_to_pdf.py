"""
title: Export Message to PDF
author: Helmi Chaouachi
git_url: https://github.com/Helmi97/open-webui-extensions/tree/main/export_to_pdf
version: 1.0.0
required_open_webui_version: 0.8.0
icon_url: https://www.svgrepo.com/show/485376/pdf-file.svg
requirements: weasyprint,markdown
"""

from __future__ import annotations

import base64
import html
import json
import re
from datetime import datetime
from typing import Any, Optional

import markdown
from pydantic import BaseModel, Field
from weasyprint import HTML

DEFAULT_GLOBAL_CSS = r"""
:root {
  --text: #1f2937;
  --muted: #6b7280;
  --border: #e5e7eb;
  --soft: #f9fafb;
  --soft-2: #f3f4f6;
  --code-bg: #111827;
  --code-fg: #f9fafb;
  --link: #2563eb;
  --quote: #4b5563;
  --brand: #1d4ed8;
}

html {
  font-size: 11pt;
}

body {
  margin: 0;
  padding: 0;
  font-family: "Segoe UI", Roboto, Arial, sans-serif;
  color: var(--text);
  background: white;
  overflow-wrap: break-word;
  -webkit-font-smoothing: antialiased;
}

#pdf-body {
  width: 100%;
  box-sizing: border-box;
}

#pdf-first-header,
#pdf-other-header,
#pdf-footer {
  width: 100%;
  box-sizing: border-box;
}

img, svg {
  max-width: 100%;
  height: auto;
}
"""

DEFAULT_FIRST_HEADER_HTML = r"""
<div class="header-shell header-shell--first">
  <div class="doc-header doc-header--first">
    <div class="doc-header__topbar"></div>

    <div class="doc-header__main">
      <div class="doc-header__left">
        <div class="doc-logo-slot">
          <!-- Example:
          <img class="doc-logo" src="data:image/png;base64,..." alt="Logo">
          -->
        </div>
      </div>

      <div class="doc-header__right">
        <div class="doc-org-name">Your Company Name</div>
        <div class="doc-org-tagline">Professional Document Export</div>
        <div class="doc-org-meta">Street Address, ZIP City</div>
        <div class="doc-org-meta">info@example.com | +00 000 000000</div>
      </div>
    </div>
  </div>
</div>
"""

DEFAULT_OTHER_HEADER_HTML = r"""
<div class="header-shell">
  <div class="doc-header doc-header--other">
    <div class="doc-header__main doc-header__main--compact">
      <div class="doc-header__left">
        <div class="doc-logo-slot doc-logo-slot--compact">
          <!-- Example:
          <img class="doc-logo doc-logo--compact" src="data:image/png;base64,..." alt="Logo">
          -->
        </div>
      </div>

      <div class="doc-header__right">
        <div class="doc-org-name doc-org-name--compact">Your Company Name</div>
        <div class="doc-org-meta">Assistant Message Export</div>
      </div>
    </div>
  </div>
</div>
"""

DEFAULT_FOOTER_HTML = r"""
<div class="footer-shell">
  <div class="doc-footer">
    <div class="doc-footer__left">
      <div class="doc-footer__label">Document</div>
      <div class="doc-footer__value">{{ export_title }}</div>
    </div>

    <div class="doc-footer__center">
      <div class="doc-footer__label">{{ user_name }}</div>
      <div class="doc-footer__value">{{ export_date }}</div>
    </div>

    <div class="doc-footer__right">
      <div class="doc-footer__label">Page</div>
      <div class="doc-footer__value page-number"></div>
    </div>
  </div>
</div>
"""

DEFAULT_BODY_HTML_TEMPLATE = r"""
<div class="document-body">
  {{ body_content }}
</div>
"""

DEFAULT_FIRST_HEADER_CSS = r"""
.header-shell--first {
  width: var(--printable-width);
  box-sizing: border-box;
  margin: 0 auto;
  padding: 0 0 4mm 0;
}

.doc-header {
  width: 100%;
  box-sizing: border-box;
}

.doc-header__topbar {
  height: 3.2mm;
  width: 100%;
  background: linear-gradient(90deg, var(--brand), #60a5fa);
  border-radius: 1.2mm;
  margin: 0 0 4mm 0;
}

.doc-header__main {
  width: 100%;
  display: table;
  table-layout: fixed;
  border-bottom: 1px solid var(--border);
  padding-bottom: 3mm;
}

.doc-header__main--compact {
  padding-bottom: 2mm;
}

.doc-header__left,
.doc-header__right {
  display: table-cell;
  vertical-align: middle;
}

.doc-header__left {
  width: 34mm;
}

.doc-header__right {
  text-align: right;
}

.doc-logo-slot {
  width: 28mm;
  height: 16mm;
  display: flex;
  align-items: center;
  justify-content: flex-start;
}

.doc-logo-slot--compact {
  height: 11mm;
}

.doc-logo {
  max-width: 28mm;
  max-height: 16mm;
  width: auto;
  height: auto;
  display: block;
}

.doc-logo--compact {
  max-width: 22mm;
  max-height: 11mm;
}

.doc-org-name {
  font-size: 16pt;
  font-weight: 700;
  line-height: 1.15;
  color: #0f172a;
  margin: 0 0 1mm 0;
  letter-spacing: 0.01em;
}

.doc-org-name--compact {
  font-size: 11pt;
  margin: 0;
}

.doc-org-tagline {
  font-size: 9pt;
  font-weight: 600;
  color: var(--brand);
  margin: 0 0 1.2mm 0;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.doc-org-meta {
  font-size: 8.3pt;
  color: var(--muted);
  line-height: 1.35;
  margin: 0.3mm 0;
}
"""

DEFAULT_OTHER_HEADER_CSS = r"""
.header-shell {
  width: var(--printable-width);
  box-sizing: border-box;
  margin: 0 auto;
  padding: 0 0 2.5mm 0;
}

.doc-header {
  width: 100%;
  box-sizing: border-box;
}

.doc-header__main {
  width: 100%;
  display: table;
  table-layout: fixed;
  border-bottom: 1px solid var(--border);
  padding-bottom: 2mm;
}

.doc-header__left,
.doc-header__right {
  display: table-cell;
  vertical-align: middle;
}

.doc-header__left {
  width: 28mm;
}

.doc-header__right {
  text-align: right;
}

.doc-logo-slot {
  width: 22mm;
  height: 11mm;
  display: flex;
  align-items: center;
  justify-content: flex-start;
}

.doc-logo {
  max-width: 22mm;
  max-height: 11mm;
  width: auto;
  height: auto;
  display: block;
}

.doc-org-name {
  font-size: 11pt;
  font-weight: 700;
  line-height: 1.15;
  color: #0f172a;
  margin: 0;
}

.doc-org-meta {
  font-size: 8pt;
  color: var(--muted);
  line-height: 1.3;
  margin: 0.4mm 0 0 0;
}
"""

DEFAULT_FOOTER_CSS = r"""
.footer-shell {
  width: var(--printable-width);
  box-sizing: border-box;
  margin: 0 auto;
  padding: 2.5mm 0 0 0;
}

.doc-footer {
  width: 100%;
  display: table;
  table-layout: fixed;
  border-top: 1px solid var(--border);
  color: var(--muted);
  font-size: 8.2pt;
  padding-top: 2mm;
}

.doc-footer__left,
.doc-footer__center,
.doc-footer__right {
  display: table-cell;
  vertical-align: top;
}

.doc-footer__left {
  text-align: left;
}

.doc-footer__center {
  text-align: center;
}

.doc-footer__right {
  text-align: right;
}

.doc-footer__label {
  font-size: 7.2pt;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: #94a3b8;
  margin: 0 0 0.8mm 0;
}

.doc-footer__value {
  font-size: 8.3pt;
  color: var(--muted);
  line-height: 1.3;
}
"""

DEFAULT_BODY_CSS = r"""
.document-body {
  padding: 15px;
  width: 100%;
  box-sizing: border-box;
}

h1, h2, h3, h4, h5, h6 {
  color: #111827;
  line-height: 1.25;
  margin-top: 1.35em;
  margin-bottom: 0.55em;
  page-break-after: avoid;
  break-after: avoid;
}

h1 {
  font-size: 24pt;
  border-bottom: 2px solid var(--border);
  padding-bottom: 0.2em;
  margin-top: 0;
}

h2 {
  font-size: 18pt;
  border-bottom: 1px solid var(--border);
  padding-bottom: 0.15em;
}

h3 {
  font-size: 15pt;
}

h4 {
  font-size: 13pt;
}

p {
  margin: 0.8em 0;
  line-height: 1.65;
}

ul, ol {
  margin: 0.8em 0 0.8em 1.4em;
  padding: 0;
}

li {
  margin: 0.25em 0;
}

blockquote {
  margin: 1em 0;
  padding: 0.2em 0 0.2em 1em;
  border-left: 4px solid #d1d5db;
  color: var(--quote);
  background: #fcfcfd;
}

hr {
  border: none;
  border-top: 1px solid var(--border);
  margin: 1.6em 0;
}

a {
  color: var(--link);
  text-decoration: none;
  word-break: break-word;
}

code {
  font-family: "Cascadia Code", "Fira Code", Consolas, monospace;
  font-size: 0.92em;
  background: var(--soft-2);
  border-radius: 4px;
  padding: 0.14em 0.36em;
  white-space: break-spaces;
}

pre {
  background: var(--code-bg);
  color: var(--code-fg);
  border-radius: 10px;
  padding: 14px 16px;
  overflow: hidden;
  white-space: pre-wrap;
  word-break: break-word;
  page-break-inside: avoid;
  break-inside: avoid;
  margin: 1em 0;
}

pre code {
  background: transparent;
  color: inherit;
  padding: 0;
  border-radius: 0;
  font-size: 0.9em;
}

table {
  width: 100%;
  border-collapse: collapse;
  margin: 1em 0;
  font-size: 10.3pt;
}

th, td {
  border: 1px solid var(--border);
  padding: 8px 10px;
  text-align: left;
  vertical-align: top;
}

th {
  background: var(--soft);
  font-weight: 600;
}

tr:nth-child(even) td {
  background: #fcfcfc;
}

.mermaid-diagram {
  margin: 1.25em 0;
  text-align: center;
  page-break-inside: avoid;
  break-inside: avoid;
  border: 1px solid var(--border);
  border-radius: 10px;
  background: white;
  padding: 0;
  overflow: hidden;
}

.mermaid-diagram img {
  max-width: 100%;
  height: auto;
  display: block;
  margin: 0 auto;
}

.mermaid-error {
  border: 1px solid #fca5a5;
  background: #fef2f2;
  border-radius: 10px;
  padding: 12px;
  margin: 1em 0;
  page-break-inside: avoid;
  break-inside: avoid;
}

.mermaid-error-title {
  font-weight: 700;
  margin-bottom: 0.4em;
  color: #991b1b;
}

.mermaid-error-details {
  margin-bottom: 0.8em;
  color: #7f1d1d;
  font-size: 0.95em;
  white-space: pre-wrap;
}

.toc {
  background: var(--soft);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 12px 14px;
  margin: 1em 0 1.5em 0;
}

.toc ul {
  margin: 0.5em 0 0 1.2em;
}

.admonition {
  border: 1px solid var(--border);
  border-left: 4px solid #60a5fa;
  background: #f8fbff;
  border-radius: 8px;
  padding: 10px 12px;
  margin: 1em 0;
  page-break-inside: avoid;
  break-inside: avoid;
}

.admonition-title {
  font-weight: 700;
  margin-bottom: 0.4em;
}
"""


class Action:
    class Valves(BaseModel):
        filename_prefix: str = Field(
            default="message",
            description="File name prefix used for the downloaded PDF.",
        )

        page_size: str = Field(
            default="A4",
            description="PDF page size, for example A4 or Letter.",
        )

        margin_mm: int = Field(
            default=5,
            description="Base page margin in millimeters. Header and footer heights are added on top of this margin.",
        )

        first_header_height_mm: int = Field(
            default=28,
            description="Reserved height in millimeters for the first page header. Increase this if the first header is taller.",
        )

        other_header_height_mm: int = Field(
            default=20,
            description="Reserved height in millimeters for headers on pages after the first page. If left smaller than the actual header, overlap can happen.",
        )

        footer_height_mm: int = Field(
            default=18,
            description="Reserved height in millimeters for the repeating footer.",
        )

        show_page_numbers: bool = Field(
            default=False,
            description="If enabled, page numbers are available as the {{ page_number }} placeholder. Keep this off if you do not want page numbers.",
        )

        mermaid_scale: int = Field(
            default=2,
            description="Rasterization scale used when converting rendered Mermaid diagrams from the browser into PNG images.",
        )

        max_mermaid_width_px: int = Field(
            default=900,
            description="Maximum display width for Mermaid diagrams in the PDF. Larger diagrams are scaled down proportionally.",
        )

        max_mermaid_height_px: int = Field(
            default=500,
            description="Maximum display height for Mermaid diagrams in the PDF. Taller diagrams are scaled down proportionally.",
        )

        global_css: str = Field(
            default=DEFAULT_GLOBAL_CSS,
            description="Shared CSS loaded for the whole document. Put variables, resets, shared utility classes, and general layout helpers here.",
        )

        first_header_html: str = Field(
            default=DEFAULT_FIRST_HEADER_HTML,
            description="HTML fragment for the first page header. This can contain logos, branding, address blocks, and any static markup. Placeholders like {{ export_title }} and {{ export_date }} are supported.",
        )
        first_header_css: str = Field(
            default=DEFAULT_FIRST_HEADER_CSS,
            description="CSS applied to the first page header only.",
        )

        other_header_html: str = Field(
            default=DEFAULT_OTHER_HEADER_HTML,
            description="HTML fragment for headers on pages after the first page. If left empty, the first page header HTML is reused.",
        )
        other_header_css: str = Field(
            default=DEFAULT_OTHER_HEADER_CSS,
            description="CSS applied to headers on pages after the first page. If left empty, the first header CSS is reused.",
        )

        footer_html: str = Field(
            default=DEFAULT_FOOTER_HTML,
            description="HTML fragment for the repeating footer. Placeholders like {{ page_number }}, {{ export_date }}, and {{ message_id }} are supported.",
        )
        footer_css: str = Field(
            default=DEFAULT_FOOTER_CSS,
            description="CSS applied to the repeating footer only.",
        )

        body_html_template: str = Field(
            default=DEFAULT_BODY_HTML_TEMPLATE,
            description="HTML template for the document body. It must include {{ body_content }} where the rendered markdown should be inserted.",
        )
        body_css: str = Field(
            default=DEFAULT_BODY_CSS,
            description="CSS applied to the body content area only.",
        )

    def __init__(self):
        self.valves = self.Valves()

    def build_filename(self, message_id: str) -> str:
        return f"{self.valves.filename_prefix}-{message_id}.pdf"

    def sanitize_filename(self, value: str) -> str:
        value = (value or "").strip()

        if not value:
            return ""

        value = re.sub(r'[<>:"/\\\\|?*\\x00-\\x1F]+', "-", value)
        value = re.sub(r"\\s+", " ", value).strip()
        value = value.rstrip(". ")

        return value[:180]

    async def prompt_filename(
        self,
        message_id: str,
        __event_call__=None,
    ) -> str:
        fallback = self.build_filename(message_id)

        if __event_call__ is None:
            return fallback

        response = await __event_call__(
            {
                "type": "input",
                "data": {
                    "title": "Save PDF",
                    "message": "Choose a file name for the exported PDF.",
                    "placeholder": fallback,
                },
            }
        )

        value = ""
        if isinstance(response, dict):
            value = response.get("value", "") or ""

        value = self.sanitize_filename(value)

        if not value:
            return fallback

        if not value.lower().endswith(".pdf"):
            value += ".pdf"

        return value

    def get_page_width_mm(self) -> float:
        page = (self.valves.page_size or "").strip().upper()

        known = {
            "A4": 210.0,
            "A3": 297.0,
            "A5": 148.0,
            "LETTER": 215.9,
            "LEGAL": 215.9,
        }

        return known.get(page, 210.0)

    def _normalize_content(self, content: Any) -> str:
        if content is None:
            return ""
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if not isinstance(item, dict):
                    continue
                if item.get("type") == "text":
                    parts.append(item.get("text", ""))
                elif isinstance(item.get("content"), str):
                    parts.append(item.get("content"))
            return "\n".join(part for part in parts if part)
        return str(content)

    def get_message_content(self, body: dict) -> str:
        target_id = body.get("id")
        messages = body.get("messages", []) or []

        if target_id:
            for message in messages:
                if not isinstance(message, dict):
                    continue

                candidate_ids = [
                    message.get("id"),
                    message.get("message_id"),
                    (
                        (message.get("info") or {}).get("id")
                        if isinstance(message.get("info"), dict)
                        else None
                    ),
                    (
                        (message.get("meta") or {}).get("id")
                        if isinstance(message.get("meta"), dict)
                        else None
                    ),
                ]

                if target_id in candidate_ids and message.get("role") == "assistant":
                    return self._normalize_content(message.get("content"))

        for message in reversed(messages):
            if isinstance(message, dict) and message.get("role") == "assistant":
                return self._normalize_content(message.get("content"))

        return ""

    def build_extract_mermaid_png_js(self, message_id: str) -> str:
        scale = self.valves.mermaid_scale
        return f"""
const messageId = {json.dumps(message_id)};
const exportScale = {scale};

function findMessageElement(id) {{
  const selectors = [
    `#message-${{CSS.escape(id)}}`,
    `#${{CSS.escape(id)}}`,
    `[data-message-id="${{id}}"]`,
    `[data-id="${{id}}"]`,
    `.message-${{CSS.escape(id)}}`
  ];
  for (const selector of selectors) {{
    const el = document.querySelector(selector);
    if (el) return el;
  }}
  return null;
}}

function sleep(ms) {{
  return new Promise(resolve => setTimeout(resolve, ms));
}}

async function loadHtml2Canvas() {{
  if (typeof window.html2canvas === "function") return;

  await new Promise((resolve, reject) => {{
    const existing = document.querySelector('script[data-openwebui-mermaid-export="html2canvas-pro"]');
    if (existing) {{
      existing.addEventListener("load", () => resolve(), {{ once: true }});
      existing.addEventListener("error", () => reject(new Error("Failed to load html2canvas-pro")), {{ once: true }});
      return;
    }}

    const script = document.createElement("script");
    script.src = "https://cdn.jsdelivr.net/npm/html2canvas-pro@1.5.12/dist/html2canvas-pro.min.js";
    script.async = true;
    script.dataset.openwebuiMermaidExport = "html2canvas-pro";
    script.onload = () => resolve();
    script.onerror = () => reject(new Error("Failed to load html2canvas-pro"));
    document.head.appendChild(script);
  }});

  if (typeof window.html2canvas !== "function") {{
    throw new Error("html2canvas-pro loaded but window.html2canvas is unavailable.");
  }}
}}

async function waitForImages(root, timeoutMs = 10000) {{
  const images = Array.from(root.querySelectorAll("img"));
  if (!images.length) return;

  await Promise.race([
    Promise.all(images.map(img => {{
      if (img.complete) return Promise.resolve();
      return new Promise(resolve => {{
        const done = () => resolve();
        img.addEventListener("load", done, {{ once: true }});
        img.addEventListener("error", done, {{ once: true }});
      }});
    }})),
    sleep(timeoutMs)
  ]);
}}

const root = findMessageElement(messageId);
if (!root) {{
  throw new Error(`Could not find message element for message id: ${{messageId}}`);
}}

await loadHtml2Canvas();

const diagramElements = Array.from(
  root.querySelectorAll("svg[id^='mermaid-'], svg.flowchart")
);

const diagrams = [];

for (let index = 0; index < diagramElements.length; index++) {{
  const svg = diagramElements[index];

  const tempRoot = document.createElement("div");
  tempRoot.style.position = "fixed";
  tempRoot.style.left = "-100000px";
  tempRoot.style.top = "0";
  tempRoot.style.background = "#ffffff";
  tempRoot.style.padding = "0";
  tempRoot.style.margin = "0";
  tempRoot.style.zIndex = "-1";
  tempRoot.style.display = "inline-block";
  tempRoot.style.boxSizing = "border-box";

  const clone = svg.cloneNode(true);
  clone.removeAttribute("width");
  clone.removeAttribute("height");
  clone.style.display = "block";
  clone.style.margin = "0";
  clone.style.background = "#ffffff";

  const viewBox = svg.getAttribute("viewBox");
  if (viewBox) {{
    const parts = viewBox.trim().split(/\\s+/).map(Number);
    if (parts.length === 4 && Number.isFinite(parts[2]) && Number.isFinite(parts[3])) {{
      clone.setAttribute("width", String(parts[2]));
      clone.setAttribute("height", String(parts[3]));
      tempRoot.style.width = `${{parts[2]}}px`;
      tempRoot.style.height = `${{parts[3]}}px`;
    }}
  }}

  tempRoot.appendChild(clone);
  document.body.appendChild(tempRoot);

  try {{
    await waitForImages(tempRoot, 5000);
    await sleep(150);

    const canvas = await window.html2canvas(tempRoot, {{
      scale: exportScale,
      useCORS: true,
      backgroundColor: "#ffffff",
      logging: false,
      allowTaint: false,
      foreignObjectRendering: false
    }});

    const png = canvas.toDataURL("image/png");

    diagrams.push({{
      index,
      id: svg.id || null,
      png,
      width: canvas.width,
      height: canvas.height
    }});
  }} finally {{
    tempRoot.remove();
  }}
}}

return {{
  success: true,
  messageId,
  diagramCount: diagrams.length,
  diagrams
}};
"""

    def scale_dimensions(
        self,
        width: int,
        height: int,
        max_width: int,
        max_height: int,
    ) -> tuple[int, int]:
        if width <= 0 or height <= 0:
            return max_width, max_height

        ratio = min(
            1.0,
            max_width / width if max_width > 0 else 1.0,
            max_height / height if max_height > 0 else 1.0,
        )

        new_width = max(1, int(round(width * ratio)))
        new_height = max(1, int(round(height * ratio)))
        return new_width, new_height

    def replace_mermaid_blocks_with_png(
        self,
        markdown_text: str,
        diagrams: list[dict],
        extract_error: Optional[str] = None,
    ) -> str:
        pattern = re.compile(
            r"```mermaid[ \t]*\n(.*?)\n```",
            flags=re.IGNORECASE | re.DOTALL,
        )

        diagram_iter = iter(diagrams)

        def repl(match: re.Match) -> str:
            mermaid_code = match.group(1).strip()

            try:
                item = next(diagram_iter)
                png = item.get("png", "")
                width = int(item.get("width", 0) or 0)
                height = int(item.get("height", 0) or 0)

                if not png.startswith("data:image/png;base64,"):
                    raise ValueError("Invalid PNG payload")

                scaled_width, scaled_height = self.scale_dimensions(
                    width=width,
                    height=height,
                    max_width=self.valves.max_mermaid_width_px,
                    max_height=self.valves.max_mermaid_height_px,
                )

                return (
                    '\n<div class="mermaid-diagram">'
                    f'<img src="{html.escape(png, quote=True)}" '
                    f'alt="Mermaid diagram" '
                    f'width="{scaled_width}" '
                    f'height="{scaled_height}" '
                    f'style="width:{scaled_width}px;height:{scaled_height}px;">'
                    "</div>\n"
                )

            except Exception as e:
                escaped = html.escape(mermaid_code)
                details = html.escape(extract_error or str(e))
                return (
                    '\n<div class="mermaid-error">'
                    '<div class="mermaid-error-title">Mermaid diagram could not be embedded</div>'
                    f'<div class="mermaid-error-details">{details}</div>'
                    f'<pre><code class="language-mermaid">{escaped}</code></pre>'
                    "</div>\n"
                )

        return pattern.sub(repl, markdown_text)

    def render_template(self, template: str, context: dict[str, str]) -> str:
        result = template or ""
        for key, value in context.items():
            result = result.replace(f"{{{{ {key} }}}}", value)
            result = result.replace(f"{{{{{key}}}}}", value)
        return result

    def build_html_document(
        self, markdown_text: str, message_id: str, user_name: str = ""
    ) -> str:
        rendered_body_markdown = markdown.markdown(
            markdown_text,
            extensions=[
                "extra",
                "admonition",
                "attr_list",
                "tables",
                "fenced_code",
                "sane_lists",
                "toc",
                "nl2br",
            ],
            output_format="html5",
        )

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        page_number_text = (
            "Page counter(page) / counter(pages)"
            if self.valves.show_page_numbers
            else ""
        )

        context = {
            "body_content": rendered_body_markdown,
            "message_id": html.escape(message_id),
            "export_title": "Assistant Message Export",
            "export_date": html.escape(now_str),
            "page_number": html.escape(page_number_text),
            "page": "counter(page)",
            "pages": "counter(pages)",
            "user_name": html.escape(user_name),
        }

        first_header_html = self.render_template(self.valves.first_header_html, context)
        other_header_html_raw = (
            self.valves.other_header_html or ""
        ).strip() or self.valves.first_header_html
        other_header_html = self.render_template(other_header_html_raw, context)
        footer_html = self.render_template(self.valves.footer_html, context)
        body_html = self.render_template(self.valves.body_html_template, context)

        other_header_css = (
            self.valves.other_header_css or ""
        ).strip() or self.valves.first_header_css

        margin = self.valves.margin_mm
        first_header_h = self.valves.first_header_height_mm
        other_header_h = self.valves.other_header_height_mm
        footer_h = self.valves.footer_height_mm

        page_width_mm = self.get_page_width_mm()
        printable_width_mm = max(10.0, page_width_mm - (2 * margin))

        return f"""<!doctype html>
    <html>
    <head>
      <meta charset="utf-8">
      <title>Assistant Message Export</title>
      <style>
        @page {{
          size: {self.valves.page_size};
          margin:
            {margin + other_header_h}mm
            {margin}mm
            {margin + footer_h}mm
            {margin}mm;
    
          @top-center {{
            content: element(pdf-other-header);
          }}
    
          @bottom-center {{
            content: element(pdf-footer);
          }}
        }}
    
        @page:first {{
          margin:
            {margin + first_header_h}mm
            {margin}mm
            {margin + footer_h}mm
            {margin}mm;
    
          @top-center {{
            content: element(pdf-first-header);
          }}
    
          @bottom-center {{
            content: element(pdf-footer);
          }}
        }}
    
        :root {{
          --page-width-mm: {page_width_mm}mm;
          --base-margin-mm: {margin}mm;
          --printable-width: {printable_width_mm}mm;
        }}
    
        #pdf-first-header {{
          position: running(pdf-first-header);
          width: var(--printable-width);
          margin: 0 auto;
          box-sizing: border-box;
        }}
    
        #pdf-other-header {{
          position: running(pdf-other-header);
          width: var(--printable-width);
          margin: 0 auto;
          box-sizing: border-box;
        }}
    
        #pdf-footer {{
          position: running(pdf-footer);
          width: var(--printable-width);
          margin: 0 auto;
          box-sizing: border-box;
        }}
    
    {self.valves.global_css}
    
        .page-number::after {{
          content: "Page " counter(page) " / " counter(pages);
        }}
    
    {self.valves.first_header_css}
    
    {other_header_css}
    
    {self.valves.footer_css}
    
    {self.valves.body_css}
      </style>
    </head>
    <body>
      <div id="pdf-first-header">
        {first_header_html}
      </div>
    
      <div id="pdf-other-header">
        {other_header_html}
      </div>
    
      <div id="pdf-footer">
        {footer_html}
      </div>
    
      <main id="pdf-body">
        {body_html}
      </main>
    </body>
    </html>
    """

    def md_to_pdf(
        self, markdown_text: str, message_id: str, user_name: str = ""
    ) -> bytes:
        html_doc = self.build_html_document(
            markdown_text, message_id, user_name=user_name
        )
        return HTML(string=html_doc).write_pdf()

    async def download_file(
        self,
        pdf_bytes: bytes,
        filename: str,
        __event_emitter__=None,
        __event_call__=None,
    ):
        encoded = base64.b64encode(pdf_bytes).decode("ascii")

        js_code = f"""
const base64 = {json.dumps(encoded)};
const filename = {json.dumps(filename)};
const binary = atob(base64);
const bytes = new Uint8Array(binary.length);

for (let i = 0; i < binary.length; i++) {{
  bytes[i] = binary.charCodeAt(i);
}}

const blob = new Blob([bytes], {{ type: "application/pdf" }});
const url = URL.createObjectURL(blob);

try {{
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.style.display = "none";
  document.body.appendChild(a);
  a.click();
  a.remove();
}} finally {{
  setTimeout(() => URL.revokeObjectURL(url), 4000);
}}

return {{ success: true, filename, size: bytes.length }};
"""

        payload = {"type": "execute", "data": {"code": js_code}}

        if __event_call__ is not None:
            return await __event_call__(payload)

        if __event_emitter__ is not None:
            await __event_emitter__(payload)
            return {"success": True, "filename": filename, "size": len(pdf_bytes)}

        return None

    async def action(
        self,
        body: dict,
        __user__=None,
        __event_emitter__=None,
        __event_call__=None,
        **kwargs,
    ):
        message_id = body.get("id")
        if not message_id:
            return {
                "content": "Could not determine the current message id from body['id']."
            }

        if __event_emitter__:
            await __event_emitter__(
                {
                    "type": "status",
                    "data": {
                        "description": "Reading message content...",
                        "done": False,
                    },
                }
            )

        markdown_text = self.get_message_content(body)
        if not markdown_text.strip():
            if __event_emitter__:
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {
                            "description": "No assistant message content found.",
                            "done": True,
                        },
                    }
                )
            return {"content": "No assistant message content found."}

        if __event_emitter__:
            await __event_emitter__(
                {
                    "type": "status",
                    "data": {
                        "description": "Collecting rendered Mermaid diagrams...",
                        "done": False,
                    },
                }
            )

        diagrams = []
        extract_result = None
        extract_error = None

        try:
            if __event_call__ is None:
                raise RuntimeError(
                    "This action needs __event_call__ so browser JS can return Mermaid image data."
                )

            extract_js = self.build_extract_mermaid_png_js(message_id)
            extract_result = await __event_call__(
                {
                    "type": "execute",
                    "data": {"code": extract_js},
                }
            )

            if not isinstance(extract_result, dict):
                raise RuntimeError(
                    f"Unexpected execute result type: {type(extract_result).__name__}"
                )

            diagrams = extract_result.get("diagrams", []) or []

        except Exception as e:
            extract_error = str(e)
            diagrams = []

        merged_markdown = self.replace_mermaid_blocks_with_png(
            markdown_text,
            diagrams,
            extract_error=extract_error,
        )

        if __event_emitter__:
            await __event_emitter__(
                {
                    "type": "status",
                    "data": {"description": "Generating PDF...", "done": False},
                }
            )

        try:
            user_name = ""
            if isinstance(__user__, dict):
                user_name = (__user__.get("name") or "").strip()

            pdf_bytes = self.md_to_pdf(
                merged_markdown,
                message_id=message_id,
                user_name=user_name,
            )
        except Exception as e:
            if __event_emitter__:
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {"description": "PDF generation failed.", "done": True},
                    }
                )
            return {
                "content": f"PDF generation failed: {e}",
                "mermaid_extract_result": extract_result,
                "mermaid_extract_error": extract_error,
            }

        filename = await self.prompt_filename(
            message_id=message_id,
            __event_call__=__event_call__,
        )

        if __event_emitter__:
            await __event_emitter__(
                {
                    "type": "status",
                    "data": {"description": "Starting download...", "done": False},
                }
            )

        result = await self.download_file(
            pdf_bytes=pdf_bytes,
            filename=filename,
            __event_emitter__=__event_emitter__,
            __event_call__=__event_call__,
        )

        if __event_emitter__:
            await __event_emitter__(
                {
                    "type": "status",
                    "data": {"description": "PDF export complete.", "done": True},
                }
            )

        return {
            "content": f"Exported message to PDF: {filename}",
            "result": result,
            "mermaid_diagrams_embedded": len(diagrams),
            "mermaid_extract_result": extract_result,
            "mermaid_extract_error": extract_error,
        }
