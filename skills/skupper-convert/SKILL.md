---
name: skupper-convert
description: Run the Skupper Markdown→AsciiDoc conversion pipeline
---

# skupper-convert

Runs the Skupper conversion pipeline: Markdown → AsciiDoc (via kramdoc) → modules/assemblies (via leben.py) → Vale lint.

## Arguments

- `--input-dir <path>` — Path to skupper-docs doc-input directory. Default: `~/repos/sk/skupper-docs/doc-input`
- `--skip-vale` — Run conversion only, skip the Vale lint step
- `--commit` — Commit results to the skupper branch

## Steps

1. **Check prerequisites**: Verify `kramdoc`, `vale`, `python3`, `npm`, and `asciidoc-comments` are available.

2. **Run the conversion pipeline**:
   ```bash
   bash scripts/convert-skupper.sh --input-dir <path>
   ```
   Use the `--input-dir` argument if provided, otherwise use `~/repos/sk/skupper-docs/doc-input`.
   If `--commit` was passed, add `--commit` to the command.

3. **Report results**:
   - Number of assemblies generated (count files in `assemblies/`)
   - Number of modules generated (count files in `modules/`)
   - Whether `assembly-map.json` was updated
   - Vale exit code and summary of findings (unless `--skip-vale`)
   - If Vale reported issues, mention that `/skupper-lint` can trace them back to `.md` sources

## Example output

```
Conversion complete:
  Assemblies: 27
  Modules: 89
  Vale: 12 warnings, 0 errors
  Run /skupper-lint for findings traced to .md source files.
```

## Notes

- This skill is called internally by other skupper-* skills when they need fresh AsciiDoc output.
- The pipeline cleans `assemblies/`, `modules/`, and `docs/` before each run.
- `assembly-map.json` is regenerated on each run and used by `traceback.py` for finding resolution.
