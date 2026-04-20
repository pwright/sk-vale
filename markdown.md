# Markdown to AsciiDoc Vale Workflow

## Goal

Use Markdown as the source of truth, convert it to AsciiDoc, split it with `leben.py`, and run Vale on the generated assembly and modules.

Corrections always go back into the original Markdown source.

## Source of truth

Edit the Markdown source files, for example under `../docs-vale/input/`.

Treat these as generated artifacts:

- `merged.md`
- `merged.adoc`
- `assemblies/`
- `modules/`

Do not fix Vale findings in generated AsciiDoc unless you are debugging the tooling itself.

## Section markers in Markdown

The Markdown source should use lightweight comment markers instead of raw AsciiDoc metadata:

```md
<!--ASSEMBLY-->
<!--PROCEDURE-->
<!--REFERENCE-->
```

Place the marker immediately after the heading it applies to.

Example:

```md
<a id="kube-checking-cli"></a>
## Checking the Skupper CLI
<!--PROCEDURE-->

Installing the skupper command-line interface (CLI) provides a simple method to get started with Skupper.

**Procedure**

1. Follow the instructions...
```

## What `scripts/merge.py` does

[`scripts/merge.py`](/home/paulwright/repos/sk/vale/sk-vale/scripts/merge.py) now has three relevant jobs in this workflow:

1. Merge a Markdown tree into one file while fixing links and deduplicating anchors.
2. Prepare Markdown markers for `kramdoc` by converting comment markers into raw AsciiDoc metadata.
3. Normalize `kramdoc` output so `leben.py` can parse IDs correctly.

### Metadata preparation

When Markdown is prepared for conversion, the script:

- Converts `<!--ASSEMBLY-->`, `<!--PROCEDURE-->`, and `<!--REFERENCE-->` into `:_mod-docs-content-type: ...`
- Inserts `[role="_abstract"]` before the first suitable short plain-text paragraph in the section
- Converts `**Procedure**` to `.Procedure` for procedure sections
- Warns if a marked section does not contain a suitable short plain-text paragraph for the abstract

The abstract warning is emitted to `stderr`. It means the source probably needs a short descriptive paragraph near the top of the section.

### ID normalization

After `kramdoc`, the script rewrites these forms into `[id="..."]`:

- `[#id]`
- `+++<a id="id"></a>+++`

It also removes the blank line that `kramdoc` leaves between an ID and its heading, because `leben.py` expects the ID to sit directly above the heading.

## Full tree workflow

Run the workflow from `sk-vale/`.

### 1. Merge and prepare the Markdown

```bash
python3 scripts/merge.py ../docs-vale/input/index.html.in -o merged.md
```

This merged output is already prepared for `kramdoc`. You do not need a separate `--prepare-md` step for the merged-tree workflow.

### 2. Convert to AsciiDoc

```bash
kramdoc --format=GFM -o merged.adoc merged.md
```

Do not use `--auto-ids` when the source already contains explicit anchors such as `<a id="..."></a>`, because that creates duplicate IDs and can cause `leben.py` to over-split the document.

### 3. Normalize the AsciiDoc IDs

```bash
python3 scripts/merge.py --normalize-adoc-ids merged.adoc
```

### 4. Split into assembly and modules

```bash
python3 leben.py merged.adoc
```

This writes:

- `assemblies/`
- `modules/`

### 5. Run Vale

```bash
vale assemblies/ modules/
```

## Index wrapper workflow

If you want to process every local Markdown page referenced by `index.html.in` as separate assemblies instead of merging everything into one file first, use [`scripts/build_index.py`](/home/paulwright/repos/sk/vale/sk-vale/scripts/build_index.py).

Example:

```bash
python3 scripts/build_index.py ../docs-vale/input/index.html.in -o output --clean
```

That wrapper:

1. Reads local `.html` links from `index.html.in`.
2. Skips templated or external links that do not resolve to local Markdown files.
3. Runs the per-file conversion flow for each source:
   `--prepare-md -> kramdoc -> --normalize-adoc-ids -> leben.py`
4. Writes generated files into shared top-level directories:
   `output/assemblies/`, `output/modules/`, and `output/images/`
5. Copies referenced image assets into `output/images/` and rewrites AsciiDoc image references to `./images/<file>`
6. Rewrites local internal `.html` links to `xref:<target-id>[...]` by using the target page or fragment ID
7. Creates `output/index.adoc` with `include::` directives for the generated assemblies in the same order as `index.html.in`

The generated root `index.adoc` also includes:

- `:toc: left`
- `:toclevels: 3`
- `:sectnums:`

It does not add introductory abstract text before the includes.

To avoid filename collisions, the wrapper prefixes generated filenames with the parent directory of the source Markdown file. For example:

- `kube-cli-kube-link-cli.adoc`
- `system-cli-kube-link-cli.adoc`

This allows different source trees to generate the same base module ID without overwriting each other in the shared `output/modules/` directory.

Use `--clean` when you want the wrapper to remove the target output directory before rebuilding so stale files do not remain from earlier runs.

## Single-file workflow

For testing one Markdown file in isolation, prepare it explicitly before `kramdoc`:

```bash
python3 scripts/merge.py --prepare-md ../docs-vale/input/kube-cli/site-configuration.md -o /tmp/site-configuration.prepared.md
kramdoc --format=GFM -o /tmp/site-configuration.adoc /tmp/site-configuration.prepared.md
python3 scripts/merge.py --normalize-adoc-ids /tmp/site-configuration.adoc
python3 leben.py /tmp/site-configuration.adoc
vale assemblies/ modules/
```

Run `leben.py` from a temp working directory if you do not want `assemblies/` and `modules/` written into `sk-vale/`.

## Correction loop

Use this loop:

1. Edit the original Markdown.
2. Merge or prepare the Markdown.
3. Run `kramdoc`.
4. Normalize IDs.
5. Run `leben.py`.
6. Run `vale`.
7. Put any fixes back into the Markdown source and repeat.

## Practical rules

- Keep a short plain-text paragraph near the top of each marked section so the script can generate `[role="_abstract"]`.
- Use `**Procedure**` in Markdown for task sections; the prep step converts it to `.Procedure`.
- Keep explicit anchors such as `<a id="..."></a>` when you need stable IDs.
- If Vale fails because the converted structure is poor, first try to improve the Markdown structure before changing the scripts.
- Do not remove existing comments in markdown.

