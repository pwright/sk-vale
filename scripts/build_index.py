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


def warn(message):
    print(f"WARNING: {message}", file=sys.stderr)


def read_index_title(index_file):
    text = Path(index_file).read_text(encoding="utf-8")
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


def copy_and_rewrite_images(content, source_dir, images_out, image_registry):
    def replace_image(match):
        macro, target, attrs = match.groups()

        if target.startswith(("http://", "https://", "/", "{")):
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


def process_markdown_source(md_file, relative_md, namespace, output_dir, leben_script, image_registry, page_ids, fragment_ids):
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
            content = copy_and_rewrite_images(content, md_file.parent, images_out, image_registry)
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
        content = copy_and_rewrite_images(content, md_file.parent, images_out, image_registry)
        content = rewrite_internal_html_links(content, source_html_path, page_ids, fragment_ids)
        assembly_destination.write_text(content, encoding="utf-8")

        return assembly_destination


def write_root_index(index_file, output_dir, assembly_paths):
    title = read_index_title(index_file)
    root_index = output_dir / "index.adoc"

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


def build_site(index_file, output_dir, clean=False):
    index_file = Path(index_file).resolve()
    output_dir = Path(output_dir).resolve()

    if clean and output_dir.exists():
        shutil.rmtree(output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "assemblies").mkdir(parents=True, exist_ok=True)
    (output_dir / "modules").mkdir(parents=True, exist_ok=True)
    (output_dir / "images").mkdir(parents=True, exist_ok=True)

    kramdoc = shutil_which("kramdoc")
    if kramdoc is None:
        raise RuntimeError("kramdoc is not installed or not on PATH")

    repo_root = Path(__file__).resolve().parent.parent
    leben_script = repo_root / "leben.py"

    source_root = index_file.parent
    assembly_paths = []
    image_registry = {}
    md_files = []

    for md_link in merge.extract_md_links(str(index_file)):
        md_file = (source_root / md_link).resolve()
        if md_file.exists():
            md_files.append(md_file)

    page_ids, fragment_ids = collect_anchor_data(md_files, source_root)

    for md_link in merge.extract_md_links(str(index_file)):
        md_file = (source_root / md_link).resolve()

        if not md_file.exists():
            warn(f"Skipping missing Markdown source: {md_link}")
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
            )
        )

    if not assembly_paths:
        raise RuntimeError(f"No Markdown sources were built from {index_file}")

    return write_root_index(index_file, output_dir, assembly_paths)


def shutil_which(command):
    for directory in os.environ.get("PATH", "").split(os.pathsep):
        candidate = Path(directory) / command
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


def main():
    parser = argparse.ArgumentParser(
        description="Build AsciiDoc outputs for each local Markdown source referenced by an index.html.in file."
    )
    parser.add_argument(
        "index_file",
        nargs="?",
        default="../docs-vale/input/index.html.in",
        help="Path to the HTML index file",
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
    args = parser.parse_args()

    root_index = build_site(args.index_file, args.output, clean=args.clean)
    print(f"Generated root index: {root_index}")


if __name__ == "__main__":
    main()
