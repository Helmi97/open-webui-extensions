"""
title: Export to GMAIL
author: Helmi Chaouachi
git_url: https://github.com/Helmi97/open-webui-extensions/tree/main/export_to_gmail
version: 1.0.1
required_open_webui_version: 0.5.0
description: Opens a Gmail compose screen with the current assistant message.
icon_url: https://www.svgrepo.com/show/444193/brand-google-gmail.svg
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

MAX_SUBJECT_LENGTH = 72
MAX_SUBJECT_LENGTH_WITH_ELLIPSIS = 69
MIN_EMAIL_GENERATION_MAX_TOKENS = 256
MAILTO_RECIPIENT_SAFE_CHARS = "@,;+"
GMAIL_POPUP_NAME = "gmail_compose_popup"
GMAIL_POPUP_FEATURES = (
    "popup=yes,width=1100,height=900,resizable=yes,scrollbars=yes"
)

HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s*(.+?)\s*$")
CHECKBOX_RE = re.compile(r"^\s*[-*+]\s+\[[ xX]\]\s+(.*)$")
BULLET_RE = re.compile(r"^\s*[-*+]\s+(.*)$")
NUMBERED_RE = re.compile(r"^\s*(\d+)[.)]\s+(.*)$")
QUOTE_RE = re.compile(r"^\s*(>+)\s*(.*)$")
MARKDOWN_LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]+\)")
INLINE_CODE_RE = re.compile(r"`([^`]+)`")
BOLD_RE = re.compile(r"\*\*(.*?)\*\*")
DOUBLE_UNDERSCORE_RE = re.compile(r"__(.*?)__")
ITALIC_STAR_RE = re.compile(r"(?<!\*)\*([^*]+)\*(?!\*)")
ITALIC_UNDERSCORE_RE = re.compile(r"(?<!_)_([^_]+)_(?!_)")
STRIKETHROUGH_RE = re.compile(r"~~(.*?)~~")
LEADING_SUBJECT_LABEL_RE = re.compile(
    r"^\s*subject\s*:\s*",
    flags=re.IGNORECASE,
)
LEADING_BODY_LABEL_RE = re.compile(
    r"^\s*body\s*:\s*",
    flags=re.IGNORECASE,
)
CODE_FENCE_START_RE = re.compile(r"^```(?:[a-zA-Z0-9_-]+)?\s*")
CODE_FENCE_END_RE = re.compile(r"\s*```$")
JSON_BLOCK_RE = re.compile(r"\{.*\}", flags=re.DOTALL)
SUBJECT_LINE_RE = re.compile(
    r"^\s*subject\s*:\s*(.+)$",
    flags=re.IGNORECASE | re.MULTILINE,
)
BODY_LINE_RE = re.compile(
    r"^\s*body\s*:\s*(.*)$",
    flags=re.IGNORECASE | re.MULTILINE | re.DOTALL,
)
WHITESPACE_RE = re.compile(r"\s+")
HORIZONTAL_WHITESPACE_RE = re.compile(r"[ \t]+")

INLINE_MARKDOWN_PATTERNS = (
    (MARKDOWN_LINK_RE, r"\1"),
    (INLINE_CODE_RE, r"\1"),
    (BOLD_RE, r"\1"),
    (DOUBLE_UNDERSCORE_RE, r"\1"),
    (ITALIC_STAR_RE, r"\1"),
    (ITALIC_UNDERSCORE_RE, r"\1"),
    (STRIKETHROUGH_RE, r"\1"),
)


@dataclass(slots=True, frozen=True)
class PromptSpec:
    title: str
    message: str
    placeholder: str


@dataclass(slots=True)
class EmailRecipients:
    to: str = ""
    cc: str = ""
    bcc: str = ""


@dataclass(slots=True)
class EmailDraft:
    subject: str
    body: str
    body_source: str
    original_body_length: int
    truncated: bool


FIELD_PROMPTS: dict[str, PromptSpec] = {
    "to": PromptSpec(
        title="Email To",
        message="Enter the recipient email address.",
        placeholder="name@example.com",
    ),
    "cc": PromptSpec(
        title="Email CC",
        message="Enter CC recipients separated by commas.",
        placeholder="name@example.com, other@example.com",
    ),
    "bcc": PromptSpec(
        title="Email BCC",
        message="Enter BCC recipients separated by commas.",
        placeholder="name@example.com, other@example.com",
    ),
    "subject_empty": PromptSpec(
        title="Email Subject",
        message="Enter the email subject.",
        placeholder="Assistant message",
    ),
}


class Action:
    class Valves(BaseModel):
        debug: bool = Field(
            default=False,
            description="Enable verbose server-side debug logging for this action.",
        )
        gmail_account_path: str = Field(
            default="",
            description=(
                "Optional Gmail path selector such as u/0, u/name@example.com, "
                "or a/example.com. Leave empty to use the default Gmail account."
            ),
        )
        default_to: str = Field(
            default="",
            description="Optional recipient email address to prefill.",
        )
        default_cc: str = Field(
            default="",
            description="Optional CC recipients, separated by commas.",
        )
        default_bcc: str = Field(
            default="",
            description="Optional BCC recipients, separated by commas.",
        )
        subject_prefix: str = Field(
            default="",
            description="Prefix added to the generated email subject.",
        )
        default_subject: str = Field(
            default="Assistant message",
            description="Fallback subject when no message text is available.",
        )
        use_llm_email_generation: bool = Field(
            default=True,
            title="Use Email Generation",
            description=(
                "Use the LLM to generate the email subject and body. When disabled, "
                "the full assistant message is used as the body."
            ),
        )
        subject_model: str = Field(
            default="",
            title="Email Generation Model",
            description=(
                "Optional model ID to use for email subject/body generation. "
                "Defaults to the current chat model."
            ),
        )
        subject_generation_temperature: float = Field(
            default=0.2,
            ge=0.0,
            le=2.0,
            title="Email Generation Temperature",
            description=(
                "Temperature used when asking the LLM to generate the email "
                "subject/body."
            ),
        )
        subject_generation_max_tokens: int = Field(
            default=512,
            ge=1,
            le=2048,
            title="Email Generation Max Tokens",
            description=(
                "Maximum tokens used when asking the LLM to generate the email "
                "subject/body."
            ),
        )
        subject_generation_prompt: str = Field(
            default=(
                "You are preparing an email draft from an assistant message. "
                "Write a concise email subject and a clean, formatted plain-text "
                "email body that keeps only content suitable for sending. "
                "Remove any text that does not belong in an email. "
                "The subject must be a single plain-text line with no markdown or "
                "special formatting. "
                "The body should be formatted for readability using paragraphs, "
                "line breaks, and optional numbered or bulleted lists when useful. "
                "Do not use markdown emphasis, headings, code fences, tables, or "
                "HTML. "
                "Do not include labels outside the JSON keys. "
                "Return only valid JSON in this exact shape: "
                '{"subject":"<subject content, plain text>","body":"<body content, formatted>"}'
            ),
            title="Email Generation Prompt",
            description="System prompt used for LLM email subject/body generation.",
        )
        prompt_for_to_if_empty: bool = Field(
            default=True,
            title="Prompt For To If Empty",
            description="Ask for the To field when default_to is empty.",
        )
        prompt_for_cc_if_empty: bool = Field(
            default=False,
            title="Prompt For CC If Empty",
            description="Ask for the CC field when default_cc is empty.",
        )
        prompt_for_bcc_if_empty: bool = Field(
            default=False,
            title="Prompt For BCC If Empty",
            description="Ask for the BCC field when default_bcc is empty.",
        )
        prompt_for_subject_if_empty: bool = Field(
            default=False,
            title="Prompt For Subject If Empty",
            description=(
                "Ask for the subject when the generated or fallback subject is empty."
            ),
        )
        loading_notification_text: str = Field(
            default="Generating the email draft...",
            title="Loading Notification Text",
            description="Loading notification shown after the last prompt is completed.",
        )
        success_notification_text: str = Field(
            default="The email is being generated and will be shown soon.",
            title="Success Notification Text",
            description="Success notification shown after the action finishes.",
        )
        max_body_chars: int = Field(
            default=10000,
            ge=1,
            le=20000,
            description="Maximum number of message characters to place into the compose body.",
        )
        priority: int = Field(
            default=0,
            description="Lower values appear earlier in the action toolbar.",
        )

    def __init__(self) -> None:
        self.valves = self.Valves()

    def _preview(self, value: Any, limit: int = 200) -> str:
        text = value if isinstance(value, str) else str(value)
        text = text.replace("\r", "\\r").replace("\n", "\\n")
        if len(text) > limit:
            return f"{text[:limit]}...<truncated {len(text) - limit} chars>"
        return text

    def _debug_log(self, message: str, **context: Any) -> None:
        if not self.valves.debug:
            return

        if not context:
            LOGGER.info("[email_assistant_message] %s", message)
            return

        rendered_parts: list[str] = []
        for key, value in context.items():
            if isinstance(value, (dict, list, tuple)):
                try:
                    rendered = json.dumps(value, default=str)
                except TypeError:
                    rendered = str(value)
            else:
                rendered = str(value)
            rendered_parts.append(f"{key}={self._preview(rendered)}")

        LOGGER.info(
            "[email_assistant_message] %s | %s",
            message,
            "; ".join(rendered_parts),
        )

    async def _emit_notification(
        self,
        __event_emitter__,
        notification_type: str,
        content: str,
    ) -> None:
        if __event_emitter__ is None:
            return

        await __event_emitter__(
            {
                "type": "notification",
                "data": {
                    "type": notification_type,
                    "content": content,
                },
            }
        )

    def _extract_text(self, value: Any) -> str:
        if value is None:
            return ""

        if isinstance(value, str):
            return value.strip()

        if isinstance(value, list):
            return "\n\n".join(
                text for item in value if (text := self._extract_text(item))
            ).strip()

        if isinstance(value, dict):
            item_type = value.get("type")
            if item_type in {"text", "input_text", "output_text"}:
                return self._extract_text(value.get("text"))

            for key in ("content", "text", "value"):
                if key in value:
                    return self._extract_text(value.get(key))

            return ""

        return str(value).strip()

    def _log_selected_message(
        self,
        source: str,
        message_text: str,
        message_id: str | None = None,
    ) -> None:
        log_context: dict[str, Any] = {
            "length": len(message_text),
            "preview": self._preview(message_text),
        }
        if message_id:
            log_context["message_id"] = message_id
        self._debug_log(source, **log_context)

    def _extract_message_text(self, body: dict) -> str:
        direct_text = self._extract_text(body.get("content"))
        if direct_text:
            self._log_selected_message(
                "Selected assistant message from body.content",
                direct_text,
            )
            return direct_text

        message = body.get("message")
        if isinstance(message, dict):
            message_text = self._extract_text(message.get("content"))
            if message_text:
                self._log_selected_message(
                    "Selected assistant message from body.message.content",
                    message_text,
                    message.get("id"),
                )
                return message_text

        messages = body.get("messages")
        if isinstance(messages, list):
            self._debug_log(
                "Scanning body.messages for the latest assistant message",
                message_count=len(messages),
            )
            for message in reversed(messages):
                if not isinstance(message, dict) or message.get("role") != "assistant":
                    continue

                message_text = self._extract_text(message.get("content"))
                if message_text:
                    self._log_selected_message(
                        "Selected assistant message from body.messages",
                        message_text,
                        message.get("id"),
                    )
                    return message_text

        history = body.get("history")
        if isinstance(history, dict):
            history_messages = history.get("messages", {})
            current_id = body.get("id") or history.get("currentId")
            self._debug_log(
                "Scanning body.history for assistant message",
                history_message_count=len(history_messages),
                current_id=current_id,
            )

            if current_id and current_id in history_messages:
                current_message = history_messages[current_id]
                message_text = self._extract_text(current_message.get("content"))
                if message_text:
                    self._log_selected_message(
                        "Selected assistant message from body.history current message",
                        message_text,
                        str(current_id),
                    )
                    return message_text

            for message in reversed(list(history_messages.values())):
                if not isinstance(message, dict) or message.get("role") != "assistant":
                    continue

                message_text = self._extract_text(message.get("content"))
                if message_text:
                    self._log_selected_message(
                        "Selected assistant message from body.history fallback scan",
                        message_text,
                        message.get("id"),
                    )
                    return message_text

        self._debug_log(
            "No assistant message content found during extraction",
            body_keys=sorted(body.keys()),
        )
        return ""

    def _collapse_spaces(self, value: str) -> str:
        return WHITESPACE_RE.sub(" ", value).strip()

    def _truncate_subject(self, subject: str) -> str:
        if len(subject) <= MAX_SUBJECT_LENGTH:
            return subject
        return f"{subject[:MAX_SUBJECT_LENGTH_WITH_ELLIPSIS].rstrip()}..."

    def _strip_inline_markdown(self, text: str) -> str:
        cleaned = text
        for pattern, replacement in INLINE_MARKDOWN_PATTERNS:
            cleaned = pattern.sub(replacement, cleaned)
        return cleaned

    def _first_non_empty_line(self, text: str) -> str:
        return next((line.strip() for line in text.splitlines() if line.strip()), "")

    def _remove_subject_prefixes(self, value: str) -> str:
        cleaned = value

        heading_match = HEADING_RE.match(cleaned)
        if heading_match:
            return heading_match.group(1)

        checkbox_match = CHECKBOX_RE.match(cleaned)
        if checkbox_match:
            return checkbox_match.group(1)

        bullet_match = BULLET_RE.match(cleaned)
        if bullet_match:
            return bullet_match.group(1)

        numbered_match = NUMBERED_RE.match(cleaned)
        if numbered_match:
            return numbered_match.group(2)

        return cleaned

    def _build_subject(self, message_text: str) -> str:
        subject_core = (
            self._truncate_subject(
                self._collapse_spaces(self._first_non_empty_line(message_text))
            )
            or self.valves.default_subject.strip()
            or "Assistant message"
        )
        return self._apply_subject_prefix(subject_core)

    def _apply_subject_prefix(self, subject: str) -> str:
        cleaned_subject = subject.strip()
        prefix = self.valves.subject_prefix.strip()
        if prefix and not cleaned_subject.lower().startswith(f"{prefix.lower()}:"):
            return f"{prefix}: {cleaned_subject}"
        return cleaned_subject

    def _normalize_subject(self, subject: str) -> str:
        cleaned = LEADING_SUBJECT_LABEL_RE.sub("", subject.strip().strip("`\"'"))
        cleaned = self._first_non_empty_line(cleaned)
        cleaned = self._remove_subject_prefixes(cleaned)
        cleaned = self._strip_inline_markdown(cleaned)
        cleaned = cleaned.strip(" \"'`*_~")
        return self._truncate_subject(self._collapse_spaces(cleaned))

    def _normalize_body_line(self, raw_line: str) -> str:
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
        stripped = stripped.strip(" \"'`*_~")
        return HORIZONTAL_WHITESPACE_RE.sub(" ", stripped).strip()

    def _normalize_body(self, body: str) -> str:
        cleaned = body.strip()
        cleaned = CODE_FENCE_START_RE.sub("", cleaned)
        cleaned = CODE_FENCE_END_RE.sub("", cleaned)
        cleaned = LEADING_BODY_LABEL_RE.sub("", cleaned)
        cleaned = cleaned.replace("\r\n", "\n").replace("\r", "\n")

        normalized_lines: list[str] = []
        for raw_line in cleaned.split("\n"):
            normalized_line = self._normalize_body_line(raw_line)
            if normalized_line:
                normalized_lines.append(normalized_line)
            elif normalized_lines and normalized_lines[-1] != "":
                normalized_lines.append("")

        return "\n".join(normalized_lines).strip()

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

    def _iter_email_content_candidates(self, text: str):
        raw = text.strip()
        if not raw:
            return

        yield raw

        unfenced = CODE_FENCE_START_RE.sub("", raw)
        unfenced = CODE_FENCE_END_RE.sub("", unfenced).strip()
        if unfenced and unfenced != raw:
            yield unfenced

        json_match = JSON_BLOCK_RE.search(unfenced or raw)
        if json_match:
            yield json_match.group(0).strip()

    def _extract_email_content_from_text(self, text: str) -> dict[str, str]:
        raw = text.strip()
        if not raw:
            return {}

        # The model sometimes returns fenced JSON or label-style text instead of a clean object.
        for candidate in self._iter_email_content_candidates(raw):
            try:
                parsed = json.loads(candidate)
            except Exception:
                continue

            if not isinstance(parsed, dict):
                continue

            normalized: dict[str, str] = {}
            subject = self._normalize_subject(str(parsed.get("subject", "")))
            body = self._normalize_body(str(parsed.get("body", "")))
            if subject:
                normalized["subject"] = subject
            if body:
                normalized["body"] = body
            if normalized:
                return normalized

        fallback: dict[str, str] = {}
        subject_match = SUBJECT_LINE_RE.search(raw)
        body_match = BODY_LINE_RE.search(raw)

        if subject_match:
            subject = self._normalize_subject(subject_match.group(1))
            if subject:
                fallback["subject"] = subject

        if body_match:
            body = self._normalize_body(body_match.group(1))
            if body:
                fallback["body"] = body

        return fallback

    def _get_user_model(self, user_data: Any) -> UserModel | None:
        if isinstance(user_data, UserModel):
            return user_data

        if not isinstance(user_data, dict) or not user_data:
            self._debug_log(
                "Cannot build UserModel for email generation",
                user_type=type(user_data).__name__,
            )
            return None

        try:
            return UserModel(**user_data)
        except Exception:
            timestamp = int(time.time())
            fallback_user_data = {
                "id": user_data.get("id", ""),
                "email": user_data.get("email", ""),
                "username": user_data.get("username"),
                "role": user_data.get("role", "user"),
                "name": user_data.get("name") or user_data.get("email") or "User",
                "profile_image_url": user_data.get("profile_image_url"),
                "profile_banner_image_url": user_data.get("profile_banner_image_url"),
                "bio": user_data.get("bio"),
                "gender": user_data.get("gender"),
                "date_of_birth": user_data.get("date_of_birth"),
                "timezone": user_data.get("timezone"),
                "presence_state": user_data.get("presence_state"),
                "status_emoji": user_data.get("status_emoji"),
                "status_message": user_data.get("status_message"),
                "status_expires_at": user_data.get("status_expires_at"),
                "info": user_data.get("info"),
                "settings": user_data.get("settings"),
                "oauth": user_data.get("oauth"),
                "scim": user_data.get("scim"),
                "last_active_at": user_data.get("last_active_at") or timestamp,
                "updated_at": user_data.get("updated_at") or timestamp,
                "created_at": user_data.get("created_at") or timestamp,
            }

            try:
                user_model = UserModel(**fallback_user_data)
            except Exception as exc:
                self._debug_log(
                    "Failed to build UserModel for email generation",
                    error=str(exc),
                    user_keys=sorted(user_data.keys()),
                )
                return None

            self._debug_log(
                "Built fallback UserModel for email generation",
                user_id=user_model.id,
                role=user_model.role,
            )
            return user_model

    def _resolve_current_model_id(self, body: dict, __model__) -> str:
        return (
            body.get("model")
            or (__model__ or {}).get("id")
            or self.valves.subject_model.strip()
        )

    async def _generate_email_content_with_llm(
        self,
        message_text: str,
        current_model_id: str,
        __request__,
        __user__,
    ) -> dict[str, str]:
        if __request__ is None:
            self._debug_log(
                "Cannot use LLM for email generation because __request__ is unavailable"
            )
            return {}

        generation_model = self.valves.subject_model.strip() or current_model_id
        if not generation_model:
            self._debug_log(
                "Cannot use LLM for email generation because no model ID is available"
            )
            return {}

        user_model = self._get_user_model(__user__)
        if user_model is None:
            self._debug_log(
                "Cannot use LLM for email generation because UserModel could not be built"
            )
            return {}

        prompt = self.valves.subject_generation_prompt.strip()
        generation_max_tokens = max(
            self.valves.subject_generation_max_tokens,
            MIN_EMAIL_GENERATION_MAX_TOKENS,
        )
        payload = {
            "model": generation_model,
            "stream": False,
            "temperature": self.valves.subject_generation_temperature,
            "max_tokens": generation_max_tokens,
            "messages": [
                {"role": "system", "content": prompt},
                {
                    "role": "user",
                    "content": (
                        "Assistant message to convert into an email draft:\n\n"
                        f"{message_text}"
                    ),
                },
            ],
        }

        self._debug_log(
            "Requesting email subject/body from Open WebUI chat completion",
            generation_model=generation_model,
            temperature=self.valves.subject_generation_temperature,
            max_tokens=generation_max_tokens,
            prompt=self._preview(prompt, 240),
            message_preview=self._preview(message_text, 240),
        )

        try:
            response = await generate_chat_completion(
                __request__,
                payload,
                user_model,
                bypass_system_prompt=True,
            )
            raw_content = self._extract_chat_completion_text(response)
            email_content = self._extract_email_content_from_text(raw_content)
            if email_content.get("subject"):
                email_content["subject"] = self._apply_subject_prefix(
                    email_content["subject"]
                )

            self._debug_log(
                "Received email subject/body from Open WebUI chat completion",
                raw_content=self._preview(raw_content, 320),
                normalized_subject=email_content.get("subject", ""),
                normalized_body_preview=self._preview(
                    email_content.get("body", ""),
                    240,
                ),
            )
            return email_content
        except Exception as exc:
            self._debug_log(
                "LLM email generation failed; falling back to heuristic subject and raw body",
                error=str(exc),
                generation_model=generation_model,
            )
            return {}

    def _truncate_body(self, body: str) -> tuple[str, int, bool]:
        original_length = len(body)
        truncated = original_length > self.valves.max_body_chars
        return body[: self.valves.max_body_chars].strip(), original_length, truncated

    async def _prompt_for_text(
        self,
        prompt_key: str,
        current_value: str,
        field_name: str,
        __event_call__,
    ) -> str | None:
        if __event_call__ is None:
            self._debug_log(
                "Field prompt skipped because __event_call__ is unavailable",
                field=field_name,
            )
            return current_value.strip()

        prompt = FIELD_PROMPTS[prompt_key]
        prompted_value = await __event_call__(
            {
                "type": "input",
                "data": {
                    "title": prompt.title,
                    "message": prompt.message,
                    "placeholder": prompt.placeholder,
                    "value": current_value,
                },
            }
        )

        if prompted_value is None:
            self._debug_log(
                "Field prompt cancelled by the user",
                field=field_name,
            )
            return None

        final_value = prompted_value.strip() if isinstance(prompted_value, str) else ""
        self._debug_log(
            "Field prompt completed",
            field=field_name,
            value=final_value,
            value_length=len(final_value),
        )
        return final_value

    async def _resolve_recipients(
        self,
        __event_call__,
    ) -> EmailRecipients | None:
        recipients = EmailRecipients(
            to=self.valves.default_to.strip(),
            cc=self.valves.default_cc.strip(),
            bcc=self.valves.default_bcc.strip(),
        )

        self._debug_log(
            "Loaded email field defaults",
            default_to=recipients.to,
            default_cc=recipients.cc,
            default_bcc=recipients.bcc,
            prompt_for_to_if_empty=self.valves.prompt_for_to_if_empty,
            prompt_for_cc_if_empty=self.valves.prompt_for_cc_if_empty,
            prompt_for_bcc_if_empty=self.valves.prompt_for_bcc_if_empty,
            prompt_for_subject_if_empty=self.valves.prompt_for_subject_if_empty,
            use_llm_email_generation=self.valves.use_llm_email_generation,
        )

        if not recipients.to and self.valves.prompt_for_to_if_empty:
            recipients.to = await self._prompt_for_text(
                "to",
                recipients.to,
                "to",
                __event_call__,
            )
            if recipients.to is None:
                return None

        if not recipients.cc and self.valves.prompt_for_cc_if_empty:
            prompted_cc = await self._prompt_for_text(
                "cc",
                recipients.cc,
                "cc",
                __event_call__,
            )
            recipients.cc = prompted_cc or ""

        if not recipients.bcc and self.valves.prompt_for_bcc_if_empty:
            prompted_bcc = await self._prompt_for_text(
                "bcc",
                recipients.bcc,
                "bcc",
                __event_call__,
            )
            recipients.bcc = prompted_bcc or ""

        return recipients

    async def _resolve_draft(
        self,
        message_text: str,
        body: dict,
        __request__,
        __user__,
        __model__,
        __event_call__,
    ) -> EmailDraft:
        generated_email_content: dict[str, str] = {}

        if self.valves.use_llm_email_generation:
            current_model_id = self._resolve_current_model_id(body, __model__)
            self._debug_log(
                "Resolving email subject/body using Open WebUI chat completion",
                current_model_id=current_model_id,
                override_email_generation_model=self.valves.subject_model.strip(),
            )
            generated_email_content = await self._generate_email_content_with_llm(
                message_text,
                current_model_id,
                __request__,
                __user__,
            )
        else:
            self._debug_log(
                "LLM email generation disabled; using heuristic subject and raw assistant message body"
            )

        subject = generated_email_content.get("subject", "")
        if not subject and self.valves.prompt_for_subject_if_empty:
            prompted_subject = await self._prompt_for_text(
                "subject_empty",
                subject,
                "subject",
                __event_call__,
            )
            if isinstance(prompted_subject, str):
                subject = prompted_subject.strip()

        if not subject:
            subject = self._build_subject(message_text)
            self._debug_log(
                "Using heuristic subject fallback",
                subject=subject,
                subject_length=len(subject),
            )

        self._debug_log(
            "Generated initial subject",
            subject=subject,
            subject_length=len(subject),
        )

        body_source = (
            "llm_normalized"
            if generated_email_content.get("body")
            else "assistant_message_normalized"
        )
        body_text = self._normalize_body(
            generated_email_content.get("body", "") or message_text
        )
        body_text, original_body_length, truncated = self._truncate_body(body_text)

        self._debug_log(
            "Prepared final email body",
            source=body_source,
            original_length=original_body_length,
            final_length=len(body_text),
            truncated=truncated,
            max_body_chars=self.valves.max_body_chars,
            preview=self._preview(body_text),
        )

        return EmailDraft(
            subject=subject,
            body=body_text,
            body_source=body_source,
            original_body_length=original_body_length,
            truncated=truncated,
        )

    def _build_mailto_url(
        self,
        recipients: EmailRecipients,
        draft: EmailDraft,
    ) -> str:
        query_params: dict[str, str] = {}
        if draft.subject:
            query_params["subject"] = draft.subject
        if draft.body:
            query_params["body"] = draft.body
        if recipients.cc:
            query_params["cc"] = recipients.cc
        if recipients.bcc:
            query_params["bcc"] = recipients.bcc

        query = urlencode(query_params, quote_via=quote)
        encoded_recipient = quote(
            recipients.to.strip(),
            safe=MAILTO_RECIPIENT_SAFE_CHARS,
        )
        url = (
            f"mailto:{encoded_recipient}?{query}"
            if query
            else f"mailto:{encoded_recipient}"
        )

        self._debug_log(
            "Built mailto URL",
            recipient=recipients.to,
            cc=recipients.cc,
            bcc=recipients.bcc,
            subject=draft.subject,
            body_length=len(draft.body),
            query_keys=sorted(query_params.keys()),
            url_length=len(url),
            url_preview=self._preview(url, 300),
        )
        return url

    def _build_webmail_url(self, base_url: str, query_params: dict[str, str]) -> str:
        filtered_params = {key: value for key, value in query_params.items() if value}
        query = urlencode(filtered_params, quote_via=quote)
        url = f"{base_url}?{query}" if query else base_url

        self._debug_log(
            "Built webmail URL",
            base_url=base_url,
            query_keys=sorted(filtered_params.keys()),
            url_length=len(url),
            url_preview=self._preview(url, 300),
        )
        return url

    def _build_gmail_base_url(self) -> str:
        path = self.valves.gmail_account_path.strip().strip("/")
        if path:
            self._debug_log(
                "Using Gmail account path override",
                gmail_account_path=path,
            )
            return f"https://mail.google.com/mail/{path}/"

        self._debug_log("Using default Gmail account path", gmail_account_path="")
        return "https://mail.google.com/mail/"

    def _build_gmail_url(
        self,
        recipients: EmailRecipients,
        draft: EmailDraft,
    ) -> str:
        gmail_mailto = self._build_mailto_url(recipients, draft)

        self._debug_log(
            "Building Gmail compose URL",
            recipient=recipients.to,
            cc=recipients.cc,
            bcc=recipients.bcc,
            subject=draft.subject,
            body_length=len(draft.body),
            gmail_account_path=self.valves.gmail_account_path.strip(),
        )

        return self._build_webmail_url(
            self._build_gmail_base_url(),
            {
                "extsrc": "mailto",
                "url": gmail_mailto,
            },
        )

    def _build_gmail_execute_code(self, gmail_url: str, return_result: bool) -> str:
        # Keep the browser action in one synchronous block so popup/new-tab opening
        # still counts as user-triggered.
        popup_success = (
            "return { ok: true, method: 'popup_window', popupBlocked: false, newTabBlocked: false, url };"
            if return_result
            else "return;"
        )
        tab_success = (
            "return { ok: true, method: 'new_tab', popupBlocked: true, newTabBlocked: false, url };"
            if return_result
            else "return;"
        )
        blocked_result = (
            "return { ok: false, method: 'blocked', popupBlocked: true, newTabBlocked: true, url };"
            if return_result
            else "return;"
        )

        return "".join(
            (
                f"const url = {json.dumps(gmail_url)};",
                "let popupWindow = null;",
                "try {",
                f"  popupWindow = window.open(url, '{GMAIL_POPUP_NAME}', '{GMAIL_POPUP_FEATURES}');",
                "} catch (e) {}",
                "if (popupWindow && !popupWindow.closed) {",
                "  try { popupWindow.opener = null; popupWindow.focus(); } catch (e) {}",
                f"  {popup_success}",
                "}",
                "let newTab = null;",
                "try {",
                "  newTab = window.open(url, '_blank');",
                "} catch (e) {}",
                "if (newTab && !newTab.closed) {",
                "  try { newTab.opener = null; newTab.focus(); } catch (e) {}",
                f"  {tab_success}",
                "}",
                blocked_result,
            )
        )

    async def _open_gmail_compose(
        self,
        gmail_url: str,
        __event_call__,
        __event_emitter__,
    ) -> dict[str, Any]:
        if __event_call__ is not None:
            self._debug_log("Opening Gmail via __event_call__ execute")
            result = await __event_call__(
                {
                    "type": "execute",
                    "data": {
                        "code": self._build_gmail_execute_code(
                            gmail_url,
                            return_result=True,
                        ),
                    },
                }
            )
            self._debug_log(
                "Received __event_call__ execute result",
                result=result,
            )
            return result if isinstance(result, dict) else {"result": result}

        if __event_emitter__ is not None:
            self._debug_log(
                "Falling back to __event_emitter__ for execute because __event_call__ is unavailable"
            )
            await __event_emitter__(
                {
                    "type": "execute",
                    "data": {
                        "code": (
                            f"(() => {{ {self._build_gmail_execute_code(gmail_url, return_result=False)} }})();"
                        ),
                    },
                }
            )
            return {"ok": True, "method": "event_emitter"}

        raise ValueError(
            "No browser execute channel is available. __event_call__ and __event_emitter__ are both missing."
        )

    async def _handle_success(self, __event_emitter__) -> None:
        if __event_emitter__ is None:
            self._debug_log(
                "Action completed without __event_emitter__; browser execute still attempted",
                client="Gmail",
            )
            return

        await self._emit_notification(
            __event_emitter__,
            "success",
            self.valves.success_notification_text,
        )
        self._debug_log("Action completed successfully", client="Gmail")

    async def _handle_loading(self, __event_emitter__) -> None:
        if __event_emitter__ is None:
            return

        await self._emit_notification(
            __event_emitter__,
            "info",
            self.valves.loading_notification_text,
        )
        self._debug_log("Loading notification emitted")

    async def _handle_failure(
        self,
        exc: Exception,
        __event_emitter__,
    ) -> None:
        if self.valves.debug:
            LOGGER.exception("[email_assistant_message] Action failed")
        else:
            LOGGER.error("[email_assistant_message] Action failed: %s", exc)

        await self._emit_notification(
            __event_emitter__,
            "error",
            str(exc),
        )

    async def action(
        self,
        body: dict,
        __event_emitter__=None,
        __event_call__=None,
        __user__=None,
        __request__=None,
        __model__=None,
    ) -> None:
        try:
            self._debug_log(
                "Action invoked",
                body_keys=sorted(body.keys()),
                user_id=__user__.get("id") if isinstance(__user__, dict) else None,
                chat_id=body.get("chat_id"),
                message_id=body.get("id"),
                model=body.get("model"),
                gmail_account_path=self.valves.gmail_account_path,
            )

            message_text = self._extract_message_text(body)
            if not message_text:
                raise ValueError("No assistant message content was found.")

            recipients = await self._resolve_recipients(__event_call__)
            if recipients is None:
                self._debug_log("Action finished early after To prompt cancellation")
                return None

            draft = await self._resolve_draft(
                message_text,
                body,
                __request__,
                __user__,
                __model__,
                __event_call__,
            )
            await self._handle_loading(__event_emitter__)
            gmail_url = self._build_gmail_url(recipients, draft)
            self._debug_log(
                "Gmail compose target resolved",
                url_length=len(gmail_url),
                url_preview=self._preview(gmail_url, 300),
            )

            execute_result = await self._open_gmail_compose(
                gmail_url,
                __event_call__,
                __event_emitter__,
            )
            self._debug_log(
                "Browser execute step completed",
                execute_result=execute_result,
            )

            if isinstance(execute_result, dict) and execute_result.get("ok") is False:
                raise ValueError(
                    "The browser blocked both popup and new-tab opening for Gmail."
                )

            await self._handle_success(__event_emitter__)
            return None
        except Exception as exc:
            await self._handle_failure(exc, __event_emitter__)
            return None
