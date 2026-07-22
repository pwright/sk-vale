#!/usr/bin/env bash
set -euo pipefail

APICURIO_REPO="https://github.com/apicurio/apicurio-registry.git"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PAGES_SUBDIR="docs/modules/ROOT/pages/getting-started"

INPUT_DIR=""
DO_COMMIT=false
APICURIO_BRANCH="apicurio"
CLEANUP_DIR=""

usage() {
    cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Run Vale linting on AsciiDoc from apicurio-registry.

Options:
  --input-dir <path>  Root of an apicurio-registry checkout.
                      Without this flag, the repo is cloned from GitHub.
  --commit            Commit results to the '$APICURIO_BRANCH' branch.
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
for cmd in python3 vale; do
    if ! command -v "$cmd" &>/dev/null; then
        missing+=("$cmd")
    fi
done
if [[ ${#missing[@]} -gt 0 ]]; then
    echo "ERROR: Missing required tools: ${missing[*]}"
    echo "  python3   - system Python 3"
    echo "  vale      - https://vale.sh/docs/install/"
    exit 1
fi

# --- Acquire source ---
if [[ -n "$INPUT_DIR" ]]; then
    PAGES_DIR="$INPUT_DIR/$PAGES_SUBDIR"
    if [[ ! -d "$PAGES_DIR" ]]; then
        echo "ERROR: $PAGES_DIR not found"
        exit 1
    fi
    PAGES_DIR="$(cd "$PAGES_DIR" && pwd)"
    echo "Using local input: $PAGES_DIR"
else
    CLEANUP_DIR="$(mktemp -d)"
    echo "Cloning apicurio-registry..."
    git clone --depth 1 "$APICURIO_REPO" "$CLEANUP_DIR/apicurio-registry"
    PAGES_DIR="$CLEANUP_DIR/apicurio-registry/$PAGES_SUBDIR"
    if [[ ! -d "$PAGES_DIR" ]]; then
        echo "ERROR: $PAGES_DIR not found in cloned repo"
        exit 1
    fi
    echo "Using cloned input: $PAGES_DIR"
fi

# --- Clean previous output ---
echo "Cleaning previous output..."
rm -rf "$REPO_ROOT/assemblies" "$REPO_ROOT/modules"
mkdir -p "$REPO_ROOT/assemblies" "$REPO_ROOT/modules"

# --- Sync vale styles ---
echo "Syncing Vale styles..."
cd "$REPO_ROOT"
vale sync

# --- Split each AsciiDoc file into assemblies and modules ---
echo "Splitting AsciiDoc files with leben.py..."
cd "$REPO_ROOT"
count=0
for adoc_file in "$PAGES_DIR"/*.adoc; do
    [[ -f "$adoc_file" ]] || continue
    python3 leben.py "$adoc_file"
    count=$((count + 1))
done

if [[ $count -eq 0 ]]; then
    echo "ERROR: No .adoc files found in $PAGES_DIR"
    exit 1
fi
echo "Processed $count files."

# --- Run Vale ---
echo "Running Vale..."
cd "$REPO_ROOT"
vale_exit=0
vale --output=JSON assemblies/ modules/ 2>&1 | tee "$REPO_ROOT/vale-report.json" || vale_exit=${PIPESTATUS[0]}

if [[ $vale_exit -eq 0 ]]; then
    echo "Vale: all checks passed."
else
    echo "Vale: finished with warnings/errors (exit code $vale_exit)."
fi

# --- Commit to apicurio branch ---
if [[ "$DO_COMMIT" == "true" ]]; then
    echo "Committing to '$APICURIO_BRANCH' branch..."
    cd "$REPO_ROOT"

    WORKTREE_DIR="$(git worktree list | grep "\[$APICURIO_BRANCH\]" | awk '{print $1}' || true)"
    WORKTREE_DIR="${WORKTREE_DIR/#\~/$HOME}"

    if [[ -n "$WORKTREE_DIR" && "$WORKTREE_DIR" != "$REPO_ROOT" ]]; then
        cp -a assemblies/ modules/ vale-report.json "$WORKTREE_DIR/"
        cd "$WORKTREE_DIR"
        git add -f assemblies/ modules/ vale-report.json
    else
        git checkout -B "$APICURIO_BRANCH"
        git add -f assemblies/ modules/ vale-report.json
    fi

    git commit -m "Update apicurio-registry vale results

Source: apicurio/apicurio-registry
Generated: $(date -u +%Y-%m-%dT%H:%M:%SZ)" || echo "Nothing to commit."
    echo "Committed to '$APICURIO_BRANCH' branch."
fi

exit $vale_exit
