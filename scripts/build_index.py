#!/usr/bin/env python3
import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections import defaultdict
from pathlib import Path
from urllib.parse import urldefrag

import merge

INDEX_TITLE_PATTERN = re.compile(r"<h1>(.*?)</h1>", re.IGNORECASE | re.DOTALL)
ASSEMBLY_INCLUDE_PATTERN = re.compile(r"include::\.\./modules/([^\[]+)\[")
IMAGE_MACRO_PATTERN = re.compile(r"(image::?)([^\[\s]+)(\[[^\n]*\])")
ANCHOR_PATTERN = re.compile(r'<a id="([^"]+)"></a>')
HTML_LINK_PATTERN = re.compile(r"link:([^\[\s]+\.html(?:#[^\[\s]+)?)(\[[^\n]*\])")


def should_skip_file(md_file):
    """Check if markdown file has 'skip: true' in YAML frontmatter.

    Returns True if the file contains YAML frontmatter with 'skip: true',
    False otherwise (including files with no frontmatter or skip: false).
    """
    try:
        content = md_file.read_text(encoding='utf-8')
    except Exception:
        return False

    # Match YAML frontmatter at the start of the file
    frontmatter_match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL | re.MULTILINE)
    if not frontmatter_match:
        return False

    yaml_content = frontmatter_match.group(1)

    # Check for skip: true (exact match, case-sensitive)
    if re.search(r'^\s*skip\s*:\s*true\s*$', yaml_content, re.MULTILINE):
        return True

    return False


def warn(message):
    print(f"WARNING: {message}", file=sys.stderr)


