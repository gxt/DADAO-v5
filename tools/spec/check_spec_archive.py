#!/usr/bin/env python3
"""SimRISC 版本归档门控（SPEC-154t；L1）。

规则：`docs/Process-06-spec目录保护规范.md §8`——每次 SimRISC 版本升号须同笔落
`.tao/archive/SimRISC-<ver>/`（只增不改）。

断言（全部**现场派生**，计数不写死）：
- A1：`spec/SimRISC-*.md` 册头版本 ∪ 附录三级标题版本 ⇒ 每个
  `.tao/archive/SimRISC-<ver>/` 目录存在；
- A2：每个归档目录含 ≥1 个 `SimRISC-*.md`，且必有 `SimRISC-00*`（指令系统设计册）；
- A3：目录内 `SimRISC-*.md` 个数 = `gen_spec_archive.py --list` 清单里该版本的文件数；
  清单里的每个版本也必须有目录（清单 ⊆ 磁盘）；
- A4（**反向**）：磁盘上每个 `.tao/archive/SimRISC-*/` 目录都必须出现在派生清单里，
  即「磁盘 ⊆ 清单」；与 A1/A3 合为**双向**（清单 ⇔ 磁盘）。
  A3/A4 依赖清单派生，派生失败 ⇒ 跳过并打印原因。

**只校验存在性与文件集，不校验内容**：`-rc` 目录是升号时点快照，会随工作树演进自然分叉
（见 §8）。

`--self-test`：内置反例（目录缺失 / 目录空 / 册头版本新于目录 / 文件数不符 / 磁盘多出
清单元）各自须 FAIL，正向样例须 PASS。
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SPEC = REPO / "spec"
ARCHIVE = REPO / ".tao" / "archive"

VERSION_RE = re.compile(r"^>\s*\*\*版本[：:]\s*(\d+(?:\.\d+){1,2}(?:-rc)?)", re.M)
H3_VER_RE = re.compile(r"^###\s+(\d+(?:\.\d+){1,2}(?:-rc)?)（", re.M)
APPENDIX_RE = re.compile(r"^##\s+附录：版本与变更记录\s*$", re.M)


def versions_from_spec(spec_dir: Path) -> set[str]:
    """册头版本 ∪ 附录三级标题版本（含 `-rc`）。"""
    found: set[str] = set()
    for path in sorted(spec_dir.glob("SimRISC-*.md")):
        text = path.read_text()
        for m in VERSION_RE.finditer(text):
            found.add(m.group(1))
        head = APPENDIX_RE.search(text)
        if head:
            for m in H3_VER_RE.finditer(text[head.start() :]):
                found.add(m.group(1))
    return found


def check_tree(archive_root: Path, required: set[str], counts: dict[str, int] | None) -> list[str]:
    errors: list[str] = []
    versions = set(required) | (set(counts) if counts is not None else set())
    for version in sorted(versions):
        dest = archive_root / f"SimRISC-{version}"
        if not dest.is_dir():
            if version in required:
                errors.append(f"A1 目录缺失：{dest.name}（版本 {version} 已被 spec 声明）")
            else:
                errors.append(
                    f"A3 清单版本缺目录：{dest.name}（清单文件数 {counts[version]}）"
                )
            continue
        files = sorted(p.name for p in dest.glob("SimRISC-*.md"))
        if not files:
            errors.append(f"A2 目录为空：{dest.name}（须含 ≥1 个 SimRISC-*.md）")
            continue
        if not any(name.startswith("SimRISC-00") for name in files):
            errors.append(f"A2 缺指令系统设计册：{dest.name}（须含 SimRISC-00*）")
        if counts is not None and version in counts and len(files) != counts[version]:
            errors.append(
                f"A3 文件数不符：{dest.name} 期望 {counts[version]} 实际 {len(files)}"
            )
    return errors


def counts_from_manifest() -> tuple[dict[str, int] | None, set[str] | None, str]:
    try:
        import gen_spec_archive as gen

        data = gen.derive()
        entries = data["versions"]
        return (
            {e["version"]: e["count"] for e in entries},
            {e["version"] for e in entries},
            "ok",
        )
    except Exception as exc:  # noqa: BLE001 - 清单派生失败只降级，不阻断 A1/A2
        return None, None, f"{type(exc).__name__}: {exc}"


def disk_versions(archive_root: Path) -> set[str]:
    """磁盘上 `.tao/archive/SimRISC-<ver>/` 的版本集合（现场扫描，不写死）。"""
    prefix = "SimRISC-"
    return {
        p.name[len(prefix) :]
        for p in archive_root.glob(f"{prefix}*")
        if p.is_dir() and p.name.startswith(prefix)
    }


def reverse_errors(archive_root: Path, listed: set[str]) -> list[str]:
    """A4：磁盘 ⊆ 清单（目录多出清单未声明的版本 ⇒ 红）。"""
    disk = disk_versions(archive_root)
    return [
        f"A4 目录不在清单：SimRISC-{version}（磁盘 {len(disk)} 个 / 清单 {len(listed)} 个）"
        for version in sorted(disk - listed)
    ]


def self_test() -> int:
    """三类反例须 FAIL、正向样例须 PASS；返回 0 = 自检通过。"""
    tmp_root = Path("/tmp/opencode")
    tmp_root.mkdir(parents=True, exist_ok=True)
    root = Path(tempfile.mkdtemp(prefix="spec-archive-selftest-", dir=tmp_root))
    rc = 0
    try:
        def make(version: str, files=("SimRISC-00-指令系统设计.md",)) -> None:
            d = root / f"SimRISC-{version}"
            d.mkdir(parents=True, exist_ok=True)
            for name in files:
                (d / name).write_text("x\n")

        # 正向：两个版本目录齐、文件数一致
        make("1.0.0", ("SimRISC-00-指令系统设计.md", "SimRISC-01-数据类指令.md"))
        make("1.0.1")
        ok = check_tree(root, {"1.0.0", "1.0.1"}, {"1.0.0": 2, "1.0.1": 1})
        print(f"[self-test] 正向样例：errors={ok} → {'PASS' if not ok else 'FAIL'}")
        rc |= 0 if not ok else 1

        # 反例 ①：目录缺失
        errs = check_tree(root, {"1.0.0", "1.0.2"}, {"1.0.0": 2, "1.0.2": 1})
        hit = any("A1 目录缺失" in e and "1.0.2" in e for e in errs)
        print(f"[self-test] 反例①目录缺失：{errs} → {'FAIL(预期)' if hit else '未触发'}")
        rc |= 0 if hit else 1

        # 反例 ②：目录空
        (root / "SimRISC-1.0.3").mkdir()
        errs = check_tree(root, {"1.0.3"}, None)
        hit = any("A2 目录为空" in e for e in errs)
        print(f"[self-test] 反例②目录空：{errs} → {'FAIL(预期)' if hit else '未触发'}")
        rc |= 0 if hit else 1

        # 反例 ③：册头版本新于目录（由临时 spec 目录派生 required）
        spec = root / "_spec"
        spec.mkdir()
        (spec / "SimRISC-00-指令系统设计.md").write_text(
            "# x\n\n> **版本：9.9.9**\n\n## 附录：版本与变更记录\n\n### 9.9.9（未发布）\n"
        )
        required = versions_from_spec(spec)
        errs = check_tree(root, required, None)
        hit = "9.9.9" in required and any("A1 目录缺失" in e for e in errs)
        print(f"[self-test] 反例③册头版本新于目录：required={sorted(required)} → {'FAIL(预期)' if hit else '未触发'}")
        rc |= 0 if hit else 1

        # 反例 ④：文件数不符（A3）
        errs = check_tree(root, {"1.0.0"}, {"1.0.0": 3})
        hit = any("A3 文件数不符" in e for e in errs)
        print(f"[self-test] 反例④文件数不符：{errs} → {'FAIL(预期)' if hit else '未触发'}")
        rc |= 0 if hit else 1

        # 反例 ⑤：磁盘多出清单未声明的目录（A4 反向断言；独立临时根，避免与前几例耦合）
        rev_root = root / "_rev"
        rev_root.mkdir()
        (rev_root / "SimRISC-1.0.9").mkdir()
        errs = reverse_errors(rev_root, {"1.0.0", "1.0.1"})
        hit = any("A4 目录不在清单" in e and "1.0.9" in e for e in errs)
        print(f"[self-test] 反例⑤磁盘多出清单元：{errs} → {'FAIL(预期)' if hit else '未触发'}")
        rc |= 0 if hit else 1
    finally:
        shutil.rmtree(root, ignore_errors=True)
    print(f"check-spec-archive --self-test: {'PASS' if rc == 0 else 'FAIL'}")
    return rc


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="SimRISC 版本归档门控（SPEC-154t）")
    parser.add_argument("--self-test", action="store_true", help="内置反例自检")
    parser.add_argument("--verbose", action="store_true", help="打印逐版本检查明细")
    args = parser.parse_args(argv)

    if args.self_test:
        return self_test()

    required = versions_from_spec(SPEC)
    counts, listed, note = counts_from_manifest()
    errors = check_tree(ARCHIVE, required, counts)
    if listed is not None:
        errors += reverse_errors(ARCHIVE, listed)
    if args.verbose or errors:
        print(f"required versions（册头 ∪ 附录）={sorted(required)}")
        print(f"清单版本={sorted(listed) if listed is not None else f'不可用（{note}）'}")
        print(f"磁盘版本={sorted(disk_versions(ARCHIVE))}")
    for err in errors:
        print(f"FAIL {err}", file=sys.stderr)
    if errors:
        print(f"check-spec-archive: FAIL（{len(errors)} 条）", file=sys.stderr)
        return 1
    print(
        f"check-spec-archive: PASS（声明 {len(required)} 个版本目录"
        f"，磁盘 {len(disk_versions(ARCHIVE))} 个"
        f"，A3/A4 {'启用' if listed is not None else f'跳过：{note}'}）"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
