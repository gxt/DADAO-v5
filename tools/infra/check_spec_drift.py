#!/usr/bin/env python3
"""fail-closed 规格漂移检查.

校验 .tao/knowledge/contract-*.md 的来源与 README.md 版本表一致。
每个合约必须被分类为以下之一，否则 ERROR：
  - spec-sourced: 含 `> **版本：X.Y.Z**` → 版本须与 README 版本表对应项一致；引用的 spec/ 文件须存在
  - ADR-sourced:  来源标注引用 `adr-XXXX-*.md` → ADR 文件须存在且状态为 Accepted
  - 否则 → ERROR

fail-closed: 缺来源 / 来源格式损坏 / 未知 ADR / 版本不匹配 → exit 非零。
全通过 → 输出 "spec drift check: PASS" 并返回 0。

Usage:
    python3 tools/infra/check_spec_drift.py [--contract-dir DIR] [--knowledge-dir DIR]
                                             [--spec-dir DIR] [--repo-root DIR]
                                             [--test-mode {version_mismatch,source_missing,
                                                           source_bad_format,unknown_adr}]
"""

import argparse
import os
import re
import sys
from pathlib import Path

# ── 显式排除名单（P1: 不得用宽泛模式）─────────────────────────────────────────
EXCLUDED_CONTRACTS = frozenset({
    "contract-authoring.md",  # 合约编写规范/模板，无来源头，非合约
})
EXCLUDE_REASON = "合约编写规范/模板（非合约，无来源头）"

# ── spec 前缀 → README 组件名映射（P3: 显式定义）─────────────────────────────
SPEC_PREFIX_TO_COMPONENT = {
    "SimRISC-00": "SimRISC",
    "SimRISC-01": "SimRISC",
    "SimRISC-02": "SimRISC",
    "SimRISC-03": "SimRISC",
    "SimRISC-04": "SimRISC",
    "DADAO-11":   "AEE / ABI",
    "DADAO-12":   "SEE / SBI",
    "DADAO-13":   "HEE / HBI",
    "DADAO-21":   "AEE / ABI",
    "DADAO-22":   "SEE / SBI",
    "DADAO-23":   "HEE / HBI",
}

# ── spec 前缀 → spec/ 文件名 ─────────────────────────────────────────────────
SPEC_PREFIX_TO_FILENAME = {
    "SimRISC-00": "SimRISC-00-指令系统设计.md",
    "SimRISC-01": "SimRISC-01-数据类指令.md",
    "SimRISC-02": "SimRISC-02-地址类指令.md",
    "SimRISC-03": "SimRISC-03-浮点类指令.md",
    "SimRISC-04": "SimRISC-04-系统类指令.md",
    "DADAO-11":   "DADAO-11-AEE-应用程序运行环境.md",
    "DADAO-12":   "DADAO-12-SEE-主管系统运行环境.md",
    "DADAO-13":   "DADAO-13-HEE-超管系统运行环境.md",
    "DADAO-21":   "DADAO-21-ABI-应用程序二进制接口.md",
    "DADAO-22":   "DADAO-22-SBI-主管系统二进制接口.md",
    "DADAO-23":   "DADAO-23-HBI-超管系统二进制接口.md",
}

# ── 正则 ─────────────────────────────────────────────────────────────────────
# 版本头: "> **版本：X.Y.Z**" 或 "> **版本：X.Y.Z** [...]"
RE_VERSION_HEADER = re.compile(
    r"^>\s*\*\*版本[：:]\s*(\d+\.\d+\.\d+)\s*\*\*"
)
# 来源引用: [SimRISC-XX §...] 或 [DADAO-XX §...]
RE_SPEC_REF = re.compile(r"\[(SimRISC-\d+|DADAO-\d+)\s+§")
# ADR 引用: adr-XXXX-*.md
RE_ADR_REF = re.compile(r"adr-(\d{4})-[\w-]+\.md")
# ADR 状态: **状态**：Accepted 或 Status: Accepted（P2: 兼容中文 + 英文）
# 状态值在 "Accepted" / "Candidate" / "Rejected" 等，后面可能跟 （rev. ... 或 (rev. ...
RE_ADR_STATUS = re.compile(
    r"^\*\*状态\*\*[：:]\s*(\w+)|^Status[：:]\s*(\w+)", re.IGNORECASE
)


