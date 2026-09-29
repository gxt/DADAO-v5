#!/usr/bin/env python3
"""check_spec_drift.py 4 类真实缺陷 fixture 负测试.

每类构造真实缺陷合约（非注入分支），运行 check_spec_drift.py 检测，
验证 exit=1。退出码 0 = 全部 4 类检测正确，非 0 = 失败。

Usage:
    python3 tools/infra/test_spec_drift_fixtures.py
"""

import subprocess
import sys
import tempfile
from pathlib import Path

CHECKER = Path(__file__).resolve().parent / "check_spec_drift.py"


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def create_fixtures(base: Path) -> dict[str, dict[str, Path]]:
    """在 base 下创建 4 类缺陷 fixture，返回 {name: {dirs}}."""

    # 通用 README（版本表供 checker 解析）
    readme = (
        "# Test\n\n"
        "| 组件 | 版本 |\n"
        "|------|------|\n"
        "| SimRISC | 0.5.4 |\n"
        "| AEE / ABI | 0.9.2 |\n\n"
        "End.\n"
    )
    # 通用 spec 文件（version_mismatch 需要它存在）
    spec_content = "# SimRISC-00 spec\n"

    fixtures: dict[str, dict[str, Path]] = {}

    # ── 1. source_missing：合约既无版本头也无 ADR 引用 ──
    d = base / "source_missing"
    _write(d / "README.md", readme)
    _write(d / ".tao" / "knowledge" / "contract-empty.md",
           "# Empty contract\n\nNo version header, no ADR reference.\n")
    fixtures["source_missing"] = {"root": d}

    # ── 2. source_bad_format：有版本头但无 spec 引用 ──
    d = base / "source_bad_format"
    _write(d / "README.md", readme)
    _write(d / ".tao" / "knowledge" / "contract-bad.md",
           "# Bad Format\n\n> **版本：0.5.4**\n\nNo spec reference on version line.\n")
    fixtures["source_bad_format"] = {"root": d}

    # ── 3. version_mismatch：合约版本 ≠ README 版本表 ──
    d = base / "version_mismatch"
    _write(d / "README.md", readme)
    _write(d / ".tao" / "knowledge" / "contract-mismatch.md",
           "# Version Mismatch\n\n> **版本：99.99.99** [SimRISC-00 §测试]\n\nMismatch.\n")
    _write(d / "spec" / "SimRISC-00-指令系统设计.md", spec_content)
    fixtures["version_mismatch"] = {"root": d}

    # ── 4. unknown_adr：引用不存在的 ADR 文件 ──
    d = base / "unknown_adr"
    _write(d / "README.md", readme)
    _write(d / ".tao" / "knowledge" / "contract-unknown-adr.md",
           "# Unknown ADR\n\nSee adr-9999-nonexistent.md for details.\n")
    fixtures["unknown_adr"] = {"root": d}

    return fixtures


def run_checker(repo_root: Path, kd: Path | None = None, sd: Path | None = None) -> int:
    """运行 check_spec_drift.py，返回退出码."""
    cmd = [sys.executable, str(CHECKER), "--repo-root", str(repo_root)]
    contract_dir = repo_root / ".tao" / "knowledge"
    cmd += ["--contract-dir", str(contract_dir)]
    if kd:
        cmd += ["--knowledge-dir", str(kd)]
    if sd:
        cmd += ["--spec-dir", str(sd)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.returncode


def main() -> int:
    passed = 0
    failed = 0
    failures: list[str] = []

    with tempfile.TemporaryDirectory(prefix="spec_drift_fixtures_") as tmp:
        base = Path(tmp)
        fixtures = create_fixtures(base)

        tests = [
            ("source_missing",    lambda r: run_checker(r)),
            ("source_bad_format", lambda r: run_checker(r)),
            ("version_mismatch",  lambda r: run_checker(r, sd=r / "spec")),
            ("unknown_adr",       lambda r: run_checker(r)),
        ]

        for name, runner in tests:
            root = fixtures[name]["root"]
            rc = runner(root)
            if rc == 1:
                print(f"  [PASS] {name}: exit=1 (缺陷被正确检测)")
                passed += 1
            else:
                msg = f"  [FAIL] {name}: exit={rc} (期望 1)"
                print(msg)
                failures.append(msg)
                failed += 1

    total = passed + failed
    print(f"\n{'='*50}")
    print(f"结果: {passed}/{total} 通过")
    if failures:
        for f in failures:
            print(f"  {f}")
        return 1
    print("spec drift fixture tests: ALL PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
