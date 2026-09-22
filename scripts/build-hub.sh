#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

for cmd in python3 asciidoctor; do
    command -v "$cmd" &>/dev/null || { echo "ERROR: $cmd not found"; exit 1; }
done

python3 "$SCRIPT_DIR/build_hub.py" \
    --config "$REPO_ROOT/jtbd/hub-config.yml" \
    --output "$REPO_ROOT/jtbd/docs" \
    --css "$REPO_ROOT/jtbd/hub.css" \
    --assemblies-dir "$REPO_ROOT/jtbd/assemblies"

echo "Hub pages: $REPO_ROOT/jtbd/docs/index.html"
