#!/usr/bin/env python3
"""Remove the disposable ``.work/`` tree, and nothing else.

Before deleting, the target is asserted to be ``<repo-root>/.work``. The path
is resolved first, so a ``.work`` symlink that points outside the repository is
refused. ``.cache/`` (persistent upstream mirrors) is never touched.
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    work = (ROOT / ".work").resolve()
    if work.parent != ROOT or work.name != ".work":
        print(f"clean-work: refusing to remove unexpected path {work}", file=sys.stderr)
        return 1
    if not work.exists():
        print(f"clean-work: {work} does not exist")
        return 0
    if not work.is_dir():
        print(f"clean-work: refusing to remove non-directory {work}", file=sys.stderr)
        return 1
    shutil.rmtree(work)
    print(f"clean-work: removed {work}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
