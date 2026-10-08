#!/usr/bin/env python3
"""Map Vale findings on generated AsciiDoc back to Markdown source files.

Uses assembly-map.json (MD path → assembly filename) and namespace prefix
conventions to resolve module filenames to their originating .md files.

Usage:
    python3 traceback.py vale-report.json assembly-map.json [--source-dir DIR]

Output: JSON array of findings grouped by .md source file.
"""
import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path


def build_reverse_map(assembly_map):
    """Build adoc filename → md path mapping from assembly-map.json.

    Also derives namespace prefixes so modules can be mapped back.
    Returns (adoc_to_md, namespace_prefixes) where namespace_prefixes
    maps each prefix string to its md directory path.
    """
    adoc_to_md = {}
    namespace_prefixes = {}

    for md_path, adoc_filename in assembly_map.items():
        adoc_to_md[adoc_filename] = md_path
        namespace = md_path.split("/")[0] if "/" in md_path else ""
        if namespace:
            prefix = f"{namespace}-"
            namespace_prefixes[prefix] = namespace

    return adoc_to_md, namespace_prefixes


def resolve_module_to_md(module_filename, adoc_to_md, namespace_prefixes):
    """Resolve a module .adoc filename to its source .md path.

    Modules use the pattern {namespace}-{module-name}.adoc.
    The namespace prefix tells us which directory the source came from.
    We match the module back to the assembly's md file by namespace.
    """
    for prefix, namespace in sorted(namespace_prefixes.items(), key=lambda x: -len(x[0])):
        if module_filename.startswith(prefix):
            md_candidates = [
                md_path for md_path in adoc_to_md.values()
                if md_path.startswith(f"{namespace}/")
            ]
            if len(md_candidates) == 1:
                return md_candidates[0]
            return md_candidates if md_candidates else None
    return None


def find_heading_line(md_content, heading_text):
    """Find the line number of a heading in markdown content.

    Returns 1-indexed line number, or None if not found.
    """
    heading_text_clean = re.sub(r'[^\w\s]', '', heading_text).strip().lower()
    for i, line in enumerate(md_content.splitlines(), 1):
        if line.startswith("#"):
            line_text = re.sub(r'^#+\s*', '', line)
            line_text_clean = re.sub(r'[^\w\s]', '', line_text).strip().lower()
            if line_text_clean == heading_text_clean:
                return i
    return None


def extract_heading_from_adoc(adoc_path):
    """Extract the document title from an AsciiDoc file."""
    try:
        content = Path(adoc_path).read_text(encoding="utf-8")
        for line in content.splitlines():
            if line.startswith("= ") and not line.startswith("=="):
                return line[2:].strip()
    except (OSError, UnicodeDecodeError):
        pass
    return None


def parse_vale_report(report_path):
    """Parse Vale JSON output into a list of findings.

    Vale JSON format: { "filepath": [ {finding}, ... ], ... }
    """
    data = json.loads(Path(report_path).read_text(encoding="utf-8"))
    if not data or data == {}:
        return []

    findings = []
    for filepath, file_findings in data.items():
        for finding in file_findings:
            findings.append({
                "adoc_file": filepath,
                "line": finding.get("Line", 0),
                "severity": finding.get("Severity", "warning"),
                "rule": finding.get("Check", ""),
                "message": finding.get("Message", ""),
                "span": finding.get("Span", []),
                "action": finding.get("Action", {}),
            })
    return findings


def resolve_finding_to_md(finding, adoc_to_md, namespace_prefixes, repo_root):
    """Resolve a single finding's adoc file to its MD source.

    Returns the finding dict augmented with md_file and md_line fields.
    """
    adoc_path = finding["adoc_file"]
    adoc_filename = Path(adoc_path).name
    adoc_dir = Path(adoc_path).parent.name

    md_path = None

    if adoc_dir == "assemblies":
        md_path = adoc_to_md.get(adoc_filename)
    elif adoc_dir == "modules":
        result = resolve_module_to_md(adoc_filename, adoc_to_md, namespace_prefixes)
        if isinstance(result, str):
            md_path = result
        elif isinstance(result, list) and result:
            heading = extract_heading_from_adoc(repo_root / adoc_path)
            if heading:
                for candidate in result:
                    source = repo_root.parent / "skupper-docs" / "doc-input" / candidate
                    if not source.exists():
                        source = repo_root / candidate
                    if source.exists():
                        content = source.read_text(encoding="utf-8")
                        if find_heading_line(content, heading):
                            md_path = candidate
                            break
            if not md_path:
                md_path = result[0]

    finding["md_file"] = md_path
    finding["md_line"] = None

    if md_path:
        heading = extract_heading_from_adoc(repo_root / adoc_path)
        if heading:
            for search_root in [
                repo_root.parent / "skupper-docs" / "doc-input",
                repo_root,
            ]:
                source = search_root / md_path
                if source.exists():
                    content = source.read_text(encoding="utf-8")
                    line = find_heading_line(content, heading)
                    if line:
                        finding["md_line"] = line
                    break

    return finding


def group_by_md(findings):
    """Group findings by their resolved MD source file."""
    grouped = defaultdict(list)
    unresolved = []

    for f in findings:
        if f["md_file"]:
            grouped[f["md_file"]].append(f)
        else:
            unresolved.append(f)

    return dict(grouped), unresolved


def format_output(grouped, unresolved):
    """Format the output as structured JSON."""
    output = {
        "findings_by_md_file": {},
        "unresolved_findings": [],
        "summary": {
            "total_findings": 0,
            "resolved_to_md": 0,
            "unresolved": len(unresolved),
            "md_files_affected": len(grouped),
        },
    }

    total = 0
    for md_file, findings in sorted(grouped.items()):
        output["findings_by_md_file"][md_file] = []
        for f in findings:
            total += 1
            output["findings_by_md_file"][md_file].append({
                "adoc_file": f["adoc_file"],
                "md_line": f["md_line"],
                "severity": f["severity"],
                "rule": f["rule"],
                "message": f["message"],
            })

    for f in unresolved:
        total += 1
        output["unresolved_findings"].append({
            "adoc_file": f["adoc_file"],
            "line": f["line"],
            "severity": f["severity"],
            "rule": f["rule"],
            "message": f["message"],
        })

    output["summary"]["total_findings"] = total
    output["summary"]["resolved_to_md"] = total - len(unresolved)

    return output


def main():
    parser = argparse.ArgumentParser(
        description="Map Vale findings on AsciiDoc back to Markdown sources"
    )
    parser.add_argument("vale_report", help="Path to vale-report.json")
    parser.add_argument("assembly_map", help="Path to assembly-map.json")
    parser.add_argument(
        "--source-dir",
        help="Root directory containing .md source files (for line matching)",
    )
    parser.add_argument(
        "--repo-root",
        help="Root of the sk-vale repo (default: auto-detect)",
    )
    args = parser.parse_args()

    if args.repo_root:
        repo_root = Path(args.repo_root).resolve()
    else:
        repo_root = Path(args.vale_report).resolve().parent

    assembly_map = json.loads(Path(args.assembly_map).read_text(encoding="utf-8"))
    adoc_to_md, namespace_prefixes = build_reverse_map(assembly_map)

    findings = parse_vale_report(args.vale_report)
    if not findings:
        output = format_output({}, [])
        print(json.dumps(output, indent=2))
        return

    resolved = [
        resolve_finding_to_md(f, adoc_to_md, namespace_prefixes, repo_root)
        for f in findings
    ]

    grouped, unresolved = group_by_md(resolved)
    output = format_output(grouped, unresolved)
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
