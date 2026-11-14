#!/usr/bin/env python3
"""check_tests_index.py — `tests/*.yaml` 根级索引门控（TESTCASES-071t，L1）。

规范来源：`docs/Process-09-测试组织规范.md` §3（四 scope 目录）与 §5（根级 case 清单）。
本门控只做**静态**校验，不跑被测语义（L1）。

检查（全部 fail-closed；计数一律现场派生，不写死）：
  1. 四个 scope 索引文件 `tests/{inst,arch,unit,tset}.yaml` 必须存在，且
     `tests/<scope>/` 目录必须存在；`tests/` 根下**任何** `*.yaml` 的 stem
     必须是合法 scope（禁止 `tests/index/`、`tests/manifest/` 之类旁路）。
  2. 顶层必须是 list（空文件视作空列表，`[]` 亦合法）。
  3. 每条目字段**恰好** `id/file/platforms/level/requires`（无缺字段/未知字段）。
  4. `id` 形如 `<scope>-<name>[-<name>...]-<nnn>`（三段以上），且前缀 scope
     必须等于所在索引的 scope。
  5. `file` 是 `tests/` 下的相对路径、位于 `<scope>/` 下、且实际存在（且为文件）。
  6. `platforms` 非空、无重复、取值属于该 scope 的允许集：
     inst = system（user/hw 预留）；arch = system（hw 预留）；
     unit = host/toolchain；tset = user（hw 预留）。
  7. `level ∈ {smoke, full}`；`requires` = 无重复的非空字符串列表。
  8. `id` 在四份索引内**全局唯一**。
  9. **载体↔索引双向断言**：`tests/<scope>/**/*<后缀>` 现场派生的载体集合必须与
     该 scope 索引里同后缀的 `file:` 集合**完全相等**（`CARRIER_SUFFIXES`，目前
     `inst` 的 `.S`）。缺 = 载体未入索引（门控看不见、删索引无哨兵）；多 = 索引
     指向非载体/幽灵条目。两侧都逐条报出。
 10. **每 id 用例数 ≤ 127**（M13-TESTCASES-042；用户 2026-11-14 裁定「每条指令的
     测试用例不要超过 127 个，换言之一个汇编文件」）：按 id 汇总**全部载体**的用例数
     （`tests/inst/**/*.S` 检查点，复用 L2 `run_asm_suite.scan_source` 同一真源；
     YAML 载体已随 `m13-testcases-043` 全退役）。超限报 `id / 实际 / 上限` 并 FAIL；
     计数现场统计、不写死。
 11. **`.yaml` 载体不得残留**（`m13-testcases-043`：YAML 全退役）：`tests/inst/` 下出现
     任何 `*.yaml` ⇒ FAIL（载体模型只有 `.S` + 手工 C/LL 探针）。
 12. **非 id 载体显式登记**（`m13-testcases-043`）：`tests/inst/00-isa-design/undi_reserved.S`
     这类「文件 stem 不是 opcode id」的载体必须在 `NON_ID_CARRIERS` **逐文件**登记，
     且必须被 `tests/inst.yaml` 索引；同一目录里出现未登记的 `.S` ⇒ FAIL
     （不做「某目录任意放行」的目录级豁免）。

用法：
  python3 tools/testcases/check_tests_index.py               # 门控（默认）
  python3 tools/testcases/check_tests_index.py --self-test   # 干净基线 + 各类注入
  python3 tools/testcases/check_tests_index.py --root DIR    # 检查另一棵树
"""
from __future__ import annotations

import argparse
import contextlib
import io
import re
import shutil
import sys
import tempfile
from pathlib import Path, PurePosixPath

import yaml

_YAML_LOADER = getattr(yaml, "CSafeLoader", yaml.SafeLoader)

ROOT = Path(__file__).resolve().parents[2]
TESTS_REL = "tests"
SCOPES = ("inst", "arch", "unit", "tset")
# Process-09 §7：inst 首期只 system，user 预留；hw = 将来硬件在环（全 scope 预留）。
SCOPE_PLATFORMS = {
    "inst": ("system", "user", "hw"),
    "arch": ("system", "hw"),
    "unit": ("host", "toolchain"),
    "tset": ("user", "hw"),
}
FIELDS = ("id", "file", "platforms", "level", "requires")
LEVELS = ("smoke", "full")
ID_RE = re.compile(r"^(?P<scope>[a-z]+)-(?P<name>[a-z0-9]+(?:-[a-z0-9]+)*)-(?P<num>\d{3})$")

# ---------------------------------------------------------------------------
# 机器几何地址扫描 + profile↔lds 交叉核对（TESTCASES-091t）
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
import machine_profile  # noqa: E402

# `.S` 载体检查点计数复用 L2 `check-inst-asm` / `validate_vectors` 的同一真源
# （`scan_source`），避免门控与执行侧各认一套语法（M13-TESTCASES-042）。
sys.path.insert(0, str(Path(__file__).resolve().parent / "inst"))
import run_asm_suite  # noqa: E402

SCAN_ROOTS = ("tests", "tools/testcases")
TEXT_SUFFIXES = (
    ".py", ".yaml", ".yml", ".s", ".S", ".md", ".lds", ".c", ".h",
    ".test", ".txt", ".sh", ".inc", ".tsv", ".ll", ".cfg", ".ld",
    ".toml", ".json",
)
OLD_RAM_LO = 0xFC00_0000_0000
OLD_RAM_HI = 0xFC00_00FF_FFFF
FORBIDDEN_EXACT = {
    0xFC00: "old RAM high wyde",
    0x00FF0000: "old 16 MiB top offset",
    0xFFFF00001000: "old BINARY_BASE alias",
    0xFFFFFFFC0000: "old 256 KiB BootROM base",
}
# 唯一预登记例外（任务书 §5）：049t 的负例目标语义就是“旧别名未映射”。
ALLOWED = {
    "tools/testcases/arch/min_rom_probe_049t.py": {
        "0xffff_0000_0000": "negative target: legacy RAM removed => UNMAPPED",
        "0xFFFF_0000_0000": "negative target: legacy RAM removed => UNMAPPED",
        "0xFFFF00000000": "negative target: legacy RAM removed => UNMAPPED",
    },
    # tset/llvm-ts 属 qemu-user/gem5 SE，非 Machine-v5 FS profile（任务书 §范围）。
    "tools/testcases/tset/llvm-ts/run_llvm_ts_user.py": {
        "0xFC0000000000": "qemu-user scripted VA base; out of Machine-v5 scope",
    },
    "tools/testcases/tset/libc-test/run_libc_test_user_suite.py": {
        "0xFC0000000000": "qemu-user scripted VA base; out of Machine-v5 scope",
    },
    "tools/testcases/tset/embench/run_embench_user_suite.py": {
        "0xFC0000000000": "qemu-user scripted VA base; out of Machine-v5 scope",
    },
}

