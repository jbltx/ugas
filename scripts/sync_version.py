#!/usr/bin/env python3
"""Propagate the package.json version into the spec and README.

Run automatically by `npm run version` (i.e. by `changeset version`) so the
synced files land inside the same Release PR. package.json is the single source
of truth for the UGAS version.
"""
import json
import pathlib
import re
from datetime import datetime

ROOT = pathlib.Path(__file__).resolve().parent.parent


def main() -> None:
    version = json.loads((ROOT / "package.json").read_text())["version"]

    spec = ROOT / "SPEC.adoc"
    text = spec.read_text()
    revdate = datetime.now().strftime("%B %Y")
    text = re.sub(r"^:revnumber:.*$", f":revnumber: {version}", text, count=1, flags=re.M)
    text = re.sub(r"^:revdate:.*$", f":revdate: {revdate}", text, count=1, flags=re.M)
    text = re.sub(r"^:ugas-version:.*$", f":ugas-version: v{version}", text, count=1, flags=re.M)
    spec.write_text(text)

    readme = ROOT / "README.md"
    rtext = readme.read_text()
    rtext = re.sub(r"(version\s*=\s*\{)[^}]*(\})", rf"\g<1>{version}\g<2>", rtext, count=1)
    readme.write_text(rtext)

    print(f"Synced version {version} into SPEC.adoc and README.md")


if __name__ == "__main__":
    main()
