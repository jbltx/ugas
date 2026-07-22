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

CHANGELOG_URL="https://github.com/jbltx/ugas/blob/main/CHANGELOG.md"

# ---------------------------------------------------------------------------
# 1. Regenerate versions.json (Appendix D shape) from the published v*/ dirs.
#    Deterministic: the version directories are the source of truth. Known
#    publish dates are preserved from any prior versions.json (array or object).
# ---------------------------------------------------------------------------
# Build a version -> date lookup from the existing file, tolerating either the
# legacy array shape or the new {versions:[...]} object shape.
DATE_LOOKUP="{}"
if [ -f "$VERSIONS_FILE" ]; then
  DATE_LOOKUP=$(jq '
    (if type=="array" then . else .versions end)
    | map({ (.version): (.released // .date // "—") }) | add // {}
  ' "$VERSIONS_FILE" 2>/dev/null || echo "{}")
fi

ENTRIES="[]"
for dir in $(ls -d "${DOCS_DIR}"/v*/ 2>/dev/null | sort -Vr); do
  ver=$(basename "$dir")
  if [ "$ver" = "v${VERSION}" ]; then
    released="$DATE"
  else
    released=$(echo "$DATE_LOOKUP" | jq -r --arg v "$ver" '.[$v] // "—"')
  fi
  ENTRIES=$(echo "$ENTRIES" | jq \
    --arg v "$ver" --arg r "$released" --arg s "pre-release" --arg c "$CHANGELOG_URL" \
    '. + [{"version": $v, "status": $s, "released": $r, "changelog": $c}]')
done

# Ensure the version being published is present even if its dir isn't listed yet.
if ! echo "$ENTRIES" | jq -e --arg v "v${VERSION}" 'any(.[]; .version == $v)' >/dev/null; then
  ENTRIES=$(echo "$ENTRIES" | jq \
    --arg v "v${VERSION}" --arg r "$DATE" --arg s "pre-release" --arg c "$CHANGELOG_URL" \
    '[{"version": $v, "status": $s, "released": $r, "changelog": $c}] + .')
fi

LATEST=$(echo "$ENTRIES" | jq -r 'if length>0 then .[0].version else "v'"${VERSION}"'" end')
jq -n --arg latest "$LATEST" --argjson versions "$ENTRIES" \
  '{latest: $latest, versions: $versions}' > "$VERSIONS_FILE"

# ---------------------------------------------------------------------------
# 2. Generate version-table rows HTML from the regenerated manifest
# ---------------------------------------------------------------------------
ROWS_FILE=$(mktemp)

IDX=0
while IFS= read -r entry; do
  ver=$(echo "$entry" | jq -r '.version')
  date_val=$(echo "$entry" | jq -r '.released')
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
done < <(jq -c '.versions[]' "$VERSIONS_FILE")

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
