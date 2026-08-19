#!/usr/bin/env bash
set -euo pipefail

SKUPPER_REPO="https://github.com/skupperproject/skupper-docs.git"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

INPUT_DIR=""
DO_COMMIT=false
SKUPPER_BRANCH="skupper"
CLEANUP_DIR=""

usage() {
    cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Convert skupper-docs Markdown to AsciiDoc and run Vale linting.

Options:
  --input-dir <path>  Directory containing .md files (e.g. ../skupper-docs/doc-input)
                      Without this flag, skupper-docs is cloned from GitHub.
  --commit            Commit results to the '$SKUPPER_BRANCH' branch.
  -h, --help          Show this help message.

Note: This script uses mkdocs.yml from upstream (or skupper.md fallback) to define which files to convert.
EOF
    exit 0
}

cleanup() {
    if [[ -n "$CLEANUP_DIR" && -d "$CLEANUP_DIR" ]]; then
        rm -rf "$CLEANUP_DIR"
    fi
}
trap cleanup EXIT

while [[ $# -gt 0 ]]; do
    case "$1" in
        --input-dir) INPUT_DIR="$2"; shift 2 ;;
        --commit)    DO_COMMIT=true; shift ;;
        -h|--help)   usage ;;
        *)           echo "Unknown option: $1"; usage ;;
    esac
done

# --- Check prerequisites ---
missing=()
for cmd in python3 kramdoc vale npm asciidoc-comments; do
    if ! command -v "$cmd" &>/dev/null; then
        missing+=("$cmd")
    fi
