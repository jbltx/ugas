#!/usr/bin/env bash
#
# Build the docs landing page from the template.
#
# Renders docs-site/index.html with the latest version and a dynamically
# generated version table.  Versions are tracked in docs/versions.json
# (created automatically on first run by scanning existing v*/ directories).
#
# Usage:
#   ./scripts/build-landing-page.sh <version> <date> <docs-dir> <source-dir>
#
# - <version>: version WITHOUT leading v  (e.g. 1.0.0-draft.4)
# - <date>:    publish date YYYY-MM-DD
# - <docs-dir>:   checked-out docs branch
# - <source-dir>: checked-out source (contains docs-site/index.html)
#
set -euo pipefail

VERSION="${1:?Usage: $0 <version> <date> <docs-dir> <source-dir>}"
DATE="${2:?Usage: $0 <version> <date> <docs-dir> <source-dir>}"
DOCS_DIR="${3:?Usage: $0 <version> <date> <docs-dir> <source-dir>}"
SOURCE_DIR="${4:?Usage: $0 <version> <date> <docs-dir> <source-dir>}"

TEMPLATE="${SOURCE_DIR}/docs-site/index.html"
VERSIONS_FILE="${DOCS_DIR}/versions.json"
OUTPUT="${DOCS_DIR}/index.html"

if [ ! -f "$TEMPLATE" ]; then
  echo "Template not found: ${TEMPLATE}" >&2
  exit 1
fi

# ---------------------------------------------------------------------------
# 1. Seed versions.json on first run by scanning existing v*/ directories
# ---------------------------------------------------------------------------
if [ ! -f "$VERSIONS_FILE" ]; then
  echo "Seeding versions.json from existing version directories..."
  SEED="[]"
  for dir in $(ls -d "${DOCS_DIR}"/v*/ 2>/dev/null | sort -Vr); do
    ver=$(basename "$dir")
    date_val=""
    if [ -f "$OUTPUT" ]; then
      date_val=$(grep -A1 ">${ver}<" "$OUTPUT" \
        | grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}' | head -1 || true)
    fi
    : "${date_val:=—}"
    SEED=$(echo "$SEED" | jq --arg v "$ver" --arg d "$date_val" --arg s "pre-release" \
      '. + [{"version": $v, "date": $d, "status": $s}]')
  done
  echo "$SEED" > "$VERSIONS_FILE"
fi

# ---------------------------------------------------------------------------
# 2. Prepend the new version (newest-first order)
# ---------------------------------------------------------------------------
if ! jq -e ".[] | select(.version == \"v${VERSION}\")" "$VERSIONS_FILE" > /dev/null 2>&1; then
  jq --arg v "v${VERSION}" --arg d "$DATE" --arg s "pre-release" \
    '[{"version": $v, "date": $d, "status": $s}] + .' \
    "$VERSIONS_FILE" > "${VERSIONS_FILE}.tmp"
  mv "${VERSIONS_FILE}.tmp" "$VERSIONS_FILE"
fi

# ---------------------------------------------------------------------------
# 3. Generate version-table rows HTML
# ---------------------------------------------------------------------------
ROWS_FILE=$(mktemp)

IDX=0
while IFS= read -r entry; do
  ver=$(echo "$entry" | jq -r '.version')
  date_val=$(echo "$entry" | jq -r '.date')
  status=$(echo "$entry" | jq -r '.status')

  if [ "$IDX" -eq 0 ]; then
    cat >> "$ROWS_FILE" <<ROWEOF
      <div class="vrow">
        <span class="ver"><span class="latest">${ver}</span> ← latest</span>
        <span class="hide-sm" style="color:var(--ink-faint)">${date_val}</span>
        <span class="badge pre">${status}</span>
        <a class="open" href="${ver}/index.html">spec · schemas →</a>
      </div>
ROWEOF
  else
    cat >> "$ROWS_FILE" <<ROWEOF
      <div class="vrow">
        <span class="ver">${ver}</span>
        <span class="hide-sm" style="color:var(--ink-faint)">${date_val}</span>
        <span class="badge pre">${status}</span>
        <a class="open" href="${ver}/index.html">spec · schemas →</a>
      </div>
ROWEOF
  fi
  IDX=$((IDX + 1))
done < <(jq -c '.[]' "$VERSIONS_FILE")

# ---------------------------------------------------------------------------
# 4. Render template → output
# ---------------------------------------------------------------------------
WORK=$(mktemp)
trap 'rm -f "$ROWS_FILE" "$WORK"' EXIT

sed "s/%%LATEST_VERSION%%/v${VERSION}/g" "$TEMPLATE" > "$WORK"

awk -v rfile="$ROWS_FILE" '
  /<!-- VERSION_ROWS -->/ { while ((getline line < rfile) > 0) print line; next }
  { print }
' "$WORK" > "$OUTPUT"

echo "Built landing page: ${OUTPUT}"
