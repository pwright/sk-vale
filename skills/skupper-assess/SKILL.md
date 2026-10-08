---
name: skupper-assess
description: CQA assessment with traceback to Markdown sources
---

# skupper-assess

Runs Content Quality Assessment (CQA) on converted AsciiDoc output and traces findings back to Markdown source files.

## Arguments

- `--scope <scope>` — Assessment scope: `full` (all files), `assembly` (assembly-level only), or a specific file path
- `--skip-convert` — Use existing AsciiDoc output without re-running conversion
- `--category <cat>` — Run only a specific CQA category (e.g., `modularization`, `procedures`, `titles-descriptions`)

## Steps

1. **Convert** (unless `--skip-convert`):
   ```bash
   bash scripts/convert-skupper.sh --input-dir ~/repos/sk/skupper-docs/doc-input
   ```

2. **Run CQA assessment**:

   Invoke the appropriate `cqa-tools` skills on the generated AsciiDoc. If `--category` is specified, run only that category. Otherwise run the full assessment:

   - `cqa-tools:cqa-assess` — Full assessment (runs all categories)

   Or individual categories:
   - `cqa-tools:cqa-modularization` — Module structure and organization
   - `cqa-tools:cqa-procedures` — Procedure quality and completeness
   - `cqa-tools:cqa-titles-descriptions` — Title and description quality
   - `cqa-tools:cqa-user-focus` — User-centric content evaluation
   - `cqa-tools:cqa-tables-images` — Table and image quality
   - `cqa-tools:cqa-links` — Link validation
   - `cqa-tools:cqa-editorial` — Editorial standards
   - `cqa-tools:cqa-legal-branding` — Legal and branding compliance

   Pass the AsciiDoc files to the CQA tools:
   - For `full` scope: assess all files in `assemblies/` and `modules/`
   - For `assembly` scope: assess only `assemblies/`
   - For a specific file: use `assembly-map.json` to find the corresponding `.adoc` file(s)

3. **Trace findings to Markdown sources**:

   For each CQA finding that references an `.adoc` file:
   - Use `assembly-map.json` to map assemblies back to `.md` paths
   - Use namespace prefixes to map modules back to `.md` paths
   - Match heading text to find approximate line numbers in the MD source

   Use the traceback script:
   ```bash
   python3 -I skills/shared/scripts/traceback.py vale-report.json assembly-map.json
   ```

   For CQA findings that aren't in Vale format, perform manual traceback using the same logic:
   - Read `assembly-map.json` for the adoc→md mapping
   - Check the namespace prefix of module filenames to determine the source directory

4. **Report with MD-referenced findings**:

   Present the CQA report with all file references pointing to `.md` sources:

   ```
   ## CQA Assessment Report

   ### Modularization (Score: 7/10)
   - kube-yaml/custom-certs.md: Module too long (>150 lines), consider splitting
   - overview/security.md: Missing procedure module for certificate rotation

   ### Procedures (Score: 8/10)
   - kube-cli/site-configuration.md: Prerequisites section incomplete
   - system-yaml/service-exposure.md: Missing verification step

   ### Titles & Descriptions (Score: 6/10)
   - overview/index.md: Title doesn't follow task-based naming
   - kube-yaml/site-linking.md: Missing short description

   ### Overall Score: 7.0/10

   Top 3 improvements:
   1. Add short descriptions to 5 files missing them
   2. Split 2 oversized modules
   3. Add verification steps to 3 procedures
   ```

## Notes

- CQA tools work on AsciiDoc — conversion is always required before assessment
- The assessment evaluates content quality beyond what Vale checks (structure, completeness, user focus)
- Use `/skupper-fix` to address structural findings
- Use `/skupper-review` for style-specific issues
- CQA scores provide a baseline for tracking documentation quality over time
