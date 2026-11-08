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


def audit(root: Path) -> int:
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
  file: inst/base/add.yaml
  platforms: [system]
  level: smoke
  requires: []
"""


def _run(root: Path) -> tuple[int, str]:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = audit(root)
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
             extra_files={"inst/base/add.yaml": "# demo\n"}, expect_rc=0)

        # 注入①：ID 重复
        dup = dict(good)
        dup["inst"] = VALID_ENTRY + VALID_ENTRY
        case("注入① ID 重复", dup, "重复",
             extra_files={"inst/base/add.yaml": "# demo\n"})

        # 注入②：file 不存在
        bad = dict(_empty_indexes())
        bad["inst"] = VALID_ENTRY.replace("inst/base/add.yaml", "inst/base/nope.yaml")
        case("注入② file 不存在", bad, "不存在")

        # 注入③：platforms 非法
        bad = dict(good)
        bad["inst"] = VALID_ENTRY.replace("[system]", "[windows]")
        case("注入③ platforms 非法", bad, "platforms",
             extra_files={"inst/base/add.yaml": "# demo\n"})

        # 注入④：level 非法
        bad = dict(good)
        bad["inst"] = VALID_ENTRY.replace("level: smoke", "level: quick")
        case("注入④ level 非法", bad, "level",
             extra_files={"inst/base/add.yaml": "# demo\n"})

        # 注入⑤：ID 前缀与索引 scope 不一致
        bad = dict(good)
        bad["inst"] = VALID_ENTRY.replace("id: inst-base-001", "id: arch-base-001")
        case("注入⑤ ID 前缀错配", bad, "前缀",
             extra_files={"inst/base/add.yaml": "# demo\n"})

        # 注入⑥：缺字段
        bad = dict(good)
        bad["inst"] = VALID_ENTRY.replace("  requires: []\n", "")
        case("注入⑥ 缺字段", bad, "缺字段",
             extra_files={"inst/base/add.yaml": "# demo\n"})

        # 注入⑦：未知字段
        bad = dict(good)
        bad["inst"] = VALID_ENTRY + "  owner: nobody\n"
        case("注入⑦ 未知字段", bad, "未知字段",
             extra_files={"inst/base/add.yaml": "# demo\n"})

        # 注入⑧：file 不在本 scope 目录
        bad = dict(good)
        bad["inst"] = VALID_ENTRY.replace("inst/base/add.yaml", "arch/base/add.yaml")
        case("注入⑧ file 越 scope", bad, "不在 scope 目录",
             extra_files={"arch/base/add.yaml": "# demo\n"})

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
        bad["inst"] = VALID_ENTRY.replace("inst/base/add.yaml", "inst/base")
        case("注入⑫ file 指向目录", bad, "不是文件",
             extra_files={"inst/base/add.yaml": "# demo\n"})

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
