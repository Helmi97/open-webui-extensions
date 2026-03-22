# Export to PPTX (Template)

Template-aware PPTX export action for Open WebUI.

## What it does

1. Reads the current assistant message.
2. Uses the current chat model, or an override model, through Open WebUI backend chat completion.
3. Optionally rewrites the message into cleaner presentation markdown.
4. Builds a slide plan JSON against the available layouts in a PPTX template.
5. Optionally repairs the slide plan once more.
6. Renders the plan into a `.pptx` file and downloads it in the browser.

## Main valves

- `template`
- `llm_model`
- `llm_temperature`
- `llm_max_tokens`
- `enable_preprocessing`
- `enable_postprocessing`
- `preprocessing_prompt`
- `processing_prompt`
- `postprocessing_prompt`
- `filename_prefix`
- `debug`

## Notes

- `template` accepts either a local `.pptx` path or an `http(s)` URL.
- Leaving `template` empty uses the default `python-pptx` presentation template.
- The action calls `generate_chat_completion(...)` through Open WebUI and uses `bypass_system_prompt=True`, matching the other export actions.
- JSON slide planning requests use `response_format={"type": "json_object"}` and fall back to a plain request if the backend rejects that option.
- Rendering is intentionally conservative: it fills text placeholders generically instead of trying to infer a custom visual design from each template.
