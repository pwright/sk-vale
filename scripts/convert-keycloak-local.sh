#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
KEYCLOAK_DIR=""
DO_CLEAN=false
SKIP_BUILD=false

usage() {
    cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Build Keycloak generated-guides with Maven, then run Vale linting via convert-keycloak.sh.

On first build (no target/generated-guides), runs a full dependency build.
On subsequent builds, only re-runs the docs plugins (much faster).

Options:
  --keycloak-dir <path>  Root of the keycloak checkout (default: $REPO_ROOT/../keycloak).
  --clean                Force a full clean rebuild of all modules.
  --skip-build           Skip Maven entirely and reuse existing generated-guides.
  -h, --help             Show this help message.
EOF
    exit 0
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --keycloak-dir) KEYCLOAK_DIR="$2"; shift 2 ;;
        --clean)        DO_CLEAN=true; shift ;;
        --skip-build)   SKIP_BUILD=true; shift ;;
        -h|--help)      usage ;;
        *)              echo "Unknown option: $1"; usage ;;
    esac
done

if [[ -z "$KEYCLOAK_DIR" ]]; then
    KEYCLOAK_DIR="$(cd "$REPO_ROOT/../keycloak" 2>/dev/null && pwd)" || {
        echo "ERROR: Could not find keycloak repo at $REPO_ROOT/../keycloak"
        echo "       Use --keycloak-dir to specify the path."
        exit 1
    }
fi

if [[ ! -f "$KEYCLOAK_DIR/docs/guides/pom.xml" ]]; then
    echo "ERROR: $KEYCLOAK_DIR does not look like a keycloak checkout (no docs/guides/pom.xml)"
    exit 1
fi

GENERATED_DIR="$KEYCLOAK_DIR/docs/guides/target/generated-guides"

# --- Build guides with Maven ---
if [[ "$SKIP_BUILD" == "true" ]]; then
    echo "Skipping Maven build (--skip-build)."
elif [[ "$DO_CLEAN" == "true" ]]; then
    echo "Clean build: rebuilding all modules from scratch..."
    rm -f "$KEYCLOAK_DIR/js/node/pnpm"
    (cd "$KEYCLOAK_DIR" && ./mvnw clean install -am -pl docs/guides -DskipTests)
elif [[ ! -d "$GENERATED_DIR" ]]; then
    echo "First build: building all upstream dependencies..."
    rm -f "$KEYCLOAK_DIR/js/node/pnpm"
    (cd "$KEYCLOAK_DIR" && ./mvnw install -am -pl docs/guides -DskipTests)
else
    echo "Incremental build: re-running docs plugins only..."
    (cd "$KEYCLOAK_DIR" && ./mvnw install -pl docs/guides -DskipTests)
fi

if [[ ! -d "$GENERATED_DIR" ]]; then
    echo "ERROR: No generated-guides found at $GENERATED_DIR"
    echo "       Run without --skip-build, or with --clean for a full rebuild."
    exit 1
fi

# --- Run convert-keycloak.sh ---
echo "Running convert-keycloak.sh..."
exec bash "$SCRIPT_DIR/convert-keycloak.sh" --input-dir "$GENERATED_DIR"