_HEX_TOKEN_RE = re.compile(r"0[xX][0-9a-fA-F_]+")


def _iter_text_files(root: Path):
    for rel_root in SCAN_ROOTS:
        base = root / rel_root
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            if not path.is_file() or path.is_symlink():
                continue
            rel = path.relative_to(root).as_posix()
            if rel == "tools/testcases/check_tests_index.py":
                continue  # the scanner's own forbidden-pattern table
            if path.suffix not in TEXT_SUFFIXES:
                continue
            try:
                data = path.read_bytes()
            except OSError:
                continue
            if b"\x00" in data:
                continue
            yield path


def _old_geometry_reason(literal: str):
    """Return a reason when a 0x literal is old Machine-v5 geometry, else None."""
    try:
        val = int(literal.replace("_", ""), 16)
    except ValueError:
        return None
    low48 = val & 0xFFFF_FFFF_FFFF
    if OLD_RAM_LO <= low48 <= OLD_RAM_HI:
        return "old 0xFC00 RAM address"
    if val in FORBIDDEN_EXACT:
        return FORBIDDEN_EXACT[val]
    return None


def scan_addresses(root: Path):
    """Return (checked_files, hits). hits = [(relpath, lineno, literal, reason)]."""
    checked = 0
    hits = []
    for path in _iter_text_files(root):
        checked += 1
        rel = path.relative_to(root).as_posix()
        allowed = {k.lower() for k in ALLOWED.get(rel, {})}
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for lineno, line in enumerate(lines, 1):
            for m in _HEX_TOKEN_RE.finditer(line):
                literal = m.group(0)
                reason = _old_geometry_reason(literal)
                if reason is None:
                    continue
                if literal.lower() in allowed:
                    continue
                hits.append((rel, lineno, literal, reason))
    return checked, hits


def _parse_lds_memory(text: str):
    out = {}
    for m in re.finditer(
            r"([A-Za-z_][A-Za-z0-9_]*)\s*\([a-z]+\)\s*:\s*ORIGIN\s*=\s*"
            r"(0x[0-9a-fA-F_]+)\s*,\s*LENGTH\s*=\s*(0x[0-9a-fA-F_]+|\d+[KkMm])",
            text):
        name, origin, length = m.group(1), m.group(2), m.group(3)
        oval = int(origin.replace("_", ""), 16)
        if length[-1] in "KkMm":
            lval = int(length[:-1]) * (1024 if length[-1] in "Kk" else 1024 * 1024)
        else:
            lval = int(length.replace("_", ""), 16)
        out[name] = (oval, lval)
    return out


def _parse_lds_entry(text: str):
    m = re.search(r"ENTRY\s*\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*\)", text)
    return m.group(1) if m else None


