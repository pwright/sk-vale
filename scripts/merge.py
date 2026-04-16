import os
import re
import argparse
import sys
from collections import Counter
from urllib.parse import urldefrag

DEFAULT_INPUT = "upstreams/skupper-docs/input/index.html.in"
DEFAULT_OUTPUT = "upstreams/merged.md"

# Regex patterns for detecting links
HTML_HREF_PATTERN = re.compile(r"""<a\s+[^>]*href=(['"])(.*?)\1""", re.IGNORECASE)
INLINE_LINK_PATTERN = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
DEFINITION_LINK_PATTERN = re.compile(r"^\[([^\]]+)\]:\s*(.*)$", re.MULTILINE)
ANCHOR_PATTERN = re.compile(r"<a id=['\"]([^'\"]+)['\"]></a>")
SECTION_HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.*)$")
CONTENT_TYPE_MARKER_PATTERN = re.compile(r"^\s*<!--\s*(ASSEMBLY|PROCEDURE|REFERENCE)\s*-->\s*$")
ORDERED_LIST_PATTERN = re.compile(r"^\s{0,3}\d+\.\s+")
FENCE_PATTERN = re.compile(r"^\s*```")
ADOC_SECTION_ID_PATTERN = re.compile(r"^([ \t]*)\[#([^\]]+)\][ \t]*$", re.MULTILINE)
ADOC_HTML_ANCHOR_PATTERN = re.compile(
    r"^([ \t]*)(?:\+\+\+)?<a id=['\"]([^'\"]+)['\"]>(?:\+{3})*</a>(?:\+\+\+)?[ \t]*$",
    re.MULTILINE,
)
ADOC_ID_HEADING_GAP_PATTERN = re.compile(
    r'(^[ \t]*\[id="[^"]+"\][ \t]*)\n(?:[ \t]*\n)+([ \t]*=+\s+)',
    re.MULTILINE,
)
MAX_ABSTRACT_CHARS = 260

def warn(message):
    """Prints a warning to stderr."""
    print(f"WARNING: {message}", file=sys.stderr)

def extract_md_links(index_file):
    """Extracts markdown file paths from an index.html file, converting local .html links to .md equivalents."""
    md_links = []

    with open(index_file, "r", encoding="utf-8") as f:
        content = f.read()

    for _, link_path in HTML_HREF_PATTERN.findall(content):
        link_path = link_path.strip()

        # Ignore external links (absolute URLs)
        if link_path.startswith("http") or link_path.startswith("/"):
            continue

        # Normalize relative paths (e.g., ./kube-cli/index.html → kube-cli/index.md)
        if link_path.startswith("./"):
            link_path = link_path[2:]  # Remove leading "./"

        md_path = link_path.replace(".html", ".md")  # Convert .html to .md

        # Append the converted .md path
        md_links.append(md_path)

    return md_links

def generate_unique_anchor(md_file):
    """Creates a unique anchor using the file's relative path and filename."""
    relative_path = os.path.splitext(md_file)[0]  # Remove .md extension
    anchor = relative_path.replace("/", "-").replace("\\", "-").lower()
    return f"#{anchor}"

def rewrite_anchors(content, anchor_map):
    """Rewrites explicit HTML anchors using a per-file anchor mapping."""
    if not anchor_map:
        return content

    def replace_anchor(match):
        anchor = match.group(1)
        return f'<a id="{anchor_map.get(anchor, anchor)}"></a>'

    return ANCHOR_PATTERN.sub(replace_anchor, content)

def fix_internal_links(content, base_dir, md_file, fragment_targets, local_anchor_map):
    """Fixes internal links so they work within a single merged Markdown file."""
    file_dir = os.path.dirname(md_file)  # Get directory of the file containing links

    def resolve_link(link):
        """Converts relative .html links to .md and then to unique anchors."""
        if link.startswith("http") or link.startswith("/"):
            return link  # Keep absolute links and anchors

        path, fragment = urldefrag(link)

        if not path and fragment:
            return f"#{local_anchor_map.get(fragment, fragment)}"

        if path.startswith("./"):
            path = path[2:]  # Remove leading "./"

        if path.endswith((".png", ".jpg", ".svg", ".gif")):
            return link  # Skip image links

        md_link = path.replace(".html", ".md")
        full_path = os.path.join(base_dir, file_dir, md_link)  # Resolve relative to the file's dir

        if os.path.exists(full_path):
            relative_path = os.path.relpath(full_path, base_dir)
            if fragment:
                return f"#{fragment_targets.get((relative_path, fragment), fragment)}"
            return generate_unique_anchor(relative_path)  # Use full relative path

        return link  # Return unchanged if file not found

    # Fix inline links: `[Text](./page.html)`
    content = INLINE_LINK_PATTERN.sub(lambda m: f"[{m.group(1)}]({resolve_link(m.group(2))})", content)

    # Fix reference-style links: `[ref]: ./page.html`
    content = DEFINITION_LINK_PATTERN.sub(lambda m: f"[{m.group(1)}]: {resolve_link(m.group(2))}", content)

    return content