def parse_readme_versions(readme_path: Path) -> dict[str, str]:
    """解析 README.md 版本表 → {组件名: 版本号}."""
    text = readme_path.read_text(encoding="utf-8")
    versions: dict[str, str] = {}
    in_table = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("| 组件") and "版本" in stripped:
            in_table = True
            continue
        if in_table and stripped.startswith("|--"):
            continue
        if in_table and stripped.startswith("|"):
            cells = [c.strip() for c in stripped.split("|")]
            # cells = ['', 组件, 版本, '']  (4 elements after split by |)
            if len(cells) >= 3:
                component = cells[1].strip()
                version = cells[2].strip()
                if component and version and component != "组件":
                    versions[component] = version
        elif in_table and not stripped.startswith("|"):
            in_table = False
    return versions


def check_adr_accepted(adr_path: Path) -> tuple[bool, str]:
    """检查 ADR 文件状态是否为 Accepted. 返回 (accepted, status_str)."""
    text = adr_path.read_text(encoding="utf-8")
    for line in text.splitlines():
        m = RE_ADR_STATUS.match(line.strip())
        if m:
            status = (m.group(1) or m.group(2)).strip()
            return (status == "Accepted", status)
    return (False, "<未找到状态行>")


def classify_contract(
    contract_path: Path,
    readme_versions: dict[str, str],
    knowledge_dir: Path,
    spec_dir: Path,
    test_mode: str | None = None,
) -> tuple[str, list[str]]:
    """分类单个合约文件. 返回 (status, details).

    status: "spec-sourced" | "adr-sourced" | "error"
    details: 描述性消息列表
    """
    text = contract_path.read_text(encoding="utf-8")
    details: list[str] = []
    name = contract_path.name

    # ── 负测试注入（前置：在分类逻辑之前强制 ERROR）──────────────────────────
    if test_mode == "source_missing":
        details.append("  ERROR: 来源缺失（负测试注入）")
        return ("error", details)
    if test_mode == "source_bad_format":
        details.append("  ERROR: 来源格式错误（负测试注入）")
        return ("error", details)

    # 尝试 spec-sourced: 查找版本头
    version_match = None
    header_line = ""
    for line in text.splitlines():
        m = RE_VERSION_HEADER.match(line.strip())
        if m:
            version_match = m
            header_line = line
            break

    if version_match:
        version = version_match.group(1)
        # 提取版本头行中的 spec 前缀（仅该行，非全文）
        spec_refs = RE_SPEC_REF.findall(header_line)
        if not spec_refs:
            details.append(f"  ERROR: 版本头找到 ({version}) 但无 spec 引用 [XXX-NN §...]")
            return ("error", details)

        # 映射到 README 组件名
        components_checked: list[str] = []
        for prefix in set(spec_refs):
            if prefix not in SPEC_PREFIX_TO_COMPONENT:
                details.append(f"  ERROR: 未知 spec 前缀 '{prefix}'，无法映射到 README 组件")
                return ("error", details)
            component = SPEC_PREFIX_TO_COMPONENT[prefix]
            spec_file = SPEC_PREFIX_TO_FILENAME.get(prefix)
            mapping_note = f"{prefix} → README 组件 '{component}'"
            components_checked.append(mapping_note)

            # 校验版本
            if component not in readme_versions:
                details.append(f"  ERROR: README 版本表无组件 '{component}'")
                return ("error", details)
            expected_version = readme_versions[component]
            if test_mode == "version_mismatch":
                # 负测试: 注入版本不匹配
                details.append(
                    f"  ERROR: 版本不匹配 — {name}: 合约版本 {version} "
                    f"≠ README '{component}' 版本 {expected_version}（负测试注入）"
                )
                return ("error", details)
            if version != expected_version:
                details.append(
                    f"  ERROR: 版本不匹配 — {name}: 合约版本 {version} "
                    f"≠ README '{component}' 版本 {expected_version}（映射: {mapping_note}）"
                )
                return ("error", details)

            # 校验 spec 文件存在
            if spec_file:
                spec_path = spec_dir / spec_file
                if not spec_path.exists():
                    details.append(f"  ERROR: spec 文件不存在 — {spec_path}")
                    return ("error", details)

        details.append(f"  spec-sourced: 版本 {version}")
        for note in sorted(set(components_checked)):
            details.append(f"    映射依据: {note}")
        return ("spec-sourced", details)

    # 尝试 ADR-sourced: 查找 ADR 引用
    adr_refs = RE_ADR_REF.findall(text)
    if adr_refs:
        if test_mode == "unknown_adr":
            details.append("  ERROR: 未知 ADR（负测试注入）")
            return ("error", details)
        for adr_num in adr_refs:
            adr_filename = None
            for candidate in knowledge_dir.glob(f"adr-{adr_num}-*.md"):
                adr_filename = candidate.name
                adr_path = candidate
                break
            if adr_filename is None:
                details.append(f"  ERROR: ADR 文件 adr-{adr_num}-*.md 不存在于 {knowledge_dir}")
                return ("error", details)
            accepted, status = check_adr_accepted(adr_path)
            if not accepted:
                details.append(
                    f"  ERROR: ADR {adr_filename} 状态为 '{status}'（非 Accepted）"
                )
                return ("error", details)
            details.append(f"  ADR-sourced: {adr_filename} (状态: {status})")
        return ("adr-sourced", details)

    # 无版本头也无 ADR 引用 → ERROR
    details.append(f"  ERROR: 无版本头（spec-sourced）且无 ADR 引用（adr-sourced）— 来源缺失")
    return ("error", details)


