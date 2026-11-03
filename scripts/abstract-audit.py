#!/usr/bin/env python3
"""Preview abstract extraction from Markdown sources before conversion.

Reuses merge.py's logic to show what each section's abstract will be,
flagging sections that have no suitable paragraph.

Usage:
    python3 scripts/abstract-audit.py [--source-dir DIR] [--json]

Defaults to ../skupper-docs/input with mkdocs.yml nav discovery.
"""
import argparse
import json
import os
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import merge


def discover_md_files(source_dir):
    """Find .md files via mkdocs.yml or fallback to glob."""
    mkdocs_path = source_dir.parent / "mkdocs.yml"
    if mkdocs_path.exists():
        relative_links = merge.extract_mkdocs_nav_links(str(mkdocs_path))
        files = []
        for link in relative_links:
            full = source_dir / link
            if full.exists():
                files.append(full)
        return files

    return sorted(source_dir.rglob("*.md"))


def extract_abstract_text(section_lines):
    """Return the abstract paragraph text, or None."""
    idx = merge.find_abstract_insertion_point(section_lines)
    if idx is None:
        return None

    lines = []
    for line in section_lines[idx:]:
        stripped = line.strip()
        if not stripped:
            break
        lines.append(stripped)

    return " ".join(lines)


def count_body_words(section_lines):
    """Count words in prose after abstract marker, excluding tables, code blocks, and block attributes."""
    idx = merge.find_abstract_insertion_point(section_lines)
    if idx is None:
        idx = 0

    in_fence = False
    in_table = False
    words = 0
    for line in section_lines[idx:]:
        stripped = line.strip()
        if merge.FENCE_PATTERN.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if stripped.startswith("|") or stripped.startswith("[cols="):
            in_table = True
            continue
        if in_table and not stripped:
            in_table = False
            continue
        if in_table:
            continue
        if stripped.startswith("[") or stripped.startswith(".") or stripped.startswith("----"):
            continue
        if stripped.startswith("image:") or stripped.startswith("include:"):
            continue
        words += len(stripped.split())
    return words


def audit_file(md_path, source_dir):
    """Audit a single Markdown file for abstract candidates."""
    with open(md_path, "r", encoding="utf-8") as f:
        content = f.read()

    content = merge.strip_external_link_references(content)
    lines = content.splitlines(keepends=True)
    heading_indices = merge.find_heading_indices(lines)

    relative = md_path.relative_to(source_dir)
    results = []

    for offset, heading_index in enumerate(heading_indices):
        next_heading = heading_indices[offset + 1] if offset + 1 < len(heading_indices) else len(lines)
        heading_match = merge.SECTION_HEADING_PATTERN.match(lines[heading_index])
        if not heading_match:
            continue

        level = len(heading_match.group(1))
        heading_text = heading_match.group(2).strip()
        section_body = lines[heading_index + 1:next_heading]

        content_type, body = merge.extract_content_type_marker(section_body)
        if not content_type:
            continue

        abstract_text = extract_abstract_text(body)
        word_count = len(abstract_text.split()) if abstract_text else 0
        char_count = len(abstract_text) if abstract_text else 0
        body_words = count_body_words(body)

        results.append({
            "file": str(relative),
            "heading": heading_text,
            "level": level,
            "content_type": content_type,
            "abstract_words": word_count,
            "abstract_chars": char_count,
            "body_words": body_words,
            "abstract": abstract_text,
        })

    return results


