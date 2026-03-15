# Share to X

Open WebUI action that opens the X compose popup for the latest assistant message.

The action uses X's documented web intent flow and lets the user review, edit, and publish the post manually.

## What It Does

- Finds the latest assistant message from the current chat payload.
- Converts the assistant message into X-friendly plain text while preserving line breaks and list structure where possible.
- In LLM mode, optionally generates values for all supported X fields.
- In non-LLM mode, prefills only the `text` field from the full assistant message content.
- Opens the X compose popup and falls back to a new tab if the popup is blocked.

## Supported Prefill Fields

- `text`
- `url`
- `hashtags`
- `via`
- `related`

## Modes

When `use_llm_share_generation=True`:

- The LLM may populate any supported X field.
- The model is asked to return JSON for `text`, `url`, `hashtags`, `via`, and `related`.
- Markdown is normalized to plain text for cleaner composition in X.

When `use_llm_share_generation=False`:

- Only the `text` field is prefilled.
- The action does not infer or generate hashtags, URLs, attribution, or related accounts.
- The text field is populated from the full assistant message content after plain-text normalization.

## Current Behavior

- The action uses the documented intent URL `https://twitter.com/intent/tweet`.
- The popup opens with `window.open(...)`.
- The user can edit everything in the X compose UI before posting.
- If the combined prefilled content exceeds X's posting limit, X will require the user to edit it before posting.
- Direct posting through the X API is out of scope.

## Installation

1. Open Open WebUI as an admin.
2. Go to the Functions / Actions area.
3. Create or update an Action function with the contents of `share_to_x.py`.
4. Save it and enable it where you want to use it.
5. Configure the valves as needed.

## Valves

| Valve | Default | Purpose |
| --- | --- | --- |
| `debug` | `False` | Enables verbose server-side debug logging. |
| `use_llm_share_generation` | `True` | Enables LLM generation for all supported X fields. |
| `share_model` | `""` | Optional override model for X share generation. Uses the current chat model when empty. |
| `share_generation_temperature` | `0.2` | Temperature for X share generation. |
| `share_generation_max_tokens` | `512` | Max tokens for X share generation. Internally floored to `256`. |
| `share_generation_prompt` | built-in prompt | System prompt used for X share generation. |
| `loading_notification_text` | `"Preparing the X share draft..."` | Loading notification shown before the browser open step. |
| `success_notification_text` | `"The X share dialog is opening."` | Success notification shown after the browser open step succeeds. |
| `max_text_chars` | `5000` | Maximum number of characters placed into the `text` field. |
| `priority` | `0` | Toolbar ordering priority. Lower values appear earlier. |

## Browser Behavior

The browser open code tries:

1. popup window
2. normal new tab

If both fail in the `__event_call__` path, the action raises:

```text
The browser blocked both popup and new-tab opening for X.
```

If Open WebUI only provides `__event_emitter__` and not `__event_call__`, the action still attempts popup then new tab, but it cannot reliably know whether the browser blocked the open.

## Limitations

- This action opens the X compose UI. It does not post automatically.
- The final compose content is plain text plus the supported intent parameters.
- X intent behavior is limited to the fields officially supported by the web intent URL.
- Very large assistant messages may be truncated by `max_text_chars` before opening the share URL.

## Files

- Action source: `share_to_x.py`
- README: `readme.md`
