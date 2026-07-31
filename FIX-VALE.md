# Vale Error Fix Workflow

## Pipeline Command

```bash
bash scripts/convert-skupper.sh --input-dir ../skupper-docs/input
```

This converts markdown → AsciiDoc → Vale validation and generates `vale-report.json`.

## General Workflow

1. **Identify error** in `vale-report.json`
2. **Map to source markdown** (see mapping rules below)
3. **Fix in source markdown** (in `../skupper-docs/input/`)
4. **Re-run pipeline** to verify fix
5. **Check vale-report.json** for resolution

## Mapping Vale Errors to Source Files

### Assembly Files
**Pattern**: `assemblies/{dir-name}-assembly-{file-name}.adoc`
**Maps to**: `../skupper-docs/input/{dir-name}/{file-name}.md`

**Example**:
- `assemblies/console-assembly-console.adoc` → `../skupper-docs/input/console/index.md`
- `assemblies/install-assembly-kube-installing-controller.adoc` → `../skupper-docs/input/install/kube-installing-controller.md`

### Module Files
**Pattern**: `modules/{dir-name}-{parent-section}-{module-name}.adoc`
**Maps to**: Section in `../skupper-docs/input/{dir-name}/{parent-file}.md`

**Example**:
- `modules/console-console-quickstart.adoc` → Section `#console-quickstart` in `../skupper-docs/input/console/index.md`
- `modules/install-installing-cli.adoc` → Section in `../skupper-docs/input/install/*.md`

**Finding the exact section**:
1. Look for the anchor ID in the module filename (last part)
2. Search for `<a id="{module-name}"></a>` in source markdown
3. Or search for the heading text from the converted module

## Common Vale Error Types

### 1. AsciiDocDITA.ConceptLink
**Message**: "Move all links and cross references to Additional resources."
**Applies to**: ASSEMBLY and CONCEPT content types
**Fix**: Move inline links to an "Additional resources" section at end of section
**Pattern**: Use `## Additional resources` (h2) or bold `**Additional resources**`

### 2. AsciiDocDITA.ContentType
**Message**: "The '_mod-docs-content-type' attribute definition is missing."
**Fix**: Add content type comment after heading in source markdown:
```markdown
## Section Title
<!--CONCEPT-->
```
**Valid types**: `ASSEMBLY`, `CONCEPT`, `PROCEDURE`, `REFERENCE`

### 3. AsciiDocDITA.ShortDescription
**Message**: "Assign [role=\"_abstract\"] to a paragraph to use it as <shortdesc> in DITA."
**Fix**: Ensure first paragraph after heading is:
- Plain text (no bold, links, or special formatting at start)
- ≤260 characters
- Appears before any other content

### 4. AsciiDocDITA.NestedSection
**Message**: "Level 2, 3, 4, and 5 sections (=== and deeper) are not supported in DITA."
**Applies to**: `### Sub-heading` (h3) and deeper in modules
**Fix**: Restructure to use only h2 (`##`) sections, or split into separate modules

### 5. AsciiDocDITA.TaskContents
**Message**: "The '.Procedure' block title is missing."
**Applies to**: PROCEDURE content type
**Fix**: Add `**Procedure**` before the procedure steps in markdown

### 6. AsciiDocDITA.TaskStep
**Message**: "Content other than a single list cannot be mapped to DITA steps."
**Applies to**: PROCEDURE content type under `.Procedure` section
**Fix**: Ensure procedure section contains ONLY a numbered or bulleted list, no other content

## Quick Error Lookup

### First Error Example
```json
"assemblies/console-assembly-console.adoc": [
  {
    "Check": "AsciiDocDITA.ConceptLink",
    "Message": "Move all links and cross references to Additional resources.",
    "Match": "link:/api/[API documentation",
    "Line": 9
  }
]
```

**Source file**: `../skupper-docs/input/console/index.md`
**Source line**: 7 (approximately - converted files add metadata)
**Source text**: `See [API documentation](/api/) for the OpenAPI documentation.`
**Issue**: Inline link in assembly introduction
**Fix needed**: Move to "Additional resources" section

## Conversion Details

The pipeline:
1. `build_index.py` - orchestrates conversion
2. `merge.prepare_markdown_file()` - prepares markdown (adds metadata)
3. `kramdoc --format=GFM` - converts to AsciiDoc
4. `merge.convert_adoc_ids()` - normalizes IDs
5. `leben.py` - splits into assemblies/modules
6. Vale linting on generated AsciiDoc

**Key point**: ALWAYS fix in source markdown, NEVER edit generated AsciiDoc files.

## Tips

- Search for `<a id="...">` anchors to find sections in source markdown
- The assembly file is always from the main `index.md` or named markdown file
- Module files are split from h2 (`##`) sections
- Content type comments must be immediately after headings
- Vale runs on the GENERATED AsciiDoc, not source markdown
- Line numbers in vale-report.json are for generated files, approximate source
