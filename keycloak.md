# Keycloak docs linting

Lint Keycloak's generated AsciiDoc guides with Vale.

## Prerequisites

- Java 17+ (for Maven build)
- Python 3
- [Vale](https://vale.sh/docs/install/)
- A local clone of the keycloak repo at `../keycloak` (relative to sk-vale), or specify a path with `--keycloak-dir`

## Scope

The pipeline processes 6 of the 9 FreeMarker guide directories — the ones that ship downstream (confirmed by Andrew Munro):

| Included | Excluded | Reason |
|----------|----------|--------|
| `high-availability/` | `admin-api/` | Not downstream |
| `observability/` | `getting-started/` | Has separate downstream version |
| `operator/` | `migration/` | Explicitly excluded |
| `securing-apps/` | | |
| `server/` | | |
| `ui-customization/` | | |

The `INCLUDE_GUIDES` array in `convert-keycloak.sh` controls which directories are processed.

The 4 traditional modular-docs books under `docs/documentation/` (api_documentation, authorization_services, server_admin, server_development) also ship downstream but need a different processing path — planned but not yet supported.

## Quick start

```bash
cd sk-vale
bash scripts/convert-keycloak-local.sh
```

The first run builds all upstream Maven dependencies (~5-10 min). Subsequent runs only re-run the docs plugins (seconds).

## How it works

1. **Maven build** generates AsciiDoc from FreeMarker templates in the keycloak repo (`docs/guides/target/generated-guides/`)
2. **leben.py** splits each `.adoc` file into single-heading modules and assemblies
3. **Vale** lints the split output against the AsciiDocDITA ruleset

Output lands in:
- `assemblies/` and `modules/` — split AsciiDoc files
- `vale-report.json` — Vale findings in JSON format

## Build options

```bash
# Incremental build (default after first run)
bash scripts/convert-keycloak-local.sh

# Full clean rebuild
bash scripts/convert-keycloak-local.sh --clean

# Skip Maven, reuse existing generated-guides (Vale iteration only)
bash scripts/convert-keycloak-local.sh --skip-build

# Custom keycloak repo location
bash scripts/convert-keycloak-local.sh --keycloak-dir ~/projects/keycloak
```

## Alternatively: use pre-built guides

If you don't need to build from source, `convert-keycloak.sh` can clone the `generated-guides` branch directly from GitHub:

```bash
bash scripts/convert-keycloak.sh
```

This skips the Maven build entirely by fetching pre-built AsciiDoc from the `generated-guides` branch of `pwright/keycloak`.

## Prompt for basics

You are adding heading annotations to Keycloak's AsciiDoc documentation guides so they pass the `ContentType` and `ShortDescription` Vale rules.

### Context

- Source files: `../keycloak/docs/guides/` (the `.adoc` FreeMarker templates, NOT `target/`)
- After editing, verify by running: `bash ../sk-vale/scripts/convert-keycloak-local.sh --keycloak-dir ../keycloak`
- Vale report: `../sk-vale/vale-report.json`
- The fixes will be submitted as a PR to keycloak — only make changes that are clearly correct

### How the pipeline works

1. FreeMarker templates in `docs/guides/` are built by Maven into `target/generated-guides/`
2. `leben.py` splits each generated `.adoc` into assemblies and modules
3. Vale lints the split output

Each guide becomes one **assembly**. Sections within a guide that have an explicit `[[id]]` marker become separate **modules**. Sections without `[[id]]` stay inline in the assembly.

`leben.py` lifts any `:attribute:` lines found at the start of a section body and places them between the `[id="..."]` line and the `= Title` line in the output. This means annotations you add after a heading in the source are correctly positioned in the split output.

### Step 1: Fix all assemblies via the guide template (131 ContentType fixes)

Edit `docs/guides/templates/guide.adoc`. Add `:_mod-docs-content-type: ASSEMBLY` after the title line:

**Before:**
```
[[${id}]]
= ${title}

ifeval::["${preview}" == "true"]
```

**After:**
```
[[${id}]]
= ${title}
:_mod-docs-content-type: ASSEMBLY

ifeval::["${preview}" == "true"]
```

This single change fixes ContentType for all 131 assemblies.

### Step 2: Add `[role="_abstract"]` to each guide (131 ShortDescription fixes)

In each guide source file (e.g., `server/caching.adoc`), add `[role="_abstract"]` on its own line immediately before the first prose paragraph inside the `<@tmpl.guide ...>` block.

**Before:**
```
<@tmpl.guide
title="Configuring distributed caches"
summary="...">

{project_name} is designed for high availability and multi-node clustered setups.
```

**After:**
```
<@tmpl.guide
title="Configuring distributed caches"
summary="...">

[role="_abstract"]
{project_name} is designed for high availability and multi-node clustered setups.
```

Rules for choosing the abstract paragraph:
- Pick the first plain-text paragraph after the guide opening
- Skip any `ifeval` blocks, admonitions, or FreeMarker directives — put `[role="_abstract"]` before the first actual prose
- The paragraph should be plain text (no bold, no links at the start, no list items)

### Step 3: Add content-type to each module section (96 ContentType fixes)

Find sections with explicit `[[id]]` markers in the source guides (~23 files have these). Add `:_mod-docs-content-type: TYPE` on the line immediately after the `==` heading.

**Before:**
```
[[cache-topology]]
== Topology aware data distribution

Configuring {project_name} to be aware of your network topology...
```

**After:**
```
[[cache-topology]]
== Topology aware data distribution
:_mod-docs-content-type: CONCEPT

[role="_abstract"]
Configuring {project_name} to be aware of your network topology...
```

#### Content-type classification rules

| Type | When to use | Heading signals |
|------|------------|----------------|
| `PROCEDURE` | Section tells the reader how to do something | Gerunds: "Configuring...", "Creating...", "Installing...". Imperatives: "Create a...", "Add a..." |
| `REFERENCE` | Section lists facts, parameters, or specifications | Noun phrases: "...endpoint", "...options", "...parameters". Tables of settings |
| `CONCEPT` | Section explains why something works or architecture | "...considerations", "Comparison of...", "How ... works", "...overview" |

When ambiguous, prefer `REFERENCE` over `CONCEPT` (fewer downstream Vale constraints). Never use `ASSEMBLY` for modules.

### Step 4: Add `[role="_abstract"]` to each module section (96 ShortDescription fixes)

In the same `[[id]]` sections fixed in Step 3, add `[role="_abstract"]` before the first prose paragraph. Follow the same rules as Step 2.

### Do NOT fix

- **LineBreak** — most come from generated FreeMarker tables
- **NestedSection** — handled by the splitter
- **CalloutList** — requires rewriting code examples

### FreeMarker caution

- Do not modify `<#import>`, `<@template>`, `<#if>`, `<#list>`, `${variable}`, `<#macro>`, or `<#nested>` directives
- Insert AsciiDoc annotations around FreeMarker blocks, not inside them
- Do not put annotations inside `ifeval::` blocks

### Workflow

1. Start with the `guide.adoc` template change (Step 1) — one edit, 131 fixes
2. Work through guide source files by directory (`server/`, `getting-started/`, `high-availability/`, etc.)
3. For each file:
   a. Add `[role="_abstract"]` before the first prose paragraph (assembly ShortDescription)
   b. Find all `[[id]]` sections and add content-type + abstract (module ContentType + ShortDescription)
4. After fixing a batch (5-10 files), run `--skip-build` to verify counts dropped
5. Report: which files changed, old total, new total

## Prompt for tidy

You are fixing Vale linting issues in Keycloak's AsciiDoc documentation guides.

  ## Context

  - Source files: ../keycloak/docs/guides/ (the .adoc templates, NOT target/)
  - Some files are FreeMarker templates (.adoc with <#import>, <@template> etc.) — edit the prose, not the 
  FreeMarker logic
  - After editing, verify by running: bash 
  ../sk-vale/scripts/convert-keycloak-local.sh --keycloak-dir ../keycloak
  - Vale report: ../sk-vale/vale-report.json
  - The fixes will be submitted as a PR to keycloak — reviewers are skeptical of drive-by style changes, so only make changes that are clearly correct and don't alter meaning

  ## Rules to fix (easy wins only)

  Fix ONLY these rules, in this priority order:

  1. **AsciiDocDITA.BlockTitle** (46 issues) — Remove `.Title` lines from blocks that aren't examples, 
  figures, or tables. If the title is important, convert the block to a titled example or move the title text into the prose.

  2. **AsciiDocDITA.RelatedLinks** (13 issues) — "Additional resources" or "Related" sections must contain only links. Move non-link prose out of these sections.

  3. **AsciiDocDITA.ExampleBlock** (8 issues) — Unwrap unnecessary `====` example block delimiters when the content works without them.

  4. **AsciiDocDITA.DiscreteHeading** (1 issue) — Replace `[discrete]` heading with a bold line or  restructure.

  5. **AsciiDocDITA.AdmonitionTitle** (1 issue) — Remove the custom title from the admonition.

  ## Do NOT fix

  - LineBreak — most come from generated FreeMarker tables, not worth touching
  - NestedSection — structural, handled by the splitter
  - ContentType / ShortDescription — require content judgment, save for later
  - CalloutList — requires rewriting code examples, not a quick win

  ## Workflow

  1. Read vale-report.json to find files with the target rules
  2. Map each finding back to its source template in docs/guides/
  3. Edit the source .adoc file (be careful with FreeMarker syntax)
  4. After fixing a batch, run the build script to verify the count dropped
  5. Report: which files changed, how many findings fixed, new total