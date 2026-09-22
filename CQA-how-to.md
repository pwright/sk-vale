# CQA 2.1 Content Quality Assessment — How-To Guide

This guide documents the CQA workflow for the Skupper (Service Interconnect) documentation, where the source of truth is **Markdown** in `skupper-docs/` and the published format is **AsciiDoc** generated via a conversion pipeline.

## Architecture

```
skupper-docs/input/           Markdown source (edit here)
        |
        v
    merge.py (prepare)        Inject metadata, normalize DITA sections
        |
        v
    kramdoc (GFM → AsciiDoc)  Convert Markdown to AsciiDoc
        |
        v
    merge.py (normalize)      Fix IDs, admonitions, source blocks
        |
        v
    leben.py (split)          Split into assemblies + modules
        |
        v
sk-vale/assemblies/           Generated AsciiDoc (assessed here)
sk-vale/modules/
```

## Principle: Fix in Markdown, Not in Scripts

Always prefer fixing content issues in the Markdown source over modifying pipeline scripts. Script changes are only appropriate when:

- kramdoc produces output that cannot be controlled from Markdown (e.g., `[,bash]` → `[source,bash]` conversion)
- A structural bug in the pipeline corrupts correct source content (e.g., `leben.py` converting `====` admonition delimiters to `****` sidebar blocks)

If a CQA issue can be resolved by editing the Markdown, do that. Document any necessary script fixes separately.

## Running the Assessment

### 1. Generate AsciiDoc from Markdown

From `sk-vale/`:

```bash
bash scripts/convert-skupper.sh --input-dir ../skupper-docs/input
```

This runs the full pipeline: prepare → kramdoc → normalize → split → Vale → HTML.

The script prints Vale results as JSON. `{}` means 0 errors, 0 warnings.

### 2. Run the CQA Assessment

```
/cqa-tools:cqa-assess @sk-vale/docs/ --scope assembly --mode assess
```

Choose the assembly and mode when prompted. The assessment covers 54 parameters across three tabs:

| Tab | Parameters | Focus |
|-----|-----------|-------|
| Pre-migration (P1-P19) | 19 | Vale, modularization, titles, links, branding |
| Quality (Q1-Q25) | 25 | Readability, editorial, user focus, navigation |
| Onboarding (O1-O10) | 10 | Legal, publishing, infrastructure |

### 3. Fix Issues in Markdown

Apply fixes in `skupper-docs/input/<section>/index.md`. The table below maps CQA issues to Markdown fixes:

| CQA Issue | Markdown Fix |
|-----------|-------------|
| Gerund titles (P11) | Change `## Checking sites` → `## Check sites` (imperative) |
| Self-referential abstract (P5, Q11) | Rewrite "This guide provides..." → action-oriented sentence |
| Blank line after abstract (P5, P9) | N/A — fixed in pipeline (`merge.py`) |
| Contraction (P13, Q18, Q20) | Change "don't" → "do not" |
| Emoji pseudo-admonitions (P4, Q10) | Change `**📌 NOTE**` → `> **NOTE:**` blockquote format |
| Self-referential body text (Q2, Q5) | Remove "This section outlines..." — state the fact directly |
| Missing `.Verification` (Q15) | Add `**Verification**` section after procedure steps |
| Missing `.Additional resources` (Q9, Q16) | Add `**Additional resources**` with `[link text](#anchor)` links |
| YAML acronym not expanded (Q8) | Expand on first use: "YAML (YAML Ain't Markup Language)" |
| Port inconsistency (P13) | Fix text to match command output |

### 4. Regenerate and Verify

```bash
bash scripts/convert-skupper.sh --input-dir ../skupper-docs/input
```

Check that Vale output is `{}` (clean). If not, fix the issues and re-run.

### 5. Re-run Assessment

Re-run `/cqa-tools:cqa-assess` to get updated scores. The report is written to `CQA-2.1-Assessment-Report.md`.

## Markdown Patterns for AsciiDoc Features

The pipeline converts these Markdown patterns to AsciiDoc:

### DITA Section Titles

Write as bold text on its own line. The pipeline converts to AsciiDoc block titles:

```markdown
**Procedure**           →  .Procedure
**Prerequisites**       →  .Prerequisites
**Verification**        →  .Verification
**Additional resources** →  .Additional resources
```

### Admonitions

Use blockquote format with bold type label:

```markdown
> **NOTE:**
> Content of the note.
```

Pipeline converts to:

```asciidoc
[NOTE]
====
Content of the note.
====
```

Supported types: `NOTE`, `WARNING`, `IMPORTANT`, `TIP`, `CAUTION`.

### Cross-References (xrefs)

Use Markdown anchor links. The pipeline converts to AsciiDoc xrefs:

```markdown
[Checking sites](#checking-sites)
```

Becomes:

```asciidoc
<<checking-sites,Checking sites>>
```

Use gerund form for link text in Additional resources sections (describes the topic for navigation), even though procedure titles use imperative form.

### Content Type Markers

Use HTML comments after the heading:

```markdown
## Check sites
<!--PROCEDURE-->

## Overview
<!--CONCEPT-->
```

### Source Blocks

Use standard Markdown fenced code blocks. The pipeline converts `[,bash]` → `[source,bash]` automatically:

````markdown
```bash
skupper site status
```
````

### Anchors (IDs)

Use HTML anchor tags before the heading:

```markdown
<a id="checking-sites"></a>
## Check sites
```

## Pipeline Fixes (Script-Level)

These fixes were required because kramdoc or leben.py produced incorrect output that cannot be controlled from Markdown:

| Script | Fix | Why |
|--------|-----|-----|
| `merge.py` | Remove blank line after `[role="_abstract"]` | Pipeline inserted extra `\n` causing empty DITA abstracts |
| `merge.py` | Convert blockquote admonitions (`____`/`*NOTE:*`) to `[NOTE]\n====` | kramdoc produces blockquote format from `>` syntax |
| `merge.py` | Convert `[,bash]` → `[source,bash]` | kramdoc omits `source,` prefix needed for ccutil/DITA |
| `leben.py` | Fix `RE_NESTED_SECTION` regex: `\s+` → `[ \t]+` | `\s+` matched `\n` on bare `====` delimiters, converting them to `****` sidebar blocks |

## Scoring Reference

| Average Score | Rating |
|---------------|--------|
| 3.5+ | Meets criteria |
| 3.0–3.4 | Mostly meets |
| 2.5–2.9 | Mostly does not meet |
| Below 2.5 | Does not meet |

## Score History

| Date | Overall | Pre-migration | Quality | Onboarding |
|------|---------|---------------|---------|------------|
| 2026-09-22 (initial) | 2.89 | 3.05 | 2.96 | 2.40 |
| 2026-09-22 (round 1) | 3.13 | 3.32 | 3.28 | 2.40 |
| 2026-09-22 (round 2) | 3.28 | 3.37 | 3.56 | 2.40 |

## Remaining Gaps (Not Fixable in Markdown)

| Issue | Parameters | Scope | Notes |
|-------|-----------|-------|-------|
| File naming prefixes (`assembly_`, `proc_`) | P3 | Repo-wide (93 files) | Requires pipeline naming convention change |
| IDs lack `_{context}` suffix | P4, P6 | Repo-wide | Requires pipeline and assembly changes |
| Product name attributes | P18, O1, O3 | Repo-wide | Requires `common/attributes.adoc` |
| Publishing infrastructure | O2, O8, O9, O10 | Repo-wide | Requires `titles/`, `pantheon/`, `LICENSE` |
