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

### How splitting changes headings

Use `--flatten-from-level N` to choose the heading level at which unanchored headings
in module bodies become bold paragraphs or table titles. Values 2–6 are accepted;
the default is 3, preserving the existing behavior. For example:

```bash
python3 leben.py path/to/file.adoc --flatten-from-level 2
```

This flattens unanchored `==` headings and deeper headings. With
`--flatten-from-level 4`, unanchored `==` and `===` headings remain unchanged.
The option applies to every file selected by the input path, glob, or directory.

`leben.py` uses explicit IDs (`[[id]]` or `[id="..."]`) to determine where files split. The first ID identifies the assembly; subsequent IDs start modules. For a heading to become a module title, it must immediately follow the ID line.

The following table shows the default behavior (`--flatten-from-level 3`):

| Source heading | With an ID immediately before it | Without an ID, inside a module |
|---|---|---|
| `== Title` | Separate module with `= Title`; included with `leveloffset=+1` | Remains `== Title` |
| `=== Title` | Separate module with `= Title`; included with `leveloffset=+2` | Becomes `**Title**` |
| `==== Title` | Separate module with `= Title`; included with `leveloffset=+3` | Becomes `**Title**` |

Deeper headings follow the same pattern: module titles become `= Title`, and the assembly's include offset preserves the original heading level. Unanchored headings of level three or deeper become bold paragraphs inside module bodies.

For example, this source:

```asciidoc
[[configuration]]
==== Configuration
```

produces `modules/configuration.adoc` with an `= Configuration` title and this assembly include:

```asciidoc
include::../modules/configuration.adoc[leveloffset=+3]
```

If an unanchored heading at or above the configured threshold is followed by a table, with only optional blank lines between them, it becomes a table title (`.Title`) instead of a bold paragraph. Flattening applies only to module bodies; headings in the assembly introduction remain unchanged. Headings below the threshold remain unchanged, so splitting does not guarantee that every nested section is removed. The option does not change ID-based module boundaries, module titles, or include offsets.

A bare `====` without heading text is an AsciiDoc example-block delimiter and remains unchanged by this transformation.

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

## Keycloak linting workflow

This workflow builds AsciiDoc guides from a local Keycloak checkout, resolves AsciiDoc conditionals for `project_product` content, splits the guides with `leben.py`, and runs Vale.

### Content included

The local build uses `docs/guides/pom.xml` and reads the generated files from `docs/guides/target/generated-guides/`. Only these guide directories are processed:

- `high-availability/`
- `observability/`
- `operator/`
- `securing-apps/`
- `server/`
- `ui-customization/`

The `admin-api/`, `getting-started/`, and `migration/` guide directories are excluded. Content under `docs/documentation/`, including the administration, authorization services, server development, and API documentation books, is not processed.

### Build and lint locally

Prerequisites: Git, JDK 21, `python3`, `vale`, and a local Keycloak checkout. Maven runs through Keycloak's `./mvnw` wrapper; a separate Maven installation is not required.

Use JDK 21 for the checkout that sets `maven.compiler.release` to `8` in `common/pom.xml`. This is the module's compatibility target, not the Java version needed to run the server. JDK 25 cannot compile that target and fails with `release version 8 not supported`.

On Fedora 44, install Temurin 21 through the Adoptium repository:

```bash
sudo dnf install adoptium-temurin-java-repository
sudo dnf install temurin-21-jdk
```

From this repository, build and lint a Keycloak checkout at `../keycloak`:

```bash
JAVA_HOME=/usr/lib/jvm/temurin-21-jdk bash scripts/convert-keycloak-local.sh
```

For another JDK distribution, set `JAVA_HOME` to its JDK 21 installation directory. To use a different Keycloak checkout:

```bash
JAVA_HOME=/usr/lib/jvm/temurin-21-jdk bash scripts/convert-keycloak-local.sh --keycloak-dir ~/projects/keycloak
```

The first run builds the guides and their upstream Maven dependencies. Once `target/generated-guides/` exists, subsequent runs build only the guides module.

```bash
# Force a full clean rebuild, including upstream dependencies
JAVA_HOME=/usr/lib/jvm/temurin-21-jdk bash scripts/convert-keycloak-local.sh --clean

# Reuse existing generated guides without running Maven
bash scripts/convert-keycloak-local.sh --skip-build
```

After editing source templates, run the build again so the generated guides include your changes. `--skip-build` only lints the previously generated content.

Results are written to `assemblies/`, `modules/`, and `vale-report.json`. Each conversion replaces the existing `assemblies/` and `modules/` directories. Make documentation fixes in the Keycloak source templates, not in these generated files.

### Lint pre-built guides

To skip the local Maven build, fetch pre-built AsciiDoc from the `generated-guides` branch of `pwright/keycloak`:

```bash
bash scripts/convert-keycloak.sh
```

Alternatively, lint an existing generated-guides directory:

```bash
bash scripts/convert-keycloak.sh --input-dir ../keycloak/docs/guides/target/generated-guides
```

See [`keycloak.md`](./keycloak.md) for additional Keycloak workflow details.

## Supporting docs

- [`markdown.md`](./markdown.md) describes the Markdown conversion workflow in detail.
- [`leben.md`](./leben.md) explains how `leben.py` splits flat AsciiDoc files.

