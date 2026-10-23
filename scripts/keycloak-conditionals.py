#!/usr/bin/env python3
"""
Resolve AsciiDoc conditional directives while preserving includes.
Processes all .adoc files in a directory tree, keeping project_product content
and removing project_community content.
"""

import os
import re
import sys
from pathlib import Path

def evaluate_condition(condition, attributes):
    """Evaluate an ifeval condition."""
    # Handle empty string comparisons
    if '""' in condition:
        # These are usually for preview features, evaluate as false
        return False

    # Extract variable and comparison
    # Examples: {project_product}==true, {project_community}==false
    match = re.search(r'\{(\w+)\}\s*(==|!=)\s*(\w+)', condition)
    if not match:
        return False

    var_name = match.group(1)
    operator = match.group(2)
    expected_value = match.group(3)

    # Get actual value from attributes
    actual_value = attributes.get(var_name, '')

    # Evaluate comparison
    if operator == '==':
        return str(actual_value).lower() == expected_value.lower()
    elif operator == '!=':
        return str(actual_value).lower() != expected_value.lower()

    return False

def process_file(input_path, output_path, attributes):
    """Process a single AsciiDoc file, resolving conditionals."""

    with open(input_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    output_lines = []
    condition_stack = []  # Stack of (condition_result, original_line)

    for line in lines:
        # Check for ifeval directive
        ifeval_match = re.match(r'^ifeval::\[(.*?)\]\s*$', line)
        if ifeval_match:
            condition = ifeval_match.group(1)
            result = evaluate_condition(condition, attributes)
            condition_stack.append((result, line))
            # Don't output the ifeval line
            continue

        # Check for endif directive
        if re.match(r'^endif::\[\]\s*$', line):
            if condition_stack:
                condition_stack.pop()
            # Don't output the endif line
            continue

        # Determine if we should output this line
        should_output = True
        for condition_result, _ in condition_stack:
            if not condition_result:
                should_output = False
                break

        if should_output:
            output_lines.append(line)

    # Write output file
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.writelines(output_lines)

def process_directory(source_dir, target_dir, attributes):
    """Process all .adoc files in a directory tree."""

    source_path = Path(source_dir)
    target_path = Path(target_dir)

    # Find all .adoc files
    adoc_files = list(source_path.rglob('*.adoc'))

    print(f"Found {len(adoc_files)} .adoc files to process")

    for input_file in adoc_files:
        # Calculate relative path
        relative_path = input_file.relative_to(source_path)
        output_file = target_path / relative_path

        print(f"Processing: {relative_path}")

        try:
            process_file(input_file, output_file, attributes)
        except Exception as e:
            print(f"ERROR processing {relative_path}: {e}", file=sys.stderr)
            continue

    print(f"\nComplete! Processed files saved to: {target_dir}")

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='Resolve AsciiDoc conditional directives, keeping project_product content.'
    )
    parser.add_argument('source_dir', help='Directory containing monolithic .adoc files')
    parser.add_argument('target_dir', help='Output directory for resolved files')
    args = parser.parse_args()

    attributes = {
        'project_product': 'true',
        'project_community': 'false',
    }

    if not os.path.isdir(args.source_dir):
        print(f"ERROR: Source directory not found: {args.source_dir}", file=sys.stderr)
        sys.exit(1)

    process_directory(args.source_dir, args.target_dir, attributes)

if __name__ == '__main__':
    main()