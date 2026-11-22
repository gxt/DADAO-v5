#!/usr/bin/env python3
"""`tests/arch/common/signature.py` — arch scope 的签名流薄壳。

**真源只有一份**：`tests/shared/signature.py`（`m16-testcases-005` 迁入）。
本文件不复制解析/比对实现，只做三件事：
  1. 按文件路径加载真源并重导出 `parse` / `compare` / `unwritten` / `Emitter`
     及槽宽常量（`SLOT` / `UNWRITTEN` / `MAX_SLOTS`）；
  2. 固定 arch 的槽宽（8 字节）与 `0xdeadbeef` 未写哨兵（与
     `tests/shared/asm/signature.inc` 同一口径）；
  3. 把 `tests/arch/<cfx>/expected.yaml` 的 `checks[].signature:` 列表映射成
     公共比较输入（`load_expected_signature`）并做结构校验
     （`validate_expected`）。

真源缺失时必须显式失败（`ImportError` 带缺件路径），不得内置第二份实现。
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

_SHARED = Path(__file__).resolve().parents[2] / "shared" / "signature.py"
if not _SHARED.is_file():
    raise ImportError(
        "tests/arch/common/signature.py: 缺件 %s（签名机制真源；"
        "m16-testcases-005 应先落地）" % _SHARED)

_spec = importlib.util.spec_from_file_location("_dadao_shared_signature", _SHARED)
if _spec is None or _spec.loader is None:  # pragma: no cover - 环境异常
    raise ImportError("无法加载签名机制真源: %s" % _SHARED)
_shared = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_shared)

# 公开 API：只重导出，不复制。
parse = _shared.parse
compare = _shared.compare
unwritten = _shared.unwritten
Emitter = _shared.Emitter
SignatureError = _shared.SignatureError

# arch 的固定口径（与 `tests/shared/asm/signature.inc` 同一真源）。
SLOT = _shared.SLOT
UNWRITTEN = _shared.UNWRITTEN
MAX_SLOTS = _shared.MAX_SLOTS


def load_expected_signature(expected_yaml, case_id):
    """返回 `case_id` 的签名流期望（按 `checks[].signature` 顺序拼接）。

    非 arch 清单（没有顶层 `cases`，如 `tests/arch/umon/expected.yaml`）或该
    case 未登记签名流时返回 `None`；该 case 登记了 `signature:` 但为空列表时
    也返回 `None`（= 不接线）。
    """
    import yaml

    path = Path(expected_yaml)
    if not path.is_file():
        return None
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("cases"), list):
        return None
    for case in data["cases"]:
        if not isinstance(case, dict) or case.get("id") != case_id:
            continue
        out = []
        for check in case.get("checks") or []:
            for value in check.get("signature") or []:
                out.append(int(value))
        return out or None
    return None


def validate_expected(expected_yaml):
    """结构校验一份 arch `expected.yaml`；返回问题列表（空 = 通过）。

    只校验签名流的结构（case/check/signature 类型、槽数 ≤ `MAX_SLOTS`），
    语义期望值仍由驱动 `--selfcheck` 与合约双向核对。
    """
    import yaml

    path = Path(expected_yaml)
    if not path.is_file():
        return ["expected.yaml 不存在: %s" % path]
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        return ["%s: YAML 解析失败: %s" % (path, exc)]
    if not isinstance(data, dict):
        return ["%s: 顶层必须是映射" % path]
    if "cases" not in data:
        # 非 arch schema（如 `tests/arch/umon/expected.yaml` 的 m5-vectors-v1，
        # 判据是 exit code/console，不是签名流）不在本薄壳的校验范围。
        if isinstance(data.get("programs"), list):
            return []
        return ["%s: 缺顶层 `cases` 列表" % path]
    problems = []
    for index, case in enumerate(data["cases"], 1):
        where = "%s 第 %d 个 case" % (path, index)
        if not isinstance(case, dict):
            problems.append("%s: 必须是映射" % where)
            continue
        cid = case.get("id")
        if not isinstance(cid, str) or not cid.startswith("arch-"):
            problems.append("%s: `id` 必须是 arch-* 字符串，实为 %r" % (where, cid))
        checks = case.get("checks")
        if not isinstance(checks, list) or not checks:
            problems.append("%s: `checks` 必须是非空列表" % where)
            continue
        for check in checks:
            if not isinstance(check, dict):
                problems.append("%s: check 必须是映射" % where)
                continue
            sig = check.get("signature")
            if sig is None:
                continue
            if not isinstance(sig, list):
                problems.append("%s/%s: `signature` 必须是列表"
                                % (where, check.get("label")))
                continue
            if len(sig) > MAX_SLOTS:
                problems.append("%s/%s: 签名槽数 %d > 上限 %d"
                                % (where, check.get("label"), len(sig),
                                   MAX_SLOTS))
            for value in sig:
                if not isinstance(value, int) or isinstance(value, bool):
                    problems.append("%s/%s: 签名值必须是整数，实为 %r"
                                    % (where, check.get("label"), value))
    return problems
