# Export to Excel

Export the tables from an assistant message to an `.xlsx` file.

## Features

- Creates one worksheet per table found in the assistant message
- Supports markdown tables and raw HTML tables
- Shows an error notification when no tables are present

## How it works

1. You click the action on an assistant message.
2. The action reads the assistant message content.
3. Markdown is rendered to HTML and all tables are extracted.
4. Each table is written to its own worksheet in a single Excel workbook.
5. The `.xlsx` file is downloaded in the browser.

## Valves

| Name | Meaning | Default |
|---|---|---|
| `priority` | Controls button order | `0` |
| `filename_prefix` | Prefix used in the output file name | `message` |
