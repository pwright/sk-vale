# sk-vale

Validates documentation source files against the AsciiDocDITA Vale ruleset. Converts Markdown (Material for MkDocs) to AsciiDoc, runs structural checks, and traces findings back to the original `.md` source.

## Project layout

```
sk-vale/
  assemblies/          # Generated AsciiDoc assemblies (DO NOT edit directly)
  modules/             # Generated AsciiDoc modules (DO NOT edit directly)
  scripts/             # Build and conversion scripts
    build_index.py     # Markdown→AsciiDoc pipeline orchestrator
    convert-skupper.sh # Full conversion pipeline (clone/convert/lint)
    merge.py           # Heading merger / splitter
  skills/              # Claude Code skills for bridge workflows
    shared/scripts/    # Shared tooling (traceback.py)
  leben.py             # AsciiDoc section splitter (modules + assembly)
  assembly-map.json    # MD path → assembly filename mapping
  vale-report.json     # Latest Vale JSON output
  .vale.ini            # Vale configuration
```

## Two source formats

| Project | Source format | Fix target |
|---------|-------------|------------|
| Apicurio Registry | AsciiDoc (`.adoc`) | Edit `.adoc` directly |
| Skupper | Markdown (`.md`) | Edit `.md` source, then re-convert |

## Converting Skupper docs

```bash
bash scripts/convert-skupper.sh --input-dir /path/to/skupper-docs/doc-input
```

The default local path is `~/repos/sk/skupper-docs/doc-input`.

## Running Vale

```bash
vale assemblies/ modules/           # Lint generated AsciiDoc
vale --output=JSON assemblies/ modules/  # JSON output for tooling
```

## Naming conventions

- Assembly files: `{namespace}-assembly-{name}.adoc`
- Module files: `{namespace}-{module-name}.adoc`
- The namespace is the parent directory of the source `.md` file (e.g., `kube-yaml`, `overview`)

## Bridge skills

Skills in `skills/` bridge the Markdown→AsciiDoc gap:

- `/skupper-convert` — Run the conversion pipeline
- `/skupper-lint` — Vale lint with traceback to `.md` sources
- `/skupper-review` — Full documentation review
- `/skupper-fix` — Apply Vale fixes to `.md` sources
- `/skupper-write` — Write new Markdown content
- `/skupper-assess` — CQA assessment with traceback

These skills use `skills/shared/scripts/traceback.py` to map AsciiDoc findings back to Markdown source files via `assembly-map.json`.

## Key constraint

All Vale rules enforce DITA 1.3 compatibility. No nested sections — each module gets one heading. If the Markdown source has sub-headings, `leben.py` splits them into separate modules automatically.
