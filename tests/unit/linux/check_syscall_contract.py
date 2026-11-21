#!/usr/bin/env python3
"""check_syscall_contract.py — syscall 契约一致性检查器（`m14-spec-002`）。

校验对象（Spec-first；期望值一律**现场派生**，条数不写死）：
  * `.tao/contracts/contract-syscall.md`（0.10.0；§1–§7 = M8 用户态映射，§8–§11 = M14 内核侧）
  * `.tao/contracts/contract-abi.md`（`rb3 = rbtp` 事实）
  * `.tao/contracts/contract-dynlink.md`（TLS 模型分工 / TP 方向与偏置归属）

断证（任一不满足 ⇒ 非零退出）：
  1. 版本 `0.10.0`；落点段指向 `.tao/contracts/`（不得再写「暂落 `.tao/knowledge/`」）；
  2. **§1 全文与派单基线 commit 逐字节一致**（基线 = 本文件常量 `BASELINE`，
     **不取 `HEAD`**；§1 = 号表口径 / 来源锁定 / 号段边界，M14 不得改一字）；
  3. §4 全文与基线逐字节一致（errno A 口径不变）；§6 基线原文逐行保留 + M14 注记（含 §8）；
  4. §8–§11 齐备；每条规范句（bullet）末带来源标注；无「待…定 / TODO / TBD」裸词；
  5. errno：`[-4095, -1]`、`-ENOSYS`、内部重启码（`ERESTARTSYS` / `ERESTARTNOINTR`）、`rd1` 不参与；
  6. `rb3` / `rbtp` 三方一致（本合约 §10 / `contract-abi` / `contract-dynlink`）；
  7. `[spec-decision]` 所在小节在 §7 有对应行；附录 A 覆盖 §8–§11。

用法：
  python3 tests/unit/linux/check_syscall_contract.py [--root DIR] [--contracts-dir DIR]
  python3 tests/unit/linux/check_syscall_contract.py --self-test   # 5 类注入（临时树；不碰真实文件）

退出码：0 = 全部一致；1 = 有不一致 / 自检失败；2 = 输入缺失或无法解析。
"""
from __future__ import annotations

import argparse
import hashlib
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

# 派单基线 commit（**常量**；M14 派单时 master tip）。不得改成 `HEAD`。
BASELINE = "174298eb"

CONTRACT_REL = Path(".tao") / "contracts" / "contract-syscall.md"
ABI_REL = Path(".tao") / "contracts" / "contract-abi.md"
DYNLINK_REL = Path(".tao") / "contracts" / "contract-dynlink.md"

EXPECTED_VERSION = "0.10.0"

MARKER_RE = re.compile(r"待[^，。；：、\n|》」』]{0,12}?定|\btodo\b|\btbd\b", re.IGNORECASE)
TAG_TAIL_RE = re.compile(r"\[([^\[\]]+)\]$")
TAG_SOURCES = (
    "DADAO-",
    "SimRISC-",
    "Kaiwu",
    "contract-",
    "ADR-",
    "spec-decision",
    "用户裁定",
    "外部权威",
    "INFRA-",
)

# §N 小节（`## §N …` 到下一个小节标题）；§1 不会误命中 §10/§11（要求标题后为空白）。
SECTIONS = (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11)


