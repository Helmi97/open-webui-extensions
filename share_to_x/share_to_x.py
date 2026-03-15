"""
title: Share to X
author: Helmi Chaouachi
git_url: https://github.com/Helmi97/open-webui-extensions/tree/main/share_to_x
version: 1.0.0
required_open_webui_version: 0.5.0
description: Opens the X compose popup with content from the current assistant message.
icon_url: https://upload.wikimedia.org/wikipedia/commons/c/ce/X_logo_2023.svg
"""

from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote, urlencode

from pydantic import BaseModel, Field

from open_webui.models.users import UserModel
from open_webui.utils.chat import generate_chat_completion

LOGGER = logging.getLogger(__name__)

MIN_SHARE_GENERATION_MAX_TOKENS = 256
X_POPUP_NAME = "x_share_popup"
X_POPUP_FEATURES = "popup=yes,width=1100,height=900,resizable=yes,scrollbars=yes"
HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s*(.+?)\s*$")
CHECKBOX_RE = re.compile(r"^\s*[-*+]\s+\[[ xX]\]\s+(.*)$")
BULLET_RE = re.compile(r"^\s*[-*+]\s+(.*)$")
NUMBERED_RE = re.compile(r"^\s*(\d+)[.)]\s+(.*)$")
QUOTE_RE = re.compile(r"^\s*(>+)\s*(.*)$")
MARKDOWN_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")
INLINE_CODE_RE = re.compile(r"`([^`]+)`")
BOLD_RE = re.compile(r"\*\*(.*?)\*\*")
DOUBLE_UNDERSCORE_RE = re.compile(r"__(.*?)__")
ITALIC_STAR_RE = re.compile(r"(?<!\*)\*([^*]+)\*(?!\*)")
ITALIC_UNDERSCORE_RE = re.compile(r"(?<!_)_([^_]+)_(?!_)")
STRIKETHROUGH_RE = re.compile(r"~~(.*?)~~")
CODE_FENCE_START_RE = re.compile(r"^```(?:[a-zA-Z0-9_-]+)?\s*")
CODE_FENCE_END_RE = re.compile(r"\s*```$")
JSON_BLOCK_RE = re.compile(r"\{.*\}", flags=re.DOTALL)
PLAIN_URL_RE = re.compile(r"https?://[^\s<>()]+", flags=re.IGNORECASE)
TRAILING_URL_PUNCTUATION = ".,!?;:)]}\"'"
HORIZONTAL_WHITESPACE_RE = re.compile(r"[ \t]+")
NON_HASHTAG_CHARS_RE = re.compile(r"[^\w]", flags=re.UNICODE)
INLINE_MARKDOWN_PATTERNS = (
    (INLINE_CODE_RE, r"\1"),
    (BOLD_RE, r"\1"),
    (DOUBLE_UNDERSCORE_RE, r"\1"),
    (ITALIC_STAR_RE, r"\1"),
    (ITALIC_UNDERSCORE_RE, r"\1"),
    (STRIKETHROUGH_RE, r"\1"),
)


@dataclass(slots=True)
class XShareDraft:
    text: str
    url: str
    hashtags: str
    via: str
    related: str
    text_source: str
    original_text_length: int
    truncated: bool


