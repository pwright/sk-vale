# AGENTS.md

This repo validates documentation source files against the AsciiDocDITA Vale ruleset. Your job is to fix the source files so they pass `vale` with zero errors and zero warnings.

## Two source formats

| Project | Source format | Source location | Fix target |
|---------|-------------|-----------------|------------|
| Apicurio Registry | AsciiDoc (`.adoc`) | `modules/`, `assemblies/` | Edit the `.adoc` files directly |
| Skupper | Markdown (`.md`) | External `skupper-docs` repo | Edit the `.md` source before conversion |

Skupper Markdown is converted to AsciiDoc via `scripts/convert-skupper.sh`. If Vale flags a converted `.adoc` file, trace the problem back to the originating `.md` file and fix it there.

## How to run the linter

For AsciiDoc files already in the repo:

```bash
vale assemblies/ modules/
```

For the full Skupper pipeline (clone, convert, lint):

```bash
bash scripts/convert-skupper.sh
```

For Apicurio (clone, split, lint):

```bash
bash scripts/convert-apicurio.sh
```

## How to fix Vale violations

**Do not guess.** Follow this process:

1. Run `vale` and read the output. Each line gives: file, line number, rule name, and message.
2. Look at files that **pass** with zero warnings. These are your examples of correct structure. Compare the failing file against a passing file with the same content type.
3. Fix the source file (`.adoc` for Apicurio, `.md` for Skupper) to match the pattern of the passing files.
4. Re-run `vale` to confirm the fix.

### Where to find passing examples

```bash
# Find modules with zero Vale issues — use these as models
vale modules/ 2>&1 | grep -L "warning\|error" 
# Or run vale on a specific file to check it
vale modules/kube-yaml.adoc
```

Look at the structure of passing files. They follow a consistent pattern.

## Required AsciiDoc structure for modules

Every module file must have this structure at the top:

```asciidoc
[id="file-name-without-extension"]
= file-name-without-extension

= Human-Readable Title

:_mod-docs-content-type: TYPE

[role="_abstract"]

First paragraph acts as short description.
```

### Content type rules

The `:_mod-docs-content-type:` attribute is required. The value determines which additional Vale rules apply:

| Value | When to use | Extra requirements |
|-------|------------|-------------------|
| `ASSEMBLY` | File that groups modules via `include::` directives | Can have an abstract paragraph and attributes before the first include; no content between or after includes except "Additional resources" |
| `PROCEDURE` | Heading uses a gerund (e.g., "Creating", "Configuring", "Installing") | Must contain a `.Procedure` block title before the ordered list of steps |
| `REFERENCE` | All other headings (nouns, descriptions) | None beyond the base requirements |
| `CONCEPT` | Conceptual/explanatory content | None beyond the base requirements |

### The most common Vale rules and how to satisfy them

| Rule | What it checks | How to fix |
|------|---------------|-----------|
| `ContentType` | `:_mod-docs-content-type:` attribute exists | Add the attribute after the title line |
| `ShortDescription` | `[role="_abstract"]` paragraph exists | Add `[role="_abstract"]` above the first paragraph |
| `TaskContents` | PROCEDURE files have `.Procedure` block title | Add `.Procedure` on the line before the ordered list |
| `AssemblyContents` | No prose between or after `include::` directives in ASSEMBLY files | Move content before the first include (abstract paragraph is fine there) or remove it; only "Additional resources" may follow includes |
| `NestedSection` | No `===` or deeper headings (DITA limitation) | Each section must be its own file; split nested sections into separate modules |
| `MismatchedId` | Quote marks in `[id="..."]` match | Use consistent double quotes |
| `DocumentTitle` | Title uses `= ` (single equals) | Don't use `==` or deeper for the document title |

## Assembly file structure

Assembly files live in `assemblies/`. They can have introductory content (abstract paragraph, attributes) before the first include, but nothing between or after includes except "Additional resources":

```asciidoc
[id="assembly-name"]
= assembly-name

:_mod-docs-content-type: ASSEMBLY

[role="_abstract"]

This section covers how to do X and Y.

include::../modules/first-module.adoc[leveloffset=+1]
include::../modules/second-module.adoc[leveloffset=+1]
```

The `[role="_abstract"]` paragraph before the includes becomes the short description (DITA `<shortdesc>`). No prose, headings, or other content is allowed between or after the `include::` directives — only an optional "Additional resources" section at the end.

## Key constraint: DITA compatibility

All rules enforce DITA 1.3 compatibility. The critical constraint: **no nested sections**. A module file gets one `= Title` heading and flat content beneath it. If the source has sub-headings (`==`, `===`), they must become separate module files linked via an assembly.

`leben.py` handles this splitting automatically:

```bash
python3 leben.py merged.adoc
```

## Fixing Skupper Markdown

When Vale flags a converted Skupper file, the fix goes in the original `.md` file. Common Markdown-side fixes:

- Add a short description paragraph immediately after each heading
- Avoid deeply nested headings (keep to `#` and `##` — deeper levels won't convert cleanly)
- Use standard Markdown lists for procedures (numbered lists become DITA steps)

After fixing the Markdown, re-run the full pipeline to verify:

```bash
bash scripts/convert-skupper.sh --input-dir /path/to/skupper-docs/input
```

## Workflow summary

```
1. Run vale → read errors/warnings
2. Find passing files with same content type → study their structure
3. Fix the SOURCE file (.adoc or .md) to match passing examples
4. Re-run vale → confirm zero issues
5. Repeat until clean
```

Always fix the source. Never edit generated output files.
