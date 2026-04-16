# sk-vale

This repository is a working area for Apicurio/Skupper documentation in AsciiDoc, with Vale checks and a small set of helper scripts for splitting, validating, and generating documentation sets.

The primary use of this repo is plain AsciiDoc. The Markdown conversion path exists for Skupper and bulk-generation work, but it is not the default authoring model.

## Repo purpose

- Maintain AsciiDoc assemblies and modules for Apicurio/Skupper documentation.
- Validate the content against the AsciiDocDITA Vale ruleset.
- Support generation tasks such as splitting a flat `.adoc` file into `assemblies/` and `modules/`.
- Support a secondary Markdown-to-AsciiDoc pipeline when source material lives outside this repo, output to `output/`.

## Main directories

- `assemblies/` contains assembly files.
- `modules/` contains reusable topic files.
- `output/` contains generated build output, including a generated `index.adoc` tree (md path only)
- `scripts/` contains helper scripts for merging and generating content.
- `.vale/` and `.vale.ini` configure Vale.

## Primary workflow: plain AsciiDoc

Use this workflow when `assemblies/` and `modules/` are the source of truth.

Edit the AsciiDoc directly in:

- `assemblies/`
- `modules/`

Run Vale against the authored content:

```bash
vale assemblies/ modules/
```

If you need to split one large AsciiDoc file into an assembly plus modules, use `leben.py`:

```bash
python3 leben.py path/to/file.adoc
```

`leben.py` writes:

- `assemblies/assembly-*.adoc`
- `modules/*.adoc`

This is useful when you start with one flat AsciiDoc source and want repo-style structure.

## Secondary workflow: Markdown to AsciiDoc

Use this workflow only when the source of truth is Markdown outside this repo, for example under `../docs-vale/input/`.

The Markdown path exists to:

- merge a Markdown tree,
- convert it with `kramdoc`,
- normalize IDs and metadata,
- split the result into assemblies and modules,
- generate a full `output/` tree.

Key scripts:

- `scripts/merge.py` prepares Markdown and normalizes generated AsciiDoc.
- `scripts/build_index.py` converts a Markdown tree referenced by `index.html.in` into `output/assemblies/`, `output/modules/`, `output/images/`, and `output/index.adoc`.
- `leben.py` splits converted flat AsciiDoc into assembly/module files.

Typical generated-site command:

```bash
python3 scripts/build_index.py ../docs-vale/input/index.html.in -o output --clean
```

For this workflow, treat generated files as build artifacts rather than hand-edited source.

## Supporting docs

- [`markdown.md`](./markdown.md) describes the Markdown conversion workflow in detail.
- [`leben.md`](./leben.md) explains how `leben.py` splits flat AsciiDoc files.