def print_summary(all_results):
    """Print a compact summary table."""
    if not all_results:
        print("No sections with content-type markers found.")
        return

    found = [r for r in all_results if r["abstract"]]
    missing = [r for r in all_results if not r["abstract"]]

    word_counts = [r["abstract_words"] for r in found]
    char_counts = [r["abstract_chars"] for r in found]

    print(f"\nSections: {len(all_results)}  |  With abstract: {len(found)}  |  Missing: {len(missing)}")

    if word_counts:
        word_counts.sort()
        mid = len(word_counts) // 2
        median = word_counts[mid] if len(word_counts) % 2 else (word_counts[mid - 1] + word_counts[mid]) // 2
        print(f"Abstract words — min: {min(word_counts)}  max: {max(word_counts)}  "
              f"mean: {sum(word_counts) // len(word_counts)}  median: {median}")
        print(f"Abstract chars — min: {min(char_counts)}  max: {max(char_counts)}  "
              f"mean: {sum(char_counts) // len(char_counts)}  median: {sorted(char_counts)[len(char_counts) // 2]}")

    buckets = {"<10w": 0, "10-19w": 0, "20-29w": 0, "30-39w": 0, "40+w": 0}
    for w in word_counts:
        if w < 10:
            buckets["<10w"] += 1
        elif w < 20:
            buckets["10-19w"] += 1
        elif w < 30:
            buckets["20-29w"] += 1
        elif w < 40:
            buckets["30-39w"] += 1
        else:
            buckets["40+w"] += 1

    print(f"Distribution: {' | '.join(f'{k}: {v}' for k, v in buckets.items())}")

    body_counts = [r["body_words"] for r in found]
    over_200 = [r for r in all_results if r["body_words"] > 200]
    if body_counts:
        body_counts.sort()
        mid = len(body_counts) // 2
        bmedian = body_counts[mid] if len(body_counts) % 2 else (body_counts[mid - 1] + body_counts[mid]) // 2
        print(f"\nBody words (abstract marker to next heading — downstream view):")
        print(f"  min: {min(body_counts)}  max: {max(body_counts)}  "
              f"mean: {sum(body_counts) // len(body_counts)}  median: {bmedian}")
        print(f"  Over 200 words: {len(over_200)}")

    print(f"\n{'File':<50} {'Heading':<35} {'Type':<10} {'Abstr':>5} {'Body':>6} {'Flag':>4}")
    print("-" * 116)

    current_file = None
    for r in all_results:
        file_col = r["file"] if r["file"] != current_file else ""
        current_file = r["file"]
        flag = " !!" if r["body_words"] > 200 else ""
        if r["abstract"]:
            status = f"{r['abstract_words']:>5} {r['body_words']:>6}{flag}"
        else:
            status = "  --- MISSING ---"
        print(f"{file_col:<50} {r['heading']:<35} {r['content_type']:<10} {status}")

    if over_200:
        print(f"\n--- Body over 200 words ({len(over_200)}) ---")
        for r in sorted(over_200, key=lambda x: -x["body_words"]):
            print(f"  {r['body_words']:>5}w  {r['file']}: {r['heading']}")

    if missing:
        print(f"\n--- Missing abstracts ({len(missing)}) ---")
        for r in missing:
            print(f"  {r['file']}: {r['heading']} ({r['content_type']})")


def main():
    parser = argparse.ArgumentParser(description="Audit abstract extraction from Markdown sources")
    parser.add_argument("--source-dir", default=None,
                        help="Directory containing .md files (default: ../skupper-docs/input)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    repo_root = SCRIPT_DIR.parent

    if args.source_dir:
        source_dir = Path(args.source_dir).resolve()
    else:
        candidates = [
            repo_root.parent / "skupper-docs" / "input",
            Path.home() / "repos" / "sk" / "skupper-docs" / "input",
        ]
        source_dir = next((c for c in candidates if c.is_dir()), None)
        if not source_dir:
            print(f"ERROR: No source directory found. Tried:\n  " +
                  "\n  ".join(str(c) for c in candidates), file=sys.stderr)
            print("Use --source-dir to specify the path.", file=sys.stderr)
            sys.exit(1)

    print(f"Source: {source_dir}", file=sys.stderr)
    md_files = discover_md_files(source_dir)
    print(f"Files: {len(md_files)}", file=sys.stderr)

    all_results = []
    for md_file in md_files:
        all_results.extend(audit_file(md_file, source_dir))

    if args.json:
        json.dump(all_results, sys.stdout, indent=2)
        print()
    else:
        print_summary(all_results)


if __name__ == "__main__":
    main()
