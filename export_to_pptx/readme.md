# Export to PPTX  (WIP)

Export an assistant message to a `.pptx` file with section slides, content slides, repeated headers and footers, placeholder support, and Mermaid/image handling.

## What it does

1. Reads the current assistant message.
2. Optionally asks the current chat model to rewrite it into a well-structured markdown document.
3. Converts Mermaid diagrams into PNGs using browser-side rendering.
4. Builds a presentation:
   - `# Title` becomes the title slide
   - `## Section` becomes a section title slide
   - deeper headings become content slide titles
   - long text is split across multiple slides
   - a single tall image is laid out beside the text
   - short 3-5 item bullet lists can be rendered as a grid
5. Downloads the `.pptx` file to the browser.

## Main valves

- `use_llm`
- `debug`
- `title_slide_subtitle`
- `closing_slide_enabled`
- `closing_slide_title`, `closing_slide_subtitle`
- `closing_slide_bg_color`, `closing_slide_bg_image_url`
- `header_text_left`, `header_text_middle`, `header_text_right`
- `footer_text_left`, `footer_text_middle`, `footer_text_right`
- `header_logo_url`, `footer_logo_url`
- `header_bg_color`, `footer_bg_color`
- `title_slide_bg_color`, `title_slide_bg_image_url`
- `section_title_slide_bg_color`, `section_title_slide_bg_image_url`
- `title_font_name`, `title_font_size_pt`, `title_color`
- `section_title_font_name`, `section_title_font_size_pt`, `section_title_color`
- `body_title_font_name`, `body_title_font_size_pt`, `body_title_color`
- `body_font_name`, `body_font_size_pt`, `body_text_color`
- `accent_color`

## Available placeholders

These work in header/footer text and `title_slide_subtitle`:

- `{{ CURRENT_PAGE }}`
- `{{ TOTAL_PAGES }}`
- `{{ FILE_NAME }}`
- `{{ PRESENTATION_TITLE }}`
- `{{ CURRENT_SECTION_TITLE }}`
- `{{ CURRENT_SUBSECTION_TITLE }}`
- `{{ USER_NAME }}`
- `{{ EXPORT_DATE }}`
- `{{ EXPORT_TIME }}`
- `{{ EXPORT_TIMESTAMP }}`
- `{{ HEADER_LOGO }}`
- `{{ FOOTER_LOGO }}`

Aliases like `{{ PAGE }}`, `{{ PAGES }}`, `{{ DATE }}`, `{{ TIME }}`, `{{ TITLE }}`, and `{{ USERNAME }}` also work.

## Notes

- If `use_llm = False`, the message is assumed to already be structured markdown.
- Mermaid export still depends on `__event_call__`, like the DOCX and PDF exporters.
- Images can be remote URLs or data URLs.
- Tables are rendered as native PowerPoint tables.
- Content is vertically centered inside the slide content area.
- `{{ HEADER_LOGO }}` uses `header_logo_url`, and `{{ FOOTER_LOGO }}` uses `footer_logo_url`.
- Header/footer logos are scaled to fit the bar height while keeping aspect ratio.
