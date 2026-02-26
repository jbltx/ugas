#!/usr/bin/env python3
"""Check that JSON and YAML schema definitions are equivalent."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

import yaml

SCHEMA_PAIRS: Dict[str, Tuple[str, str]] = {
    "attribute": ("schemas/attribute.json", "schemas/attribute.yaml"),
    "attribute_set": ("schemas/attribute_set.json", "schemas/attribute_set.yaml"),
    "gameplay_effect": ("schemas/gameplay_effect.json", "schemas/gameplay_effect.yaml"),
    "gameplay_ability": ("schemas/gameplay_ability.json", "schemas/gameplay_ability.yaml"),
    "gameplay_tag": ("schemas/gameplay_tag.json", "schemas/gameplay_tag.yaml"),
    "gameplay_controller": (
        "schemas/gameplay_controller.json",
        "schemas/gameplay_controller.yaml",
    ),
}

ROOT_METADATA_KEYS = {"$schema", "$id", "title", "description"}


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_yaml(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def strip_root_metadata(schema: Any) -> Any:
    if not isinstance(schema, dict):
        return schema
    return {key: value for key, value in schema.items() if key not in ROOT_METADATA_KEYS}


def normalize(schema: Any) -> Any:
    if isinstance(schema, dict):
        return {key: normalize(value) for key, value in schema.items()}
    if isinstance(schema, list):
        return [normalize(item) for item in schema]
    return schema


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    errors: List[str] = []

    for name, (json_rel, yaml_rel) in SCHEMA_PAIRS.items():
        json_path = root / json_rel
        yaml_path = root / yaml_rel

        if not json_path.exists():
            errors.append(f"{name}: missing JSON schema ({json_rel})")
            continue
        if not yaml_path.exists():
            errors.append(f"{name}: missing YAML schema ({yaml_rel})")
            continue

        try:
            json_schema = load_json(json_path)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{name}: failed to parse JSON schema ({exc})")
            continue

        try:
            yaml_schema = load_yaml(yaml_path)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{name}: failed to parse YAML schema ({exc})")
            continue

        json_schema = normalize(strip_root_metadata(json_schema))
        yaml_schema = normalize(strip_root_metadata(yaml_schema))

        if json_schema != yaml_schema:
            errors.append(f"{name}: JSON and YAML schemas differ")

    if errors:
        print("Schema definition equivalence check failed:\n")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Schema definition equivalence check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
