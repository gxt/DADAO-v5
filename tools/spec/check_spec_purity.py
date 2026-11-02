#!/usr/bin/env python3
"""spec 纯净度门控（SPEC-165t）：`spec/SimRISC-*` 只允许规范内容。

为什么
------
`spec/` 是技术规范正文（唯一真源），只应包含：指令定义 / 编码 / 格式 / 语义 /
异常 / revision。项目侧痕迹（范围标注 `scope`、里程碑、任务号、ADR/ISS 号、
合约指针、`.tao/` 路径、按范围的条数总账、`MISC-` 旧表名）属于
`.tao/contracts/contract-isa.md` 的「范围表」与任务书，不得写进规范。

禁用词（任一命中 ⇒ 非零退出）
------------------------------
``scope`` / ``ADR-nnnn`` / ``ISS-nnn`` / 任务号（SPEC-/QEMU-/LLVM-/INFRA-/
TESTCASES-/INTEG-/GOLDEN-/GEM5-/SAIL-）/ ``contract-*.md`` / ``.tao/`` /
``MISC-`` / ``v5`` / 里程碑号（``M0``–``M99``）/ ``用户裁定`` / ``里程碑``

用法
----
* ``python3 tools/spec/check_spec_purity.py``              # 扫仓库 spec/SimRISC-*.md
* ``python3 tools/spec/check_spec_purity.py --root DIR``   # 扫 DIR/SimRISC-*.md（fixture）
* ``python3 tools/spec/check_spec_purity.py --self-test``  # ≥3 类注入自检（临时树）

计数**现场统计**，不写死。退出码：0 = 纯净；1 = 命中禁用词 / 自检失败。
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = ROOT / "spec"

BANNED: list[tuple[str, re.Pattern[str]]] = [
    ("范围标注 scope", re.compile(r"\bscope\b")),
    ("ADR 指针", re.compile(r"\bADR-\d{4}\b")),
    ("ISS 号", re.compile(r"\bISS-\d+\b")),
    ("任务号", re.compile(
        r"\b(?:SPEC|QEMU|LLVM|INFRA|TESTCASES|INTEG|GOLDEN|GEM5|SAIL)-\d+")),
    ("合约指针 contract-*.md", re.compile(r"contract-[a-z0-9-]+\.md")),
    ("交互目录 .tao/", re.compile(r"\.tao/")),
    ("旧表名 MISC-", re.compile(r"MISC-")),
    ("项目代号 v5", re.compile(r"\bv5\b")),
    ("里程碑号", re.compile(r"(?<![A-Za-z0-9])M[0-9]{1,2}(?![0-9])")),
    ("决策记录用语「用户裁定」", re.compile(r"用户裁定")),
    ("里程碑用语", re.compile(r"里程碑")),
]


def files(root: Path | None = None) -> list[Path]:
    return sorted((root or SPEC).glob("SimRISC-*.md"))


def scan(root: Path | None = None) -> tuple[list[str], int, dict[str, int]]:
    violations: list[str] = []
    checked = 0
    per_rule: dict[str, int] = {name: 0 for name, _ in BANNED}
    for path in files(root):
        checked += 1
        for ln, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            for name, pat in BANNED:
                for m in pat.finditer(line):
                    per_rule[name] += 1
                    violations.append(f"{path.name}:{ln}: [{name}] {m.group(0)!r}")
    return violations, checked, per_rule


def run(root: Path | None = None, verbose: bool = True) -> int:
    violations, checked, per_rule = scan(root)
    if verbose:
        hit = {k: v for k, v in per_rule.items() if v}
        print(f"check-spec-purity: files={checked}  rules={len(BANNED)}  "
              f"hits={len(violations)}  by_rule={hit or '{}'}")
        for v in violations[:40]:
            print("  " + v)
        if len(violations) > 40:
            print(f"  … {len(violations) - 40} more")
    if violations:
        print(f"check-spec-purity: FAIL ({len(violations)} hit(s) in {checked} file(s))")
        return 1
    print(f"check-spec-purity: PASS（{checked} 册无禁用词）")
    return 0


def self_test() -> int:
    """≥3 类注入：每类须 FAIL，基线须 PASS；全部在临时树内，不碰真实 spec/。"""
    tmp_root = Path(tempfile.gettempdir()) / "opencode" / "SPEC-165t"
    tmp_root.mkdir(parents=True, exist_ok=True)
    tmpdir = Path(tempfile.mkdtemp(prefix="purity-", dir=tmp_root))
    baseline = (SPEC / "SimRISC-00-指令系统设计.md").read_text(encoding="utf-8")
    # 注入点在册头（真实行），确定性且不依赖正文措辞。锚点**从被检册现场派生**、
    # 不钉具体版本串——否则每次发布 / 新开 `-rc` 都会与册头脱钩（锚点消失 ⇒ 自检恒红）。
    anchors = re.findall(r"^>\s*\*\*版本[：:].*$", baseline, re.M)
    if len(anchors) != 1:
        print(f"[FAIL] self-test: 册头 `> **版本：…**` 行应恰 1 条，实得 {len(anchors)} 条",
              file=sys.stderr)
        shutil.rmtree(tmpdir, ignore_errors=True)
        return 1
    anchor = anchors[0]
    cases = [
        ("baseline", "", True, "未注入 ⇒ 期望 rc=0"),
        ("scope", "\n> **scope: fp**", False, "塞 `scope: fp` ⇒ 期望 rc!=0"),
        ("task-id", "\n- 由 `SPEC-999t` 落地。", False, "塞任务号 ⇒ 期望 rc!=0"),
        ("adr", "\n- 决策见 `ADR-9999`。", False, "塞 ADR 号 ⇒ 期望 rc!=0"),
        ("misc-table", "\n- 子表 `MISC-octa`。", False, "塞旧表名 `MISC-` ⇒ 期望 rc!=0"),
    ]
    ok = True
    try:
        for i, (name, inject, expect_zero, desc) in enumerate(cases, 1):
            d = tmpdir / f"case{i}"
            d.mkdir()
            text = baseline.replace(anchor, anchor + inject) if inject else baseline
            if inject and text == baseline:
                print(f"[FAIL] self-test {name}: 空注入")
                ok = False
                continue
            (d / "SimRISC-00-指令系统设计.md").write_text(text, encoding="utf-8")
            rc = run(d, verbose=False)
            good = (rc == 0) if expect_zero else (rc != 0)
            print(f"[{'PASS' if good else 'FAIL'}] self-test case{i} {name}: "
                  f"期望={'0' if expect_zero else '非0'} 实际={rc}（{desc}）")
            ok = ok and good
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
    print(f"self-test: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="spec/SimRISC-* 纯净度门控")
    ap.add_argument("--root", type=Path, default=None, help="扫描 DIR/SimRISC-*.md（fixture）")
    ap.add_argument("--self-test", action="store_true", help="≥3 类注入自检（临时树）")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    if args.root is not None and not args.root.is_dir():
        print(f"check-spec-purity: ERROR --root 不是目录: {args.root}", file=sys.stderr)
        return 1
    return run(args.root)


if __name__ == "__main__":
    raise SystemExit(main())
