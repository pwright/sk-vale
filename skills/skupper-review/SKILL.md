---
name: skupper-review
description: Full documentation review with traceback to Markdown sources
---

# skupper-review

Comprehensive documentation review combining Vale structural checks, IBM Style Guide language review, and technical review — all traced back to Markdown source files.

## Arguments

- `--style` — Style review only (Vale + IBM SG language/grammar)
- `--tech` — Technical review only (accuracy, completeness, code examples)
- `--file <md-path>` — Review a single file (e.g., `kube-yaml/custom-certs.md`)
- `--skip-convert` — Skip conversion, use existing AsciiDoc output

## Steps

1. **Convert** (unless `--skip-convert`):
   ```bash
   bash scripts/convert-skupper.sh --input-dir ~/repos/sk/skupper-docs/doc-input
   ```

2. **Style review** (unless `--tech` only):

   a. **Vale structural checks** on generated AsciiDoc:
      ```bash
      vale --output=JSON assemblies/ modules/
      ```
      Trace findings to MD via:
      ```bash
      python3 -I skills/shared/scripts/traceback.py vale-report.json assembly-map.json
      ```

   b. **IBM Style Guide review** — Invoke the following skills on the `.md` source files directly (these are format-agnostic):
      - `docs-tools:ibm-sg-language-and-grammar`
      - `docs-tools:ibm-sg-punctuation`
      - `docs-tools:ibm-sg-structure-and-format`
      - `docs-tools:ibm-sg-technical-elements`

   c. **Red Hat SSG review** — Invoke on `.md` source files:
      - `docs-tools:rh-ssg-grammar-and-language`
      - `docs-tools:rh-ssg-formatting`
      - `docs-tools:rh-ssg-structure`

3. **Technical review** (unless `--style` only):

   Invoke `docs-tools:docs-review-technical` on the Markdown source files. This agent is format-agnostic and reviews for:
   - Incorrect commands or code examples
   - Missing prerequisites
   - False architectural claims
   - Absent failure paths
   - Broken procedures

4. **Consolidate and report**:

   Merge all findings into a single report. For each finding, indicate:
   - **Source**: Which review caught it (Vale/IBM-SG/RH-SSG/Technical)
   - **File**: The `.md` source file path
   - **Line**: Approximate line number in the `.md` source
   - **Severity**: error / warning / suggestion
   - **Category**: structural, language, technical, style
   - **Fixable**: Whether it can be fixed in the `.md` source directly

   Group findings by file. Distinguish:
   - **Fixable in MD** — Issues that can be resolved by editing the `.md` source
   - **Pipeline-level** — Issues that are artifacts of the conversion process
   - **Structural** — DITA constraints that require reorganizing content

## Example output

```
## Review: kube-yaml/custom-certs.md

### Structural (Vale)
- [warning] ShortDescription: Missing short description paragraph (~line 5)
- [warning] ContentType: Missing content type attribute (~line 1)

### Language (IBM SG)
- [suggestion] Use "might" instead of "may" when expressing possibility (line 12)

### Technical
- [warning] Command `skupper init` is deprecated — use `skupper site create` (line 34)

### Summary
| Category    | Errors | Warnings | Suggestions |
|-------------|--------|----------|-------------|
| Structural  | 0      | 2        | 0           |
| Language    | 0      | 0        | 1           |
| Technical   | 0      | 1        | 0           |
```

## Notes

- Style review skills work directly on Markdown — no conversion needed for those checks
- Structural review requires AsciiDoc output (DITA validation happens post-conversion)
- Technical review is the most valuable for catching accuracy issues
- Use `/skupper-fix` to apply fixes after review
