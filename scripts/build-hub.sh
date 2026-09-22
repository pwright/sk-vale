#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

for cmd in python3 asciidoctor; do
    command -v "$cmd" &>/dev/null || { echo "ERROR: $cmd not found"; exit 1; }
done

OUTPUT_DIR="${1:-$REPO_ROOT/jtbd/docs}"
[[ "$OUTPUT_DIR" != /* ]] && OUTPUT_DIR="$REPO_ROOT/$OUTPUT_DIR"

python3 "$SCRIPT_DIR/build_hub.py" \
    --config "$REPO_ROOT/jtbd/hub-config.yml" \
    --output "$OUTPUT_DIR" \
    --css "$REPO_ROOT/jtbd/hub.css" \
    --assemblies-dir "$REPO_ROOT/jtbd/assemblies"

echo "Hub pages: $OUTPUT_DIR/index.html"
