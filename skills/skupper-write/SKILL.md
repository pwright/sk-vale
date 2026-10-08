---
name: skupper-write
description: Write new Markdown content for skupper-docs
---

# skupper-write

Creates new Markdown documentation for skupper-docs in Material for MkDocs format, validated against the conversion pipeline.

## Arguments

- First argument: Topic or title for the new content (e.g., "TLS certificates guide")
- `--output-dir <path>` — Subdirectory within doc-input to write to (e.g., `console/`)
- `--type <type>` — Content type: `concept`, `procedure`, `reference` (default: inferred from title)
- `--skip-validate` — Skip post-write validation

## Steps

1. **Read skupper-docs structure**:

   Examine the existing documentation to understand conventions:
   ```bash
   cat ~/repos/sk/skupper-docs/mkdocs.yml
   ```

   Read 2-3 existing `.md` files in the target directory to understand:
   - Heading structure and depth
   - Frontmatter conventions
   - How procedures are written (numbered lists)
   - How concepts are structured
   - Admonition and callout usage (Material for MkDocs syntax)

2. **Determine content type**:

   If `--type` was not specified, infer from the title:
   - Gerund titles ("Creating", "Configuring", "Installing") → `procedure`
   - Noun/description titles ("Architecture", "Security overview") → `concept`
   - List/table titles ("CLI reference", "Configuration options") → `reference`

3. **Write the content**:

   Invoke the `docs-tools:docs-writer` agent with `--format mkdocs`:
   - Pass the topic, content type, and target directory
   - The writer agent understands MkDocs format natively
   - Provide context from the existing docs structure

   If the docs-writer agent is not available, write the content directly following these MkDocs conventions:
   - Use `#` for the page title, `##` for sections (avoid `###` and deeper — DITA constraint)
   - Add a short description paragraph immediately after each heading
   - Use standard numbered lists for procedure steps
   - Use Material for MkDocs admonitions: `!!! note`, `!!! warning`, etc.
   - No YAML frontmatter unless the project uses it

4. **Write output file**:

   Write to `~/repos/sk/skupper-docs/doc-input/<output-dir>/<filename>.md`

   The filename should be kebab-case derived from the title.

5. **Validate** (unless `--skip-validate`):

   Run the lint skill to check the new content converts cleanly:
   ```bash
   bash scripts/convert-skupper.sh --input-dir ~/repos/sk/skupper-docs/doc-input
   ```
   Then run traceback to check for issues:
   ```bash
   python3 -I skills/shared/scripts/traceback.py vale-report.json assembly-map.json
   ```

   If there are findings in the new file, fix them before reporting completion.

6. **Report**:
   ```
   Created: ~/repos/sk/skupper-docs/doc-input/console/monitoring.md
   Type: procedure
   Sections: 4
   Validation: passed (0 Vale findings)

   Next steps:
   - Add to mkdocs.yml nav section
   - Run /skupper-review for full review
   ```

## Notes

- Keep headings to `#` and `##` only — deeper headings cause DITA nested section violations
- Every heading must be followed by a paragraph (becomes the short description)
- Procedure sections must contain a numbered list (becomes the DITA steps)
- Check the `mkdocs.yml` nav to see where the new file should be placed
- The file must be added to `mkdocs.yml` to be included in the conversion
