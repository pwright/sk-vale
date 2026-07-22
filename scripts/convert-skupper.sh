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
  --input-dir <path>  Directory containing index.md (e.g. ../skupper-docs/input)
                      Without this flag, skupper-docs is cloned from GitHub.
  --commit            Commit results to the '$SKUPPER_BRANCH' branch.
  -h, --help          Show this help message.
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
for cmd in python3 kramdoc vale; do
    if ! command -v "$cmd" &>/dev/null; then
        missing+=("$cmd")
    fi
done
if [[ ${#missing[@]} -gt 0 ]]; then
    echo "ERROR: Missing required tools: ${missing[*]}"
    echo "  python3   - system Python 3"
    echo "  kramdoc   - gem install kramdown-asciidoc"
    echo "  vale      - https://vale.sh/docs/install/"
    exit 1
fi

# --- Acquire source ---
if [[ -n "$INPUT_DIR" ]]; then
    if [[ ! -f "$INPUT_DIR/index.md" ]]; then
        echo "ERROR: $INPUT_DIR/index.md not found"
        exit 1
    fi
    SOURCE_DIR="$(cd "$INPUT_DIR" && pwd)"
    echo "Using local input: $SOURCE_DIR"
else
    CLEANUP_DIR="$(mktemp -d)"
    echo "Cloning skupper-docs..."
    git clone --depth 1 "$SKUPPER_REPO" "$CLEANUP_DIR/skupper-docs"
    SOURCE_DIR="$CLEANUP_DIR/skupper-docs/input"
    if [[ ! -f "$SOURCE_DIR/index.md" ]]; then
        echo "ERROR: $SOURCE_DIR/index.md not found in cloned repo"
        exit 1
    fi
    echo "Using cloned input: $SOURCE_DIR"
fi

# --- Clean previous output ---
echo "Cleaning previous output..."
rm -rf "$REPO_ROOT/assemblies" "$REPO_ROOT/modules"
mkdir -p "$REPO_ROOT/assemblies" "$REPO_ROOT/modules"
rm -f "$REPO_ROOT/merged.md" "$REPO_ROOT/merged.adoc"

# --- Sync vale styles ---
echo "Syncing Vale styles..."
cd "$REPO_ROOT"
vale sync

# --- Step 1: Merge Markdown ---
echo "Step 1/5: Merging Markdown..."
python3 "$SCRIPT_DIR/merge.py" "$SOURCE_DIR/index.md" -o "$REPO_ROOT/merged.md"

if [[ ! -s "$REPO_ROOT/merged.md" ]]; then
    echo "ERROR: merged.md is empty -- no links extracted from index.md"
    exit 1
fi

# --- Step 2: Convert to AsciiDoc ---
echo "Step 2/5: Converting to AsciiDoc with kramdoc..."
kramdoc --format=GFM -o "$REPO_ROOT/merged.adoc" "$REPO_ROOT/merged.md"

# --- Step 3: Normalize AsciiDoc IDs ---
echo "Step 3/5: Normalizing AsciiDoc IDs..."
python3 "$SCRIPT_DIR/merge.py" --normalize-adoc-ids "$REPO_ROOT/merged.adoc"

# --- Step 4: Split into assemblies and modules ---
echo "Step 4/5: Splitting into assemblies and modules..."
cd "$REPO_ROOT"
python3 leben.py merged.adoc

# --- Step 5: Run Vale ---
echo "Step 5/5: Running Vale..."
cd "$REPO_ROOT"
vale_exit=0
vale assemblies/ modules/ 2>&1 | tee "$REPO_ROOT/vale-report.txt" || vale_exit=${PIPESTATUS[0]}

if [[ $vale_exit -eq 0 ]]; then
    echo "Vale: all checks passed."
else
    echo "Vale: finished with warnings/errors (exit code $vale_exit)."
fi

# --- Commit to skupper branch ---
if [[ "$DO_COMMIT" == "true" ]]; then
    echo "Committing to '$SKUPPER_BRANCH' branch..."
    cd "$REPO_ROOT"

    WORKTREE_DIR="$(git worktree list | grep "\[$SKUPPER_BRANCH\]" | awk '{print $1}')"
    WORKTREE_DIR="${WORKTREE_DIR/#\~/$HOME}"

    if [[ -n "$WORKTREE_DIR" && "$WORKTREE_DIR" != "$REPO_ROOT" ]]; then
        cp -a merged.md merged.adoc assemblies/ modules/ vale-report.txt "$WORKTREE_DIR/"
        cd "$WORKTREE_DIR"
        git add merged.md merged.adoc assemblies/ modules/ vale-report.txt
    else
        git checkout -B "$SKUPPER_BRANCH"
        git add merged.md merged.adoc assemblies/ modules/ vale-report.txt
    fi

    git commit -m "Update skupper-docs vale results

Source: skupperproject/skupper-docs
Generated: $(date -u +%Y-%m-%dT%H:%M:%SZ)" || echo "Nothing to commit."
    echo "Committed to '$SKUPPER_BRANCH' branch."
fi

exit $vale_exit
