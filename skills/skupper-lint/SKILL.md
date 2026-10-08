---
name: skupper-lint
description: Vale lint with traceback to Markdown source files
---

# skupper-lint

Runs Vale on converted AsciiDoc and traces findings back to their originating Markdown source files.

## Arguments

- `--file <md-path>` — Lint a single file (e.g., `kube-yaml/custom-certs.md`). Lints all files if omitted.
- `--skip-convert` — Skip conversion, use existing `assemblies/` and `modules/`
- `--fix` — After reporting, open the MD source and apply fixes
- `--severity <level>` — Filter by minimum severity: `suggestion`, `warning` (default), or `error`
- `--rule <name>` — Filter findings to a specific Vale rule (e.g., `ShortDescription`, `ContentType`)

## Steps

1. **Convert** (unless `--skip-convert`):
   Run the conversion pipeline using the `/skupper-convert` skill instructions:
   ```bash
   bash scripts/convert-skupper.sh --input-dir ~/repos/sk/skupper-docs/doc-input
   ```

2. **Run Vale**:
   ```bash
   vale --output=JSON assemblies/ modules/ > vale-report.json
   ```
   If `--file` was specified, determine the corresponding assembly/modules by checking `assembly-map.json`, and lint only those files.

3. **Trace findings to Markdown sources**:
   ```bash
   python3 -I skills/shared/scripts/traceback.py vale-report.json assembly-map.json
   ```
   This maps each AsciiDoc finding back to its `.md` source file using `assembly-map.json` and namespace prefix conventions.

4. **Present findings grouped by MD file**:
   For each affected `.md` file, show:
   - The `.md` file path
   - Each finding with: severity, rule name, message, and approximate line in the MD source
   - The original `.adoc` file for reference

   Format as a table or structured list. Group by file, sort by severity (errors first).

5. **If `--fix` was requested**: For each fixable finding, read the `.md` source file and apply the fix following the patterns in AGENTS.md. Common fixes:
   - `ShortDescription` → Add a short description paragraph after the heading
   - `ContentType` → Ensure the heading style maps to the right content type after conversion
   - `NestedSection` → Restructure to avoid deeply nested headings

   After fixes, re-run the pipeline to verify.

## Example output

```
## kube-yaml/custom-certs.md (3 findings)

| Sev     | Rule             | Message                              | ~Line |
|---------|------------------|--------------------------------------|-------|
| warning | ShortDescription | Missing short description paragraph  | 5     |
| warning | ContentType      | Missing content type attribute       | 1     |
| error   | NestedSection    | Nested section not allowed in DITA   | 23    |

## overview/security.md (1 finding)

| Sev     | Rule             | Message                              | ~Line |
|---------|------------------|--------------------------------------|-------|
| warning | ShortDescription | Missing short description paragraph  | 3     |

Summary: 4 findings in 2 files (1 error, 3 warnings)
```

## Notes

- Findings reference `.md` file paths, not generated `.adoc` paths
- Line numbers are approximate — they point to the heading of the section containing the issue
- Some findings may be "unresolved" if traceback can't determine the source (these show the `.adoc` path)
