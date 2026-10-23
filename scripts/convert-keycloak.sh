#!/usr/bin/env bash
set -euo pipefail

KEYCLOAK_REPO="https://github.com/pwright/keycloak.git"
KEYCLOAK_BRANCH_SRC="generated-guides"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

INPUT_DIR=""
DO_COMMIT=false
KEYCLOAK_BRANCH="keycloak"
CLEANUP_DIR=""
RESOLVED_DIR=""

INCLUDE_GUIDES=(
    high-availability
    observability
    operator
    securing-apps
    server
    ui-customization
)

usage() {
    cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Run Vale linting on AsciiDoc from pwright/keycloak (generated-guides branch).

Options:
  --input-dir <path>  Root of a keycloak generated-guides checkout.
                      Without this flag, the repo is cloned from GitHub.
  --commit            Commit results to the '$KEYCLOAK_BRANCH' branch.
  -h, --help          Show this help message.
EOF
    exit 0
}

cleanup() {
    if [[ -n "$CLEANUP_DIR" && -d "$CLEANUP_DIR" ]]; then
        rm -rf "$CLEANUP_DIR"
    fi
    if [[ -n "$RESOLVED_DIR" && -d "$RESOLVED_DIR" ]]; then
        rm -rf "$RESOLVED_DIR"
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
    if [[ ! -d "$INPUT_DIR" ]]; then
        echo "ERROR: $INPUT_DIR not found"
        exit 1
    fi
    INPUT_DIR="$(cd "$INPUT_DIR" && pwd)"
    echo "Using local input: $INPUT_DIR"
else
    CLEANUP_DIR="$(mktemp -d)"
    echo "Cloning pwright/keycloak ($KEYCLOAK_BRANCH_SRC branch)..."
    git clone --depth 1 --branch "$KEYCLOAK_BRANCH_SRC" "$KEYCLOAK_REPO" "$CLEANUP_DIR/keycloak"
    INPUT_DIR="$CLEANUP_DIR/keycloak"
    echo "Using cloned input: $INPUT_DIR"
fi

# --- Clean previous output ---
echo "Cleaning previous output..."
rm -rf "$REPO_ROOT/assemblies" "$REPO_ROOT/modules"
mkdir -p "$REPO_ROOT/assemblies" "$REPO_ROOT/modules"

# --- Sync vale styles ---
echo "Syncing Vale styles..."
cd "$REPO_ROOT"
vale sync

# --- Resolve conditionals on monolithic files ---
echo "Resolving AsciiDoc conditionals (keeping project_product content)..."
RESOLVED_DIR="$(mktemp -d)"
python3 "$SCRIPT_DIR/keycloak-conditionals.py" "$INPUT_DIR" "$RESOLVED_DIR"
INPUT_DIR="$RESOLVED_DIR"

# --- Split each AsciiDoc file into assemblies and modules ---
echo "Splitting AsciiDoc files with leben.py..."
cd "$REPO_ROOT"
count=0
for guide_dir in "${INCLUDE_GUIDES[@]}"; do
    guide_path="$INPUT_DIR/$guide_dir"
    if [[ ! -d "$guide_path" ]]; then
        echo "WARNING: Guide directory not found: $guide_path"
        continue
    fi
    while IFS= read -r -d '' adoc_file; do
        python3 leben.py "$adoc_file"
        count=$((count + 1))
    done < <(find "$guide_path" -name '*.adoc' \
        -not -path '*/partials/*' \
        -not -path '*/templates/*' \
        -not -name 'attributes.adoc' \
        -not -name 'assembly.xml' \
        -print0)
done

if [[ $count -eq 0 ]]; then
    echo "ERROR: No .adoc files found in $INPUT_DIR"
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

# --- Commit to keycloak branch ---
if [[ "$DO_COMMIT" == "true" ]]; then
    echo "Committing to '$KEYCLOAK_BRANCH' branch..."
    cd "$REPO_ROOT"

    WORKTREE_DIR="$(git worktree list | grep "\[$KEYCLOAK_BRANCH\]" | awk '{print $1}' || true)"
    WORKTREE_DIR="${WORKTREE_DIR/#\~/$HOME}"

    if [[ -n "$WORKTREE_DIR" && "$WORKTREE_DIR" != "$REPO_ROOT" ]]; then
        cp -a assemblies/ modules/ vale-report.json "$WORKTREE_DIR/"
        cd "$WORKTREE_DIR"
        git add -f assemblies/ modules/ vale-report.json
    else
        git checkout -B "$KEYCLOAK_BRANCH"
        git add -f assemblies/ modules/ vale-report.json
    fi

    git commit -m "Update keycloak vale results

Source: pwright/keycloak ($KEYCLOAK_BRANCH_SRC)
Generated: $(date -u +%Y-%m-%dT%H:%M:%SZ)" || echo "Nothing to commit."
    echo "Committed to '$KEYCLOAK_BRANCH' branch."
fi

exit $vale_exit
