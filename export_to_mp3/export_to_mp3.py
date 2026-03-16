"""
title: Export to MP3
description: Download a spoken MP3 version of the assistant message
version: 1.0.0
author: Helmi Chaouachi
git_url: https://github.com/Helmi97/open-webui-extensions/tree/main/export_to_mp3
required_open_webui_version: 0.8.0
icon_url: https://www.svgrepo.com/show/362087/file-sound.svg
"""

from __future__ import annotations

import base64
import io
import json
import logging
import os
import re
import tempfile
import time
import zipfile
from pathlib import Path
from typing import Any

from fastapi import HTTPException
from pydantic import BaseModel, Field
import requests

from open_webui.models.users import UserModel
from open_webui.routers.audio import speech as generate_speech
from open_webui.utils.chat import generate_chat_completion
from open_webui.config import CACHE_DIR

LOGGER = logging.getLogger(__name__)

MIN_CLEANUP_MAX_TOKENS = 256
HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s*(.+?)\s*$")
CHECKBOX_RE = re.compile(r"^\s*[-*+]\s+\[[ xX]\]\s+(.*)$")
BULLET_RE = re.compile(r"^\s*[-*+]\s+(.*)$")
NUMBERED_RE = re.compile(r"^\s*(\d+)[.)]\s+(.*)$")
QUOTE_RE = re.compile(r"^\s*(>+)\s*(.*)$")
MARKDOWN_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)\s]+(?:\s+\"[^\"]*\")?)\)")
IMAGE_RE = re.compile(r"!\[[^\]]*\]\([^)]+\)")
INLINE_CODE_RE = re.compile(r"`([^`]+)`")
BOLD_RE = re.compile(r"\*\*(.*?)\*\*")
DOUBLE_UNDERSCORE_RE = re.compile(r"__(.*?)__")
ITALIC_STAR_RE = re.compile(r"(?<!\*)\*([^*]+)\*(?!\*)")
ITALIC_UNDERSCORE_RE = re.compile(r"(?<!_)_([^_]+)_(?!_)")
STRIKETHROUGH_RE = re.compile(r"~~(.*?)~~")
CODE_FENCE_RE = re.compile(r"```(?:[a-zA-Z0-9_-]+)?\s*\n.*?\n```", re.DOTALL)
MERMAID_FENCE_RE = re.compile(r"```mermaid\s*\n.*?\n```", re.DOTALL | re.IGNORECASE)
HTML_TAG_RE = re.compile(r"<[^>]+>")
HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
URL_RE = re.compile(r"https?://[^\s<>()]+", re.IGNORECASE)
TABLE_SEPARATOR_RE = re.compile(r"^\s*\|?[\s:-]+\|[\s|:-]*$")
BRACKET_CITATION_RE = re.compile(r"\[\d+\]")
OWUI_CITATION_RE = re.compile(r"\u3010[^\u3011]+\u3011")
CONTROL_RE = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F]")
HORIZONTAL_WHITESPACE_RE = re.compile(r"[ \t]+")
BLANK_BLOCK_RE = re.compile(r"\n{3,}")
INLINE_MARKDOWN_PATTERNS = (
    (INLINE_CODE_RE, " "),
    (BOLD_RE, r"\1"),
    (DOUBLE_UNDERSCORE_RE, r"\1"),
    (ITALIC_STAR_RE, r"\1"),
    (ITALIC_UNDERSCORE_RE, r"\1"),
    (STRIKETHROUGH_RE, r"\1"),
)
DEFAULT_CLEANUP_PROMPT = (
    "You convert assistant messages into plain text for text-to-speech. "
    "Return only the final spoken text, with no markdown, no code fences, and no JSON. "
    "Remove code blocks, inline code, tables, mermaid diagrams, URLs, file paths, raw HTML, "
    "citation markers, image syntax, and any metadata that should not be spoken aloud. "
    "Preserve the actual meaning of the assistant message. Rewrite bullets into natural spoken "
    "sentences when helpful. If the message is mostly code or structured data, replace it with a "
    "brief plain-language explanation of what it contains instead of reading it verbatim."
)
CMU_ARCTIC_XVECTORS_URL = (
    "https://huggingface.co/datasets/Matthijs/cmu-arctic-xvectors/resolve/main/"
    "spkrec-xvect.zip"
)
SPEAKER_EMBEDDINGS_CACHE_DIR = CACHE_DIR / "audio" / "speaker_embeddings"
SPEAKER_EMBEDDINGS_CACHE_DIR.mkdir(parents=True, exist_ok=True)
CMU_ARCTIC_XVECTORS_ARCHIVE_PATH = SPEAKER_EMBEDDINGS_CACHE_DIR / "spkrec-xvect.zip"


