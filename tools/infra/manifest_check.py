#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SHA1 = re.compile(r"^[0-9a-f]{40}$")


def load(name: str) -> dict:
    with (ROOT / "manifests" / name).open("rb") as stream:
        return tomllib.load(stream)


def check_components(components: dict, errors: list[str]) -> None:
    seen: set[str] = set()
    for component in components.get("component", []):
        name = component.get("name", "")
        if not name or name in seen:
            errors.append(f"components.lock.toml: invalid or duplicate component {name!r}")
        seen.add(name)
        if not component.get("enabled"):
            # Placeholder components keep commit = "" until their module ADR
            # records the upstream selection and exact commit.
            continue
        if not SHA1.fullmatch(component.get("commit", "")):
            errors.append(f"component {name}: enabled components require a full commit")
        series = ROOT / component.get("patch_series", "")
        if not series.is_file():
            errors.append(f"component {name}: missing patch series {series}")


def check_references(references: dict, errors: list[str]) -> None:
    for reference in references.get("reference", []):
        ident = reference.get("id", "")
        if not ident:
            errors.append("references.lock.toml: reference id is required")
        if not SHA1.fullmatch(reference.get("head", "")):
            errors.append(f"reference {ident}: head must be a full commit")
        # v5 uses project-relative paths under .work/ (0628 required absolute
        # paths pointing at the original author's local checkouts).
        path = reference.get("path", "")
        if not path or Path(path).is_absolute():
            errors.append(f"reference {ident}: path must be a non-empty project-relative path")


def main() -> int:
    errors: list[str] = []
    components = load("components.lock.toml")
    references = load("references.lock.toml")

    check_components(components, errors)
    check_references(references, errors)

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    enabled = [c["name"] for c in components.get("component", []) if c.get("enabled")]
    print(f"enabled components: {', '.join(enabled) if enabled else 'none'}")
    print(f"references: {len(references.get('reference', []))}")
    print("manifest validation: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
