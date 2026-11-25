"""issues_store — read the per-milestone issue ledgers.

The issue ledger used to be one global file (``issues.yaml``).  It is now split
per milestone (user ruling 2026-11-25):

* ``.tao/knowledge/issues-left.yaml``   — no live milestone owns it (M14/M15
  closed items, ``milestone: null`` backlog, and M20 for now)
* ``.tao/knowledge/issues-m16.yaml`` … ``issues-m19.yaml`` — owned by the
  session that runs that milestone

Two ID shapes coexist and both must keep working forever:

* legacy ``ISS-<digits>`` (the 193 entries that existed before the split were
  frozen: they are *not* renumbered, and ``.tao/archive`` references them)
* new ``ISS-<file>-NNN`` (e.g. ``ISS-m16-045``, ``ISS-left-001``) — required
  for every entry added after the split, so a new ID can never collide with a
  milestone another session owns.

Writers: only the owning milestone session may write its own file; touching a
file that belongs to another milestone needs the user's approval.  The two
writers that must stay mechanical are enforced by ``check_issues.py``.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

KNOWLEDGE = Path(__file__).resolve().parents[2] / ".tao" / "knowledge"
GLOB = "issues-*.yaml"

OLD_ID_RE = re.compile(r"^ISS-(\d+)$")
NEW_ID_RE = re.compile(r"^ISS-(left|m\d+)-(\d{3,})$")

MILESTONES = ("M16", "M17", "M18", "M19")


def paths() -> list[Path]:
    """Every per-milestone ledger, sorted (left first, then m16…)."""
    found = sorted(KNOWLEDGE.glob(GLOB))
    if not found:
        raise SystemExit(f"issues_store: no {GLOB} under {KNOWLEDGE}")
    return found


def file_key(path: Path) -> str:
    """``issues-m16.yaml`` -> ``m16``; ``issues-left.yaml`` -> ``left``."""
    return path.stem.split("issues-", 1)[1]


def path_for(milestone: str | None) -> Path:
    """The file that owns ``milestone`` (left for anything not M16–M19)."""
    tag = str(milestone or "").upper()
    key = tag.lower() if tag in MILESTONES else "left"
    return KNOWLEDGE / f"issues-{key}.yaml"


def _load(path: Path) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if data is None:
        return []
    if not isinstance(data, list):
        raise SystemExit(f"issues_store: {path.name} must be a list")
    return data


def load_all() -> list[dict]:
    """Every entry of every ledger, file order then entry order."""
    out: list[dict] = []
    for p in paths():
        out.extend(_load(p))
    return out


def load_all_with_file() -> list[tuple[Path, dict]]:
    out: list[tuple[Path, dict]] = []
    for p in paths():
        out.extend((p, issue) for issue in _load(p))
    return out


def sort_key(issue: dict) -> tuple:
    """Total order spanning both ID shapes (legacy first, then per-file)."""
    text = str(issue.get("id"))
    m = OLD_ID_RE.match(text)
    if m:
        return (0, int(m.group(1)), "", 0)
    m = NEW_ID_RE.match(text)
    if m:
        return (1, 0, m.group(1), int(m.group(2)))
    return (2, 0, text, 0)


def next_id(key: str) -> str:
    """Smallest unused ``ISS-<key>-NNN`` (NNN starts at 001)."""
    used: set[int] = set()
    path = KNOWLEDGE / f"issues-{key}.yaml"
    if path.is_file():
        for issue in _load(path):
            m = NEW_ID_RE.match(str(issue.get("id")))
            if m and m.group(1) == key:
                used.add(int(m.group(2)))
    n = 1
    while n in used:
        n += 1
    return f"ISS-{key}-{n:03d}"


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[1] not in ("count", "paths", "ids"):
        print("usage: issues_store.py {count|paths|ids}", file=sys.stderr)
        return 2
    if argv[1] == "paths":
        for p in paths():
            print(p)
        return 0
    if argv[1] == "ids":
        for issue in load_all():
            print(issue.get("id"))
        return 0
    print(len(load_all()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
