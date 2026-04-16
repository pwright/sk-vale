# Splitting AsciiDoc Files with `leben.py`

`leben.py` splits a flat AsciiDoc file into one assembly file and a set of module files.

It is useful when you start with a single `.adoc` document and want repo-style output under `assemblies/` and `modules/`.

## What `leben.py` looks for

The script scans for AsciiDoc IDs in either of these forms:

- `[[some-id]]`
- `[id="some-id"]`

The first ID it finds becomes the assembly ID. Every later ID is treated as the start of a module.

For the assembly title, `leben.py` prefers the level-1 heading immediately after the first ID. For each module title, it prefers the next heading after that module ID. If the expected heading is missing, the script falls back to using the ID as the title.

## What the script writes

Running the script creates:

- `assemblies/assembly-<id>.adoc`
- `modules/<id>.adoc`

The assembly file contains:

- the root ID,
- any assembly-level body text between the assembly heading and the first module ID,
- `include::` directives for each generated module.

Each module file contains:

- the module ID,
- any leading AsciiDoc document attributes from that section, such as `:_mod-docs-content-type:`,
- the generated title line,
- the remaining body content for that module.

If a section begins with document attributes, `leben.py` lifts those attributes so the generated output follows this pattern:

```adoc
[id="example-id"]
:_mod-docs-content-type: PROCEDURE
= Example Title
```

## Command syntax

```bash
python3 leben.py <file.adoc|glob|directory>
```

Examples:

```bash
python3 leben.py my-big-doc.adoc
python3 leben.py '*.adoc'
python3 leben.py my_docs/
```

## Input expectations

`leben.py` works best when the source follows a simple pattern:

- the document starts with an ID for the assembly,
- that ID is followed by a level-1 heading,
- each module starts with its own ID,
- each module ID is followed by a section heading.

The script is tolerant of missing headings, but the output is better when the structure is explicit.

## Practical notes

- The first ID in the file determines the assembly filename.
- All later IDs are treated as module boundaries.
- Content before the first module ID stays in the generated assembly.
- The script writes output into `assemblies/` and `modules/` relative to the current working directory.
- If you run it on a directory, it processes every `.adoc` file in that directory.