def check_profile_lds(root: Path):
    """Cross-check profile table ↔ linker scripts (counts derived live)."""
    print("-" * 72)
    print("  地址静态扫描 + profile↔lds 交叉核对")
    profs = machine_profile.all_profiles()
    errors = []
    checked, hits = scan_addresses(root)
    for rel, lineno, literal, reason in hits:
        errors.append(f"OLD GEOMETRY: {rel}:{lineno}: {literal} ({reason})")
    if not hits:
        print(f"  地址扫描: {checked} 个文本文件，旧几何残留 0")

    lds_map = {"tiny": "tests/shared/linker/dadao-tiny.lds",
               "vast": "tests/shared/linker/dadao-vast.lds"}
    for name, rel in lds_map.items():
        path = root / rel
        if not path.is_file():
            errors.append(f"LDS MISSING: {rel}")
            continue
        text = path.read_text(encoding="utf-8")
        mem = _parse_lds_memory(text)
        prof = profs[name]
        if "RAM" not in mem:
            errors.append(f"LDS: {rel} missing RAM MEMORY region")
        else:
            origin, length = mem["RAM"]
            if origin != prof.ram_base:
                errors.append(f"LDS: {rel} RAM ORIGIN {origin:#x} != "
                              f"profile {name} ram_base {prof.ram_base:#x}")
            if length != prof["ram_size"]:
                errors.append(f"LDS: {rel} RAM LENGTH {length:#x} != "
                              f"profile {name} ram_size {prof['ram_size']:#x}")
        if "ROM" in mem:
            origin, length = mem["ROM"]
            if origin != prof.bootrom_base:
                errors.append(f"LDS: {rel} ROM ORIGIN {origin:#x} != "
                              f"profile {name} bootrom_base {prof.bootrom_base:#x}")
            if length != prof["bootrom_size"]:
                errors.append(f"LDS: {rel} ROM LENGTH {length:#x} != "
                              f"profile {name} bootrom_size {prof['bootrom_size']:#x}")
        if _parse_lds_entry(text) != "_start":
            errors.append(f"LDS: {rel} ENTRY must be _start")
        mheap = re.search(r"__heap_end\s*=\s*(0x[0-9a-fA-F_]+)\s*;", text)
        expected_heap = prof.sp - 0x1000
        if not mheap:
            errors.append(f"LDS: {rel} missing __heap_end = sp - 0x1000")
        elif int(mheap.group(1).replace("_", ""), 16) != expected_heap:
            errors.append(f"LDS: {rel} __heap_end {mheap.group(1)} != "
                          f"sp-0x1000 {expected_heap:#x}")
    common = root / "tests/shared/linker/dadao-common.lds"
    if not common.is_file():
        errors.append("LDS MISSING: tests/shared/linker/dadao-common.lds")
    else:
        ctext = common.read_text(encoding="utf-8")
        for sym in ("__bss_start = .;", "__bss_end = .;",
                    "PROVIDE(__heap_start = __end);"):
            if sym not in ctext:
                errors.append(f"LDS COMMON: missing {sym!r}")
        for rel in lds_map.values():
            if "INCLUDE dadao-common.lds" not in (root / rel).read_text(encoding="utf-8"):
                errors.append(f"LDS: {rel} does not INCLUDE dadao-common.lds")
    print(f"  profile↔lds: {len(lds_map)} 份链接脚本 + common 逐项核对")

    # BootROM 复位窗口：power.lds ORIGIN == vast reset_pc。
    power_lds = root / "tests/shared/bootrom/step5/power.lds"
    if power_lds.is_file():
        mem = _parse_lds_memory(power_lds.read_text(encoding="utf-8"))
        prof = profs["vast"]
        origin = mem.get("ROM", (None, None))[0]
        if origin != prof.reset_pc:
            errors.append(f"BOOTROM: power.lds ORIGIN {origin} != vast reset_pc "
                          f"{prof.reset_pc:#x}")
        offset = prof.reset_pc - prof.bootrom_base
        if not (0 <= offset <= prof["bootrom_size"] - 0x10000):
            errors.append(f"BOOTROM: vast reset offset {offset:#x} outside "
                          f"{prof['bootrom_size']:#x} image")

    # Assembler headers must match the profile table (generated by
    # tools/testcases/arch/gen_machine_inc.py).
    for name, prof in profs.items():
        inc = root / ("tests/shared/asm/machine-%s.inc" % name)
        if not inc.is_file():
            errors.append(f"ASM HEADER MISSING: {inc.relative_to(root)}")
            continue
        text = inc.read_text(encoding="utf-8")
        for sym, val in (("RAM_BASE", prof.ram_base), ("RAM_END", prof.ram_end),
                         ("ENTRY", prof.entry), ("SP", prof.sp),
                         ("BOOTROM_BASE", prof.bootrom_base),
                         ("RESET_PC", prof.reset_pc)):
            expected = ".equ %s, %#x" % (sym, val)
            if expected not in text:
                errors.append(f"ASM HEADER DRIFT: {inc.relative_to(root)} "
                              f"missing {expected!r}")

    # picolibc Tiny layout (A scheme): crt stub ROM / app SRAM / e_entry ROM.
    pico = root / "tests/shared/linker/picolibc-tiny.ld"
    if pico.is_file():
        ptext = pico.read_text(encoding="utf-8")
        for needle in ("ORIGIN = 0xffffffff0000", "ORIGIN = 0xffffff010100",
                       "__stack = 0xffffff7eff00", ".text.start"):
            if needle not in ptext:
                errors.append(f"PICOLIBC LDS: missing {needle!r}")
    else:
        errors.append("PICOLIBC LDS MISSING: tests/shared/linker/picolibc-tiny.ld")

    # Harness must not carry a RAM base literal (profile-derived only).
    harness = root / "tools/testcases/lib/build_test_binary.py"
    if harness.is_file():
        text = harness.read_text(encoding="utf-8")
        if re.search(r"BINARY_BASE\s*=\s*0x[0-9a-fA-F_]+", text):
            errors.append("HARNESS: build_test_binary.py BINARY_BASE literal "
                          "(must be profile-derived)")
    return errors


# ---------------------------------------------------------------------------
# 载体↔索引双向断言（M13-TESTCASES-041）
# ---------------------------------------------------------------------------
# 040 实测：删掉一条索引后本门控仍 PASS ⇒ 缺「删除哨兵」，索引可无提示缩水。
# 判据是**集合相等**（不是计数）：载体由文件系统现场派生，索引由 YAML 现场派生，
# 两侧差集都逐条报出。只纳入「一载体一索引」的 scope：
#   * inst 的执行型载体 = `tests/inst/<册>/<id>.S`（与 validate-vectors 同一现场扫描）；
#   * arch/unit 的载体模型不同（unit 的 `.s` 多为 `.ll` 派生、arch 有辅助 `.S` 头），
#     其覆盖由各自门控承担，不在此处按后缀断言。
CARRIER_SUFFIXES = {"inst": (".S",)}

# 非 opcode 身份的载体（`m13-testcases-043`）：文件名不是 id，不能当 id 载体断言，
# 但仍是索引必须覆盖的现场载体。**逐文件登记**（键 = `tests/` 下相对路径），
# 不做「某目录下任意 `.S` 豁免」。
NON_ID_CARRIERS = {
    "inst/00-isa-design/undi_reserved.S":
        "保留编码（QFC 空白格）⇒ UNDI；无 opcode 身份，索引 id = inst-00-isa-design-001",
}


# ---------------------------------------------------------------------------
# 每 id 用例数上限（M13-TESTCASES-042；用户 2026-11-14 裁定）
# ---------------------------------------------------------------------------
# 规则原文：「无特殊情况下，每条指令的测试用例不要超过127个，换言之，一个汇编文件」。
# 计数 = 该 id 在**全部载体**上的用例数：YAML 用例条目 + `.S` 载体检查点（链例 +
# 故障例）。`.S` 一侧复用 `inst/run_asm_suite.scan_source`（与 L2 `check-inst-asm`
# 和 `validate_vectors` 同一真源），不另写一套语法。
# 上限 127 是**规则**本身（不是基线计数），故为常量；其余计数一律现场派生。
CASE_LIMIT = 127


def _asm_case_counts(root: Path) -> dict[str, dict[str, int]]:
    """`inst` `.S` 载体的检查点数（链例 `checks` + 故障例），按 id（= 文件 stem）。"""
    per_id: dict[str, dict[str, int]] = {}
    for rel in sorted(_carrier_files(root, "inst")):
        path = root / TESTS_REL / rel
        try:
            info = run_asm_suite.scan_source(path)
        except (OSError, UnicodeDecodeError):
            continue
        n = info["checks"] + len(info["faults"])
        if n:
            per_id.setdefault(path.stem, {})[rel] = n
    return per_id


