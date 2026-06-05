#!/usr/bin/env bash
#
# Generate SPEC.md and llms-full.txt from SPEC.adoc.
#
# Prerequisites: asciidoctor, pandoc
#
# Usage:
#   ./scripts/generate-llm-files.sh <source-dir> <output-dir> <version>
#
set -euo pipefail

SOURCE_DIR="${1:?Usage: $0 <source-dir> <output-dir> <version>}"
OUTPUT_DIR="${2:?Usage: $0 <source-dir> <output-dir> <version>}"
VERSION="${3:?Usage: $0 <source-dir> <output-dir> <version>}"

mkdir -p "${OUTPUT_DIR}"

# AsciiDoc → DocBook XML (resolves all include:: directives)
asciidoctor \
  -b docbook \
  -a revnumber="${VERSION#v}" \
  -a ugas-version="${VERSION}" \
  -a stem=latexmath \
  "${SOURCE_DIR}/SPEC.adoc" \
  -o "${OUTPUT_DIR}/SPEC.xml"

# DocBook XML → GitHub Flavored Markdown
# --wrap=none prevents breaking inline math expressions
pandoc \
  -f docbook \
  -t gfm \
  --wrap=none \
  "${OUTPUT_DIR}/SPEC.xml" \
  -o "${OUTPUT_DIR}/SPEC.md"

rm -f "${OUTPUT_DIR}/SPEC.xml"

# Build llms-full.txt: spec + schemas + examples
cp "${OUTPUT_DIR}/SPEC.md" "${OUTPUT_DIR}/llms-full.txt"

cat >> "${OUTPUT_DIR}/llms-full.txt" <<'HEADER'

---

# Schema Definitions

The following YAML schemas define the data format for each UGAS entity type.

HEADER

for schema_file in "${SOURCE_DIR}"/schemas/*.yaml; do
  filename="$(basename "${schema_file}")"
  pretty_name="$(echo "${filename%.yaml}" | tr '_' ' ' | awk '{for(i=1;i<=NF;i++) $i=toupper(substr($i,1,1)) substr($i,2)}1')"
  printf '\n## %s Schema\n\n```yaml\n' "${pretty_name}" >> "${OUTPUT_DIR}/llms-full.txt"
  cat "${schema_file}" >> "${OUTPUT_DIR}/llms-full.txt"
  printf '```\n' >> "${OUTPUT_DIR}/llms-full.txt"
done

cat >> "${OUTPUT_DIR}/llms-full.txt" <<'HEADER'

---

# Schema Examples

The following YAML files are concrete examples of UGAS entity definitions.

HEADER

for example_file in "${SOURCE_DIR}"/schemas/examples/*.yaml; do
  filename="$(basename "${example_file}")"
  pretty_name="$(echo "${filename%.yaml}" | tr '_' ' ' | awk '{for(i=1;i<=NF;i++) $i=toupper(substr($i,1,1)) substr($i,2)}1')"
  printf '\n## Example: %s\n\n```yaml\n' "${pretty_name}" >> "${OUTPUT_DIR}/llms-full.txt"
  cat "${example_file}" >> "${OUTPUT_DIR}/llms-full.txt"
  printf '```\n' >> "${OUTPUT_DIR}/llms-full.txt"
done

echo "Generated: ${OUTPUT_DIR}/SPEC.md"
echo "Generated: ${OUTPUT_DIR}/llms-full.txt"
