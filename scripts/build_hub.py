#!/usr/bin/env python3
"""Build multi-page HTML hub from JTBD-organized AsciiDoc assemblies."""

import argparse
import os
import re
import shutil
import subprocess
import sys
from html import escape
from pathlib import Path

import yaml


def parse_assembly_metadata(adoc_path):
    """Extract title and abstract from an assembly .adoc file."""
    title = ""
    abstract_lines = []
    in_abstract = False
    past_blank = False

    with open(adoc_path) as f:
        for line in f:
            line = line.rstrip("\n")
            if line.startswith("= "):
                title = line[2:].strip()
            elif line == '[role="_abstract"]':
                in_abstract = True
                past_blank = False
            elif in_abstract:
                if not past_blank:
                    if line == "":
                        past_blank = True
                    continue
                if line.startswith("include::") or line.startswith("["):
                    break
                if line == "" and abstract_lines:
                    break
                abstract_lines.append(line)

    abstract = " ".join(abstract_lines).strip()
    abstract = re.sub(r"[*_`]", "", abstract)
    if len(abstract) > 200:
        abstract = abstract[:197].rsplit(" ", 1)[0] + "..."

    return title, abstract


def collect_ids(adoc_path):
    """Collect all IDs from an assembly and its included modules."""
    ids = set()
    assembly_dir = os.path.dirname(adoc_path)

    with open(adoc_path) as f:
        for line in f:
            m = re.match(r'\[id="([^"]+)"\]', line)
            if m:
                ids.add(m.group(1))
            m = re.match(r"include::(\S+)\[", line)
            if m:
                full_path = os.path.normpath(
                    os.path.join(assembly_dir, m.group(1))
                )
                if os.path.isfile(full_path):
                    with open(full_path) as mf:
                        for mline in mf:
                            mm = re.match(r'\[id="([^"]+)"\]', mline)
                            if mm:
                                ids.add(mm.group(1))

    return ids


def fix_xrefs(html_content, current_html, id_to_file):
    """Rewrite cross-assembly href='#id' links to point to the correct file."""

    def replace_href(match):
        anchor_id = match.group(1)
        target_file = id_to_file.get(anchor_id)
        if target_file and target_file != current_html:
            return f'href="{target_file}#{anchor_id}"'
        return match.group(0)

    return re.sub(r'href="#([^"]+)"', replace_href, html_content)


