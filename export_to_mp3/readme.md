# Export to MP3

Download an assistant message as a spoken `.mp3` file.

## Features

- Reuses Open WebUI's built-in TTS pipeline
- Cleans assistant messages into speech-friendly plain text before synthesis
- Removes code, markdown, tables, URLs, and other content that should not be spoken aloud
- Downloads the generated audio directly in the browser

## How it works

1. You click the action on an assistant message.
2. The action extracts the assistant message text.
3. It converts the message into speech-friendly plain text.
4. It calls Open WebUI's own TTS function to generate an MP3.
5. The `.mp3` file is downloaded in the browser.

## Valves

| Name | Meaning | Default |
|---|---|---|
| `priority` | Controls button order | `0` |
| `filename_prefix` | Prefix used in the output file name | `message` |
| `use_llm_cleanup` | Use an Open WebUI chat model to prepare speech text | `True` |
| `cleanup_model` | Optional model override for speech-text cleanup | `""` |
| `cleanup_temperature` | Temperature used for speech-text cleanup | `0.1` |
| `cleanup_max_tokens` | Maximum tokens used for speech-text cleanup | `2048` |
| `max_input_chars` | Maximum characters sent to TTS | `12000` |
| `voice` | Optional voice override | `""` |
| `speed` | Speech speed | `1.0` |