def is_plain_text_paragraph(paragraph_lines):
    """Returns True if a paragraph looks like short prose suitable for an abstract."""
    if not paragraph_lines:
        return False

    joined = " ".join(line.strip() for line in paragraph_lines).strip()
    if not joined or len(joined) > MAX_ABSTRACT_CHARS:
        return False

    first = paragraph_lines[0].strip()
    disallowed_prefixes = (
        "<a ",
        "<!--",
        "[",
        ":",
        "* ",
        "- ",
        "+ ",
        ">",
        "|",
        ".",
        "```",
    )

    if first.startswith(disallowed_prefixes):
        return False

    if first.startswith("**") and first.endswith("**"):
        return False

    if ORDERED_LIST_PATTERN.match(first):
        return False

    return True

def find_heading_indices(lines):
    """Returns indices for Markdown headings outside fenced code blocks."""
    heading_indices = []
    in_fence = False

    for i, line in enumerate(lines):
        if FENCE_PATTERN.match(line):
            in_fence = not in_fence
            continue

        if not in_fence and SECTION_HEADING_PATTERN.match(line):
            heading_indices.append(i)

    return heading_indices

def extract_content_type_marker(section_lines):
    """Removes and returns a content-type marker near the top of a section."""
    body = list(section_lines)

    for i, line in enumerate(body):
        stripped = line.strip()
        if not stripped:
            continue

        match = CONTENT_TYPE_MARKER_PATTERN.match(line)
        if match:
            del body[i]
            return match.group(1), body

        break

    return None, body

def find_abstract_insertion_point(section_lines):
    """Finds the first suitable paragraph for use as a generated abstract."""
    i = 0
    in_fence = False

    while i < len(section_lines):
        line = section_lines[i]

        if FENCE_PATTERN.match(line):
            in_fence = not in_fence
            i += 1
            continue

        if in_fence:
            i += 1
            continue

        stripped = line.strip()

        if not stripped or CONTENT_TYPE_MARKER_PATTERN.match(line):
            i += 1
            continue

        if stripped.startswith("<!--") and stripped.endswith("-->"):
            i += 1
            continue

        start = i
        paragraph_lines = []

        while i < len(section_lines):
            current = section_lines[i]
            current_stripped = current.strip()

            if not current_stripped:
                break

            if FENCE_PATTERN.match(current):
                break

            paragraph_lines.append(current)
            i += 1

        if is_plain_text_paragraph(paragraph_lines):
            return start

        return None

    return None

def ensure_procedure_block_title(section_lines):
    """Normalizes or inserts a Procedure block title for task sections."""
    body = list(section_lines)
    in_fence = False

    for i, line in enumerate(body):
        if FENCE_PATTERN.match(line):
            in_fence = not in_fence
            continue

        if in_fence:
            continue

        if line.strip() == ".Procedure":
            return body

        if line.strip() == "**Procedure**":
            body[i] = line.replace("**Procedure**", ".Procedure", 1)
            return body

    in_fence = False
    for i, line in enumerate(body):
        if FENCE_PATTERN.match(line):
            in_fence = not in_fence
            continue

        if not in_fence and ORDERED_LIST_PATTERN.match(line):
            body[i:i] = [".Procedure\n", "\n"]
            return body

    return body

def prepare_section_body(section_lines, source_name, heading_text):
    """Injects AsciiDocDITA metadata into a Markdown section based on markers."""
    content_type, body = extract_content_type_marker(section_lines)

    if not content_type:
        return section_lines

    body = ensure_procedure_block_title(body) if content_type == "PROCEDURE" else body

    prepared = ["\n", f":_mod-docs-content-type: {content_type}\n", "\n"]
    abstract_index = find_abstract_insertion_point(body)

    if abstract_index is None:
        warn(f"{source_name}: heading '{heading_text}' has no suitable short plain-text paragraph for [role=\"_abstract\"]")
        return prepared + body

    prepared.extend(body[:abstract_index])
    prepared.extend(["[role=\"_abstract\"]\n", "\n"])
    prepared.extend(body[abstract_index:])

    return prepared

def prepare_markdown_for_kramdoc(content, source_name="<memory>"):
    """Converts lightweight Markdown markers into raw AsciiDoc metadata."""
    lines = content.splitlines(keepends=True)
    heading_indices = find_heading_indices(lines)

    if not heading_indices:
        return content

    prepared = []
    pos = 0

    for offset, heading_index in enumerate(heading_indices):
        next_heading = heading_indices[offset + 1] if offset + 1 < len(heading_indices) else len(lines)
        heading_match = SECTION_HEADING_PATTERN.match(lines[heading_index])
        heading_text = heading_match.group(2).strip() if heading_match else lines[heading_index].strip()

        prepared.extend(lines[pos:heading_index + 1])
        prepared.extend(
            prepare_section_body(
                lines[heading_index + 1:next_heading],
                source_name,
                heading_text,
            )
        )
        pos = next_heading

    prepared.extend(lines[pos:])
    return "".join(prepared)