def check_case_limit(root: Path) -> list[str]:
    """每 id 用例数 ≤ `CASE_LIMIT`；超限逐条报 `id / 实际 / 上限`。"""
    errors: list[str] = []
    per_id: dict[str, dict[str, int]] = {}
    for cid, srcs in _asm_case_counts(root).items():
        bucket = per_id.setdefault(cid, {})
        for rel, n in srcs.items():
            bucket[rel] = bucket.get(rel, 0) + n
    if not per_id:
        return errors
    worst = max(per_id.items(), key=lambda kv: sum(kv[1].values()))
    for cid in sorted(per_id):
        total = sum(per_id[cid].values())
        if total > CASE_LIMIT:
            detail = ", ".join("%s=%d" % kv for kv in sorted(per_id[cid].items()))
            errors.append("CASE LIMIT: id=%s 用例 %d > 上限 %d（%s）"
                          % (cid, total, CASE_LIMIT, detail))
    print(f"  每 id 用例上限（≤{CASE_LIMIT}）: {len(per_id)} 个 id，最大 "
          f"{worst[0]}={sum(worst[1].values())}（现场统计）")
    return errors


def _carrier_files(root: Path, scope: str) -> set[str]:
    """现场派生 `<scope>` 下的载体文件（相对 `tests/` 的 posix 路径）。"""
    tests_root = root / TESTS_REL
    scope_dir = tests_root / scope
    if not scope_dir.is_dir():
        return set()
    out: set[str] = set()
    for suffix in CARRIER_SUFFIXES.get(scope, ()):
        for path in scope_dir.rglob(f"*{suffix}"):
            if path.is_file():
                out.add(path.relative_to(tests_root).as_posix())
    return out


def check_carrier_bijection(
    root: Path,
    indexed_files: dict[str, list[str]],
) -> list[str]:
    """载体集合 == 索引集合；不等则逐条报「缺 / 多」。计数一律现场派生。"""
    errors: list[str] = []
    for scope, suffixes in CARRIER_SUFFIXES.items():
        carriers = _carrier_files(root, scope)
        idx_list = [f for f in indexed_files.get(scope, [])
                    if PurePosixPath(f).suffix in suffixes]
        in_index = set(idx_list)
        dup = sorted({f for f in idx_list if idx_list.count(f) > 1})
        missing = sorted(carriers - in_index)
        ghost = sorted(in_index - carriers)
        for rel in dup:
            errors.append(
                f"tests/{scope}.yaml: 同一载体被多条索引重复引用（多）: {rel}")
        for rel in missing:
            errors.append(
                f"tests/{scope}.yaml: 载体未入索引（缺）: {rel}")
        for rel in ghost:
            errors.append(
                f"tests/{scope}.yaml: 索引指向非载体（多）: {rel}")
        print(f"  载体↔索引（{scope} {''.join(suffixes)}）: 载体 {len(carriers)} 个 / "
              f"索引 {len(idx_list)} 条 / 缺 {len(missing)} / 多 {len(ghost)}")
    return errors


def check_no_yaml_carriers(root: Path) -> list[str]:
    """`tests/inst/` 下不得再有 YAML 载体（`m13-testcases-043`：YAML 全退役）。

    载体模型收敛为 `.S`（+ 手工 C/LL 探针）；残留的 `*.yaml` 会让「载体集」被两套
    语法解释（有的门控认、有的不认）⇒ 直接判红，由人决定是删还是登记。
    """
    inst = root / TESTS_REL / "inst"
    if not inst.is_dir():
        return []
    stray = sorted(p.relative_to(root).as_posix() for p in inst.rglob("*.yaml")
                   if p.is_file())
    return [f"YAML CARRIER RESIDUE: {rel}（tests/inst 下只允许 .S 载体；"
            f"YAML 载体已于 m13-testcases-043 全退役）" for rel in stray]


def check_non_id_carriers(
    root: Path,
    registry: dict[str, str],
    indexed_files: dict[str, list[str]],
) -> list[str]:
    """非 id 载体：**逐文件**登记 + 必须在索引里；同目录不含未登记 `.S`。

    不做目录级豁免：登记目录里出现未登记的 `.S` ⇒ FAIL；登记项缺失/未入索引 ⇒ FAIL。
    """
    errors: list[str] = []
    for rel, why in sorted(registry.items()):
        path = root / TESTS_REL / rel
        if not rel.startswith("inst/"):
            errors.append(f"NON-ID CARRIER: `{rel}` 必须位于 `inst/` 下（登记理由: {why}）")
            continue
        if not path.is_file():
            errors.append(f"NON-ID CARRIER MISSING: 登记的非 id 载体不存在: tests/{rel}"
                          f"（理由: {why}）")
            continue
        if rel not in set(indexed_files.get("inst", [])):
            errors.append(f"tests/inst.yaml: 非 id 载体未入索引（缺）: {rel}")
        parent = path.parent
        for other in sorted(parent.glob("*.S")):
            other_rel = other.relative_to(root / TESTS_REL).as_posix()
            if other_rel not in registry:
                errors.append(
                    f"NON-ID CARRIER UNSET: {rel} 所在目录存在未登记的 .S: {other_rel}"
                    "（非 id 载体须逐文件登记，不做目录级豁免）")
    if registry:
        print(f"  非 id 载体（显式登记）: {len(registry)} 个")
    return errors


def _load_index(path: Path) -> tuple[object, str | None]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return None, f"无法读取: {exc}"
    try:
        return yaml.load(text, Loader=_YAML_LOADER), None
    except yaml.YAMLError as exc:
        return None, f"YAML 解析失败: {exc}"