done
if [[ ${#missing[@]} -gt 0 ]]; then
    echo "ERROR: Missing required tools: ${missing[*]}"
    echo "  python3             - system Python 3"
    echo "  kramdoc             - gem install kramdown-asciidoc"
    echo "  vale                - https://vale.sh/docs/install/"
    echo "  npm                 - Node.js package manager"
    echo "  asciidoc-comments   - npm install -g @techwriter/asciidoc-comments"
    exit 1
fi

# --- Acquire source ---
if [[ -n "$INPUT_DIR" ]]; then
    if [[ ! -d "$INPUT_DIR" ]]; then
        echo "ERROR: $INPUT_DIR directory not found"
        exit 1
    fi
    SOURCE_DIR="$(cd "$INPUT_DIR" && pwd)"
    echo "Using local input: $SOURCE_DIR"
else
    CLEANUP_DIR="$(mktemp -d)"
    echo "Cloning skupper-docs..."
    git clone --depth 1 "$SKUPPER_REPO" "$CLEANUP_DIR/skupper-docs"
    SOURCE_DIR="$CLEANUP_DIR/skupper-docs/doc-input"
    if [[ ! -d "$SOURCE_DIR" ]]; then
        echo "ERROR: $SOURCE_DIR directory not found in cloned repo"
        exit 1
    fi
    echo "Using cloned input: $SOURCE_DIR"
fi

# --- Clean previous output ---
echo "Cleaning previous output..."
rm -rf "$REPO_ROOT/assemblies" "$REPO_ROOT/modules" "$REPO_ROOT/docs"
rm -f "$REPO_ROOT/index.adoc" "$REPO_ROOT/merged.md" "$REPO_ROOT/merged.adoc"
mkdir -p "$REPO_ROOT/output"

# --- Sync vale styles ---
echo "Syncing Vale styles..."
cd "$REPO_ROOT"
vale sync

# --- Build site using build_index.py ---
echo "Step 1/3: Building assemblies and modules from Markdown..."

# Use mkdocs.yml from upstream or skupper.md as fallback
if [[ -f "$SOURCE_DIR/../mkdocs.yml" ]]; then
    MKDOCS_FILE="$SOURCE_DIR/../mkdocs.yml"
    echo "Using mkdocs.yml from upstream"
elif [[ -f "$REPO_ROOT/skupper.md" ]]; then
    MKDOCS_FILE="$REPO_ROOT/skupper.md"
    echo "Using fallback skupper.md"
else
    echo "ERROR: No index file found (looked for mkdocs.yml or skupper.md)"
    exit 1
fi

python3 "$SCRIPT_DIR/build_index.py" "$MKDOCS_FILE" --output "$REPO_ROOT" --source-dir "$SOURCE_DIR"

if [[ ! -d "$REPO_ROOT/assemblies" ]] || [[ ! -d "$REPO_ROOT/modules" ]]; then
    echo "ERROR: build_index.py failed to create assemblies/ and modules/"
    exit 1
fi

echo "Generated index.adoc with $(ls -1 "$REPO_ROOT/assemblies"/*.adoc 2>/dev/null | wc -l) assemblies and $(ls -1 "$REPO_ROOT/modules"/*.adoc 2>/dev/null | wc -l) modules"

# --- Generate subset index (master.adoc) ---
echo "Generating subset documentation (master.adoc)..."
if [[ -f "$REPO_ROOT/subset.yml" ]]; then
    python3 "$SCRIPT_DIR/build_index.py" \
        "$REPO_ROOT/subset.yml" \
        --output "$REPO_ROOT" \
        --source-dir "$SOURCE_DIR" \
        --index-only \
        --title "User Guide" \
        --output-name "master.adoc"

    if [[ -f "$REPO_ROOT/master.adoc" ]]; then
        echo "Generated master.adoc with $(grep -c '^include::' "$REPO_ROOT/master.adoc") assemblies"
    else
        echo "WARNING: master.adoc generation failed"
    fi
else
    echo "INFO: subset.yml not found, skipping master.adoc generation"
fi

# --- Step 2: Run Vale ---
echo "Step 2/3: Running Vale..."
cd "$REPO_ROOT"
vale_exit=0
vale --output=JSON assemblies/ modules/ 2>&1 | tee "$REPO_ROOT/vale-report.json" || vale_exit=${PIPESTATUS[0]}

if [[ $vale_exit -eq 0 ]]; then
    echo "Vale: all checks passed."
else
    echo "Vale: finished with warnings/errors (exit code $vale_exit)."
fi

# --- Step 3: Generate HTML documentation ---
echo "Step 3/3: Generating HTML documentation..."
cd "$REPO_ROOT"
mkdir -p "$REPO_ROOT/docs"

if [[ ! -f "$REPO_ROOT/index.adoc" ]]; then
    echo "ERROR: index.adoc not found, cannot generate HTML"
    exit 1
fi

html_exit=0
asciidoc-comments "$REPO_ROOT/index.adoc" > "$REPO_ROOT/docs/index.html" || html_exit=$?

if [[ $html_exit -eq 0 ]]; then
    echo "HTML generation: completed successfully."
    echo "Generated: $REPO_ROOT/docs/index.html"
else
    echo "ERROR: HTML generation failed (exit code $html_exit)"
    exit 1
fi

# --- Commit to skupper branch ---
if [[ "$DO_COMMIT" == "true" ]]; then
    echo "Committing to '$SKUPPER_BRANCH' branch..."
    cd "$REPO_ROOT"

    WORKTREE_DIR="$(git worktree list | grep "\[$SKUPPER_BRANCH\]" | awk '{print $1}' || true)"
    WORKTREE_DIR="${WORKTREE_DIR/#\~/$HOME}"

    if [[ -n "$WORKTREE_DIR" && "$WORKTREE_DIR" != "$REPO_ROOT" ]]; then
        cp -a index.adoc assemblies/ modules/ docs/ vale-report.json "$WORKTREE_DIR/"
        [[ -f "$REPO_ROOT/master.adoc" ]] && cp -a master.adoc "$WORKTREE_DIR/"
        cd "$WORKTREE_DIR"
        git add -f index.adoc assemblies/ modules/ docs/ vale-report.json
        [[ -f master.adoc ]] && git add -f master.adoc
    else
        git checkout -B "$SKUPPER_BRANCH"
        git add -f index.adoc assemblies/ modules/ docs/ vale-report.json
        [[ -f master.adoc ]] && git add -f master.adoc
    fi

    git commit -m "Update skupper-docs vale results

Source: skupperproject/skupper-docs
Generated: $(date -u +%Y-%m-%dT%H:%M:%SZ)" || echo "Nothing to commit."
    echo "Committed to '$SKUPPER_BRANCH' branch."
    # Exit 0 when --commit succeeds, regardless of Vale warnings
    # Vale warnings are informational and saved in vale-report.json
    exit 0
fi

exit $vale_exit
