#!/usr/bin/env python3
"""
Count headings in Markdown or AsciiDoc files.

Outputs JSON with heading counts by level.
"""
import argparse
import json
import re
import sys
from pathlib import Path

# Regex patterns for heading detection
MD_HEADING_PATTERN = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)
ADOC_HEADING_PATTERN = re.compile(r'^(=+)\s+(.+)$', re.MULTILINE)
MD_CODE_FENCE = re.compile(r'^```', re.MULTILINE)


def count_markdown_headings(content):
    """Count headings in markdown content, excluding code blocks."""
    heading_counts = {f'h{i}': 0 for i in range(1, 7)}
    headings_list = []

    # Remove code blocks to avoid counting headings in code
    in_code_block = False
    lines = content.split('\n')
    line_mapping = {}  # Maps filtered line index to original line number
    filtered_lines = []

    original_line_num = 1
    for line in lines:
        if line.strip().startswith('```'):
            in_code_block = not in_code_block
            original_line_num += 1
            continue
        if not in_code_block:
            line_mapping[len(filtered_lines)] = original_line_num
            filtered_lines.append(line)
        original_line_num += 1

    filtered_content = '\n'.join(filtered_lines)

    # Count headings and track details
    current_pos = 0
    for match in MD_HEADING_PATTERN.finditer(filtered_content):
        level = len(match.group(1))
        text = match.group(2).strip()
        heading_counts[f'h{level}'] += 1

        # Calculate line number
        lines_before_match = filtered_content[:match.start()].count('\n')
        original_line = line_mapping.get(lines_before_match, lines_before_match + 1)

        headings_list.append({
            'level': level,
            'text': text,
            'line': original_line
        })

    return heading_counts, headings_list


def count_asciidoc_headings(content):
    """Count headings in AsciiDoc content."""
    heading_counts = {f'h{i}': 0 for i in range(1, 7)}
    headings_list = []

    # In AsciiDoc, = is h1, == is h2, etc.
    for match in ADOC_HEADING_PATTERN.finditer(content):
        level = len(match.group(1))
        text = match.group(2).strip()
        if level <= 6:
            heading_counts[f'h{level}'] += 1

            # Calculate line number
            line_num = content[:match.start()].count('\n') + 1

            headings_list.append({
                'level': level,
                'text': text,
                'line': line_num
            })

    return heading_counts, headings_list


def count_headings(file_path):
    """Count headings in a file, auto-detecting format."""
    path = Path(file_path)

    if not path.exists():
        print(f"ERROR: File not found: {file_path}", file=sys.stderr)
        sys.exit(1)

    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Determine format by extension
    if path.suffix in ['.md', '.markdown']:
        heading_counts, headings_list = count_markdown_headings(content)
        format_type = 'markdown'
    elif path.suffix in ['.adoc', '.asciidoc']:
        heading_counts, headings_list = count_asciidoc_headings(content)
        format_type = 'asciidoc'
    else:
        # Default to markdown
        heading_counts, headings_list = count_markdown_headings(content)
        format_type = 'markdown'

    return {
        'file': str(path),
        'format': format_type,
        'headings': heading_counts,
        'total_headings': sum(heading_counts.values()),
        'heading_details': headings_list
    }


def main():
    parser = argparse.ArgumentParser(
        description='Count headings in Markdown or AsciiDoc files'
    )
    parser.add_argument(
        'file',
        help='File to analyze'
    )
    parser.add_argument(
        '-o', '--output',
        help='Output JSON file (default: stdout)'
    )

    args = parser.parse_args()

    result = count_headings(args.file)

    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2)
        print(f"Metrics written to: {args.output}", file=sys.stderr)
    else:
        print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