def prepare_markdown_file(input_file, output_file):
    """Prepares a Markdown file for kramdoc without modifying the source file."""
    with open(input_file, "r", encoding="utf-8") as in_f:
        content = in_f.read()

    prepared = prepare_markdown_for_kramdoc(content, input_file)

    output_dir = os.path.dirname(output_file)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    with open(output_file, "w", encoding="utf-8") as out_f:
        out_f.write(prepared)

    print(f"Prepared Markdown saved to: {output_file}")

def normalize_adoc_ids(content):
    """Rewrites kramdoc-style IDs and passthrough HTML anchors as AsciiDoc IDs."""
    content = ADOC_HTML_ANCHOR_PATTERN.sub(r'\1[id="\2"]', content)
    content = ADOC_SECTION_ID_PATTERN.sub(r'\1[id="\2"]', content)
    content = ADOC_ID_HEADING_GAP_PATTERN.sub(r"\1\n\2", content)
    return content

def convert_adoc_ids(input_file, output_file):
    """Normalizes AsciiDoc IDs in-place or to a new output file."""
    with open(input_file, "r", encoding="utf-8") as in_f:
        content = in_f.read()

    converted = normalize_adoc_ids(content)

    output_dir = os.path.dirname(output_file)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    with open(output_file, "w", encoding="utf-8") as out_f:
        out_f.write(converted)

    print(f"Normalized AsciiDoc IDs saved to: {output_file}")

def merge_markdown(index_file, output_file):
    """Merges markdown files into a single file while fixing internal links."""
    base_dir = os.path.dirname(index_file)
    md_links = extract_md_links(index_file)

    # Ensure output directory exists
    output_dir = os.path.dirname(output_file)
    os.makedirs(output_dir, exist_ok=True)

    documents = []

    for md_file in md_links:
        full_path = os.path.join(base_dir, md_file)
        if not os.path.exists(full_path):
            continue

        with open(full_path, "r", encoding="utf-8") as f:
            content = f.read()

        relative_path = os.path.relpath(full_path, base_dir)
        page_anchor = generate_unique_anchor(relative_path)[1:]
        explicit_anchors = ANCHOR_PATTERN.findall(content)

        documents.append({
            "md_file": md_file,
            "relative_path": relative_path,
            "content": content,
            "page_anchor": page_anchor,
            "explicit_anchors": explicit_anchors,
        })

    anchor_counts = Counter(
        anchor
        for document in documents
        for anchor in document["explicit_anchors"]
    )

    fragment_targets = {}
    for document in documents:
        anchor_map = {}
        for anchor in document["explicit_anchors"]:
            rewritten_anchor = anchor
            if anchor_counts[anchor] > 1:
                rewritten_anchor = f'{document["page_anchor"]}-{anchor}'
            anchor_map[anchor] = rewritten_anchor
            fragment_targets[(document["relative_path"], anchor)] = rewritten_anchor
        document["anchor_map"] = anchor_map
        document["insert_page_anchor"] = document["page_anchor"] not in document["explicit_anchors"]

    merged_content = []

    for document in documents:
        content = fix_internal_links(
            document["content"],
            base_dir,
            document["md_file"],
            fragment_targets,
            document["anchor_map"],
        )
        content = rewrite_anchors(content, document["anchor_map"])
        content = prepare_markdown_for_kramdoc(content, document["relative_path"])

        if document["insert_page_anchor"]:
            content = f'<a id="{document["page_anchor"]}"></a>\n' + content

        merged_content.append(content.strip())

    with open(output_file, "w", encoding="utf-8") as out_f:
        out_f.write("\n\n".join(merged_content) + "\n")

    print(f"Merged markdown saved to: {output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Merge nested markdown files into a single file while fixing internal links.")
    parser.add_argument("index_file", nargs="?", default=DEFAULT_INPUT, help="Path to the index.md file (default: input/index.html.in)")
    parser.add_argument("-o", "--output", help="Output file")
    parser.add_argument(
        "--normalize-adoc-ids",
        action="store_true",
        help="Rewrite kramdoc-style AsciiDoc IDs and passthrough HTML anchors as [id=\"...\"]",
    )
    parser.add_argument(
        "--prepare-md",
        action="store_true",
        help="Convert Markdown content-type markers into raw AsciiDoc metadata before kramdoc",
    )
    
    args = parser.parse_args()
    if args.normalize_adoc_ids:
        output_file = args.output or args.index_file
        convert_adoc_ids(args.index_file, output_file)
    elif args.prepare_md:
        output_file = args.output or args.index_file
        prepare_markdown_file(args.index_file, output_file)
    else:
        output_file = args.output or DEFAULT_OUTPUT
        merge_markdown(args.index_file, output_file)
