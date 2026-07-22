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
- `scripts/` contains helper scripts for merging, converting, and generating content.
- `.github/workflows/` contains the GitHub Action for automated skupper-docs linting.
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
- `scripts/build_index.py` converts a Markdown tree referenced by an index file (`index.md` or `index.html.in`) into `output/assemblies/`, `output/modules/`, `output/images/`, and `output/index.adoc`.
- `scripts/convert-skupper.sh` runs the full skupper-docs pipeline (see below).
- `leben.py` splits converted flat AsciiDoc into assembly/module files.

Typical generated-site command:

```bash
python3 scripts/build_index.py ../docs-vale/input/index.md -o output --clean
```

For this workflow, treat generated files as build artifacts rather than hand-edited source.

## Skupper-docs linting workflow

This workflow converts Markdown from [skupperproject/skupper-docs](https://github.com/skupperproject/skupper-docs) to AsciiDoc and runs Vale linting.

By default, the script clones skupper-docs `main` from GitHub. Use `--input-dir` to point at a local directory instead. Use `--commit` to commit results to the `skupper` branch (without it, the script only runs the pipeline and prints Vale output).

### Run locally

Clone skupper-docs from GitHub and lint:

```bash
bash scripts/convert-skupper.sh
```

Use a local directory as input:

```bash
bash scripts/convert-skupper.sh --input-dir ../skupper-docs/input
```

Clone from GitHub, lint, and commit to the `skupper` branch:

```bash
bash scripts/convert-skupper.sh --commit
```

Prerequisites: `python3`, `kramdoc` (`gem install kramdown-asciidoc`), and `vale`.

### Pipeline steps

1. Merge all Markdown referenced by `index.md` into `merged.md`
2. Convert to AsciiDoc with `kramdoc --format=GFM`
3. Normalize AsciiDoc IDs
4. Split into `assemblies/` and `modules/` with `leben.py`
5. Run `vale assemblies/ modules/`

### Automated linting

A GitHub Action (`.github/workflows/skupper-vale.yml`) runs the pipeline weekly, on push to `main`, and on manual dispatch. Results are force-pushed to the `skupper` branch.

### The skupper branch contains

- `merged.md` -- merged Markdown from all skupper-docs index entries
- `merged.adoc` -- kramdoc-converted AsciiDoc
- `assemblies/` -- split assembly files
- `modules/` -- split module files

## Apicurio-registry linting workflow

This workflow runs Vale linting on AsciiDoc from [apicurio/apicurio-registry](https://github.com/apicurio/apicurio-registry). The source is already AsciiDoc (Antora structure), so no Markdown conversion is needed -- `leben.py` splits the flat files into `assemblies/` and `modules/`, then Vale lints them.

By default, the script clones apicurio-registry `main` from GitHub. Use `--input-dir` to point at a local checkout instead. Use `--commit` to commit results to the `apicurio` branch (without it, the script only prints Vale output).

### Run locally

Clone apicurio-registry from GitHub and lint:

```bash
bash scripts/convert-apicurio.sh
```

Use a local checkout as input:

```bash
bash scripts/convert-apicurio.sh --input-dir ../apicurio-registry
```

Clone from GitHub, lint, and commit to the `apicurio` branch:

```bash
bash scripts/convert-apicurio.sh --commit
```

Prerequisites: `python3` and `vale`.

## Supporting docs

- [`markdown.md`](./markdown.md) describes the Markdown conversion workflow in detail.
- [`leben.md`](./leben.md) explains how `leben.py` splits flat AsciiDoc files.

