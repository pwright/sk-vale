#!/usr/bin/env python3
"""Extract abstracts from generated AsciiDoc assemblies and modules.

Reads [role="_abstract"] paragraphs from the adoc output and produces
JSON matching the same schema as abstract-audit.py, for comparison.

Usage:
    python3 scripts/extract-abstracts.py [--dir DIR] > abstracts.json
"""
import argparse
import json
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent

CONTENT_TYPE_PATTERN = re.compile(r"^:_mod-docs-content-type:\s*(\S+)")
HEADING_PATTERN = re.compile(r"^(=+)\s+(.*)")
ABSTRACT_MARKER = '[role="_abstract"]'


def extract_from_adoc(adoc_path, base_dir):
    lines = adoc_path.read_text(encoding="utf-8").splitlines()
    relative = str(adoc_path.relative_to(base_dir))

    heading = None
    level = 0
    content_type = None

    abstract_lines = []
    in_abstract = False

    for line in lines:
        hm = HEADING_PATTERN.match(line)
        if hm:
            heading = hm.group(2).strip()
            level = len(hm.group(1))
            continue

        cm = CONTENT_TYPE_PATTERN.match(line)
        if cm:
            content_type = cm.group(1)
            continue

        if line.strip() == ABSTRACT_MARKER:
            in_abstract = True
            abstract_lines = []
            continue

        if in_abstract:
            if not line.strip():
                break
            abstract_lines.append(line.strip())

    abstract = " ".join(abstract_lines) if abstract_lines else None
    word_count = len(abstract.split()) if abstract else 0
    char_count = len(abstract) if abstract else 0

    return {
        "file": relative,
        "heading": heading or adoc_path.stem,
        "level": level,
        "content_type": content_type,
        "abstract_words": word_count,
        "abstract_chars": char_count,
        "abstract": abstract,
    }


def main():
    parser = argparse.ArgumentParser(description="Extract abstracts from generated AsciiDoc")
    parser.add_argument("--dir", default=None,
                        help="Root directory containing assemblies/ and modules/ (default: repo root)")
    args = parser.parse_args()

    base_dir = Path(args.dir).resolve() if args.dir else REPO_ROOT

    results = []
    for subdir in ["assemblies", "modules"]:
        target = base_dir / subdir
        if not target.is_dir():
            print(f"WARNING: {target} not found", file=sys.stderr)
            continue
        for adoc in sorted(target.glob("*.adoc")):
            results.append(extract_from_adoc(adoc, base_dir))

    json.dump(results, sys.stdout, indent=2)
    print()


if __name__ == "__main__":
    main()
