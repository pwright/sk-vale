# Markdown-to-AsciiDoc Conversion Pipeline

How Skupper documentation flows from Material for MkDocs Markdown to DITA-compatible AsciiDoc modules and assemblies.

## Entry point

```bash
bash scripts/convert-skupper.sh --input-dir ~/repos/sk/skupper-docs/doc-input
```

The script orchestrates three stages: build, Vale lint, and HTML generation. The build stage is the one that matters for content structure.

## Pipeline stages

### Stage 1: prepare_markdown_for_kramdoc (merge.py)

Runs per-file before kramdoc. Transforms Markdown conventions into raw AsciiDoc metadata that kramdoc will pass through.

What it does:

- **Content-type markers** — `<!--ASSEMBLY-->`, `<!--REFERENCE-->`, `<!--PROCEDURE-->` comments become `:_mod-docs-content-type:` attributes.
- **Abstract injection** — The first plain-text paragraph after a heading gets `[role="_abstract"]`.
- **DITA section titles** — Bold markers like `**Prerequisites**`, `**Procedure**`, `**Verification**` become `.Prerequisites`, `.Procedure`, etc. (AsciiDoc block titles). `**Additional resources**` also gets `[role="_additional-resources"]`.
- **Procedure block titles** — If a PROCEDURE section has an ordered list but no `.Procedure` title, one is inserted.
- **External link stripping** — Reference-style link definitions pointing to `github.io` are removed along with their usages.

### Stage 2: kramdoc

```
kramdoc --format=GFM -o source.adoc prepared.md
```

Converts GFM Markdown to AsciiDoc. Key behaviors:

- `#` → `=`, `##` → `==`, `###` → `===` (heading levels)
- Pipe tables → `|===` tables
- Fenced code blocks → `[source,lang]` + `----` delimiters
- `<a id="..."></a>` anchors → passthrough HTML (normalized later)
- Admonitions (`> **NOTE:**`) → blockquote-style admonition blocks

### Stage 3: convert_adoc_ids (merge.py)

Post-processes kramdoc output:

- **HTML anchor normalization** — `<a id="x"></a>` → `[id="x"]`
- **Section ID normalization** — Kramdoc-style section IDs → `[id="..."]`
- **Admonition conversion** — Sidebar (`****`) and blockquote (`____`) admonitions → proper example blocks (`====`)
- **Language attribute fix** — `[,yaml]` → `[source,yaml]`
- **Attribute substitution** — Adds `subs="attributes+"` to code blocks containing `{attribute_name}` references (for Jinja-style variables like `{{skupper_cli_version}}`)

### Stage 4: leben.py (section splitter)

Splits each AsciiDoc file into one assembly and multiple modules.

**Split rules:**

- The first `==` section becomes the **assembly** (includes assembly body + `include::` directives)
- Each subsequent `==` section becomes a **module** (one file per section)
- Module filenames derive from the `[id="..."]` anchor: `observer-images.adoc`
- Assembly filenames: `assembly-observer-config.adoc`

**Nested section handling** (`_flatten_nested_sections`):

`===` headings (from `###` in Markdown) cannot exist in DITA-compatible modules (one heading per module). They are converted to:

- **`.Title`** (table caption) — when the next non-blank line starts with `|===`
- **`**Bold**`** (inline heading) — otherwise

This is the mechanism that controls table captions. A `###` heading produces a table caption **only** if the table immediately follows (no text in between).

### Stage 5: build_index.py (orchestrator)

Coordinates the full pipeline per markdown file:

1. Calls `merge.prepare_markdown_file()` → prepared markdown
2. Calls `kramdoc` → raw AsciiDoc
3. Calls `merge.convert_adoc_ids()` → normalized AsciiDoc
4. Calls `leben.py` → assemblies/ + modules/
5. Namespaces output files: `{directory}-{filename}.adoc` (e.g., `kube-yaml-kube-site-resources-yaml.adoc`)
6. Rewrites `include::` paths in assemblies to use namespaced module names
7. Resolves internal cross-references (`link:page.html#anchor` → `xref:id_{context}`)
8. Writes `assembly-map.json` mapping `md-path → assembly-filename`

The index file (`mkdocs.yml`) controls which Markdown files are processed and their ordering.

## How table captions work

Tables in the AsciiDoc output get captions (`.Title` lines) through this chain:

```
Markdown                  kramdoc              leben.py
───────                   ───────              ────────
### Heading        →      === Heading    →     .Heading        (table caption)
                          |===                 |===

### Heading        →      === Heading    →     **Heading**     (bold text, NO caption)
Some text                 Some text
                          |===                 |===

(no heading)       →      |===           →     |===            (NO caption)
| col1 | col2 |
```

**Rule:** To give a table a caption, place a `###` heading directly before it with no intervening text. Any paragraph between the `###` and the table causes the heading to become bold text instead.

**If text must accompany the table:** Move it after the table, not before.

## How DITA section titles work

Certain bold markers in Markdown are recognized as DITA structural elements:

| Markdown | AsciiDoc output | Purpose |
|----------|----------------|---------|
| `**Prerequisites**` | `.Prerequisites` | Block title for prereqs list |
| `**Procedure**` | `.Procedure` | Block title for steps |
| `**Verification**` | `.Verification` | Block title for verification steps |
| `**Additional resources**` | `[role="_additional-resources"]` + `.Additional resources` | Semantic role + title |

These are handled by `normalize_dita_section_titles()` in merge.py, not by kramdoc.

## How content types work

HTML comments in Markdown signal the module type:

| Marker | AsciiDoc attribute | Meaning |
|--------|-------------------|---------|
| `<!--ASSEMBLY-->` | `:_mod-docs-content-type: ASSEMBLY` | Container that includes modules |
| `<!--REFERENCE-->` | `:_mod-docs-content-type: REFERENCE` | Reference/configuration table |
| `<!--PROCEDURE-->` | `:_mod-docs-content-type: PROCEDURE` | Task with steps |
| `<!--CONCEPT-->` | `:_mod-docs-content-type: CONCEPT` | Conceptual explanation |

Place the marker on the line immediately after the `##` heading.

## File naming

| Type | Pattern | Example |
|------|---------|---------|
| Module | `{namespace}-{id}.adoc` | `console-observer-images.adoc` |
| Assembly | `{namespace}-assembly-{id}.adoc` | `console-assembly-observer-config.adoc` |
| Namespace | Parent directory of the `.md` file | `kube-yaml`, `console`, `overview` |

## Prerequisites

Tools required by the pipeline:

- `python3` — runs merge.py, build_index.py, leben.py
- `kramdoc` — `gem install kramdown-asciidoc` (Markdown → AsciiDoc converter)
- `vale` — documentation linter
- `asciidoc-comments` — `npm install -g @techwriter/asciidoc-comments` (HTML generation)

## Key files

| File | Role |
|------|------|
| `scripts/convert-skupper.sh` | Shell entry point, orchestrates everything |
| `scripts/build_index.py` | Per-file pipeline orchestrator |
| `scripts/merge.py` | Markdown preparation + AsciiDoc post-processing |
| `leben.py` | AsciiDoc section splitter (modules + assemblies) |
| `assembly-map.json` | Maps `md-path → assembly-filename` for traceability |
| `.vale.ini` | Vale linter configuration |