def _check_entry(
    entry: object,
    scope: str,
    idx: int,
    tests_root: Path,
    errors: list[str],
) -> str | None:
    """校验单条目；返回 id（供全局唯一性检查；无效时为 None）。"""
    where = f"tests/{scope}.yaml 第 {idx} 条"
    if not isinstance(entry, dict):
        errors.append(f"{where}: 条目必须是映射，实为 {type(entry).__name__}")
        return None

    keys = set(entry)
    missing = [f for f in FIELDS if f not in keys]
    unknown = sorted(keys - set(FIELDS))
    if missing:
        errors.append(f"{where}: 缺字段 {missing}")
    if unknown:
        errors.append(f"{where}: 未知字段 {unknown}（允许: {list(FIELDS)}）")

    cid = entry.get("id")
    if not isinstance(cid, str) or not cid:
        errors.append(f"{where}: `id` 必须是非空字符串")
        cid = None
    else:
        m = ID_RE.match(cid)
        if not m:
            errors.append(f"{where}: `id`=`{cid}` 不合 `<scope>-<name>[-<name>...]-<nnn>`")
        elif m.group("scope") != scope:
            errors.append(
                f"{where}: `id` 前缀 `{m.group('scope')}` ≠ 所在索引 scope `{scope}`")

    rel = entry.get("file")
    if not isinstance(rel, str) or not rel:
        errors.append(f"{where}: `file` 必须是非空字符串")
    else:
        pure = PurePosixPath(rel)
        if pure.is_absolute():
            errors.append(f"{where}: `file`=`{rel}` 必须是 `tests/` 下相对路径（禁绝对路径）")
        elif ".." in pure.parts:
            errors.append(f"{where}: `file`=`{rel}` 含 `..`（禁止越出 `tests/`）")
        elif not pure.parts or pure.parts[0] != scope:
            errors.append(f"{where}: `file`=`{rel}` 不在 scope 目录 `{scope}/` 下")
        else:
            target = tests_root / pure
            try:
                target.resolve().relative_to(tests_root.resolve())
            except (ValueError, OSError):
                errors.append(f"{where}: `file`=`{rel}` 解析后越出 `tests/`")
            else:
                if not target.exists():
                    errors.append(f"{where}: `file` 不存在: tests/{rel}")
                elif not target.is_file():
                    errors.append(f"{where}: `file` 不是文件: tests/{rel}")

    platforms = entry.get("platforms")
    got_platforms: list[str] = []
    if not isinstance(platforms, list) or not platforms:
        errors.append(f"{where}: `platforms` 必须是非空列表")
    else:
        got_platforms = [p for p in platforms if isinstance(p, str)]
        if len(got_platforms) != len(platforms):
            errors.append(f"{where}: `platforms` 只能含字符串: {platforms}")
        if len(set(got_platforms)) != len(got_platforms):
            errors.append(f"{where}: `platforms` 有重复: {got_platforms}")
        bad = [p for p in got_platforms if p not in SCOPE_PLATFORMS[scope]]
        if bad:
            errors.append(
                f"{where}: `platforms` 非法 {bad}（scope `{scope}` 允许 "
                f"{list(SCOPE_PLATFORMS[scope])}）")

    level = entry.get("level")
    if level not in LEVELS:
        errors.append(f"{where}: `level`=`{level!r}` 须为 {list(LEVELS)}")

    requires = entry.get("requires")
    if not isinstance(requires, list):
        errors.append(f"{where}: `requires` 必须是列表（可为空）")
    else:
        bad_req = [r for r in requires if not isinstance(r, str) or not r]
        if bad_req:
            errors.append(f"{where}: `requires` 含非字符串/空串: {bad_req!r}")
        reqs = [r for r in requires if isinstance(r, str)]
        if len(set(reqs)) != len(reqs):
            errors.append(f"{where}: `requires` 有重复: {reqs}")

    return cid


def audit(root: Path, registry: dict[str, str] | None = None) -> int:
    print("=" * 72)
    print("check-tests-index — tests/ 根级索引（L1）")
    print("=" * 72)
    errors: list[str] = []
    tests_root = root / TESTS_REL

    if not tests_root.is_dir():
        print(f"  ERROR: `tests/` 不存在: {tests_root} ⇒ fail-closed")
        print("结果: FAIL (1 项)")
        return 1

    # ── 1. tests/ 根下 *.yaml 必须都是 scope 索引；四个索引/目录必须存在 ──
    root_yamls = sorted(p for p in tests_root.glob("*.yaml") if p.is_file())
    for path in root_yamls:
        if path.stem not in SCOPES:
            errors.append(
                f"tests/{path.name}: 根级 `*.yaml` 的 scope `{path.stem}` 不合法"
                f"（允许 {list(SCOPES)}；禁止 `tests/index/`、`tests/manifest/` 等旁路）")

    counts: dict[str, int] = {}
    seen_ids: dict[str, str] = {}
    indexed_files: dict[str, list[str]] = {s: [] for s in SCOPES}
    for scope in SCOPES:
        index_path = tests_root / f"{scope}.yaml"
        scope_dir = tests_root / scope
        if not scope_dir.is_dir():
            errors.append(f"tests/{scope}/: scope 目录不存在")
        if not index_path.is_file():
            errors.append(f"tests/{scope}.yaml: 索引文件不存在")
            continue

        data, err = _load_index(index_path)
        if err:
            errors.append(f"tests/{scope}.yaml: {err}")
            continue
        if data is None:
            data = []  # 空文件 = 空列表
        if not isinstance(data, list):
            errors.append(
                f"tests/{scope}.yaml: 顶层必须是列表（空列表亦合法），实为 "
                f"{type(data).__name__}")
            continue

        counts[scope] = len(data)
        for idx, entry in enumerate(data, 1):
            if isinstance(entry, dict):
                rel = entry.get("file")
                if isinstance(rel, str) and rel:
                    indexed_files[scope].append(rel)
            cid = _check_entry(entry, scope, idx, tests_root, errors)
            if cid is None:
                continue
            if cid in seen_ids:
                errors.append(
                    f"tests/{scope}.yaml 第 {idx} 条: `id`=`{cid}` 重复"
                    f"（已在 {seen_ids[cid]} 出现）")
            else:
                seen_ids[cid] = f"tests/{scope}.yaml 第 {idx} 条"

    total = sum(counts.values())
    print(f"  scope 索引文件（现场统计）: {len(root_yamls)} 个根级 *.yaml；"
          f"合法 scope 索引 {len(counts)}/{len(SCOPES)}")
    print("  条目计数（现场派生）: " + " / ".join(
        f"{s}={counts.get(s, 0)}" for s in SCOPES) + f" / total={total}")

    errors.extend(check_carrier_bijection(root, indexed_files))
    errors.extend(check_non_id_carriers(
        root, NON_ID_CARRIERS if registry is None else registry, indexed_files))
    errors.extend(check_no_yaml_carriers(root))
    errors.extend(check_case_limit(root))

    geo_errors = check_profile_lds(root)
    errors.extend(geo_errors)
    if not geo_errors:
        print("  机器几何: 旧地址残留 0；profile↔lds 一致")

    print("-" * 72)
    if errors:
        for e in errors:
            print(f"  VIOLATION: {e}")
        print(f"结果: FAIL ({len(errors)} 项)")
        return 1
    print(f"结果: PASS（{total} 条；ID 唯一 / file 存在 / 字段·平台·level 合法 / "
          f"scope 合法）")
    return 0