def read_index_title(index_file, title_override=None):
    """Extract title from index file or use override.

    Supports:
    - HTML files: reads <h1> tag
    - YAML files: reads site_name field
    - Override: explicit title parameter
    """
    if title_override:
        return title_override

    index_path = Path(index_file)

    # Handle YAML files
    if index_path.suffix in ('.yml', '.yaml'):
        try:
            import yaml
            with open(index_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            return config.get('site_name', 'Documentation')
        except Exception:
            return "Documentation"

    # Handle HTML files (existing logic)
    text = index_path.read_text(encoding="utf-8")
    match = INDEX_TITLE_PATTERN.search(text)
    if not match:
        return "Documentation"
    return re.sub(r"\s+", " ", match.group(1)).strip()


def run_command(args, cwd=None):
    subprocess.run(args, cwd=cwd, check=True)


def md_to_html_path(md_link):
    return Path(md_link).with_suffix(".html").as_posix()


def collect_anchor_data(md_files, source_root):
    page_ids = {}
    fragment_ids = {}
    id_sources = defaultdict(list)

    for md_file in md_files:
        relative_md = md_file.relative_to(source_root).as_posix()
        html_path = md_to_html_path(relative_md)
        text = md_file.read_text(encoding="utf-8")
        anchors = ANCHOR_PATTERN.findall(text)

        if not anchors:
            warn(f"{relative_md}: no explicit anchors found for internal xref mapping")
            continue

        page_ids[html_path] = anchors[0]

        for anchor in anchors:
            fragment_ids[(html_path, anchor)] = anchor
            id_sources[anchor].append(relative_md)

    duplicates = {anchor: paths for anchor, paths in id_sources.items() if len(paths) > 1}
    if duplicates:
        duplicate_lines = ", ".join(f"{anchor}: {paths}" for anchor, paths in sorted(duplicates.items()))
        raise RuntimeError(f"Duplicate anchor IDs across source files: {duplicate_lines}")

    return page_ids, fragment_ids


def namespaced_filename(namespace, filename):
    return f"{namespace}-{filename}"


def rewrite_assembly_includes(content, renamed_modules):
    def replace_include(match):
        original_name = match.group(1)
        renamed_name = renamed_modules[original_name]
        return f"include::../modules/{renamed_name}["

    return ASSEMBLY_INCLUDE_PATTERN.sub(replace_include, content)


def copy_and_rewrite_images(content, source_dir, images_out, image_registry, copy_images=False):
    def replace_image(match):
        macro, target, attrs = match.groups()

        if target.startswith(("http://", "https://", "/", "{")):
            return match.group(0)

        if not copy_images:
            # Don't copy images, just return original reference
            return match.group(0)

        source_path = (source_dir / target).resolve()
        if not source_path.exists():
            warn(f"Skipping missing image source: {source_path}")
            return match.group(0)

        output_name = source_path.name
        destination = images_out / output_name
        existing = image_registry.get(output_name)
        if existing is None:
            shutil.copy2(source_path, destination)
            image_registry[output_name] = source_path
        elif existing != source_path:
            raise RuntimeError(
                f"Image filename collision for {output_name}: {existing} and {source_path}"
            )

        return f"{macro}./images/{output_name}{attrs}"

    return IMAGE_MACRO_PATTERN.sub(replace_image, content)


def rewrite_internal_html_links(content, source_html_path, page_ids, fragment_ids):
    source_html_path = Path(source_html_path)

    def replace_link(match):
        target, attrs = match.groups()

        if target.startswith(("http://", "https://", "/", "{")):
            return match.group(0)

        path_part, fragment = urldefrag(target)
        if path_part:
            target_path = os.path.normpath(os.path.join(source_html_path.parent.as_posix(), path_part))
        else:
            target_path = source_html_path.as_posix()
        target_path = target_path.replace("\\", "/")

        if fragment:
            target_id = fragment_ids.get((target_path, fragment))
        else:
            target_id = page_ids.get(target_path)

        if not target_id:
            warn(f"{source_html_path.as_posix()}: unable to resolve internal link target {target}")
            return match.group(0)

        return f"xref:{target_id}{attrs}"

    return HTML_LINK_PATTERN.sub(replace_link, content)


def process_markdown_source(md_file, relative_md, namespace, output_dir, leben_script, image_registry, page_ids, fragment_ids, copy_images=False):
    assemblies_out = output_dir / "assemblies"
    modules_out = output_dir / "modules"
    images_out = output_dir / "images"
    source_html_path = md_to_html_path(relative_md)

    with tempfile.TemporaryDirectory(prefix="build-index-") as temp_dir:
        temp_dir = Path(temp_dir)
        prepared_md = temp_dir / "prepared.md"
        converted_adoc = temp_dir / "source.adoc"

        merge.prepare_markdown_file(str(md_file), str(prepared_md))
        run_command(["kramdoc", "--format=GFM", "-o", str(converted_adoc), str(prepared_md)])
        merge.convert_adoc_ids(str(converted_adoc), str(converted_adoc))
        run_command([sys.executable, str(leben_script), converted_adoc.name], cwd=str(temp_dir))

        assembly_files = sorted((temp_dir / "assemblies").glob("*.adoc"))
        module_files = sorted((temp_dir / "modules").glob("*.adoc"))

        if len(assembly_files) != 1:
            raise RuntimeError(f"{md_file}: expected exactly one assembly, found {len(assembly_files)}")

        renamed_modules = {}
        for module_file in module_files:
            renamed_name = namespaced_filename(namespace, module_file.name)
            destination = modules_out / renamed_name
            if destination.exists():
                raise RuntimeError(f"{md_file}: duplicate module output path {destination}")
            content = module_file.read_text(encoding="utf-8")
            content = copy_and_rewrite_images(content, md_file.parent, images_out, image_registry, copy_images)
            content = rewrite_internal_html_links(content, source_html_path, page_ids, fragment_ids)
            destination.write_text(content, encoding="utf-8")
            renamed_modules[module_file.name] = renamed_name

        assembly_file = assembly_files[0]
        assembly_name = namespaced_filename(namespace, assembly_file.name)
        assembly_destination = assemblies_out / assembly_name
        if assembly_destination.exists():
            raise RuntimeError(f"{md_file}: duplicate assembly output path {assembly_destination}")

        content = assembly_file.read_text(encoding="utf-8")
        content = rewrite_assembly_includes(content, renamed_modules)
        content = copy_and_rewrite_images(content, md_file.parent, images_out, image_registry, copy_images)
        content = rewrite_internal_html_links(content, source_html_path, page_ids, fragment_ids)
        assembly_destination.write_text(content, encoding="utf-8")

        return assembly_destination


def write_root_index(index_file, output_dir, assembly_paths, title_override=None, output_name=None):
    """Generate root index file with custom title and filename.

    Args:
        index_file: Source index file (for title extraction)
        output_dir: Output directory
        assembly_paths: List of assembly file paths to include
        title_override: Optional title override
        output_name: Optional output filename (default: "index.adoc")

    Returns:
        Path to generated root index file
    """
    title = read_index_title(index_file, title_override)
    filename = output_name or "index.adoc"
    root_index = output_dir / filename

    lines = [
        ':doctype: book\n',
        ':toc: left\n',
        ':toclevels: 3\n',
        ':sectnums:\n',
        '\n',
        '[id="generated-index"]\n',
        f'= {title}\n',
        '\n',
    ]

    for assembly_path in assembly_paths:
        rel_path = assembly_path.relative_to(output_dir)
        lines.append(f"include::{rel_path.as_posix()}[leveloffset=+1]\n")

    root_index.write_text("".join(lines), encoding="utf-8")
    return root_index


def build_site(index_file, output_dir, clean=False, source_dir=None, copy_images=False,
               index_only=False, title_override=None, output_name=None):
    """Build documentation site from index file.

    Args:
        index_file: Path to index file (mkdocs.yml, YAML, or HTML)
        output_dir: Output directory for generated files
        clean: Remove output directory before building
        source_dir: Source directory containing .md files
        copy_images: Copy images to output directory
        index_only: Skip assembly generation, only create index from existing assemblies
        title_override: Override title extracted from index file
        output_name: Custom output filename (default: "index.adoc")
    """
    index_file = Path(index_file).resolve()
    output_dir = Path(output_dir).resolve()

    if clean and output_dir.exists():
        shutil.rmtree(output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "assemblies").mkdir(parents=True, exist_ok=True)
    (output_dir / "modules").mkdir(parents=True, exist_ok=True)
    (output_dir / "images").mkdir(parents=True, exist_ok=True)

    # Use provided source_dir or default to index_file.parent
    source_root = Path(source_dir).resolve() if source_dir else index_file.parent

    # Detect file type and extract links accordingly
    index_file_str = str(index_file)
    if index_file_str.endswith('.yml') or index_file_str.endswith('.yaml'):
        md_links = merge.extract_mkdocs_nav_links(index_file_str)
    else:
        md_links = merge.extract_md_links(index_file_str)

    if index_only:
        # Index-only mode: map markdown files to existing assemblies
        assembly_paths = []
        assemblies_dir = output_dir / "assemblies"

        if not assemblies_dir.exists() or not any(assemblies_dir.glob("*.adoc")):
            raise RuntimeError(
                f"No existing assemblies found in {assemblies_dir}. "
                "Run full build first without --index-only flag."
            )

        # Build mapping of existing assemblies
        existing_assemblies = {}
        for asm_file in assemblies_dir.glob("*.adoc"):
            existing_assemblies[asm_file.name] = asm_file

        # Map markdown files to assemblies
        for md_link in md_links:
            md_file = (source_root / md_link).resolve()

            if not md_file.exists():
                warn(f"Skipping missing Markdown source: {md_link}")
                continue

            if should_skip_file(md_file):
                warn(f"Skipping {md_link}: skip: true in YAML frontmatter")
                continue

            namespace = md_file.parent.name
            # Find matching assembly by namespace prefix
            matching_assemblies = [
                asm for asm_name, asm in existing_assemblies.items()
                if asm_name.startswith(f"{namespace}-assembly-")
            ]

            if not matching_assemblies:
                warn(f"No assembly found for {md_link} (namespace: {namespace})")
                continue

            # For multiple matches, use filename matching as tiebreaker
            if len(matching_assemblies) == 1:
                assembly_paths.append(matching_assemblies[0])
            else:
                stem = md_file.stem
                best_match = None
                for asm in matching_assemblies:
                    if stem in asm.name or asm.name.endswith(f"-{stem}.adoc"):
                        best_match = asm
                        break
                if best_match:
                    assembly_paths.append(best_match)
                else:
                    assembly_paths.append(matching_assemblies[0])
                    warn(f"Multiple assemblies for {md_link}, using {matching_assemblies[0].name}")

        if not assembly_paths:
            raise RuntimeError(f"No assemblies matched markdown files from {index_file}")

        return write_root_index(index_file, output_dir, assembly_paths, title_override, output_name)

    # Full build mode (existing logic)
    kramdoc = shutil_which("kramdoc")
    if kramdoc is None:
        raise RuntimeError("kramdoc is not installed or not on PATH")

    repo_root = Path(__file__).resolve().parent.parent
    leben_script = repo_root / "leben.py"
    assembly_paths = []
    image_registry = {}

    # Collect all md_files first for anchor data
    md_files = []
    for md_link in md_links:
        md_file = (source_root / md_link).resolve()
        if md_file.exists():
            md_files.append(md_file)

    page_ids, fragment_ids = collect_anchor_data(md_files, source_root)

    # Process each markdown source
    for md_link in md_links:
        md_file = (source_root / md_link).resolve()

        if not md_file.exists():
            warn(f"Skipping missing Markdown source: {md_link}")
            continue

        if should_skip_file(md_file):
            warn(f"Skipping {md_link}: skip: true in YAML frontmatter")
            continue

        namespace = md_file.parent.name
        relative_md = md_file.relative_to(source_root).as_posix()
        assembly_paths.append(
            process_markdown_source(
                md_file,
                relative_md,
                namespace,
                output_dir,
                leben_script,
                image_registry,
                page_ids,
                fragment_ids,
                copy_images,
            )
        )

    if not assembly_paths:
        raise RuntimeError(f"No Markdown sources were built from {index_file}")

    return write_root_index(index_file, output_dir, assembly_paths, title_override, output_name)


def shutil_which(command):
    for directory in os.environ.get("PATH", "").split(os.pathsep):
        candidate = Path(directory) / command
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


def main():
    parser = argparse.ArgumentParser(
        description="Build AsciiDoc outputs for each local Markdown source referenced by an index file."
    )
    parser.add_argument(
        "index_file",
        nargs="?",
        default="../skupper-docs/mkdocs.yml",
        help="Path to the index file (mkdocs.yml, subset.yml, skupper.md, or index.html.in)",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="output",
        help="Directory where generated AsciiDoc files are written",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Remove the output directory before rebuilding",
    )
    parser.add_argument(
        "--source-dir",
        metavar="DIR",
        help="Source directory containing .md files (defaults to index file's parent directory)",
    )
    parser.add_argument(
        "--copy-images",
        action="store_true",
        help="Copy images from source to output/images/ directory (default: false)",
    )
    parser.add_argument(
        "--index-only",
        action="store_true",
        help="Generate index file only, reusing existing assemblies (no markdown processing)",
    )
    parser.add_argument(
        "--title",
        metavar="TITLE",
        help="Override title for generated index (default: extract from index file)",
    )
    parser.add_argument(
        "--output-name",
        metavar="NAME",
        help="Output index filename (default: index.adoc)",
    )
    args = parser.parse_args()

    root_index = build_site(
        args.index_file,
        args.output,
        clean=args.clean,
        source_dir=args.source_dir,
        copy_images=args.copy_images,
        index_only=args.index_only,
        title_override=args.title,
        output_name=args.output_name,
    )
    print(f"Generated root index: {root_index}")


if __name__ == "__main__":
    main()
