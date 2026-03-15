# Share to OpenWebUI Community

Open WebUI action that opens the OpenWebUI Community post composer for the latest assistant message.

The action uses the current Community compose URL pattern `https://openwebui.com/post?title=...&content=...` and lets the user review and publish manually.

## What It Does

- Finds the latest assistant message from the current chat payload.
- Preserves the assistant message content as Markdown for the Community `content` field, including formatting such as headers, bold, italics, lists, links, blockquotes, and code fences.
- In LLM mode, optionally generates values for the supported Community fields.
- In non-LLM mode, prefills `content` from the full assistant message and derives `title` from the first non-empty line.
- Opens the Community composer in a popup and falls back to a new tab if the popup is blocked.

## Supported Prefill Fields

- `title`
- `content`

## Modes

When `use_llm_share_generation=True`:

- The LLM may populate `title` and `content`.
- The model is asked to return JSON for the supported Community fields.
- The `content` field is expected to be Markdown, not flattened plain text.

When `use_llm_share_generation=False`:

- `content` is prefilled from the full assistant message content.
- `title` falls back to the first non-empty normalized line, then `default_title`.

## Current Behavior

- The action opens `https://openwebui.com/post` with `title` and `content` query parameters.
- The popup opens with `window.open(...)`.
- The user can edit the post in the OpenWebUI Community UI before publishing.
- Markdown formatting in `content` is preserved as far as the source assistant message already contains it.
- Direct posting through an API is out of scope.

## Installation

1. Open Open WebUI as an admin.
2. Go to the Functions / Actions area.
3. Create or update an Action function with the contents of `share_to_openwebui_community.py`.
4. Save it and enable it where you want to use it.
5. Configure the valves as needed.

## Valves

| Valve | Default | Purpose |
| --- | --- | --- |
| `debug` | `False` | Enables verbose server-side debug logging. |
| `community_post_base_url` | `https://openwebui.com/post` | Base compose URL for OpenWebUI Community posts. |
| `default_title` | `Assistant message` | Fallback title used when no title can be derived. |
| `use_llm_share_generation` | `True` | Enables LLM generation for `title` and `content`. |
| `share_model` | `""` | Optional override model for Community share generation. Uses the current chat model when empty. |
| `share_generation_temperature` | `0.2` | Temperature for Community share generation. |
| `share_generation_max_tokens` | `512` | Max tokens for Community share generation. Internally floored to `256`. |
| `share_generation_prompt` | built-in prompt | System prompt used for Community share generation. |
| `loading_notification_text` | `"Preparing the OpenWebUI Community post draft..."` | Loading notification shown before the browser open step. |
| `success_notification_text` | `"The OpenWebUI Community post composer is opening."` | Success notification shown after the browser open step succeeds. |
| `max_title_chars` | `120` | Maximum number of characters placed into the `title` field. |
| `max_content_chars` | `5000` | Maximum number of characters placed into the `content` field. |
| `priority` | `0` | Toolbar ordering priority. Lower values appear earlier. |

## Browser Behavior

The browser open code tries:

1. popup window
2. normal new tab

If both fail in the `__event_call__` path, the action raises:

```text
The browser blocked both popup and new-tab opening for OpenWebUI Community.
```

If Open WebUI only provides `__event_emitter__` and not `__event_call__`, the action still attempts popup then new tab, but it cannot reliably know whether the browser blocked the open.

## Limitations

- This action opens the OpenWebUI Community compose UI. It does not post automatically.
- The current compose URL requires the user to be logged in to `openwebui.com`. If not logged in, the site redirects to the main page with a login message.
- Very large assistant messages may be truncated by `max_content_chars` before opening the share URL.
- Extremely large drafts can still hit browser URL-length limits because the compose flow is URL-based.

## Files

- Action source: `share_to_openwebui_community.py`
- README: `readme.md`