# ---------------------------------------------------------------------------
# self-test：临时树 + 干净基线 + 各类注入（每条断言均有可达 FAIL）
# ---------------------------------------------------------------------------

def _write_profile_lds(root: Path, tamper: str | None = None) -> None:
    """Write minimal, profile-consistent linker scripts for the self-test tree."""
    profs = machine_profile.all_profiles()
    for name, rel in (("tiny", "shared/linker/dadao-tiny.lds"),
                      ("vast", "shared/linker/dadao-vast.lds")):
        prof = profs[name]
        origin, length = prof.ram_base, prof["ram_size"]
        rom_origin, rom_len = prof.bootrom_base, prof["bootrom_size"]
        if tamper == rel:
            origin += 0x1000
        text = (
            "ENTRY(_start)\nMEMORY\n{\n"
            f"  RAM (rwx) : ORIGIN = 0x{origin:X}, LENGTH = 0x{length:X}\n"
            f"  ROM (rx)  : ORIGIN = 0x{rom_origin:X}, LENGTH = 0x{rom_len:X}\n"
            "}\nSECTIONS\n{\n  .text : ALIGN(4) { *(.text) } > RAM\n"
            f"  INCLUDE dadao-common.lds\n"
            f"  .rom : ALIGN(4) {{ *(.rom) }} > ROM\n}}\n"
            f"__heap_end = 0x{prof.sp - 0x1000:X};\n")
        path = root / TESTS_REL / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    common = root / TESTS_REL / "shared" / "linker" / "dadao-common.lds"
    common.parent.mkdir(parents=True, exist_ok=True)
    common.write_text(
        "  .bss : ALIGN(8) { __bss_start = .; *(.bss) __bss_end = .; } > RAM\n"
        "  PROVIDE(__heap_start = __end);\n", encoding="utf-8")
    (root / TESTS_REL / "shared" / "linker" / "picolibc-tiny.ld").write_text(
        "MEMORY { flash (rx!w) : ORIGIN = 0xffffffff0000, LENGTH = 0x10000\n"
        "         ram (rwx) : ORIGIN = 0xffffff010100, LENGTH = 0x7eff00 }\n"
        "__stack = 0xffffff7eff00;\n"
        "SECTIONS { .text.start : { *(.text.start) } > flash }\n",
        encoding="utf-8")


def _write_tree(
    root: Path,
    indexes: dict[str, str],
    extra_files: dict[str, str] | None = None,
) -> None:
    for scope in SCOPES:
        (root / TESTS_REL / scope).mkdir(parents=True, exist_ok=True)
    for scope, text in indexes.items():
        (root / TESTS_REL / f"{scope}.yaml").write_text(text, encoding="utf-8")
    for rel, text in (extra_files or {}).items():
        path = root / TESTS_REL / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    _write_profile_lds(root)
    src_asm = ROOT / "tests" / "shared" / "asm"
    if src_asm.is_dir():
        dst_asm = root / TESTS_REL / "shared" / "asm"
        dst_asm.mkdir(parents=True, exist_ok=True)
        for inc in src_asm.glob("*.inc"):
            shutil.copyfile(inc, dst_asm / inc.name)


def _empty_indexes() -> dict[str, str]:
    return {scope: "[]\n" for scope in SCOPES}


VALID_ENTRY = """\
- id: inst-base-001
  file: inst/base/add.c
  platforms: [system]
  level: smoke
  requires: []
"""

VALID_ASM_ENTRY = """\
- id: inst-01-load-store-001
  file: inst/01-load-store/add.S
  platforms: [system]
  level: full
  requires: []
"""


def _run(root: Path, registry: dict[str, str] | None = None) -> tuple[int, str]:
    """跑一次 audit。合成树默认**空登记表**（仓库自带的非 id 载体不在临时树里）。"""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = audit(root, {} if registry is None else registry)
    return rc, buf.getvalue()


