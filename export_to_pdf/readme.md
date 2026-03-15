# 📄 Export to PDF

Turn an assistant message in Open WebUI into a polished PDF with selectable text, branded layouts, custom headers/footers, and Mermaid diagram support.

---

## ✨ Features

- 📄 A real PDF with **Selectable/searchable text** , not a screenshot
- 📊 **Images, tables and Mermaid diagrams supported**
- 🎨 **Customizable headers (HTML + CSS)**
- 🎨 **Customizable footer (HTML + CSS)**
- 🎨 **Customizable body template (HTML + CSS)**
- 🧩 **Built-in placeholders plus prompted custom placeholders**

---

## 🧪 Valves

### Basic export valves

| Valve | Meaning | Possible values |
|---|---|---|
| `filename_prefix` | Default filename prefix used in fallback name | Any short text, for example `"message"`, `"report"`, `"invoice"` |
| `page_size` | PDF page size | Common values: `"A4"`, `"A3"`, `"A5"`, `"Letter"`, `"Legal"` |
| `margin_mm` | Base page margin. Header/footer heights are added on top | Any non-negative integer, for example `0`, `5`, `10`, `15` |
| `show_page_numbers` | Enables page numbers via `.page-number` CSS helper | `True` or `False` |
| `mermaid_scale` | Browser rasterization scale for Mermaid diagrams | Positive integers, commonly `1`, `2`, `3` |
| `max_mermaid_width_px` | Max Mermaid display width in PDF | Positive integers, for example `600`, `800`, `900`, `1200` |
| `max_mermaid_height_px` | Max Mermaid display height in PDF | Positive integers, for example `300`, `450`, `500`, `700` |

### Header and footer layout valves

| Valve | Meaning | Possible values |
|---|---|---|
| `first_header_height_mm` | Reserved height for first page header | Non-negative integers, for example `0`, `20`, `28`, `35`, `40` |
| `other_header_height_mm` | Reserved height for later-page header | Non-negative integers, for example `0`, `15`, `20`, `25`, `30` |
| `footer_height_mm` | Reserved height for footer | Non-negative integers, for example `0`, `12`, `18`, `24` |

### Template valves

| Valve | Meaning | Possible values |
|---|---|---|
| `global_css` | Shared CSS for the whole document | Put variables, resets, shared classes here |
| `first_header_html` | HTML for first page header | Any valid HTML fragment. Supports placeholders  |
| `first_header_css` | CSS for first page header | Any valid CSS string. Use for branding and layout  |
| `other_header_html` | HTML for headers after page 1 | Any valid HTML fragment, or empty string to reuse first header. Supports placeholders |
| `other_header_css` | CSS for later headers | Any valid CSS string, or empty string to reuse first header CSS |
| `footer_html` | HTML for footer | Any valid HTML fragment. Supports placeholders  |
| `footer_css` | CSS for footer | Any valid CSS string. Use for metadata, page number layout, etc. |
| `body_html_template` | Wrapper HTML for body content | Any valid HTML fragment, but it must include `{{ BODY_CONTENT }}` or `{{ body_content }}` |
| `body_css` | CSS for body area | Any valid CSS string. Controls body typography and content styling |

---

## 🔤 Available placeholders

You can use these inside `first_header_html`, `other_header_html`, `footer_html`, and `body_html_template`.

### Built-in placeholders

These are filled automatically:

- `{{ FILE_NAME }}`
- `{{ EXPORT_DATE }}`
- `{{ EXPORT_TIME }}`
- `{{ EXPORT_TIMESTAMP }}`
- `{{ USER_NAME }}`
- `{{ MESSAGE_ID }}`
- `{{ EXPORT_TITLE }}`
- `{{ BODY_CONTENT }}`
- `{{ PAGE_NUMBER }}`
- `{{ PAGE }}`
- `{{ PAGES }}`

Lowercase aliases remain supported for backward compatibility, for example `{{ body_content }}` and `{{ export_date }}`.

### Custom placeholders

You can add your own placeholders, for example:

- `{{ CLIENT_NAME }}`
- `{{ PROJECT_NAME }}`
- `{{ REVIEWER }}`

When exporting, the action scans the HTML template fragments, detects extra placeholders, and prompts the user for values.

### 📌 Notes

* `body_html_template` **must** contain `{{ BODY_CONTENT }}` or `{{ body_content }}`
* `{{ PAGE_NUMBER }}`, `{{ PAGE }}`, and `{{ PAGES }}` render working page counter markup in HTML templates
* real page numbers can also be shown with:

```html
<div class="page-number"></div>
```

when `show_page_numbers = True`

---

## 👍 Recommended values

```python
filename_prefix = "message"
page_size = "A4"
margin_mm = 5

first_header_height_mm = 28
other_header_height_mm = 20
footer_height_mm = 18

show_page_numbers = False

mermaid_scale = 2
max_mermaid_width_px = 900
max_mermaid_height_px = 500
```

---

## 🧰 Common usage

### 1. Clean export without header/footer

```python
first_header_html = ""
other_header_html = ""
footer_html = ""

first_header_height_mm = 0
other_header_height_mm = 0
footer_height_mm = 0
```

Good for simple notes or study exports.

---

### 2. Same header on all pages

Leave this empty:

```python
other_header_html = ""
other_header_css = ""
```

It will automatically reuse the first-page header HTML/CSS.

---

### 3. Branded company document

Use:

* `first_header_html` for a rich first page
* `other_header_html` for a smaller repeating header
* `footer_html` for metadata, confidentiality, and page number

Example footer snippet:

```html
<div class="doc-footer__left">{{ USER_NAME }}</div>
<div class="doc-footer__center">{{ EXPORT_TIMESTAMP }}</div>
<div class="doc-footer__right page-number"></div>
```

---

### 4. Add a logo

Example:

```html
<img class="doc-logo" src="data:image/png;base64,..." alt="Logo">
```

Best option: use a base64 image for portability.

---

### 5. Large Mermaid diagrams

If diagrams are too large, reduce them safely with:

```python
max_mermaid_width_px = 800
max_mermaid_height_px = 450
```

Aspect ratio stays correct automatically.

---

### 6. Custom body wrapper

Example:

```html
<div class="document-body">
  <div class="report-frame">
    {{ BODY_CONTENT }}
  </div>
</div>
```

Then style `.report-frame` in `body_css`.

---