def section(text: str, number: int) -> str | None:
    pattern = re.compile(
        r"^## §%d[ \t].*?$(.*?)(?=^## §\d+[ \t]|^## 附录|\Z)" % number,
        re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(text)
    return match.group(1) if match else None


def header_block(text: str) -> str:
    return text.split("\n---\n", 1)[0]


def appendix_block(text: str) -> str:
    match = re.search(r"^## 附录 A：来源对照$(.*)\Z", text, re.MULTILINE | re.DOTALL)
    return match.group(1) if match else ""


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def git_show(root: Path, commit: str, rel: Path) -> str:
    proc = subprocess.run(
        ["git", "show", f"{commit}:{rel.as_posix()}"],
        cwd=root,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"git show {commit}:{rel.as_posix()} 失败（rc={proc.returncode}）："
            f"{proc.stderr.strip()[:300]}"
        )
    return proc.stdout


class Report:
    def __init__(self) -> None:
        self.fails: list[str] = []
        self.stats: list[str] = []

    def check(self, name: str, ok: bool, detail: str = "") -> bool:
        status = "PASS" if ok else "FAIL"
        suffix = f" | {detail}" if detail else ""
        print(f"  [{status}] {name}{suffix}")
        if not ok:
            self.fails.append(name)
        return ok

    def stat(self, text: str) -> None:
        self.stats.append(text)


def check_tags(section_text: str, name: str, rep: Report) -> None:
    """每条规范句（bullet）末尾必须有来源标注；计数现场统计。"""
    bullets = [line for line in section_text.splitlines() if line.startswith("- ")]
    rep.stat(f"{name} 规范句（bullet 行）数 = {len(bullets)}")
    rep.check(f"{name} 规范句非空（非 vacuous）", len(bullets) > 0, f"bullets={len(bullets)}")
    for line in bullets:
        match = TAG_TAIL_RE.search(line)
        body = match.group(1) if match else ""
        ok = bool(match) and body.startswith(TAG_SOURCES)
        rep.check(
            f"{name} 规范句带来源标注",
            ok,
            (line[:60] + "…") if not ok else body[:40],
        )


def run_checks(root: Path, contracts_dir: Path | None = None) -> tuple[int, Report]:
    rep = Report()
    contracts = contracts_dir if contracts_dir is not None else root / ".tao" / "contracts"
    contract_path = contracts / "contract-syscall.md"
    abi_path = contracts / "contract-abi.md"
    dynlink_path = contracts / "contract-dynlink.md"
    for path in (contract_path, abi_path, dynlink_path):
        if not path.is_file():
            print(f"[ERR] 输入缺失：{path}", file=sys.stderr)
            return 2, rep

    text = read(contract_path)
    abi_text = read(abi_path)
    dynlink_text = read(dynlink_path)

    print("── 1. 版本头与落点 ──")
    head = header_block(text)
    version_match = re.search(r"\*\*版本：([0-9]+\.[0-9]+\.[0-9]+)\*\*", head)
    version = version_match.group(1) if version_match else "<缺>"
    rep.check("版本 = 0.10.0", version == EXPECTED_VERSION, f"actual={version}")
    rep.check(
        "落点段指向 .tao/contracts/",
        "`.tao/contracts/`" in head,
        "header 含 `.tao/contracts/`",
    )
    rep.check(
        "落点段不再写「暂落 .tao/knowledge/」",
        "暂落 `.tao/knowledge/`" not in head,
        "旧句已改",
    )

    print("\n── 2. §1 号表与来源锁定（与派单基线逐字节一致）──")
    baseline_text = git_show(root, BASELINE, CONTRACT_REL)
    sec1_cur = section(text, 1)
    sec1_base = section(baseline_text, 1)
    if sec1_cur is None or sec1_base is None:
        rep.check("§1 存在（当前 / 基线）", False, f"cur={sec1_cur is not None} base={sec1_base is not None}")
    else:
        rep.check(
            "§1 与基线逐字节一致",
            sec1_cur == sec1_base,
            f"cur_sha={sha256(sec1_cur)[:16]} base_sha={sha256(sec1_base)[:16]} bytes={len(sec1_cur)}",
        )

    print("\n── 3. §4 / §6（A 口径不变；§6 原文保留 + M14 注记）──")
    sec4_cur = section(text, 4)
    sec4_base = section(baseline_text, 4)
    rep.check(
        "§4 与基线逐字节一致（errno A 口径不变）",
        sec4_cur is not None and sec4_cur == sec4_base,
        f"bytes={len(sec4_cur or '')}",
    )
    sec6_cur = section(text, 6)
    sec6_base = section(baseline_text, 6)
    if sec6_cur is None or sec6_base is None:
        rep.check("§6 存在（当前 / 基线）", False, "")
    else:
        base_lines = [line.strip() for line in sec6_base.splitlines() if line.strip()]
        missing = [line for line in base_lines if line not in sec6_cur]
        rep.check("§6 基线原文逐行保留", not missing, f"缺失行 {len(missing)}")
        rep.check(
            "§6 含 M14 注记指针（§8）",
            "M14 注记" in sec6_cur and "§8" in sec6_cur,
            "注记段存在",
        )

    print("\n── 4. §8–§11（内容齐备 / 来源标注 / 无裸待定词）──")
    sections: dict[int, str] = {}
    for number in SECTIONS:
        body = section(text, number)
        sections[number] = body or ""
        rep.check(f"§{number} 存在", body is not None)
    for number in (8, 9, 10, 11):
        body = sections[number]
        check_tags(body, f"§{number}", rep)
        hits = [line for line in body.splitlines() if MARKER_RE.search(line)]
        rep.check(f"§{number} 无「待…定/TODO/TBD」裸词", not hits, f"命中 {len(hits)} 行")

    print("\n── 5. §8 入口分工要点 ──")
    sec8 = sections[8]
    for token in (
        "cfx_umon_user_switch_run_mode",
        "cfx_umon_user_excp_vector",
        "cfx_umon_supv_",
        "cfx_smon_supv_",
        "cfx_smon_supv_excp_vector",
        "escape cfx_umon, [excp_cause_ip, 4]",
        "excp_cause_info & 0x3FFFF",
        "CFXESC",
        "CFXPERM",
        "cg5",
        "cg6",
        "cfx_hmon",
        "DADAO-23",
    ):
        rep.check(f"§8 点名 {token}", token in sec8)

    print("\n── 6. §9 errno 边界与内核内部码 ──")
    sec9 = sections[9]
    normalized = re.sub(r"\s+", " ", sec9.replace("`", ""))
    for token in ("[-4095, -1]", "-4095,-1"):
        if token in normalized:
            rep.check("§9 含 errno 区间 [-4095, -1]", True, token)
            break
    else:
        rep.check("§9 含 errno 区间 [-4095, -1]", False, "未找到区间串")
    for token in ("-ENOSYS", "ERESTARTSYS", "ERESTARTNOINTR", "rd1", "rderrno"):
        rep.check(f"§9 点名 {token}", token in sec9)

    print("\n── 7. §10 rb3 / rbtp 三方一致 ──")
    syscall_row = re.compile(r"^\|\s*`rb3`\s*\|\s*`rbtp`\s*\|")
    abi_row = re.compile(r"^\|\s*rb3\s*\|\s*rbtp\s*\|")
    dynlink_row = re.compile(r"^\|\s*`rb3`\s*\|\s*`rbtp`\s*\|")
    rep.check(
        "contract-syscall §10 有 `rb3` = `rbtp` 行",
        any(syscall_row.search(line) for line in sections[10].splitlines()),
    )
    rep.check("contract-abi 有 `rb3` = `rbtp` 行", any(abi_row.search(line) for line in abi_text.splitlines()))
    rep.check(
        "contract-dynlink 有 `rb3` = `rbtp` 行",
        any(dynlink_row.search(line) for line in dynlink_text.splitlines()),
    )
    for token in ("CLONE_SETTLS", "execve", "initial-exec", "local-exec", "TLS_ABOVE_TP", "contract-dynlink §2.4", "contract-dynlink §7"):
        rep.check(f"§10 点名 {token}", token in sections[10])

    print("\n── 8. §11 原子性要点 ──")
    sec11 = sections[11]
    for token in ("SimRISC-12 §1", "spurious failure", "不能跨任何 syscall", "FUTEX_WAKE", "clone", "TLB", "cache"):
        rep.check(f"§11 点名 {token}", token in sec11)

    print("\n── 9. §7 覆盖 spec-decision 项 / 附录 A 覆盖 §8–§11 ──")
    sec7 = sections[7]
    for number in (8, 9, 10, 11):
        if "[spec-decision]" in sections[number]:
            rep.check(f"§{number} 的 [spec-decision] 项在 §7 有落点", f"§{number}" in sec7)
    appendix = appendix_block(text)
    for number in (8, 9, 10, 11):
        pattern = re.compile(r"^\|\s*§%d\s*\|" % number, re.MULTILINE)
        rep.check(f"附录 A 有 §{number} 行", bool(pattern.search(appendix)))

    print()
    for line in rep.stats:
        print(f"  [SUM] {line}")
    return (0 if not rep.fails else 1), rep


# ── 自检：5 类注入（临时契约目录；真实文件只读）──────────────────────────────

INJECTIONS = [
    {
        "name": "rb3 误配（contract-abi 的 `rb3` 行改 `rbtp` → `gpr`）",
        "file": "contract-abi.md",
        "old": "| rb3 | rbtp | thread pointer（TP） |",
        "new": "| rb3 | gpr | thread pointer（TP） |",
    },
    {
        "name": "errno 区间错（§9 `[-4095, -1]` → `[-4096, -1]`）",
        "file": "contract-syscall.md",
        "old": "取值范围 **`[-4095, -1]`**",
        "new": "取值范围 **`[-4096, -1]`**",
    },
    {
        "name": "来源标注缺失（§8 嵌套句末标注删除）",
        "file": "contract-syscall.md",
        "old": "[DADAO-22 §1 调用约定][DADAO-12 §5. 异常进入与异常退出]",
        "new": "",
    },
    {
        "name": "§1 号表漂移（§1.1 `rd15` 误写 `rd14`）",
        "file": "contract-syscall.md",
        "old": "syscall 号存放在 **`rd15`**",
        "new": "syscall 号存放在 **`rd14`**",
    },
    {
        "name": "版本回退（`0.10.0` → `0.9.2`）",
        "file": "contract-syscall.md",
        "old": "**版本：0.10.0**",
        "new": "**版本：0.9.2**",
    },
]


def self_test() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="syscall-contract-selftest-"))
    rels = [CONTRACT_REL.name, ABI_REL.name, DYNLINK_REL.name]
    try:
        for name in rels:
            shutil.copy2(ROOT / ".tao" / "contracts" / name, tmp / name)
        original = {name: read(ROOT / ".tao" / "contracts" / name) for name in rels}

        print("── self-test 基线（未注入应 PASS）──")
        rc, _ = run_checks(ROOT, tmp)
        if rc != 0:
            print(f"self-test: 基线未通过（rc={rc}）", file=sys.stderr)
            return 1

        failures = 0
        for inj in INJECTIONS:
            path = tmp / inj["file"]
            text = original[inj["file"]]
            hits = text.count(inj["old"])
            print(f"\n── self-test 注入：{inj['name']}（命中 {hits} 处）──")
            if hits != 1:
                print("  [FAIL] 注入点不唯一 ⇒ 注入失效", file=sys.stderr)
                failures += 1
                continue
            path.write_text(text.replace(inj["old"], inj["new"], 1), encoding="utf-8")
            rc_bad, _ = run_checks(ROOT, tmp)
            print(f"  [{'PASS' if rc_bad != 0 else 'FAIL'}] 注入后应非零退出 | expected=rc!=0 actual=rc={rc_bad}")
            failures += 0 if rc_bad != 0 else 1
            path.write_text(original[inj["file"]], encoding="utf-8")
            rc_good, _ = run_checks(ROOT, tmp)
            print(f"  [{'PASS' if rc_good == 0 else 'FAIL'}] 还原后应回绿 | expected=rc=0 actual=rc={rc_good}")
            failures += 0 if rc_good == 0 else 1

        print(f"\nself-test: {len(INJECTIONS)} 类注入，失败 {failures} 项")
        return 0 if failures == 0 else 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="syscall 契约一致性检查器（m14-spec-002）")
    parser.add_argument("--root", type=Path, default=ROOT, help="仓库根（默认本脚本上两级）")
    parser.add_argument("--contracts-dir", type=Path, default=None, help="契约目录（默认 <root>/.tao/contracts）")
    parser.add_argument("--self-test", action="store_true", help="5 类注入自检（临时契约目录）")
    args = parser.parse_args()

    if args.self_test:
        return self_test()

    print("── syscall 契约一致性检查（contract-syscall.md 0.10.0 ↔ contract-abi / contract-dynlink）──")
    try:
        rc, rep = run_checks(args.root, args.contracts_dir)
    except RuntimeError as exc:
        print(f"[ERR] {exc}", file=sys.stderr)
        return 2
    print(f"\n结果：{'PASS' if rc == 0 else 'FAIL'}（失败项 {len(rep.fails)}，退出码 {rc}）")
    return rc


if __name__ == "__main__":
    sys.exit(main())
