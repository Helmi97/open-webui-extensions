# Export to Outlook Web

Open WebUI action that opens an Outlook Web compose window for the latest assistant message.

It can either:
- use Open WebUI chat completion to generate a clean email subject and body, or
- use the assistant message directly as the email body without calling the LLM.

The action tries to open Outlook Web in this order:
1. popup window
2. new tab
3. error if both are blocked

## What It Does

- Finds the latest assistant message from the current chat payload.
- Optionally prompts for missing `To`, `CC`, `BCC`, and `Subject` values.
- Optionally generates `subject` and `body` with the current chat model or an override model.
- Normalizes the final email body to plain text.
- Opens Outlook Web compose using Outlook's deeplink query parameters.
- Emits notifications for loading, success, and failure.

## Current Behavior

- Subject is plain text only.
- Body is normalized plain text only.
- Markdown styling such as bold, italic, inline code, headings, and strikethrough is stripped from the final body.
- Popup opening is tried first. If the popup is blocked, the action tries a normal new tab.
- The default compose endpoint is `https://outlook.office.com/mail/deeplink/compose`.
- For personal Outlook.com / Hotmail / Live accounts, set `outlook_base_url` to `https://outlook.live.com/mail/0/deeplink/compose` if needed.

## Installation

1. Open Open WebUI as an admin.
2. Go to the Functions / Actions area.
3. Create or update an Action function with the contents of `export_to_outlook_web.py`.
4. Save it and enable it where you want to use it.
5. Configure the valves as needed.

## Usage

1. Open a chat that contains an assistant response you want to export.
2. Click the action button.
3. Fill in any prompted fields if they are enabled and empty.
4. Wait for the loading notification.
5. Outlook Web opens in a popup or a new tab.
6. After the browser execute step succeeds, the success notification is shown.

## Notifications

- Loading notification: emitted after the last prompt is completed and before the Outlook Web open command runs.
- Success notification: emitted after the popup/new-tab execute step succeeds.
- Error notification: emitted if the action fails, including when both popup and new-tab opening are blocked.

## Valves

| Valve | Default | Purpose |
| --- | --- | --- |
| `debug` | `False` | Enables verbose server-side debug logs. |
| `outlook_base_url` | `"https://outlook.office.com/mail/deeplink/compose"` | Outlook Web compose URL. Change to `https://outlook.live.com/mail/0/deeplink/compose` for personal accounts if needed. |
| `default_to` | `""` | Prefilled `To` value. |
| `default_cc` | `""` | Prefilled `CC` value. |
| `default_bcc` | `""` | Prefilled `BCC` value. |
| `subject_prefix` | `""` | Prefix added to the generated subject if missing. |
| `default_subject` | `"Assistant message"` | Heuristic fallback subject when no generated subject is available. |
| `use_llm_email_generation` | `True` | If enabled, uses Open WebUI chat completion to generate the subject and body. |
| `subject_model` | `""` | Optional override model for email generation. Uses the current chat model when empty. |
| `subject_generation_temperature` | `0.2` | Temperature for email generation. |
| `subject_generation_max_tokens` | `512` | Max tokens for email generation. Internally floored to `256`. |
| `subject_generation_prompt` | built-in prompt | System prompt used for subject/body generation. |
| `prompt_for_to_if_empty` | `True` | Prompts for `To` when `default_to` is empty. |
| `prompt_for_cc_if_empty` | `False` | Prompts for `CC` when `default_cc` is empty. |
| `prompt_for_bcc_if_empty` | `False` | Prompts for `BCC` when `default_bcc` is empty. |
| `prompt_for_subject_if_empty` | `False` | Prompts for `Subject` when the generated/fallback subject is empty. |
| `loading_notification_text` | `"Generating the email draft..."` | Loading notification shown before the browser open step. |
| `success_notification_text` | `"The email is being generated and will be shown soon."` | Success notification shown after the browser open step succeeds. |
| `max_body_chars` | `10000` | Maximum number of characters placed into the email body. |
| `priority` | `0` | Toolbar ordering priority. Lower values appear earlier. |

## Browser Behavior

The browser open code tries:

1. popup window
2. normal new tab

If both fail in the `__event_call__` path, the action raises:

```text
The browser blocked both popup and new-tab opening for Outlook Web.
```

If Open WebUI only provides `__event_emitter__` and not `__event_call__`, the action still attempts popup then new tab, but it cannot reliably know whether the browser blocked the open.

## Debugging

Set `debug=True` to enable server-side logs.

Useful things you will see in logs:

- assistant message extraction path
- recipient and subject resolution
- model selection for email generation
- generated subject/body previews
- Outlook Web URL generation
- browser execute result
- full exception trace on failure

## Limitations

- This action opens Outlook Web compose. It does not send the email.
- The final body is plain text, not rich HTML.
- The action depends on browser-side execute support from Open WebUI.
- Popup blockers can still interfere with the Outlook Web open step.
- The correct Outlook Web host can differ between Microsoft 365 and personal accounts, so `outlook_base_url` may need adjustment.

## Files

- Action source: `export_to_outlook_web.py`
- README: `readme.md`
