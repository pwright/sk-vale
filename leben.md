# Splitting AsciiDoc Files with `leben.py`

Have you ever written a huge, monolithic AsciiDoc file and wished you could automatically split it into smaller, more manageable parts? The `leben.py` script is designed to do just that, without requiring any special AsciiDoc annotations. It's built to simplify your workflow by automatically converting a single, flat AsciiDoc file into an assembly file and a set of module files.

---

## What `leben.py` Does

The script works by analyzing the structure of your document, specifically by looking for unique IDs and headings. It identifies the first top-level section as the **assembly** and every subsequent section as a **module**.

Here's a breakdown of its behavior:

. **Identifies the Assembly**: It finds the first ID in your file (either `[[id]]` or `[id="..."]`) and uses it to name the main assembly file. The heading that follows is used as the assembly's title.

. **Extracts the Assembly Body**: It saves the content that appears after the assembly's title and before the first module. This content becomes the introductory text for your new assembly.

. **Creates Modules**: For every subsequent section, it creates a separate AsciiDoc module file. The module's ID becomes its filename, and its title is extracted from the heading.

. **Assembles the Final Document**: The new assembly file is created, containing the introductory body and `include::` directives that link to all the new module files.

---

## How to Use the Script

To use `leben.py`, you simply run it from your command line and provide the path to your AsciiDoc file, a glob pattern, or an entire directory.

### Command Syntax

Bash

```
leben.py <file.adoc|glob|directory>
```

### Examples

- **Single File**: To process a single file, such as `my-big-doc.adoc`:
	Bash
	```
	leben.py my-big-doc.adoc
	```
- **Using a Glob Pattern**: To process all AsciiDoc files in the current directory:
	Bash
	```
	leben.py *.adoc
	```
- **Processing a Directory**: To process all AsciiDoc files within a specific directory:
	Bash
	```
	leben.py my_docs/
	```

---

## Output Structure

The script automatically creates two new directories in the location where you run the command:

- `assemblies/`: This directory holds the main assembly files. Assembly filenames are prefixed with `assembly-`.
- `modules/`: This directory contains all the individual module files.

### Example Output

If you run `leben.py` on a file named `my-big-doc.adoc` with an ID of `[[my-assembly]]`, the script will create the following files:

- `assemblies/assembly-my-assembly.adoc`
- `modules/module-one.adoc`
- `modules/another-module.adoc`

And so on, for each section in your original file.

---

## Important Considerations for Writers

- **ID and Heading Structure**: The script relies on a consistent ID and heading structure. Ensure your main document has a top-level ID and a level-1 heading. Subsequent sections should have IDs and headings of level 2 or higher.
- **The First ID is Key**: The script only uses the first ID it finds to name the assembly. All other IDs are treated as modules.
- **Assembly Body**: The script preserves all content before the first module's ID, which is then placed in your new assembly file. If you have any content you want to keep at the beginning of your main document, make sure it's placed there.