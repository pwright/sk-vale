#!/usr/bin/env python3
"""
Generate completeness report from conversion pipeline metrics.

Aggregates metrics from merge, kramdoc, and split stages to create
a unified completeness report.
"""
import argparse
import json
import sys
from pathlib import Path


def load_metrics(filepath):
    """Load metrics from JSON file."""
    if not filepath or not Path(filepath).exists():
        return None

    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def calculate_completeness(merge_metrics, kramdoc_metrics, split_metrics):
    """Calculate completeness statistics from all stages."""
    completeness = {
        "status": "unknown",
        "files_discovered": 0,
        "files_processed": 0,
        "files_missing": 0,
        "completeness_percentage": 0.0
    }

    if not merge_metrics:
        return completeness

    input_data = merge_metrics.get("input", {})
    completeness["files_discovered"] = input_data.get("files_discovered", 0)
    completeness["files_processed"] = input_data.get("files_found", 0)
    completeness["files_missing"] = input_data.get("files_missing", 0)

    if completeness["files_discovered"] > 0:
        completeness["completeness_percentage"] = round(
            (completeness["files_processed"] / completeness["files_discovered"]) * 100,
            1
        )

    # Determine status
    if completeness["files_missing"] == 0:
        completeness["status"] = "complete"
    elif completeness["completeness_percentage"] >= 90:
        completeness["status"] = "warning"
    else:
        completeness["status"] = "incomplete"

    return completeness


def extract_heading_counts(metrics, stage_key):
    """Extract heading counts from metrics."""
    if not metrics:
        return {}

    if stage_key == "merged_md":
        return metrics.get("output", {}).get("headings", {})
    elif stage_key == "merged_adoc":
        return metrics.get("headings", {})
    elif stage_key == "split":
        output = metrics.get("output", {})
        return {
            "assemblies": output.get("assemblies_created", 0),
            "modules": output.get("modules_created", 0)
        }

    return {}


def generate_warnings(merge_metrics, kramdoc_metrics, split_metrics, completeness):
    """Generate list of warnings based on metrics."""
    warnings = []

    # File missing warnings
    if completeness["files_missing"] > 0:
        warnings.append(
            f"{completeness['files_missing']} file(s) from index.md not found"
        )

    # Heading preservation warnings
    if merge_metrics and kramdoc_metrics:
        md_headings = merge_metrics.get("output", {}).get("headings", {})
        adoc_headings = kramdoc_metrics.get("headings", {})

        md_total = sum(md_headings.values())
        adoc_total = sum(adoc_headings.values())

        if adoc_total < md_total:
            loss = md_total - adoc_total
            warnings.append(
                f"{loss} heading(s) lost during kramdoc conversion (may be normalization)"
            )

    # H1 count vs assemblies mismatch
    if kramdoc_metrics and split_metrics:
        h1_count = kramdoc_metrics.get("headings", {}).get("h1", 0)
        assemblies = split_metrics.get("output", {}).get("assemblies_created", 0)

        if assemblies != h1_count:
            warnings.append(
                f"H1 headings ({h1_count}) != assemblies created ({assemblies})"
            )

    return warnings


def generate_report(merge_file, kramdoc_file, split_file):
    """Generate completeness report from metric files."""
    merge_metrics = load_metrics(merge_file)
    kramdoc_metrics = load_metrics(kramdoc_file)
    split_metrics = load_metrics(split_file)

    completeness = calculate_completeness(merge_metrics, kramdoc_metrics, split_metrics)
    warnings = generate_warnings(merge_metrics, kramdoc_metrics, split_metrics, completeness)

    # Build heading counts structure
    heading_counts = {
        "merged_md": extract_heading_counts(merge_metrics, "merged_md"),
        "merged_adoc": extract_heading_counts(kramdoc_metrics, "merged_adoc"),
        "split": extract_heading_counts(split_metrics, "split")
    }

    # Extract heading details
    heading_details = {
        "merged_md": merge_metrics.get("output", {}).get("heading_details", []) if merge_metrics else [],
        "merged_adoc": kramdoc_metrics.get("heading_details", []) if kramdoc_metrics else [],
        "modules": split_metrics.get("output", {}).get("modules", []) if split_metrics else [],
        "assemblies": split_metrics.get("output", {}).get("assemblies", []) if split_metrics else []
    }

    # Build full report
    report = {
        "summary": completeness,
        "heading_counts": heading_counts,
        "heading_details": heading_details,
        "warnings": warnings,
        "missing_files": merge_metrics.get("missing_files", []) if merge_metrics else [],
        "stages": {
            "merge": merge_metrics,
            "kramdoc": kramdoc_metrics,
            "split": split_metrics
        }
    }

    return report


