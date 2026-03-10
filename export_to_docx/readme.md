# Export Message to DOCX

Export an assistant message to a `.docx` file using your own template.

## Features

- 🎨 Use your own DOCX template hosted at any server-accessible URL
- 🧾 Supports text, headings, lists, quotes, code blocks, tables, and images
- 📊 Supports Mermaid diagrams rendered from the message and inserted into the document

## How it works

1. You click the action on an assistant message.
2. The action downloads the DOCX template from `template_url`.
3. It scans the template for placeholders.
4. Built-in placeholders are filled automatically.
5. You will be asked to input any extra placeholders.
6. The assistant message content is converted into DOCX content.
7. The generated body is inserted at `{{ BODY_CONTENT }}`.
8. The final `.docx` file is downloaded.

## Valves

| Name | Meaning | Default |
|---|---|---|
| `filename_prefix` | Prefix used in the output file name | `message` |
| `template_url` | Public URL to the DOCX template file | your configured template URL |
| `body_placeholder` | Placeholder where the generated body is inserted | `{{ BODY_CONTENT }}` |
| `mermaid_scale` | Rendering scale used for diagrams before insertion | `2` |
| `max_mermaid_width_in` | Maximum Mermaid diagram width in inches | `6.5` |
| `max_mermaid_height_in` | Maximum Mermaid diagram height in inches | `4.5` |
| `max_image_width_in` | Maximum normal image width in inches | `6.5` |
| `max_image_height_in` | Maximum normal image height in inches | `6.0` |
| `request_timeout_s` | HTTP timeout for template and image downloads | `30` |

## How to create a template

Create a normal Word or Google Docs document and place placeholders where you want values to appear.

### Built-in placeholders

These are filled automatically:

- `{{ FILE_NAME }}`
- `{{ EXPORT_DATE }}`
- `{{ EXPORT_TIME }}`
- `{{ USER_NAME }}`
- `{{ BODY_CONTENT }}`

### Custom placeholders

You can add your own placeholders, for example:

- `{{ CLIENT_NAME }}`
- `{{ PROJECT_NAME }}`
- `{{ REVIEWER }}`

When exporting, the action will detect them and ask the user to enter values.

**Important notes**

- {{ BODY_CONTENT }} should be on its own line

- Use placeholder names in uppercase with underscores

- Keep logos, page numbers, and styling directly in the template

- Make sure the template URL is accessible by the server