def self_test() -> int:
    print("=" * 72)
    print("check-tests-index --self-test（干净基线 PASS + 注入各自 FAIL）")
    print("=" * 72)
    tmp_base = Path(tempfile.gettempdir()) / "opencode" / "TESTCASES-071t"
    tmp_base.mkdir(parents=True, exist_ok=True)
    tmpdir = Path(tempfile.mkdtemp(prefix="tests-index-", dir=tmp_base))
    ok = True
    try:
        case_no = 0

        def case(
            name: str,
            indexes: dict[str, str],
            marker: str | None,
            extra_files: dict[str, str] | None = None,
            expect_rc: int = 1,
        ) -> None:
            nonlocal ok, case_no
            case_no += 1
            work = tmpdir / f"case{case_no}"
            _write_tree(work, indexes, extra_files)
            rc, out = _run(work)
            hit = marker is None or marker in out
            good = rc == expect_rc and hit
            ok = ok and good
            print(f"  [{'PASS' if good else 'FAIL'}] self-test case{case_no} {name}: "
                  f"期望 rc={expect_rc} 实际 rc={rc} marker={hit}")

        # 干净基线①：四个空索引（`[]` 与空文件均合法）
        empty = _empty_indexes()
        empty["inst"] = ""
        case("干净基线·空索引", empty, None, expect_rc=0)
        # 干净基线②：一条合法条目
        good = _empty_indexes()
        good["inst"] = VALID_ENTRY
        case("干净基线·一条合法条目", good, None,
             extra_files={"inst/base/add.c": "/* demo */\n"}, expect_rc=0)

        # 干净基线③：载体与索引成对（.S 唯一时双向断言不得误报）
        paired = _empty_indexes()
        paired["inst"] = VALID_ASM_ENTRY
        case("干净基线·载体↔索引成对", paired, None,
             extra_files={"inst/01-load-store/add.S": "nop\n"}, expect_rc=0)

        # 注入·载体未入索引：磁盘有 .S、索引没有 ⇒ 缺（040 的删除缺口）
        bad = dict(_empty_indexes())
        case("注入·载体未入索引", bad, "载体未入索引（缺）: inst/01-load-store/only.S",
             extra_files={"inst/01-load-store/only.S": "nop\n"})

        # 注入·索引指向非载体：索引有 .S 条目、磁盘无该文件 ⇒ 多（幽灵条目）
        bad = dict(_empty_indexes())
        bad["inst"] = VALID_ASM_ENTRY
        case("注入·索引指向非载体", bad, "索引指向非载体（多）: inst/01-load-store/add.S")

        # 注入·同一载体被两条索引引用：集合相等而条数不等 ⇒ 必须红（不得只看集合）
        bad = dict(_empty_indexes())
        bad["inst"] = VALID_ASM_ENTRY + VALID_ASM_ENTRY.replace(
            "inst-01-load-store-001", "inst-01-load-store-002")
        case("注入·同一载体重复引用", bad,
             "重复引用（多）: inst/01-load-store/add.S",
             extra_files={"inst/01-load-store/add.S": "nop\n"})

        # 注入①：ID 重复
        dup = dict(good)
        dup["inst"] = VALID_ENTRY + VALID_ENTRY
        case("注入① ID 重复", dup, "重复",
             extra_files={"inst/base/add.c": "/* demo */\n"})

        # 注入②：file 不存在
        bad = dict(_empty_indexes())
        bad["inst"] = VALID_ENTRY.replace("inst/base/add.c", "inst/base/nope.c")
        case("注入② file 不存在", bad, "不存在")

        # 注入③：platforms 非法
        bad = dict(good)
        bad["inst"] = VALID_ENTRY.replace("[system]", "[windows]")
        case("注入③ platforms 非法", bad, "platforms",
             extra_files={"inst/base/add.c": "/* demo */\n"})

        # 注入④：level 非法
        bad = dict(good)
        bad["inst"] = VALID_ENTRY.replace("level: smoke", "level: quick")
        case("注入④ level 非法", bad, "level",
             extra_files={"inst/base/add.c": "/* demo */\n"})

        # 注入⑤：ID 前缀与索引 scope 不一致
        bad = dict(good)
        bad["inst"] = VALID_ENTRY.replace("id: inst-base-001", "id: arch-base-001")
        case("注入⑤ ID 前缀错配", bad, "前缀",
             extra_files={"inst/base/add.c": "/* demo */\n"})

        # 注入⑥：缺字段
        bad = dict(good)
        bad["inst"] = VALID_ENTRY.replace("  requires: []\n", "")
        case("注入⑥ 缺字段", bad, "缺字段",
             extra_files={"inst/base/add.c": "/* demo */\n"})

        # 注入⑦：未知字段
        bad = dict(good)
        bad["inst"] = VALID_ENTRY + "  owner: nobody\n"
        case("注入⑦ 未知字段", bad, "未知字段",
             extra_files={"inst/base/add.c": "/* demo */\n"})

        # 注入⑧：file 不在本 scope 目录
        bad = dict(good)
        bad["inst"] = VALID_ENTRY.replace("inst/base/add.c", "arch/base/add.c")
        case("注入⑧ file 越 scope", bad, "不在 scope 目录",
             extra_files={"arch/base/add.c": "/* demo */\n"})

        # 注入⑨：tests/ 根下出现非法 scope 索引
        bad = dict(_empty_indexes())
        case("注入⑨ 非法 scope 索引文件", bad, "不合法",
             extra_files={"tst.yaml": "[]\n"})

        # 注入⑩：YAML 解析失败
        bad = dict(_empty_indexes())
        bad["inst"] = "- id: [unclosed\n"
        case("注入⑩ YAML 解析失败", bad, "YAML 解析失败")

        # 注入⑪：顶层不是列表
        bad = dict(_empty_indexes())
        bad["inst"] = "{}\n"
        case("注入⑪ 顶层非列表", bad, "顶层必须是列表")

        # 注入⑫：file 指向目录（不是文件）
        bad = dict(good)
        bad["inst"] = VALID_ENTRY.replace("inst/base/add.c", "inst/base")
        case("注入⑫ file 指向目录", bad, "不是文件",
             extra_files={"inst/base/add.c": "/* demo */\n"})

        # 注入⑬：scope 目录缺失
        bad = dict(_empty_indexes())
        case_dir_work = tmpdir / "case-dir"
        case_dir_work.mkdir()
        _write_tree(case_dir_work, bad)
        shutil.rmtree(case_dir_work / TESTS_REL / "tset")
        rc, out = _run(case_dir_work)
        good_dir = rc == 1 and "scope 目录不存在" in out
        ok = ok and good_dir
        print(f"  [{'PASS' if good_dir else 'FAIL'}] self-test case-dir "
              f"注入⑬ scope 目录缺失: rc={rc} marker={'scope 目录不存在' in out}")

        # 注入⑭：旧几何地址残留 ⇒ 地址扫描 FAIL
        case_no += 1
        work = tmpdir / f"case{case_no}"
        _write_tree(work, _empty_indexes())
        (work / TESTS_REL / "inst" / "old.txt").write_text(
            "address 0xFC0000001000\n", encoding="utf-8")
        rc, out = _run(work)
        good_old = rc == 1 and "OLD GEOMETRY" in out
        ok = ok and good_old
        print(f"  [{'PASS' if good_old else 'FAIL'}] self-test case{case_no} "
              f"注入⑭ 旧地址残留: rc={rc} marker={'OLD GEOMETRY' in out}")

        # 注入⑮：篡改 lds RAM ORIGIN ⇒ profile↔lds FAIL
        case_no += 1
        work = tmpdir / f"case{case_no}"
        _write_tree(work, _empty_indexes())
        _write_profile_lds(work, tamper="shared/linker/dadao-tiny.lds")
        rc, out = _run(work)
        good_lds = rc == 1 and "RAM ORIGIN" in out
        ok = ok and good_lds
        print(f"  [{'PASS' if good_lds else 'FAIL'}] self-test case{case_no} "
              f"注入⑮ lds ORIGIN 篡改: rc={rc} marker={'RAM ORIGIN' in out}")

        # 注入⑯：篡改生成的汇编头 ⇒ profile↔header FAIL
        case_no += 1
        work = tmpdir / f"case{case_no}"
        _write_tree(work, _empty_indexes())
        inc = work / TESTS_REL / "shared" / "asm" / "machine-tiny.inc"
        inc.write_text(
            inc.read_text(encoding="utf-8").replace(
                ".equ RAM_BASE, 0xffffff000000", ".equ RAM_BASE, 0x1000"),
            encoding="utf-8")
        rc, out = _run(work)
        good_inc = rc == 1 and "ASM HEADER DRIFT" in out
        ok = ok and good_inc
        print(f"  [{'PASS' if good_inc else 'FAIL'}] self-test case{case_no} "
              f"注入⑯ asm header 篡改: rc={rc} marker={'ASM HEADER DRIFT' in out}")

        # 每 id 用例上限（M13-TESTCASES-042）：127 PASS / 128 FAIL，两条都跑
        def limit_tree(work: Path, asm_n: int = 0) -> None:
            indexes = dict(_empty_indexes())
            if asm_n:
                indexes["inst"] = VALID_ASM_ENTRY.replace(
                    "inst/01-load-store/add.S",
                    "inst/01-load-store/zz_asmlimit.S")
            _write_tree(work, indexes)
            if asm_n:
                pts = "".join("\t__CHECK_RD\t%d, 1\n" % (i + 1)
                              for i in range(asm_n))
                (work / TESTS_REL / "inst" / "01-load-store").mkdir(
                    parents=True, exist_ok=True)
                (work / TESTS_REL / "inst" / "01-load-store" / "zz_asmlimit.S"
                 ).write_text(pts, encoding="utf-8")

        case_no += 1
        work = tmpdir / f"case{case_no}"
        limit_tree(work, 127)
        rc, out = _run(work)
        ok127 = rc == 0 and "每 id 用例上限" in out
        ok = ok and ok127
        print(f"  [{'PASS' if ok127 else 'FAIL'}] self-test case{case_no} "
              f"用例上限 127（.S 检查点）: rc={rc}")

        case_no += 1
        work = tmpdir / f"case{case_no}"
        limit_tree(work, 128)
        rc, out = _run(work)
        ok_asm = rc == 1 and "CASE LIMIT: id=zz_asmlimit 用例 128 > 上限 127" in out
        ok = ok and ok_asm
        print(f"  [{'PASS' if ok_asm else 'FAIL'}] self-test case{case_no} "
              f"注入⑱ 用例上限 128（.S 检查点）: rc={rc} marker={ok_asm}")

        # YAML 载体残留（M13-TESTCASES-043）：tests/inst 下出现 *.yaml ⇒ FAIL
        case_no += 1
        work = tmpdir / f"case{case_no}"
        _write_tree(work, _empty_indexes(),
                    extra_files={"inst/base/add.yaml": "- id: inst-base-001\n"})
        rc, out = _run(work)
        good_yaml = rc == 1 and "YAML CARRIER RESIDUE" in out
        ok = ok and good_yaml
        print(f"  [{'PASS' if good_yaml else 'FAIL'}] self-test case{case_no} "
              f"注入 YAML 载体残留: rc={rc} "
              f"marker={'YAML CARRIER RESIDUE' in out}")

        # 非 id 载体显式登记（M13-TESTCASES-043）：四条，各自可达 FAIL
        reg = {"inst/00-isa-design/undi_reserved.S": "self-test 登记项"}
        ent = VALID_ASM_ENTRY.replace("inst/01-load-store/add.S",
                                      "inst/00-isa-design/undi_reserved.S").replace(
            "inst-01-load-store-001", "inst-00-isa-design-001")

        case_no += 1
        work = tmpdir / f"case{case_no}"
        _write_tree(work, _empty_indexes())
        rc, out = _run(work, reg)
        good_missing = rc == 1 and "NON-ID CARRIER MISSING" in out
        ok = ok and good_missing
        print(f"  [{'PASS' if good_missing else 'FAIL'}] self-test case{case_no} "
              f"注入⑲ 登记的非 id 载体不存在: rc={rc} "
              f"marker={'NON-ID CARRIER MISSING' in out}")

        case_no += 1
        work = tmpdir / f"case{case_no}"
        idx = dict(_empty_indexes())
        idx["inst"] = ent
        _write_tree(work, idx,
                    extra_files={"inst/00-isa-design/undi_reserved.S": "nop\n"})
        rc, out = _run(work, reg)
        good_reg = rc == 0
        ok = ok and good_reg
        print(f"  [{'PASS' if good_reg else 'FAIL'}] self-test case{case_no} "
              f"干净基线·非 id 载体已登记且入索引: rc={rc}")

        case_no += 1
        work = tmpdir / f"case{case_no}"
        _write_tree(work, _empty_indexes(),
                    extra_files={"inst/00-isa-design/undi_reserved.S": "nop\n"})
        rc, out = _run(work, reg)
        good_unidx = rc == 1 and "非 id 载体未入索引" in out
        ok = ok and good_unidx
        print(f"  [{'PASS' if good_unidx else 'FAIL'}] self-test case{case_no} "
              f"注入⑳ 非 id 载体未入索引: rc={rc} "
              f"marker={'非 id 载体未入索引' in out}")

        case_no += 1
        work = tmpdir / f"case{case_no}"
        idx = dict(_empty_indexes())
        idx["inst"] = ent + VALID_ASM_ENTRY.replace(
            "inst/01-load-store/add.S", "inst/00-isa-design/extra.S")
        _write_tree(work, idx,
                    extra_files={"inst/00-isa-design/undi_reserved.S": "nop\n",
                                 "inst/00-isa-design/extra.S": "nop\n"})
        rc, out = _run(work, reg)
        good_unset = rc == 1 and "NON-ID CARRIER UNSET" in out
        ok = ok and good_unset
        print(f"  [{'PASS' if good_unset else 'FAIL'}] self-test case{case_no} "
              f"注入㉑ 同目录未登记 .S: rc={rc} "
              f"marker={'NON-ID CARRIER UNSET' in out}")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    print("-" * 72)
    print(f"self-test: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", type=Path, default=None,
                    help="检查另一棵树（默认仓库根）")
    ap.add_argument("--self-test", action="store_true", help="跑内置注入自检")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    root = args.root.resolve() if args.root else ROOT
    if not root.is_dir():
        print(f"check-tests-index: ERROR: --root 不存在: {root}", file=sys.stderr)
        return 1
    return audit(root)


if __name__ == "__main__":
    raise SystemExit(main())
