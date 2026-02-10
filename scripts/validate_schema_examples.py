#!/usr/bin/env python3
"""Validate schema examples in schemas/examples and SPEC.md."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import yaml
from jsonschema import Draft7Validator

PLACEHOLDER_SCALARS = {"string", "float", "enum", "boolean", "object", "number"}

SCHEMA_FILES = {
    "attribute": "schemas/attribute.json",
    "attribute_set": "schemas/attribute_set.json",
    "gameplay_effect": "schemas/gameplay_effect.json",
    "gameplay_ability": "schemas/gameplay_ability.json",
    "gameplay_tag": "schemas/gameplay_tag.json",
    "gameplay_controller": "schemas/gameplay_controller.json",
}

SCHEMA_SUFFIXES = {
    "/schemas/attribute.json": "attribute",
    "/schemas/attribute_set.json": "attribute_set",
    "/schemas/gameplay_effect.json": "gameplay_effect",
    "/schemas/gameplay_ability.json": "gameplay_ability",
    "/schemas/gameplay_tag.json": "gameplay_tag",
    "/schemas/gameplay_controller.json": "gameplay_controller",
}


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def has_placeholder(value: Any) -> bool:
    if isinstance(value, dict):
        return any(has_placeholder(v) for v in value.values())
    if isinstance(value, list):
        return any(has_placeholder(v) for v in value)
    if isinstance(value, str):
        return value.strip() in PLACEHOLDER_SCALARS
    return False


def normalize_candidate(data: Any) -> Optional[Tuple[str, Any]]:
    if not isinstance(data, dict):
        return None

    schema_id = data.get("$schema")
    schema_key = schema_key_from_schema_id(schema_id)
    if schema_key:
        payload = {key: value for key, value in data.items() if key != "$schema"}
        return schema_key, payload

    return None


def schema_key_from_schema_id(schema_id: Any) -> Optional[str]:
    if not isinstance(schema_id, str):
        return None
    for suffix, schema_key in SCHEMA_SUFFIXES.items():
        if schema_id.endswith(suffix):
            return schema_key
    return None


def extract_fenced_blocks(text: str) -> Iterable[Tuple[str, str, int]]:
    in_block = False
    lang = ""
    start_line = 0
    buffer: List[str] = []

    for line_number, line in enumerate(text.splitlines(), start=1):
        if line.startswith("```"):
            if not in_block:
                lang = line[3:].strip().lower()
                in_block = True
                start_line = line_number + 1
                buffer = []
            else:
                yield lang, "\n".join(buffer), start_line
                in_block = False
                lang = ""
                buffer = []
            continue
        if in_block:
            buffer.append(line)


def validate_document(
    validator: Draft7Validator,
    data: Any,
    source: str,
    errors: List[str],
) -> None:
    validation_errors = sorted(validator.iter_errors(data), key=lambda e: e.path)
    if not validation_errors:
        return

    for error in validation_errors:
        path = ".".join(str(p) for p in error.path) or "<root>"
        errors.append(f"{source}: {path}: {error.message}")


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    schemas_root = root / "schemas"
    spec_path = root / "SPEC.md"

    schemas: Dict[str, Dict[str, Any]] = {}
    validators: Dict[str, Draft7Validator] = {}
    required_fields: Dict[str, List[str]] = {}

    for key, rel_path in SCHEMA_FILES.items():
        schema_path = root / rel_path
        if not schema_path.exists():
            continue
        schema = load_json(schema_path)
        schemas[key] = schema
        validators[key] = Draft7Validator(schema)
        required_fields[key] = schema.get("required", [])

    if not schemas:
        print("No schemas found. Expected JSON schemas in schemas/.")
        return 1

    errors: List[str] = []
    validated_count = 0
    skipped_spec = 0

    # Validate examples folder
    examples_root = schemas_root / "examples"
    if examples_root.exists():
        for path in sorted(examples_root.rglob("*")):
            if path.suffix.lower() not in {".yaml", ".yml", ".json"}:
                continue
            try:
                if path.suffix.lower() == ".json":
                    data = load_json(path)
                    docs = [data]
                else:
                    with path.open("r", encoding="utf-8") as handle:
                        docs = list(yaml.safe_load_all(handle))
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{path}: failed to parse ({exc})")
                continue

            for index, doc in enumerate(docs, start=1):
                if doc is None:
                    continue
                schema_key = schema_key_from_schema_id(doc.get("$schema"))
                if schema_key is None:
                    errors.append(
                        f"{path}: missing or unknown $schema for document {index}"
                    )
                    continue

                payload = {key: value for key, value in doc.items() if key != "$schema"}
                if schema_key not in validators:
                    errors.append(f"{path}: missing schema for {schema_key}")
                    continue

                if has_placeholder(payload):
                    errors.append(f"{path}: placeholder values found in document {index}")
                    continue

                required = required_fields.get(schema_key, [])
                if required and not all(key in payload for key in required):
                    errors.append(f"{path}: missing required fields in document {index}")
                    continue

                source = f"{path} (doc {index})"
                validate_document(validators[schema_key], payload, source, errors)
                validated_count += 1

    # Validate SPEC.md code blocks
    if spec_path.exists():
        spec_text = spec_path.read_text(encoding="utf-8")
        for lang, content, start_line in extract_fenced_blocks(spec_text):
            if lang not in {"yaml", "yml", "json"}:
                continue
            try:
                if lang == "json":
                    docs = [json.loads(content)]
                else:
                    docs = list(yaml.safe_load_all(content))
            except Exception as exc:  # noqa: BLE001
                errors.append(f"SPEC.md:{start_line}: failed to parse ({exc})")
                continue

            for index, doc in enumerate(docs, start=1):
                if doc is None:
                    continue
                normalized = normalize_candidate(doc)
                if normalized is None:
                    skipped_spec += 1
                    continue

                schema_key, payload = normalized
                if schema_key not in validators:
                    skipped_spec += 1
                    continue

                if has_placeholder(payload):
                    skipped_spec += 1
                    continue

                required = required_fields.get(schema_key, [])
                if required and not all(key in payload for key in required):
                    skipped_spec += 1
                    continue

                source = f"SPEC.md:{start_line} (doc {index})"
                validate_document(validators[schema_key], payload, source, errors)
                validated_count += 1

    if errors:
        print("Schema example validation failed:\n")
        for error in errors:
            print(f"- {error}")
        return 1

    print(f"Schema example validation passed. Validated {validated_count} snippets.")
    if skipped_spec:
        print(f"Skipped {skipped_spec} non-schema or partial SPEC.md snippets.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
