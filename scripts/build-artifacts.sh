#!/usr/bin/env bash
#
# Generate machine-readable consumer artifacts into an assembled version tree.
#
# Run AFTER the version directory has been populated with SPEC.md, schemas/,
# genres/ (and, in later phases, schemas/bundle.json, genres/index.json, rag/).
# Produces, into <version-dir>:
#   * sections/*.md + sections/index.json  (pre-chunked spec)
#   * index.json                           (checksummed resource manifest — last)
# and writes the generated llms.txt to <llms-out> (the docs root).
#
# Usage:
#   build-artifacts.sh <version-dir> <version> <llms-out> [base-url]
#
set -euo pipefail

VERSION_DIR="${1:?Usage: $0 <version-dir> <version> <llms-out> [base-url]}"
VERSION="${2:?Usage: $0 <version-dir> <version> <llms-out> [base-url]}"
LLMS_OUT="${3:?Usage: $0 <version-dir> <version> <llms-out> [base-url]}"
BASE_URL="${4:-https://ugas.jbltx.com}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 1. Pre-chunk the spec into addressable sections.
python3 "${SCRIPT_DIR}/build_sections.py" "${VERSION_DIR}/SPEC.md" "${VERSION_DIR}/sections"

# 2. Enumerate genre packs + template entities.
python3 "${SCRIPT_DIR}/build_genre_manifest.py" "${VERSION_DIR}/genres" "${VERSION}"

# 3. Bundle all schemas into one offline-resolvable validation document.
python3 "${SCRIPT_DIR}/build_schema_bundle.py" "${VERSION_DIR}/schemas" "${VERSION}"

# (P2 build_rag.py hooks in here, before the resource manifest, as it lands.)

# 4. Manifest last — it checksums every artifact produced above.
python3 "${SCRIPT_DIR}/build_manifest.py" "${VERSION_DIR}" "${VERSION}" --base-url "${BASE_URL}"

# 5. Generate llms.txt FROM the manifest so the human index can never drift.
python3 "${SCRIPT_DIR}/build_llms_txt.py" "${VERSION_DIR}/index.json" "${LLMS_OUT}"

echo "Consumer artifacts generated in ${VERSION_DIR}"
