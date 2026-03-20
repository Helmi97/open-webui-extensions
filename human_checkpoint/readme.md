# Human Checkpoint

`human_checkpoint` is an Open WebUI Workspace Tool that lets the model request structured human input through a browser modal instead of another free-form chat turn.

It takes a JSON Schema at runtime, renders the form with Jedison in the user's browser, waits for submit, cancel, or timeout, and returns a structured JSON result back to the tool call.

## What It Does

- Uses `__event_call__` with `type: "execute"` so the browser runs the full modal flow.
- Loads Jedison from CDN on demand if it is not already present.
- Renders a modal dialog with title and description taken from the schema.
- Merges schema defaults with the configured `initial_data` valve before the form is shown.
- Disables submit while validation errors exist.
- Returns one of four structured results:
  - `{"status": "submitted", "data": {...}}`
  - `{"status": "cancelled"}`
  - `{"status": "timeout"}`
  - `{"status": "error", "message": "..."}`
- Cleans up the modal DOM, restores focus, and removes its event listeners when the interaction ends.

## Installation

1. Open Open WebUI as an admin.
2. Go to the Tools area.
3. Create or update a Workspace Tool with the contents of `human_checkpoint.py`.
4. Save it.
5. Configure the valves as needed.

## Runtime Contract

The tool is intentionally minimal at call time:

```json
{
  "schema": {
    "title": "Database Credentials",
    "description": "Provide the connection settings for the import job.",
    "type": "object",
    "properties": {
      "host": {
        "type": "string",
        "title": "Host"
      },
      "port": {
        "type": "integer",
        "title": "Port",
        "default": 5432,
        "minimum": 1,
        "maximum": 65535
      },
      "username": {
        "type": "string",
        "title": "Username"
      },
      "password": {
        "type": "string",
        "title": "Password"
      },
      "ssl": {
        "type": "boolean",
        "title": "Use SSL",
        "default": true
      }
    },
    "required": ["host", "username", "password"]
  }
}
```

Guidance:

- Put labels, descriptions, defaults, enums, and validation rules in the schema.
- Keep stable UI settings in valves, not in the tool call.
- Prefer one complete schema over several back-and-forth prompts.
- Password masking depends on the schema conventions Jedison supports for that field type.

## Valves

| Valve | Default | Purpose |
| --- | --- | --- |
| `submit_label` | `"Submit"` | Label for the primary action button. |
| `cancel_label` | `"Cancel"` | Label for the secondary action button. |
| `timeout_ms` | `240000` | Browser-side timeout in milliseconds. Use `0` to disable the tool timeout. |
| `initial_data` | `{}` | Static JSON object merged over schema defaults before rendering. |
| `ui_options` | `{}` | Extra Jedison options. Reserved keys such as `container`, `schema`, `theme`, and `data` are overwritten by the tool. |
| `css` | `""` | Extra CSS appended after the built-in modal styles. |
| `cdn_url` | `https://cdn.jsdelivr.net/npm/jedison@latest/dist/umd/jedison.umd.js` | URL used to load Jedison in the browser if needed. |
| `dialog_width` | `"92vw"` | CSS width for the dialog. |
| `dialog_max_width` | `"860px"` | CSS max-width for the dialog. |
| `theme_name` | `"default"` | Jedison theme: `default`, `bootstrap5`, `bootstrap4`, or `bootstrap3`. Bootstrap themes attempt to load matching CSS automatically. |
| `show_cancel_button` | `true` | Controls whether the cancel button is shown. |
| `close_on_escape` | `true` | Controls whether `Escape` cancels the dialog. |
| `close_on_overlay_click` | `false` | Controls whether clicking the backdrop cancels the dialog. |

## Return Values

### Submitted

```json
{
  "status": "submitted",
  "data": {
    "host": "db.internal",
    "port": 5432,
    "username": "etl_user",
    "password": "secret",
    "ssl": true
  }
}
```

### Cancelled

```json
{
  "status": "cancelled"
}
```

### Timeout

```json
{
  "status": "timeout"
}
```

### Error

```json
{
  "status": "error",
  "message": "human_checkpoint requires an active Open WebUI browser session because it opens a client-side modal through __event_call__."
}
```

## Notes

- This tool requires a live browser session. Direct API-only calls that do not have `__event_call__` available will return an error.
- Open WebUI also has a server-side event-call timeout. The default is typically 300 seconds. If `timeout_ms` is larger than that server timeout, the server can fail the call before the browser-side timeout fires.
- The integration layer is intentionally thin. Field rendering and validation behavior are delegated to Jedison rather than reimplemented in Python.

## Files

- Tool source: `human_checkpoint.py`
- README: `readme.md`
