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
rm -rf "$REPO_ROOT/assemblies" "$REPO_ROOT/modules" "$REPO_ROOT/images"
rm -f "$REPO_ROOT/index.adoc" "$REPO_ROOT/merged.md" "$REPO_ROOT/merged.adoc"
mkdir -p "$REPO_ROOT/output"

# --- Sync vale styles ---
echo "Syncing Vale styles..."
cd "$REPO_ROOT"
vale sync

# --- Build site using build_index.py ---
echo "Step 1/2: Building assemblies and modules from Markdown..."
python3 "$SCRIPT_DIR/build_index.py" "$SOURCE_DIR/index.md" --output "$REPO_ROOT"

if [[ ! -d "$REPO_ROOT/assemblies" ]] || [[ ! -d "$REPO_ROOT/modules" ]]; then
    echo "ERROR: build_index.py failed to create assemblies/ and modules/"
    exit 1
fi

echo "Generated index.adoc with $(ls -1 "$REPO_ROOT/assemblies"/*.adoc 2>/dev/null | wc -l) assemblies and $(ls -1 "$REPO_ROOT/modules"/*.adoc 2>/dev/null | wc -l) modules"

# --- Step 2: Run Vale ---
echo "Step 2/2: Running Vale..."
cd "$REPO_ROOT"
vale_exit=0
vale --output=JSON assemblies/ modules/ 2>&1 | tee "$REPO_ROOT/vale-report.json" || vale_exit=${PIPESTATUS[0]}

if [[ $vale_exit -eq 0 ]]; then
    echo "Vale: all checks passed."
else
    echo "Vale: finished with warnings/errors (exit code $vale_exit)."
fi

# --- Commit to skupper branch ---
if [[ "$DO_COMMIT" == "true" ]]; then
    echo "Committing to '$SKUPPER_BRANCH' branch..."
    cd "$REPO_ROOT"

    WORKTREE_DIR="$(git worktree list | grep "\[$SKUPPER_BRANCH\]" | awk '{print $1}' || true)"
    WORKTREE_DIR="${WORKTREE_DIR/#\~/$HOME}"

    if [[ -n "$WORKTREE_DIR" && "$WORKTREE_DIR" != "$REPO_ROOT" ]]; then
        cp -a index.adoc assemblies/ modules/ images/ vale-report.json "$WORKTREE_DIR/"
        cd "$WORKTREE_DIR"
        git add -f index.adoc assemblies/ modules/ images/ vale-report.json
    else
        git checkout -B "$SKUPPER_BRANCH"
        git add -f index.adoc assemblies/ modules/ images/ vale-report.json
    fi

    git commit -m "Update skupper-docs vale results

Source: skupperproject/skupper-docs
Generated: $(date -u +%Y-%m-%dT%H:%M:%SZ)" || echo "Nothing to commit."
    echo "Committed to '$SKUPPER_BRANCH' branch."
fi

exit $vale_exit