def render_assembly(adoc_path, output_dir, docinfo_dir):
    """Run asciidoctor on an assembly file."""
    cmd = [
        "asciidoctor",
        "-D", str(output_dir),
        "-a", "toc=left",
        "-a", "toclevels=3",
        "-a", f"docinfodir={docinfo_dir}",
        "-a", "docinfo=shared",
        str(adoc_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  WARNING: asciidoctor failed for {adoc_path}", file=sys.stderr)
        print(f"  {result.stderr.strip()}", file=sys.stderr)
        return False
    if result.stderr.strip():
        for line in result.stderr.strip().splitlines():
            print(f"  {line}", file=sys.stderr)
    return True


def generate_hub_page(config, assembly_meta, output_path):
    """Generate the hub index.html page."""
    title = config.get("title", "Documentation")
    subtitle = config.get("subtitle", "")

    nav_items = []
    nav_items.append("    <ul>")
    for cat in config["categories"]:
        cat_slug = re.sub(r"[^a-z0-9]+", "-", cat["name"].lower()).strip("-")
        nav_items.append(
            f'      <li><a href="#cat-{cat_slug}">{escape(cat["name"])}</a></li>'
        )
    nav_items.append("    </ul>")
    nav_html = "\n".join(nav_items)

    main_sections = []
    for cat in config["categories"]:
        cat_slug = re.sub(r"[^a-z0-9]+", "-", cat["name"].lower()).strip("-")
        cards = []
        for adoc in cat["assemblies"]:
            html_name = Path(adoc).stem + ".html"
            meta = assembly_meta.get(adoc, {})
            atitle = meta.get("title", adoc)
            abstract = meta.get("abstract", "")
            cards.append(
                f'      <a class="hub-card" href="{html_name}">\n'
                f"        <h3>{escape(atitle)}</h3>\n"
                f"        <p>{escape(abstract)}</p>\n"
                f"      </a>"
            )
        cards_html = "\n".join(cards)
        main_sections.append(
            f'  <section class="hub-category" id="cat-{cat_slug}">\n'
            f"    <h2>{escape(cat['name'])}</h2>\n"
            f"    <p>{escape(cat.get('description', ''))}</p>\n"
            f'    <div class="hub-cards">\n'
            f"{cards_html}\n"
            f"    </div>\n"
            f"  </section>"
        )
    main_html = "\n".join(main_sections)

    subtitle_html = ""
    if subtitle:
        subtitle_html = f'  <p class="hub-subtitle">{escape(subtitle)}</p>'

    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{escape(title)}</title>
  <link rel="stylesheet" href="hub.css">
</head>
<body class="hub-page">
<header class="hub-header">
  <h1>{escape(title)}</h1>
{subtitle_html}
</header>
<div class="hub-container">
  <nav class="hub-nav">
{nav_html}
  </nav>
  <main class="hub-main">
{main_html}
  </main>
</div>
</body>
</html>
"""

    with open(output_path, "w") as f:
        f.write(page)


def main():
    parser = argparse.ArgumentParser(description="Build JTBD hub pages")
    parser.add_argument("--config", required=True, help="Path to hub-config.yml")
    parser.add_argument("--output", required=True, help="Output directory for HTML")
    parser.add_argument(
        "--assemblies-dir", required=True, help="Path to assemblies directory"
    )
    parser.add_argument("--css", required=True, help="Path to hub.css source file")
    args = parser.parse_args()

    with open(args.config) as f:
        config = yaml.safe_load(f)

    output_dir = os.path.abspath(args.output)
    assemblies_dir = os.path.abspath(args.assemblies_dir)
    docinfo_dir = os.path.abspath(os.path.dirname(args.config))

    os.makedirs(output_dir, exist_ok=True)

    all_assemblies = []
    for cat in config["categories"]:
        all_assemblies.extend(cat["assemblies"])

    print("Parsing assembly metadata...")
    assembly_meta = {}
    id_to_file = {}

    for adoc in all_assemblies:
        adoc_path = os.path.join(assemblies_dir, adoc)
        if not os.path.isfile(adoc_path):
            print(f"  WARNING: {adoc_path} not found, skipping", file=sys.stderr)
            continue

        title, abstract = parse_assembly_metadata(adoc_path)
        assembly_meta[adoc] = {"title": title, "abstract": abstract}

        html_name = Path(adoc).stem + ".html"
        ids = collect_ids(adoc_path)
        for aid in ids:
            id_to_file[aid] = html_name

    print(f"Rendering {len(all_assemblies)} assembly pages...")
    rendered = 0
    for adoc in all_assemblies:
        adoc_path = os.path.join(assemblies_dir, adoc)
        if not os.path.isfile(adoc_path):
            continue
        print(f"  {adoc}")
        if render_assembly(adoc_path, output_dir, docinfo_dir):
            rendered += 1

    print("Fixing cross-assembly links...")
    fixed_count = 0
    for adoc in all_assemblies:
        html_name = Path(adoc).stem + ".html"
        html_path = os.path.join(output_dir, html_name)
        if not os.path.isfile(html_path):
            continue

        with open(html_path) as f:
            content = f.read()

        fixed = fix_xrefs(content, html_name, id_to_file)
        if fixed != content:
            with open(html_path, "w") as f:
                f.write(fixed)
            fixed_count += 1

    if fixed_count:
        print(f"  Fixed xrefs in {fixed_count} file(s)")

    print("Generating hub page...")
    generate_hub_page(config, assembly_meta, os.path.join(output_dir, "index.html"))

    shutil.copy2(args.css, os.path.join(output_dir, "hub.css"))

    print(f"Done. {rendered} pages + hub: {output_dir}/index.html")


if __name__ == "__main__":
    main()