class _SyntheticSpeechRequest:
    def __init__(self, app, payload: bytes):
        self.app = app
        self._payload = payload

    async def body(self) -> bytes:
        return self._payload


class _SpeakerEmbeddingsDataset:
    def __init__(self, archive_path: str, members: list[str]):
        self.archive_path = archive_path
        self.members = members
        self.filenames = [
            os.path.splitext(os.path.basename(member))[0] for member in members
        ]

    def __getitem__(self, key):
        if key == "filename":
            return self.filenames

        if isinstance(key, int):
            import numpy as np

            member = self.members[key]
            with zipfile.ZipFile(self.archive_path, "r") as archive:
                with archive.open(member) as embedding_file:
                    xvector = np.load(
                        io.BytesIO(embedding_file.read()),
                        allow_pickle=False,
                    )
            return {
                "filename": self.filenames[key],
                "xvector": xvector,
            }

        raise KeyError(key)

    def __len__(self):
        return len(self.members)


class Action:
    class Valves(BaseModel):
        priority: int = Field(
            default=0,
            description="Controls button display order (lower = appears first).",
        )
        filename_prefix: str = Field(
            default="message",
            description="Prefix used for the downloaded MP3 file name.",
        )
        use_llm_cleanup: bool = Field(
            default=True,
            description=(
                "Use the current chat model to convert the assistant message into "
                "speech-friendly plain text before synthesis."
            ),
        )
        cleanup_model: str = Field(
            default="",
            description=(
                "Optional model ID used for speech-text cleanup. Defaults to the "
                "current chat model."
            ),
        )
        cleanup_temperature: float = Field(
            default=0.1,
            ge=0.0,
            le=2.0,
            description="Temperature used for speech-text cleanup.",
        )
        cleanup_max_tokens: int = Field(
            default=2048,
            ge=128,
            le=8192,
            description="Maximum tokens used for speech-text cleanup.",
        )
        cleanup_prompt: str = Field(
            default=DEFAULT_CLEANUP_PROMPT,
            description="System prompt used when `use_llm_cleanup` is enabled.",
        )
        max_input_chars: int = Field(
            default=12000,
            ge=500,
            le=50000,
            description="Maximum characters sent to the TTS backend after cleanup.",
        )
        voice: str = Field(
            default="",
            description=(
                "Optional voice override. When empty, the Open WebUI TTS voice "
                "configuration is used."
            ),
        )
        speed: float = Field(
            default=1.0,
            ge=0.25,
            le=4.0,
            description="Speech speed passed to TTS providers that support it.",
        )
        debug: bool = Field(
            default=False,
            description="Enable verbose server-side debug logging for this action.",
        )

    def __init__(self):
        self.valves = self.Valves()

    def _preview(self, value: Any, limit: int = 220) -> str:
        text = value if isinstance(value, str) else str(value)
        text = text.replace("\r", "\\r").replace("\n", "\\n")
        return text if len(text) <= limit else f"{text[:limit]}...<truncated>"

    def _debug_log(self, message: str, **context: Any) -> None:
        if not self.valves.debug:
            return
        if not context:
            LOGGER.info("[export_to_spoken_mp3] %s", message)
            return
        rendered = []
        for key, value in context.items():
            try:
                rendered_value = (
                    json.dumps(value, default=str)
                    if isinstance(value, (dict, list, tuple))
                    else str(value)
                )
            except TypeError:
                rendered_value = str(value)
            rendered.append(f"{key}={self._preview(rendered_value)}")
        LOGGER.info("[export_to_spoken_mp3] %s | %s", message, "; ".join(rendered))

    async def emit_error(self, message: str, __event_emitter__=None):
        if __event_emitter__:
            await __event_emitter__(
                {
                    "type": "notification",
                    "data": {"type": "error", "content": message},
                }
            )

    async def emit_status(
        self, description: str, done: bool, __event_emitter__=None
    ):
        if __event_emitter__:
            await __event_emitter__(
                {
                    "type": "status",
                    "data": {"description": description, "done": done},
                }
            )

    def build_filename(self, message_id: str) -> str:
        return f"{self.valves.filename_prefix}-{message_id}.mp3"

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
            if value.get("type") in {"text", "input_text", "output_text"}:
                return self._extract_text(value.get("text"))
            for key in ("content", "text", "value"):
                if key in value:
                    return self._extract_text(value.get(key))
            return ""
        return str(value).strip()

    def get_message_content(self, body: dict) -> str:
        target_id = body.get("id")
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
                    if (
                        target_id in candidate_ids
                        and message.get("role") == "assistant"
                    ):
                        message_text = self._extract_text(message.get("content"))
                        if message_text:
                            return message_text
            for message in reversed(messages):
                if isinstance(message, dict) and message.get("role") == "assistant":
                    message_text = self._extract_text(message.get("content"))
                    if message_text:
                        return message_text

        history = body.get("history")
        if isinstance(history, dict):
            history_messages = history.get("messages", {})
            current_id = target_id or history.get("currentId")
            if current_id and current_id in history_messages:
                message_text = self._extract_text(
                    history_messages[current_id].get("content")
                )
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
            url = match.group(2).split()[0].strip()
            return label if label and label != url else ""

        return MARKDOWN_LINK_RE.sub(replacer, text)

    def _strip_inline_markdown(self, text: str) -> str:
        cleaned = self._replace_markdown_links(text)
        for pattern, replacement in INLINE_MARKDOWN_PATTERNS:
            cleaned = pattern.sub(replacement, cleaned)
        return cleaned

    def _looks_like_structured_or_code(self, line: str) -> bool:
        stripped = line.strip()
        if not stripped:
            return False
        if TABLE_SEPARATOR_RE.match(stripped):
            return True
        if stripped.count("|") >= 2:
            return True
        if len(re.findall(r"[{}[\];<>_=\\/]", stripped)) >= 4:
            return True
        if re.search(
            r"(?:\bdef\b|\bclass\b|\breturn\b|\bimport\b|=>|::|</?\w+>|^\{|\}$)",
            stripped,
        ):
            return True
        if stripped.startswith(("```", "{", "}", "[", "]", "SELECT ", "INSERT ")):
            return True
        alpha_count = len(re.findall(r"[A-Za-z]", stripped))
        punct_count = len(re.findall(r"[^A-Za-z0-9\s]", stripped))
        return alpha_count > 0 and punct_count > alpha_count

    def _normalize_line(self, raw_line: str) -> str:
        stripped = raw_line.strip()
        if not stripped:
            return ""
        if self._looks_like_structured_or_code(stripped):
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
                stripped = checkbox_match.group(1)
            elif bullet_match:
                stripped = bullet_match.group(1)
            elif numbered_match:
                stripped = f"{numbered_match.group(1)}. {numbered_match.group(2)}"
            elif quote_match:
                stripped = quote_match.group(2)

        stripped = self._strip_inline_markdown(stripped)
        stripped = BRACKET_CITATION_RE.sub("", stripped)
        stripped = OWUI_CITATION_RE.sub("", stripped)
        stripped = URL_RE.sub("", stripped)
        stripped = HORIZONTAL_WHITESPACE_RE.sub(" ", stripped.strip(" \"'`*_~|"))
        return stripped.strip()

    def heuristic_cleanup(self, text: str) -> str:
        cleaned = (text or "").replace("\r\n", "\n").replace("\r", "\n")
        cleaned = CONTROL_RE.sub("", cleaned)
        cleaned = HTML_COMMENT_RE.sub("", cleaned)
        cleaned = MERMAID_FENCE_RE.sub("", cleaned)
        cleaned = CODE_FENCE_RE.sub("", cleaned)
        cleaned = IMAGE_RE.sub("", cleaned)
        cleaned = self._replace_markdown_links(cleaned)
        cleaned = HTML_TAG_RE.sub(" ", cleaned)
        cleaned = BRACKET_CITATION_RE.sub("", cleaned)
        cleaned = OWUI_CITATION_RE.sub("", cleaned)

        normalized_lines: list[str] = []
        for raw_line in cleaned.split("\n"):
            line = self._normalize_line(raw_line)
            if line:
                normalized_lines.append(line)
            elif normalized_lines and normalized_lines[-1] != "":
                normalized_lines.append("")

        normalized = "\n".join(normalized_lines).strip()
        normalized = BLANK_BLOCK_RE.sub("\n\n", normalized)
        return normalized.strip()

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

    async def cleanup_for_speech(
        self,
        message_text: str,
        body: dict,
        __request__,
        __user__,
        __model__,
    ) -> str:
        fallback_text = self.heuristic_cleanup(message_text)

        if __request__ is None or not self.valves.use_llm_cleanup:
            return fallback_text

        cleanup_model = (
            self.valves.cleanup_model.strip()
            or body.get("model")
            or (__model__ or {}).get("id")
        )
        user_model = self._get_user_model(__user__)

        if not cleanup_model or user_model is None:
            return fallback_text

        payload = {
            "model": cleanup_model,
            "stream": False,
            "temperature": self.valves.cleanup_temperature,
            "max_tokens": max(
                self.valves.cleanup_max_tokens, MIN_CLEANUP_MAX_TOKENS
            ),
            "messages": [
                {"role": "system", "content": self.valves.cleanup_prompt.strip()},
                {
                    "role": "user",
                    "content": (
                        "Assistant message to prepare for spoken audio export:\n\n"
                        f"{message_text}"
                    ),
                },
            ],
        }

        try:
            response = await generate_chat_completion(
                __request__,
                payload,
                user_model,
                bypass_system_prompt=True,
            )
            cleaned = self._extract_chat_completion_text(response).strip()
            if not cleaned:
                return fallback_text
            cleaned = self.heuristic_cleanup(cleaned)
            return cleaned or fallback_text
        except Exception as exc:
            self._debug_log("LLM cleanup failed; using heuristic cleanup", error=str(exc))
            return fallback_text

    def _truncate_text(self, text: str) -> str:
        limit = self.valves.max_input_chars
        if len(text) <= limit:
            return text

        truncated = text[:limit]
        punctuation_cut = max(
            truncated.rfind(". "),
            truncated.rfind("! "),
            truncated.rfind("? "),
            truncated.rfind("\n"),
        )
        if punctuation_cut >= max(0, limit - 500):
            truncated = truncated[: punctuation_cut + 1]
        else:
            word_cut = truncated.rfind(" ")
            if word_cut > 0:
                truncated = truncated[:word_cut]

        return truncated.strip()

    def _ensure_cmu_arctic_xvectors_archive(self) -> str:
        if CMU_ARCTIC_XVECTORS_ARCHIVE_PATH.is_file():
            return str(CMU_ARCTIC_XVECTORS_ARCHIVE_PATH)

        temp_path = CMU_ARCTIC_XVECTORS_ARCHIVE_PATH.with_suffix(".tmp")
        try:
            with requests.get(
                CMU_ARCTIC_XVECTORS_URL,
                stream=True,
                timeout=(10, 300),
            ) as response:
                response.raise_for_status()
                with open(temp_path, "wb") as archive_file:
                    for chunk in response.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            archive_file.write(chunk)

            os.replace(temp_path, CMU_ARCTIC_XVECTORS_ARCHIVE_PATH)
        except Exception:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise

        return str(CMU_ARCTIC_XVECTORS_ARCHIVE_PATH)

    def _build_speaker_embeddings_dataset(self) -> _SpeakerEmbeddingsDataset:
        archive_path = self._ensure_cmu_arctic_xvectors_archive()
        with zipfile.ZipFile(archive_path, "r") as archive:
            members = sorted(
                name for name in archive.namelist() if name.endswith(".npy")
            )

        if not members:
            raise RuntimeError("Speaker embeddings archive is empty.")

        return _SpeakerEmbeddingsDataset(archive_path=archive_path, members=members)

    def _ensure_transformers_speaker_embeddings(self, __request__) -> None:
        if __request__ is None:
            return

        if __request__.app.state.config.TTS_ENGINE != "transformers":
            return

        dataset = getattr(
            __request__.app.state,
            "speech_speaker_embeddings_dataset",
            None,
        )
        if dataset is not None:
            return

        self._debug_log("Preparing local speaker embeddings dataset for transformers TTS")
        __request__.app.state.speech_speaker_embeddings_dataset = (
            self._build_speaker_embeddings_dataset()
        )

    async def _synthesize_transformers_mp3(self, text: str, __request__) -> bytes:
        import soundfile as sf
        import torch
        from pydub import AudioSegment
        from transformers import pipeline

        self._ensure_transformers_speaker_embeddings(__request__)

        if getattr(__request__.app.state, "speech_synthesiser", None) is None:
            __request__.app.state.speech_synthesiser = pipeline(
                "text-to-speech",
                "microsoft/speecht5_tts",
            )

        embeddings_dataset = __request__.app.state.speech_speaker_embeddings_dataset
        speaker_index = 6799
        configured_speaker = __request__.app.state.config.TTS_MODEL
        try:
            speaker_index = embeddings_dataset["filename"].index(configured_speaker)
        except Exception:
            pass

        speaker_embedding = torch.tensor(
            embeddings_dataset[speaker_index]["xvector"]
        ).unsqueeze(0)
        speech = __request__.app.state.speech_synthesiser(
            text,
            forward_params={"speaker_embeddings": speaker_embedding},
        )

        wav_path = None
        mp3_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as wav_file:
                wav_path = wav_file.name
            sf.write(wav_path, speech["audio"], samplerate=speech["sampling_rate"])

            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as mp3_file:
                mp3_path = mp3_file.name
            AudioSegment.from_wav(wav_path).export(mp3_path, format="mp3")

            return Path(mp3_path).read_bytes()
        finally:
            if wav_path and os.path.exists(wav_path):
                os.remove(wav_path)
            if mp3_path and os.path.exists(mp3_path):
                os.remove(mp3_path)

    async def synthesize_mp3(
        self,
        text: str,
        __request__,
        __user__,
    ) -> bytes:
        if __request__ is None:
            raise RuntimeError("This action requires __request__ for TTS generation.")

        user_model = self._get_user_model(__user__)
        if user_model is None:
            raise RuntimeError("Could not resolve the current user for TTS generation.")

        if __request__.app.state.config.TTS_ENGINE == "transformers":
            return await self._synthesize_transformers_mp3(text, __request__)

        voice = self.valves.voice.strip() or __request__.app.state.config.TTS_VOICE
        payload = {
            "input": text,
            "voice": voice,
            "speed": self.valves.speed,
            "response_format": "mp3",
        }
        request_payload = json.dumps(payload).encode("utf-8")
        synthetic_request = _SyntheticSpeechRequest(__request__.app, request_payload)
        response = await generate_speech(synthetic_request, user_model)

        file_path = getattr(response, "path", None)
        if not file_path:
            raise RuntimeError("TTS generation did not return a downloadable file.")

        return Path(file_path).read_bytes()

    async def download_file(
        self,
        mp3_bytes: bytes,
        filename: str,
        __event_emitter__=None,
        __event_call__=None,
    ):
        encoded = base64.b64encode(mp3_bytes).decode("ascii")

        js_code = f"""
const base64 = {json.dumps(encoded)};
const filename = {json.dumps(filename)};
const binary = atob(base64);
const bytes = new Uint8Array(binary.length);

for (let i = 0; i < binary.length; i++) {{
  bytes[i] = binary.charCodeAt(i);
}}

const blob = new Blob([bytes], {{ type: "audio/mpeg" }});
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
            return {"success": True, "filename": filename, "size": len(mp3_bytes)}

        return None

    async def action(
        self,
        body: dict,
        __user__=None,
        __event_emitter__=None,
        __event_call__=None,
        __request__=None,
        __model__=None,
        **kwargs,
    ):
        message_id = body.get("id")
        if not message_id:
            await self.emit_error(
                "Spoken MP3 export failed: could not determine the current message id.",
                __event_emitter__,
            )
            return {
                "content": "Could not determine the current message id from body['id']."
            }

        filename = self.build_filename(message_id)

        await self.emit_status("Reading message content...", False, __event_emitter__)
        message_text = self.get_message_content(body)
        self._debug_log(
            "Extracted assistant message content",
            message_id=message_id,
            original_length=len(message_text),
            preview=self._preview(message_text),
        )
        if not message_text.strip():
            await self.emit_error(
                "Spoken MP3 export failed: no assistant message content found.",
                __event_emitter__,
            )
            await self.emit_status(
                "No assistant message content found.",
                True,
                __event_emitter__,
            )
            return {"content": "No assistant message content found."}

        await self.emit_status(
            "Preparing text for speech...", False, __event_emitter__
        )
        spoken_text = await self.cleanup_for_speech(
            message_text,
            body,
            __request__,
            __user__,
            __model__,
        )
        spoken_text = self._truncate_text(spoken_text)

        self._debug_log(
            "Prepared text for speech",
            cleaned_length=len(spoken_text),
            preview=self._preview(spoken_text),
        )
        if not spoken_text.strip():
            await self.emit_error(
                "Spoken MP3 export failed: no speakable text remained after cleanup.",
                __event_emitter__,
            )
            await self.emit_status(
                "No speakable text remained after cleanup.",
                True,
                __event_emitter__,
            )
            return {"content": "No speakable text remained after cleanup."}

        await self.emit_status("Generating MP3...", False, __event_emitter__)
        try:
            mp3_bytes = await self.synthesize_mp3(
                spoken_text,
                __request__,
                __user__,
            )
        except HTTPException as exc:
            detail = exc.detail if getattr(exc, "detail", None) else str(exc)
            await self.emit_error(
                f"Spoken MP3 export failed: {detail}",
                __event_emitter__,
            )
            await self.emit_status("MP3 generation failed.", True, __event_emitter__)
            return {"content": f"Spoken MP3 export failed: {detail}"}
        except Exception as exc:
            await self.emit_error(
                f"Spoken MP3 export failed: {exc}",
                __event_emitter__,
            )
            await self.emit_status("MP3 generation failed.", True, __event_emitter__)
            return {"content": f"Spoken MP3 export failed: {exc}"}

        await self.emit_status("Starting download...", False, __event_emitter__)
        result = await self.download_file(
            mp3_bytes=mp3_bytes,
            filename=filename,
            __event_emitter__=__event_emitter__,
            __event_call__=__event_call__,
        )

        await self.emit_status(
            "Spoken MP3 export complete.",
            True,
            __event_emitter__,
        )
        return {
            "content": f"Exported message to spoken MP3: {filename}",
            "result": result,
            "spoken_text_length": len(spoken_text),
        }