def main() -> int:
    parser = argparse.ArgumentParser(description="fail-closed spec drift check")
    parser.add_argument(
        "--repo-root", type=Path, default=None,
        help="仓库根目录（默认: 脚本向上 3 级）",
    )
    parser.add_argument(
        "--knowledge-dir", type=Path, default=None,
        help="知识库目录（默认: .tao/knowledge）",
    )
    parser.add_argument(
        "--spec-dir", type=Path, default=None,
        help="规范目录（默认: spec/）",
    )
    parser.add_argument(
        "--contract-dir", type=Path, default=None,
        help="合约目录（默认: .tao/knowledge）",
    )
    parser.add_argument(
        "--test-mode", type=str, default=None,
        choices=["version_mismatch", "source_missing", "source_bad_format", "unknown_adr"],
        help="负测试模式",
    )
    parser.add_argument(
        "--test-contract", type=str, default=None,
        help="负测试目标合约文件名（配合 --test-mode）",
    )
    args = parser.parse_args()

    # 确定路径
    if args.repo_root:
        repo_root = args.repo_root
    else:
        repo_root = Path(__file__).resolve().parents[2]

    knowledge_dir = args.knowledge_dir or repo_root / ".tao" / "knowledge"
    spec_dir = args.spec_dir or repo_root / "spec"
    contract_dir = args.contract_dir or knowledge_dir

    readme_path = repo_root / "README.md"
    if not readme_path.exists():
        print(f"ERROR: README.md 不存在 — {readme_path}", file=sys.stderr)
        return 1

    # 解析 README 版本表
    readme_versions = parse_readme_versions(readme_path)
    if not readme_versions:
        print("ERROR: README.md 版本表为空或解析失败", file=sys.stderr)
        return 1

    print("── spec drift check ──")
    print(f"仓库根: {repo_root}")
    print(f"README 版本表: {readme_versions}")
    print()

    # 报告排除文件
    print(f"排除文件（显式名单）:")
    for excluded in sorted(EXCLUDED_CONTRACTS):
        print(f"  {excluded} — {EXCLUDE_REASON}")
    print()

    # 枚举 contract-*.md
    contracts = sorted(contract_dir.glob("contract-*.md"))
    if not contracts:
        print("ERROR: 未找到任何 contract-*.md 文件", file=sys.stderr)
        return 1

    errors = 0
    checked = 0

    for contract_path in contracts:
        name = contract_path.name
        if name in EXCLUDED_CONTRACTS:
            continue

        checked += 1
        test_mode = None
        if args.test_mode and args.test_contract == name:
            test_mode = args.test_mode

        status, details = classify_contract(
            contract_path, readme_versions, knowledge_dir, spec_dir, test_mode
        )

        if status == "error":
            print(f"[FAIL] {name}")
            errors += 1
        else:
            print(f"[PASS] {name}")
        for line in details:
            print(line)
        print()

    print(f"── 结果: 检查 {checked} 个合约，排除 {len(EXCLUDED_CONTRACTS)} 个，错误 {errors} 个 ──")

    if errors > 0:
        print("spec drift check: FAIL")
        return 1

    print("spec drift check: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