def format_text_summary(report):
    """Generate human-readable text summary."""
    summary = report["summary"]
    heading_counts = report["heading_counts"]
    heading_details = report.get("heading_details", {})
    warnings = report["warnings"]
    missing_files = report["missing_files"]

    # Status symbol
    if summary["status"] == "complete":
        status_symbol = "✓"
    elif summary["status"] == "warning":
        status_symbol = "⚠"
    else:
        status_symbol = "✗"

    lines = [
        "Skupper-docs Conversion Completeness Report",
        "=" * 50,
        "",
        f"SUMMARY: {status_symbol} {summary['status'].title()} ({summary['completeness_percentage']}%)",
        "",
        "Files:",
        f"  Discovered from index.md: {summary['files_discovered']}",
        f"  Successfully processed:   {summary['files_processed']}",
        f"  Missing/skipped:          {summary['files_missing']}",
        "",
        "Headings:",
    ]

    # Markdown headings
    md_headings = heading_counts.get("merged_md", {})
    if md_headings:
        h_counts = " ".join([f"H{i}: {md_headings.get(f'h{i}', 0)}" for i in range(1, 4)])
        lines.append(f"  Source (merged.md):       {h_counts}")

    # AsciiDoc headings
    adoc_headings = heading_counts.get("merged_adoc", {})
    if adoc_headings:
        h_counts = " ".join([f"H{i}: {adoc_headings.get(f'h{i}', 0)}" for i in range(1, 4)])
        lines.append(f"  AsciiDoc (merged.adoc):   {h_counts}")

    # Split output
    split_counts = heading_counts.get("split", {})
    if split_counts:
        lines.append(
            f"  Split output:             "
            f"Assemblies: {split_counts.get('assemblies', 0)}  "
            f"Modules: {split_counts.get('modules', 0)}"
        )

    # Show sample headings from AsciiDoc
    adoc_heading_list = heading_details.get("merged_adoc", [])
    if adoc_heading_list:
        lines.extend(["", "Sample Headings (first 10):"])
        for i, heading in enumerate(adoc_heading_list[:10], 1):
            indent = "  " * heading["level"]
            lines.append(f"  {i}. {indent}[H{heading['level']}] {heading['text']} (line {heading['line']})")
        if len(adoc_heading_list) > 10:
            lines.append(f"  ... and {len(adoc_heading_list) - 10} more (see JSON for full list)")

    # Warnings
    if warnings:
        lines.extend(["", "WARNINGS:"])
        for warning in warnings:
            lines.append(f"  ⚠ {warning}")

    # Missing files
    if missing_files:
        lines.extend(["", "Missing files:"])
        for file in missing_files[:10]:  # Limit to first 10
            lines.append(f"  - {file}")
        if len(missing_files) > 10:
            lines.append(f"  ... and {len(missing_files) - 10} more")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description='Generate completeness report from conversion pipeline metrics'
    )
    parser.add_argument(
        '--merge',
        required=True,
        help='Path to merge metrics JSON file'
    )
    parser.add_argument(
        '--kramdoc',
        required=True,
        help='Path to kramdoc metrics JSON file'
    )
    parser.add_argument(
        '--split',
        required=True,
        help='Path to split metrics JSON file'
    )
    parser.add_argument(
        '-o', '--output',
        required=True,
        help='Output JSON file'
    )
    parser.add_argument(
        '--text-summary',
        help='Also write text summary to this file'
    )

    args = parser.parse_args()

    # Generate report
    report = generate_report(args.merge, args.kramdoc, args.split)

    # Ensure output directory exists
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Write JSON report
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2)

    print(f"Completeness report written to: {args.output}")

    # Write text summary if requested
    if args.text_summary:
        text_summary = format_text_summary(report)
        with open(args.text_summary, 'w', encoding='utf-8') as f:
            f.write(text_summary)
        print(f"Text summary written to: {args.text_summary}")
    else:
        # Print to stdout
        print("\n" + format_text_summary(report))


if __name__ == '__main__':
    main()