class Action:
    class Valves(BaseModel):
        debug: bool = Field(default=False, description="Enable verbose debug logging.")
        use_llm_share_generation: bool = Field(
            default=True,
            title="Use Share Generation",
            description=(
                "Use the LLM to generate X fields. When disabled, only the text "
                "field is prefilled from the assistant message."
            ),
        )
        share_model: str = Field(
            default="",
            title="Share Generation Model",
            description="Optional model ID for X share generation.",
        )
        share_generation_temperature: float = Field(
            default=0.2,
            ge=0.0,
            le=2.0,
            title="Share Generation Temperature",
            description="Temperature used for X share generation.",
        )
        share_generation_max_tokens: int = Field(
            default=512,
            ge=1,
            le=2048,
            title="Share Generation Max Tokens",
            description="Maximum tokens used for X share generation.",
        )
        share_generation_prompt: str = Field(
            default=(
                "You are preparing a draft for the X compose dialog from an assistant "
                "message. Return only valid JSON in this exact shape: "
                '{"text":"<plain-text post body>","url":"<single public url or empty>",'
                '"hashtags":["<tag1>","<tag2>"],"via":"<username without @ or empty>",'
                '"related":["<username1>","<username2>"]}. '
                "Preserve useful structure in plain text, including line breaks and "
                "bullets when helpful. Remove markdown emphasis, code fences, tables, "
                "and HTML. Hashtags must not include #. via and related must not include @."
            ),
            title="Share Generation Prompt",
            description="System prompt used for LLM X share generation.",
        )
        loading_notification_text: str = Field(
            default="Preparing the X share draft...",
            title="Loading Notification Text",
            description="Loading notification shown before opening the popup.",
        )
        success_notification_text: str = Field(
            default="The X share dialog is opening.",
            title="Success Notification Text",
            description="Success notification shown after the popup step succeeds.",
        )
        max_text_chars: int = Field(
            default=5000,
            ge=1,
            le=10000,
            description="Maximum number of characters placed into the X text field.",
        )
        priority: int = Field(default=0, description="Toolbar ordering priority.")

    def __init__(self) -> None:
        self.valves = self.Valves()

    def _preview(self, value: Any, limit: int = 200) -> str:
        text = value if isinstance(value, str) else str(value)
        text = text.replace("\r", "\\r").replace("\n", "\\n")
        return text if len(text) <= limit else f"{text[:limit]}...<truncated>"

    def _debug_log(self, message: str, **context: Any) -> None:
        if not self.valves.debug:
            return
        if not context:
            LOGGER.info("[share_to_x] %s", message)
            return
        rendered = []
        for key, value in context.items():
            try:
                rendered_value = json.dumps(value, default=str) if isinstance(value, (dict, list, tuple)) else str(value)
            except TypeError:
                rendered_value = str(value)
            rendered.append(f"{key}={self._preview(rendered_value)}")
        LOGGER.info("[share_to_x] %s | %s", message, "; ".join(rendered))

    async def _emit_notification(self, __event_emitter__, notification_type: str, content: str) -> None:
        if __event_emitter__ is None:
            return
        await __event_emitter__({"type": "notification", "data": {"type": notification_type, "content": content}})

    def _extract_text(self, value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            return value.strip()
        if isinstance(value, list):
            return "\n\n".join(text for item in value if (text := self._extract_text(item))).strip()
        if isinstance(value, dict):
            if value.get("type") in {"text", "input_text", "output_text"}:
                return self._extract_text(value.get("text"))
            for key in ("content", "text", "value"):
                if key in value:
                    return self._extract_text(value.get(key))
            return ""
        return str(value).strip()

    def _extract_message_text(self, body: dict) -> str:
        direct_text = self._extract_text(body.get("content"))
        if direct_text:
            return direct_text
        message = body.get("message")
        if isinstance(message, dict):
            message_text = self._extract_text(message.get("content"))
            if message_text:
                return message_text
        messages = body.get("messages")
        if isinstance(messages, list):
            for message in reversed(messages):
                if isinstance(message, dict) and message.get("role") == "assistant":
                    message_text = self._extract_text(message.get("content"))
                    if message_text:
                        return message_text
        history = body.get("history")
        if isinstance(history, dict):
            history_messages = history.get("messages", {})
            current_id = body.get("id") or history.get("currentId")
            if current_id and current_id in history_messages:
                message_text = self._extract_text(history_messages[current_id].get("content"))
                if message_text:
                    return message_text
            for message in reversed(list(history_messages.values())):
                if isinstance(message, dict) and message.get("role") == "assistant":
                    message_text = self._extract_text(message.get("content"))
                    if message_text:
                        return message_text
        return ""

    def _replace_markdown_links(self, text: str) -> str:
        def replacer(match: re.Match[str]) -> str:
            label = match.group(1).strip()
            url = match.group(2).strip()
            return url if not label or label == url else f"{label} ({url})"
        return MARKDOWN_LINK_RE.sub(replacer, text)

    def _strip_inline_markdown(self, text: str) -> str:
        cleaned = self._replace_markdown_links(text)
        for pattern, replacement in INLINE_MARKDOWN_PATTERNS:
            cleaned = pattern.sub(replacement, cleaned)
        return cleaned

    def _normalize_line(self, raw_line: str) -> str:
        stripped = raw_line.strip()
        if not stripped:
            return ""
        heading_match = HEADING_RE.match(stripped)
        if heading_match:
            stripped = heading_match.group(1)
        else:
            checkbox_match = CHECKBOX_RE.match(stripped)
            bullet_match = BULLET_RE.match(stripped)
            numbered_match = NUMBERED_RE.match(stripped)
            quote_match = QUOTE_RE.match(stripped)
            if checkbox_match:
                stripped = f"- {checkbox_match.group(1)}"
            elif bullet_match:
                stripped = f"- {bullet_match.group(1)}"
            elif numbered_match:
                stripped = f"{numbered_match.group(1)}. {numbered_match.group(2)}"
            elif quote_match:
                stripped = f"{quote_match.group(1)} {quote_match.group(2)}".rstrip()
        stripped = self._strip_inline_markdown(stripped)
        return HORIZONTAL_WHITESPACE_RE.sub(" ", stripped.strip(" \"'`*_~")).strip()

    def _normalize_text(self, text: str) -> str:
        cleaned = CODE_FENCE_START_RE.sub("", text.strip())
        cleaned = CODE_FENCE_END_RE.sub("", cleaned).replace("\r\n", "\n").replace("\r", "\n")
        normalized_lines: list[str] = []
        for raw_line in cleaned.split("\n"):
            line = self._normalize_line(raw_line)
            if line:
                normalized_lines.append(line)
            elif normalized_lines and normalized_lines[-1] != "":
                normalized_lines.append("")
        return "\n".join(normalized_lines).strip()

    def _clean_url_candidate(self, value: str) -> str:
        return value.strip().rstrip(TRAILING_URL_PUNCTUATION)

    def _normalize_url(self, value: Any) -> str:
        raw = self._extract_text(value)
        match = PLAIN_URL_RE.search(raw) if raw else None
        return self._clean_url_candidate(match.group(0)) if match else ""

    def _normalize_username(self, value: Any) -> str:
        raw = self._extract_text(value).strip().lstrip("@")
        if not raw:
            return ""
        return re.split(r"[\s,/?#]+", raw, maxsplit=1)[0].strip("@ ")

    def _normalize_hashtags(self, value: Any) -> str:
        raw_items = value if isinstance(value, list) else self._extract_text(value).split(",")
        tags: list[str] = []
        for item in raw_items:
            token = self._extract_text(item).lstrip("#").strip()
            cleaned = NON_HASHTAG_CHARS_RE.sub("", token)
            if cleaned and cleaned not in tags:
                tags.append(cleaned)
        return ",".join(tags)

    def _normalize_related(self, value: Any) -> str:
        raw_items = value if isinstance(value, list) else self._extract_text(value).split(",")
        usernames: list[str] = []
        for item in raw_items:
            username = self._normalize_username(item)
            if username and username not in usernames:
                usernames.append(username)
        return ",".join(usernames)

    def _extract_chat_completion_text(self, response: Any) -> str:
        if response is None:
            return ""
        if isinstance(response, dict):
            choices = response.get("choices")
            if isinstance(choices, list) and choices:
                message = choices[0].get("message", {})
                if isinstance(message, dict):
                    return self._extract_text(message.get("content"))
            if "content" in response:
                return self._extract_text(response.get("content"))
        response_body = getattr(response, "body", None)
        if response_body:
            try:
                payload = json.loads(response_body.decode("utf-8"))
            except Exception:
                return ""
            return self._extract_chat_completion_text(payload)
        return ""

    def _extract_share_content_from_text(self, text: str) -> dict[str, str]:
        raw = text.strip()
        if not raw:
            return {}
        candidates = [raw]
        unfenced = CODE_FENCE_START_RE.sub("", raw)
        unfenced = CODE_FENCE_END_RE.sub("", unfenced).strip()
        if unfenced and unfenced != raw:
            candidates.append(unfenced)
        json_match = JSON_BLOCK_RE.search(unfenced or raw)
        if json_match:
            candidates.append(json_match.group(0).strip())
        for candidate in candidates:
            try:
                parsed = json.loads(candidate)
            except Exception:
                continue
            if not isinstance(parsed, dict):
                continue
            normalized = {
                "text": self._normalize_text(self._extract_text(parsed.get("text"))),
                "url": self._normalize_url(parsed.get("url")),
                "hashtags": self._normalize_hashtags(parsed.get("hashtags", [])),
                "via": self._normalize_username(parsed.get("via")),
                "related": self._normalize_related(parsed.get("related", [])),
            }
            return {key: value for key, value in normalized.items() if value}
        return {}

    def _get_user_model(self, user_data: Any) -> UserModel | None:
        if isinstance(user_data, UserModel):
            return user_data
        if not isinstance(user_data, dict) or not user_data:
            return None
        try:
            return UserModel(**user_data)
        except Exception:
            timestamp = int(time.time())
            fallback = {
                "id": user_data.get("id", ""),
                "email": user_data.get("email", ""),
                "username": user_data.get("username"),
                "role": user_data.get("role", "user"),
                "name": user_data.get("name") or user_data.get("email") or "User",
                "last_active_at": user_data.get("last_active_at") or timestamp,
                "updated_at": user_data.get("updated_at") or timestamp,
                "created_at": user_data.get("created_at") or timestamp,
            }
            try:
                return UserModel(**fallback)
            except Exception:
                return None

    async def _generate_share_fields(self, message_text: str, body: dict, __request__, __user__, __model__) -> dict[str, str]:
        if __request__ is None or not self.valves.use_llm_share_generation:
            return {}
        generation_model = self.valves.share_model.strip() or body.get("model") or (__model__ or {}).get("id")
        user_model = self._get_user_model(__user__)
        if not generation_model or user_model is None:
            return {}
        payload = {
            "model": generation_model,
            "stream": False,
            "temperature": self.valves.share_generation_temperature,
            "max_tokens": max(self.valves.share_generation_max_tokens, MIN_SHARE_GENERATION_MAX_TOKENS),
            "messages": [
                {"role": "system", "content": self.valves.share_generation_prompt.strip()},
                {"role": "user", "content": f"Assistant message to convert into an X share draft:\n\n{message_text}"},
            ],
        }
        try:
            response = await generate_chat_completion(__request__, payload, user_model, bypass_system_prompt=True)
            return self._extract_share_content_from_text(self._extract_chat_completion_text(response))
        except Exception as exc:
            self._debug_log("LLM X share generation failed; falling back to text-only mode", error=str(exc))
            return {}

    def _truncate_text(self, text: str) -> tuple[str, int, bool]:
        original_length = len(text)
        truncated = original_length > self.valves.max_text_chars
        return text[: self.valves.max_text_chars].strip(), original_length, truncated

    async def _resolve_draft(self, message_text: str, body: dict, __request__, __user__, __model__) -> XShareDraft:
        generated = await self._generate_share_fields(message_text, body, __request__, __user__, __model__)
        text_source = "llm_normalized" if generated.get("text") else "assistant_message_normalized"
        text_value = self._normalize_text(generated.get("text", "") or message_text)
        text_value, original_length, truncated = self._truncate_text(text_value)
        if not self.valves.use_llm_share_generation:
            generated = {}
        return XShareDraft(
            text=text_value,
            url=generated.get("url", ""),
            hashtags=generated.get("hashtags", ""),
            via=generated.get("via", ""),
            related=generated.get("related", ""),
            text_source=text_source,
            original_text_length=original_length,
            truncated=truncated,
        )

    def _build_x_share_url(self, draft: XShareDraft) -> str:
        query_params = {key: value for key, value in {
            "text": draft.text,
            "url": draft.url,
            "hashtags": draft.hashtags,
            "via": draft.via,
            "related": draft.related,
        }.items() if value}
        query = urlencode(query_params, quote_via=quote)
        return f"https://twitter.com/intent/tweet?{query}" if query else "https://twitter.com/intent/tweet"

    def _build_execute_code(self, share_url: str, return_result: bool) -> str:
        popup_success = "return { ok: true, method: 'popup_window', popupBlocked: false, newTabBlocked: false, url };" if return_result else "return;"
        tab_success = "return { ok: true, method: 'new_tab', popupBlocked: true, newTabBlocked: false, url };" if return_result else "return;"
        blocked_result = "return { ok: false, method: 'blocked', popupBlocked: true, newTabBlocked: true, url };" if return_result else "return;"
        return "".join((
            f"const url = {json.dumps(share_url)};",
            "let popupWindow = null;",
            "try {",
            f"  popupWindow = window.open(url, '{X_POPUP_NAME}', '{X_POPUP_FEATURES}');",
            "} catch (e) {}",
            "if (popupWindow && !popupWindow.closed) { try { popupWindow.opener = null; popupWindow.focus(); } catch (e) {} ",
            popup_success,
            "}",
            "let newTab = null;",
            "try { newTab = window.open(url, '_blank'); } catch (e) {}",
            "if (newTab && !newTab.closed) { try { newTab.opener = null; newTab.focus(); } catch (e) {} ",
            tab_success,
            "}",
            blocked_result,
        ))

    async def _open_share_dialog(self, share_url: str, __event_call__, __event_emitter__) -> dict[str, Any]:
        if __event_call__ is not None:
            result = await __event_call__({"type": "execute", "data": {"code": self._build_execute_code(share_url, True)}})
            return result if isinstance(result, dict) else {"result": result}
        if __event_emitter__ is not None:
            await __event_emitter__({"type": "execute", "data": {"code": f"(() => {{ {self._build_execute_code(share_url, False)} }})();"}})
            return {"ok": True, "method": "event_emitter"}
        raise ValueError("No browser execute channel is available. __event_call__ and __event_emitter__ are both missing.")

    async def _handle_loading(self, __event_emitter__) -> None:
        await self._emit_notification(__event_emitter__, "info", self.valves.loading_notification_text)

    async def _handle_success(self, __event_emitter__) -> None:
        await self._emit_notification(__event_emitter__, "success", self.valves.success_notification_text)

    async def _handle_failure(self, exc: Exception, __event_emitter__) -> None:
        if self.valves.debug:
            LOGGER.exception("[share_to_x] Action failed")
        else:
            LOGGER.error("[share_to_x] Action failed: %s", exc)
        await self._emit_notification(__event_emitter__, "error", str(exc))

    async def action(self, body: dict, __event_emitter__=None, __event_call__=None, __user__=None, __request__=None, __model__=None) -> None:
        try:
            self._debug_log("Action invoked", body_keys=sorted(body.keys()), model=body.get("model"))
            message_text = self._extract_message_text(body)
            if not message_text:
                raise ValueError("No assistant message content was found.")
            draft = await self._resolve_draft(message_text, body, __request__, __user__, __model__)
            if not any((draft.text, draft.url, draft.hashtags, draft.via, draft.related)):
                raise ValueError("No shareable X content could be prepared.")
            await self._handle_loading(__event_emitter__)
            share_url = self._build_x_share_url(draft)
            execute_result = await self._open_share_dialog(share_url, __event_call__, __event_emitter__)
            self._debug_log(
                "Prepared X share draft",
                text_source=draft.text_source,
                original_text_length=draft.original_text_length,
                final_text_length=len(draft.text),
                truncated=draft.truncated,
                url=draft.url,
                hashtags=draft.hashtags,
                via=draft.via,
                related=draft.related,
                share_url=self._preview(share_url, 300),
                execute_result=execute_result,
            )
            if isinstance(execute_result, dict) and execute_result.get("ok") is False:
                raise ValueError("The browser blocked both popup and new-tab opening for X.")
            await self._handle_success(__event_emitter__)
        except Exception as exc:
            await self._handle_failure(exc, __event_emitter__)
