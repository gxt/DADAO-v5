#!/usr/bin/env python3
"""check_interface_alignment.py — 跨模块接口对齐核对脚本（INTEG-003t）。

机械核对4类接口的一致性：
  1. LLVM MC ELF emitter 字段 ↔ ADR-0003/contract-elf.md 期望值
  2. ADR-0003 ↔ ADR-0004（QEMU 机器常量、双镜像协议）
  3. testcases 向量 schema ↔ QEMU harness 消费的 YAML 字段
  4. opcodes.yaml ↔ LLVM/QEMU 两侧实现（交叉核对）

期望值**内联自 ADR/合约**（脚本里注明来源），不从实现反推。

Exit 0: 全部 PASS
Exit 1: 存在不一致（FAIL）
Exit 2: 脚本内部错误
"""

import glob
import os
import re
import subprocess
import sys

REPO_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))

# ---------------------------------------------------------------------------
# Result tracking
# ---------------------------------------------------------------------------

results: list[tuple[str, str, str, str]] = []
# status: "PASS", "FAIL", "MANUAL"


def record(category: str, item: str, status: str, detail: str = ""):
    results.append((category, item, status, detail))


def load_file(rel_path: str) -> str:
    path = os.path.join(REPO_ROOT, rel_path)
    if not os.path.isfile(path):
        return ""
    with open(path, encoding="utf-8") as f:
        return f.read()


def run_tool(rel_path: str, args: list[str] | None = None) -> tuple[int, str]:
    """Run a Python tool as subprocess, return (exit_code, combined_output)."""
    full = os.path.join(REPO_ROOT, rel_path)
    if not os.path.isfile(full):
        return -1, f"{rel_path} 未找到"
    cmd = [sys.executable, full] + (args or [])
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=60,
                           cwd=REPO_ROOT)
        return r.returncode, (r.stdout + r.stderr).strip()
    except subprocess.TimeoutExpired:
        return -1, "超时"
    except Exception as e:
        return -1, str(e)


# ---------------------------------------------------------------------------
# Category 1: LLVM MC ELF emitter fields ↔ ADR-0003/contract-elf.md
# ---------------------------------------------------------------------------

def check_elf_fields():
    cat = "1.ELF"

    patches_dir = os.path.join(REPO_ROOT, "components", "llvm-project", "patches")
    patch_content = ""
    for pf in sorted(glob.glob(os.path.join(patches_dir, "*.patch"))):
        with open(pf, encoding="utf-8") as f:
            patch_content += f.read()

    # --- e_machine = EM_DADAO = 0x0DA0 ---
    # Source: ADR-0003 §D1, contract-elf.md §1.1
    expected_em = 0x0DA0
    em_pattern = re.compile(r'EM_DADAO\s*=\s*(0x[0-9a-fA-F]+)')
    em_match = em_pattern.search(patch_content)
    if em_match:
        actual = int(em_match.group(1), 16)
        if actual == expected_em:
            record(cat, "e_machine=EM_DADAO=0x0DA0", "PASS",
                   f"LLVM patch: {hex(actual)}")
        else:
            record(cat, "e_machine=EM_DADAO=0x0DA0", "FAIL",
                   f"期望 0x{expected_em:X}, 实际 {hex(actual)}")
    else:
        record(cat, "e_machine=EM_DADAO=0x0DA0", "FAIL",
               "LLVM patch 未找到 EM_DADAO 定义")

    # --- EI_CLASS = ELFCLASS64 (Is64Bit_=true) ---
    # Source: ADR-0003 §D1, contract-elf.md §1.1
    if "Is64Bit_=*/true" in patch_content:
        record(cat, "EI_CLASS=ELFCLASS64(2)", "PASS",
               "MCELFObjectTargetWriter(Is64Bit_=true,...)")
    else:
        record(cat, "EI_CLASS=ELFCLASS64(2)", "FAIL",
               "未找到 Is64Bit_=true")

    # --- EI_DATA = ELFDATA2MSB (IsLittleEndian=false) ---
    # Source: ADR-0003 §D1, contract-elf.md §1.1
    if "IsLittleEndian = false" in patch_content:
        record(cat, "EI_DATA=ELFDATA2MSB(2)", "PASS",
               "DADAOMCAsmInfo: IsLittleEndian = false")
    else:
        record(cat, "EI_DATA=ELFDATA2MSB(2)", "FAIL",
               "未找到 IsLittleEndian = false")

    # --- EI_OSABI = ELFOSABI_NONE (0) ---
    # Source: ADR-0003 §D1, contract-elf.md §1.1
    if "ELFOSABI_NONE" in patch_content:
        record(cat, "EI_OSABI=ELFOSABI_NONE(0)", "PASS",
               "createDadaoELFObjectWriter(ELF::ELFOSABI_NONE)")
    else:
        record(cat, "EI_OSABI=ELFOSABI_NONE(0)", "FAIL",
               "未找到 ELFOSABI_NONE")

    # --- e_flags = 0x00000001 (真取值比对) ---
    # Source: ADR-0003 §D1, contract-elf.md §1.3
    # bits 0–7=版本号(M1=1), bits 8–31=0
    # 两种实现路径均有效：
    #   (a) getEFlags() override 返回常量
    #   (b) setELFHeaderEFlags(CONST) 通过 TargetELFStreamer
    #
    # 只在 diff 的 '+' 新增非注释代码行里搜索（排除 mail header / commit
    # message / '+++' 文件头行 / C/C++ 注释行），避免 commit message 或
    # 注释中的字面量造成假阳性/假阴性。
    EXPECTED_E_FLAGS = 0x00000001
    actual = None
    method = ""

    def _is_comment(s: str) -> bool:
        """判断一行是否为 C/C++ 注释行（行首去空白后以注释标记开头）。"""
        s = s.strip()
        return (s.startswith("//") or s.startswith("/*")
                or s.startswith("*") or s.startswith("*/"))

    # 提取 diff '+' 非注释代码行（排除 '+++' 文件头行、注释行）
    # 用于 setELFHeaderEFlags / getEFlags 调用搜索和常量定义回查。
    code_lines = "\n".join(
        ln[1:] for ln in patch_content.splitlines()
        if (ln.startswith("+")
            and not ln.startswith("+++")
            and not _is_comment(ln[1:]))
    )

    # 所有 '+' 行（含注释），仅用于不涉及常量值比对的简单存在性检查
    # （本函数不使用，保留供未来扩展；当前全部搜索均在 code_lines 中）

    # 路径 (a): 搜索 getEFlags 函数体中的 return 语句（仅在非注释代码行中）
    geteflags_pattern = re.compile(
        r'getEFlags\s*\(\s*\)[^{]*\{[^}]*return\s+(0x[0-9a-fA-F]+|\d+)\s*;',
        re.DOTALL
    )
    m = geteflags_pattern.search(code_lines)
    if m:
        raw = m.group(1)
        actual = int(raw, 16) if raw.startswith("0x") or raw.startswith("0X") else int(raw)
        method = f"getEFlags() 返回 {hex(actual)}"

    # 路径 (b): 搜索 setELFHeaderEFlags 调用（仅在非注释代码行中）
    if actual is None:
        seteflags_pattern = re.compile(
            r'setELFHeaderEFlags\s*\(\s*([A-Za-z_]\w*|0x[0-9a-fA-F]+|\d+)\s*\)'
        )
        m2 = seteflags_pattern.search(code_lines)
        if m2:
            arg = m2.group(1)
            # 数字字面量直接解析；标识符须回查同一 patch 代码内的常量定义
            if arg.startswith("0x") or arg.startswith("0X") or arg.isdigit():
                actual = int(arg, 16) if arg.startswith("0x") or arg.startswith("0X") else int(arg)
                method = f"setELFHeaderEFlags({hex(actual)})"
            else:
                # 标识符：在非注释代码行中查找其常量定义
                const_pat = re.compile(
                    rf'\b{re.escape(arg)}\s*=\s*(0x[0-9a-fA-F]+|\d+)\s*;'
                )
                m3 = const_pat.search(code_lines)
                if m3:
                    raw = m3.group(1)
                    actual = int(raw, 16) if raw.startswith("0x") or raw.startswith("0X") else int(raw)
                    method = f"setELFHeaderEFlags({arg}={hex(actual)})"
                else:
                    method = f"setELFHeaderEFlags({arg}=未解析)"

    if actual is not None:
        if actual == EXPECTED_E_FLAGS:
            record(cat, "e_flags=0x00000001", "PASS", method)
        else:
            record(cat, "e_flags=0x00000001", "FAIL",
                   f"{method}，期望 0x{EXPECTED_E_FLAGS:X}（ADR-0003 §D1）")
    else:
        # 未设置 ⇒ LLVM 默认 e_flags = 0
        record(cat, "e_flags=0x00000001", "FAIL",
               "LLVM patch 未设置 e_flags（未找到 getEFlags() 或 "
               "setELFHeaderEFlags()），默认为 0 "
               "（ADR-0003 §D1 要求 0x00000001）")


# ---------------------------------------------------------------------------
# Category 2: ADR-0003 ↔ ADR-0004 (QEMU machine constants)
# ---------------------------------------------------------------------------

def check_adr_alignment():
    cat = "2.ADR"

    patches_dir = os.path.join(REPO_ROOT, "components", "qemu", "patches")
    patch_content = ""
    for pf in sorted(glob.glob(os.path.join(patches_dir, "*.patch"))):
        with open(pf, encoding="utf-8") as f:
            patch_content += f.read()

    # --- Machine name = "dadao-m1" ---
    # Source: ADR-0004 §D2.3
    if 'MACHINE_TYPE_NAME("dadao-m1")' in patch_content:
        record(cat, 'machine_name="dadao-m1"', "PASS",
               'MACHINE_TYPE_NAME("dadao-m1")')
    else:
        record(cat, 'machine_name="dadao-m1"', "FAIL",
               "QEMU patch 未找到 dadao-m1 机器名定义")

    # --- RAM base = 0xffff_0000_0000, size = 16 MiB ---
    # Source: ADR-0004 §D1
    ram_base_exp = 0xFFFF_0000_0000
    ram_size_exp = 16 * 1024 * 1024
    ram_base_match = re.search(r'DADAO_RAM_BASE\s+(0x[0-9a-fA-F]+)', patch_content)
    ram_size_match = re.search(r'DADAO_RAM_SIZE\s+\((\d+\s*\*\s*\d+\s*\*\s*\d+)\)', patch_content)
    if ram_base_match:
        actual = int(ram_base_match.group(1), 16)
        if actual == ram_base_exp:
            record(cat, f"RAM_BASE=0x{ram_base_exp:X}", "PASS",
                   f"QEMU: DADAO_RAM_BASE = {hex(actual)}")
        else:
            record(cat, f"RAM_BASE=0x{ram_base_exp:X}", "FAIL",
                   f"期望 0x{ram_base_exp:X}, 实际 {hex(actual)}")
    else:
        record(cat, f"RAM_BASE=0x{ram_base_exp:X}", "FAIL",
               "QEMU patch 未找到 DADAO_RAM_BASE")

    if ram_size_match:
        actual = 1
        for f in ram_size_match.group(1).split("*"):
            actual *= int(f.strip())
        if actual == ram_size_exp:
            record(cat, "RAM_SIZE=16MiB", "PASS",
                   f"QEMU: DADAO_RAM_SIZE = {actual} ({actual // (1024*1024)} MiB)")
        else:
            record(cat, "RAM_SIZE=16MiB", "FAIL",
                   f"期望 {ram_size_exp}, 实际 {actual}")
    else:
        record(cat, "RAM_SIZE=16MiB", "FAIL",
               "QEMU patch 未找到 DADAO_RAM_SIZE")

    # --- Exit port base = 0xffff_8000_0000, size = 8 ---
    # Source: ADR-0004 §D3
    exit_base_exp = 0xFFFF_8000_0000
    exit_size_exp = 8
    exit_base_match = re.search(r'DADAO_EXIT_PORT_BASE\s+(0x[0-9a-fA-F]+)', patch_content)
    exit_size_match = re.search(r'DADAO_EXIT_PORT_SIZE\s+(\d+)', patch_content)
    if exit_base_match:
        actual = int(exit_base_match.group(1), 16)
        if actual == exit_base_exp:
            record(cat, f"EXIT_PORT_BASE=0x{exit_base_exp:X}", "PASS",
                   f"QEMU: DADAO_EXIT_PORT_BASE = {hex(actual)}")
        else:
            record(cat, f"EXIT_PORT_BASE=0x{exit_base_exp:X}", "FAIL",
                   f"期望 0x{exit_base_exp:X}, 实際 {hex(actual)}")
    else:
        record(cat, f"EXIT_PORT_BASE=0x{exit_base_exp:X}", "FAIL",
               "QEMU patch 未找到 DADAO_EXIT_PORT_BASE")

    if exit_size_match:
        actual = int(exit_size_match.group(1))
        if actual == exit_size_exp:
            record(cat, "EXIT_PORT_SIZE=8", "PASS",
                   f"QEMU: DADAO_EXIT_PORT_SIZE = {actual}")
        else:
            record(cat, "EXIT_PORT_SIZE=8", "FAIL",
                   f"期望 {exit_size_exp}, 实際 {actual}")
    else:
        record(cat, "EXIT_PORT_SIZE=8", "FAIL",
               "QEMU patch 未找到 DADAO_EXIT_PORT_SIZE")

    # --- Boot ROM base = 0xffff_ffff_0000, size = 64 KiB ---
    # Source: ADR-0004 §D1
    rom_base_exp = 0xFFFF_FFFF_0000
    rom_size_exp = 64 * 1024
    rom_base_match = re.search(r'DADAO_ROM_BASE\s+(0x[0-9a-fA-F]+)', patch_content)
    rom_size_match = re.search(r'DADAO_ROM_SIZE\s+\((\d+\s*\*\s*\d+)\)', patch_content)
    if rom_base_match:
        actual = int(rom_base_match.group(1), 16)
        if actual == rom_base_exp:
            record(cat, f"ROM_BASE=0x{rom_base_exp:X}", "PASS",
                   f"QEMU: DADAO_ROM_BASE = {hex(actual)}")
        else:
            record(cat, f"ROM_BASE=0x{rom_base_exp:X}", "FAIL",
                   f"期望 0x{rom_base_exp:X}, 实際 {hex(actual)}")
    else:
        record(cat, f"ROM_BASE=0x{rom_base_exp:X}", "FAIL",
               "QEMU patch 未找到 DADAO_ROM_BASE")

    if rom_size_match:
        actual = 1
        for f in rom_size_match.group(1).split("*"):
            actual *= int(f.strip())
        if actual == rom_size_exp:
            record(cat, "ROM_SIZE=64KiB", "PASS",
                   f"QEMU: DADAO_ROM_SIZE = {actual} ({actual // 1024} KiB)")
        else:
            record(cat, "ROM_SIZE=64KiB", "FAIL",
                   f"期望 {rom_size_exp}, 实際 {actual}")
    else:
        record(cat, "ROM_SIZE=64KiB", "FAIL",
               "QEMU patch 未找到 DADAO_ROM_SIZE")

    # --- Dual image: -bios + -kernel (MANUAL — 宽泛语义匹配) ---
    # Source: ADR-0004 §D2.3
    # 判定标准：QEMU 在缺少 -bios 或 -kernel 时报错退出
    has_bios_err = "bios rom.bin is required" in patch_content or \
                   "bios is required" in patch_content.lower()
    has_kernel_err = "kernel test.bin is required" in patch_content or \
                     "kernel is required" in patch_content.lower()
    if has_bios_err and has_kernel_err:
        record(cat, "dual_image_bios_kernel", "PASS",
               "QEMU 缺少 -bios/-kernel 时报错退出")
    else:
        record(cat, "dual_image_bios_kernel", "FAIL",
               "QEMU patch 未找到缺少 -bios/-kernel 时的报错退出逻辑")

    # --- Exit code mapping: fault codes ---
    # Source: ADR-0004 §D5.8
    expected_fault_codes = {
        "PASS": 0x00,
        "UNMAPPED": 0x87,
        "ILLI": 0x88,
        "UNDI": 0x89,
        "RASOF": 0x8A,
        "RASUF": 0x8B,
        "MALIGN": 0x8C,
        "IALIGN": 0x8D,
    }
    for name, code in expected_fault_codes.items():
        pattern = re.compile(rf'DADAO_EXIT_{name}\s*=\s*(0x[0-9a-fA-F]+|\d+)')
        m = pattern.search(patch_content)
        if m:
            raw = m.group(1)
            actual = int(raw, 16) if raw.startswith("0x") else int(raw)
            if actual == code:
                record(cat, f"EXIT_{name}=0x{code:02X}", "PASS",
                       f"QEMU: DADAO_EXIT_{name} = 0x{actual:02X}")
            else:
                record(cat, f"EXIT_{name}=0x{code:02X}", "FAIL",
                       f"期望 0x{code:02X}, 实際 0x{actual:02X}")
        else:
            record(cat, f"EXIT_{name}=0x{code:02X}", "FAIL",
                   f"QEMU patch 未找到 DADAO_EXIT_{name}")

    # --- RESET_PC = ROM_BASE ---
    # Source: ADR-0004 §D2.1
    reset_match = re.search(r'DADAO_RESET_PC\s+(\S+)', patch_content)
    if reset_match:
        val = reset_match.group(1).strip()
        if val == "DADAO_ROM_BASE":
            record(cat, "RESET_PC=ROM_BASE", "PASS",
                   f"DADAO_RESET_PC = DADAO_ROM_BASE (= 0x{rom_base_exp:X})")
        else:
            record(cat, "RESET_PC=ROM_BASE", "FAIL",
                   f"DADAO_RESET_PC = {val}, 期望 DADAO_ROM_BASE")
    else:
        record(cat, "RESET_PC=ROM_BASE", "FAIL",
               "QEMU patch 未找到 DADAO_RESET_PC")

    # --- Harness constants (build_test_binary.py) ---
    # Source: ADR-0004 §D1
    harness_content = load_file("tests/scripts/build_test_binary.py")
    if harness_content:
        h_binary_match = re.search(r'BINARY_BASE\s*=\s*(0x[0-9a-fA-F_]+)', harness_content)
        h_exit_match = re.search(r'EXIT_PORT\s*=\s*(0x[0-9a-fA-F_]+)', harness_content)
        if h_binary_match:
            actual = int(h_binary_match.group(1).replace("_", ""), 16)
            if actual == ram_base_exp:
                record(cat, "harness.BINARY_BASE=RAM_BASE", "PASS",
                       f"build_test_binary.py: BINARY_BASE = 0x{actual:X}")
            else:
                record(cat, "harness.BINARY_BASE=RAM_BASE", "FAIL",
                       f"期望 0x{ram_base_exp:X}, 实際 0x{actual:X}")
        if h_exit_match:
            actual = int(h_exit_match.group(1).replace("_", ""), 16)
            if actual == exit_base_exp:
                record(cat, "harness.EXIT_PORT=EXIT_PORT_BASE", "PASS",
                       f"build_test_binary.py: EXIT_PORT = 0x{actual:X}")
            else:
                record(cat, "harness.EXIT_PORT=EXIT_PORT_BASE", "FAIL",
                       f"期望 0x{exit_base_exp:X}, 实際 0x{actual:X}")

    # --- Harness fault code mapping (run_qemu_test.py) ---
    # Source: ADR-0004 §D5.8
    harness_run_content = load_file("tests/scripts/run_qemu_test.py")
    if harness_run_content:
        h_fault_match = re.search(r'FAULT_NAMES\s*=\s*\{([^}]+)\}', harness_run_content, re.DOTALL)
        if h_fault_match:
            fault_text = h_fault_match.group(1)
            harness_faults = {}
            for m in re.finditer(r'(0x[0-9a-fA-F]+)\s*:\s*"(\w+)"', fault_text):
                harness_faults[m.group(2)] = int(m.group(1), 16)
            for name, code in expected_fault_codes.items():
                if name == "PASS":
                    continue
                if name in harness_faults:
                    if harness_faults[name] == code:
                        record(cat, f"harness.{name}=0x{code:02X}", "PASS",
                               f"run_qemu_test.py: {name} = 0x{harness_faults[name]:02X}")
                    else:
                        record(cat, f"harness.{name}=0x{code:02X}", "FAIL",
                               f"期望 0x{code:02X}, 实際 0x{harness_faults[name]:02X}")
                else:
                    record(cat, f"harness.{name}=0x{code:02X}", "FAIL",
                           f"run_qemu_test.py FAULT_NAMES 未包含 {name}")


# ---------------------------------------------------------------------------
# Category 3: testcases vector schema ↔ QEMU harness
# ---------------------------------------------------------------------------

def check_schema_harness():
    cat = "3.Schema"

    schema_content = load_file("tests/vectors/schema.md")
    harness_build = load_file("tests/scripts/build_test_binary.py")
    harness_run = load_file("tests/scripts/run_qemu_test.py")

    if not schema_content:
        record(cat, "schema.md 存在", "FAIL", "tests/vectors/schema.md 未找到")
        return
    record(cat, "schema.md 存在", "PASS", "")

    # --- Schema 字段定义 ---
    required_fields = [
        "mnemonic", "insn", "format", "class", "encoding",
        "input_state", "spec_cite",
    ]
    optional_fields = [
        "expected_state", "expected_pc", "expected_fault",
        "status", "deferred_reason", "notes",
    ]
    for field in required_fields + optional_fields:
        if f"| `{field}`" in schema_content or f"|`{field}`" in schema_content:
            record(cat, f"schema 定义 {field}", "PASS", "")
        else:
            record(cat, f"schema 定义 {field}", "FAIL",
                   f"schema.md 中未找到字段 {field}")

    # --- Harness 精确消费模式比对 ---
    # 每个字段对应 harness 中的实际读取模式（case.get("X") / case["X"]）
    # 如果 harness 中不存在该精确模式 → FAIL（schema↔harness 契约断裂）
    harness_fields = {
        # field: (精确正则, 来源文件内容, 说明)
        "encoding.word": (
            r'''(?:case|vector_case)\[["']encoding["']\]\[["']word["']\]''',
            harness_build, "build_test_binary.py: case[\"encoding\"][\"word\"]"
        ),
        "mnemonic": (
            r'''(?:case|vector_case)\.get\(["']mnemonic["']''',
            harness_build + harness_run, "harness: case.get(\"mnemonic\")"
        ),
        "input_state": (
            r'''(?:case|vector_case)\.get\(["']input_state["']''',
            harness_build, "build_test_binary.py: case.get(\"input_state\")"
        ),
        "input_state.rd": (
            r'''input_state\.get\(["']rd["']\)''',
            harness_build, "build_test_binary.py: input_state.get(\"rd\")"
        ),
        "input_state.rb": (
            r'''input_state\.get\(["']rb["']\)''',
            harness_build, "build_test_binary.py: input_state.get(\"rb\")"
        ),
        "input_state.ra": (
            r'''input_state\.get\(["']ra["']\)''',
            harness_build, "build_test_binary.py: input_state.get(\"ra\")"
        ),
        "input_state.memory": (
            r'''input_state\.get\(["']memory["']\)''',
            harness_build, "build_test_binary.py: input_state.get(\"memory\")"
        ),
        "expected_state": (
            r'''(?:case|vector_case)\.get\(["']expected_state["']''',
            harness_build, "build_test_binary.py: case.get(\"expected_state\")"
        ),
        "expected_fault": (
            r'''(?:case|vector_case)\.get\(["']expected_fault["']''',
            harness_build + harness_run, "harness: case.get(\"expected_fault\")"
        ),
        "expected_pc": (
            r'''(?:case|vector_case)\.get\(["']expected_pc["']''',
            harness_build, "build_test_binary.py: case.get(\"expected_pc\")"
        ),
        "status": (
            r'''(?:case|vector_case)\.get\(["']status["']''',
            harness_run, "run_qemu_test.py: case.get(\"status\")"
        ),
        "class": (
            r'''(?:case|vector_case)\.get\(["']class["']''',
            harness_run, "run_qemu_test.py: case.get(\"class\")"
        ),
        "insn": (
            r'''(?:case|vector_case)\.get\(["']insn["']''',
            harness_run, "run_qemu_test.py: case.get(\"insn\")"
        ),
    }
    for field, (pattern, content, desc) in harness_fields.items():
        if re.search(pattern, content):
            record(cat, f"harness 消费 {field}", "PASS", desc)
        else:
            record(cat, f"harness 消费 {field}", "FAIL",
                   f"未在 harness 中找到精确消费模式: {desc}")

    # --- encoding sub-fields ---
    for sf in ("word", "reserved"):
        if f"encoding.{sf}" in schema_content or f"`{sf}`" in schema_content:
            record(cat, f"schema 定义 encoding.{sf}", "PASS", "")
        else:
            record(cat, f"schema 定义 encoding.{sf}", "FAIL",
                   f"schema.md 中未找到 encoding.{sf}")

    # --- fault type definitions ---
    for ft in ("ILLI", "UNDI", "MALIGN", "IALIGN", "RASOF", "RASUF", "UNMAPPED"):
        if ft in schema_content:
            record(cat, f"schema 定义 fault {ft}", "PASS", "")
        else:
            record(cat, f"schema 定义 fault {ft}", "FAIL",
                   f"schema.md 中未找到 fault 类型 {ft}")

    # --- class definitions ---
    for cls in ("encoding", "legality", "semantic", "boundary", "overlap"):
        if cls in schema_content:
            record(cat, f"schema 定义 class {cls}", "PASS", "")
        else:
            record(cat, f"schema 定义 class {cls}", "FAIL",
                   f"schema.md 中未找到 class {cls}")


# ---------------------------------------------------------------------------
# Category 4: opcodes.yaml ↔ LLVM/QEMU (真跨模块交叉核对)
# ---------------------------------------------------------------------------

def check_opcodes_cross():
    cat = "4.Opcodes"

    opcodes_path = os.path.join(REPO_ROOT, "contracts", "opcodes.yaml")
    if not os.path.isfile(opcodes_path):
        record(cat, "opcodes.yaml 存在", "FAIL", "contracts/opcodes.yaml 未找到")
        return
    record(cat, "opcodes.yaml 存在", "PASS", "")

    try:
        import yaml as _yaml
    except ImportError:
        record(cat, "PyYAML 可用", "FAIL", "需要 PyYAML")
        return

    with open(opcodes_path, encoding="utf-8") as f:
        records = _yaml.safe_load(f)

    # --- opcodes.yaml 条目数（真断言：期望 256 总计 / 178 M1） ---
    # Source: contracts/opcodes.yaml 结构约定
    total = len(records)
    m1_count = sum(1 for r in records if not r.get("excluded_m1", False))
    EXPECTED_TOTAL = 256
    EXPECTED_M1 = 178
    if total == EXPECTED_TOTAL and m1_count == EXPECTED_M1:
        record(cat, "opcodes.yaml 条目数", "PASS",
               f"总计 {total}, M1 内 {m1_count}")
    else:
        record(cat, "opcodes.yaml 条目数", "FAIL",
               f"期望 总计{EXPECTED_TOTAL}/M1{EXPECTED_M1}，"
               f"实际 总计{total}/M1{m1_count}")

    # --- 结构完整性 ---
    missing = []
    for i, rec in enumerate(records):
        for key in ("insn", "mnemonic", "format", "op", "mask", "value"):
            if key not in rec:
                missing.append(f"  [{i}] {rec.get('insn','?')}: 缺少 {key}")
    if missing:
        record(cat, "opcodes.yaml 结构完整性", "FAIL", "\n".join(missing[:5]))
    else:
        record(cat, "opcodes.yaml 结构完整性", "PASS",
               f"全部 {total} 条均有 insn/mnemonic/format/op/mask/value")

    # --- 内部 mask/value 自洽 ---
    mask_errors = []
    for i, rec in enumerate(records):
        mask = int(rec["mask"], 16)
        value = int(rec["value"], 16)
        if (value & mask) != value:
            mask_errors.append(
                f"  [{i}] {rec['insn']}: (value & mask) != value "
                f"(0x{value:08X} & 0x{mask:08X} = 0x{value & mask:08X})"
            )
    if mask_errors:
        record(cat, "mask/value 内部自洽", "FAIL", "\n".join(mask_errors[:5]))
    else:
        record(cat, "mask/value 内部自洽", "PASS",
               f"全部 {total} 条 (value & mask) == value")

    # --- 真跨模块交叉：LLVM lit 字节 ↔ opcodes.yaml ---
    # 调用 check_lit_bytes.py，其比对 # OBJ: 字节 ↔ opcodes.yaml mask/value
    rc, out = run_tool("tools/llvm/check_lit_bytes.py")
    if rc == 0:
        record(cat, "LLVM lit ↔ opcodes.yaml", "PASS", out.split("\n")[0])
    elif rc < 0:
        record(cat, "LLVM lit ↔ opcodes.yaml", "FAIL",
               f"工具运行失败: {out}")
    else:
        record(cat, "LLVM lit ↔ opcodes.yaml", "FAIL", out)

    # --- 真跨模块交叉：QEMU trans_* ↔ opcodes.yaml ---
    # 调用 check_qemu_trans.py --strict
    rc, out = run_tool("tools/qemu/check_qemu_trans.py", ["--strict"])
    if rc == 0:
        record(cat, "QEMU trans ↔ opcodes.yaml", "PASS", out.split("\n")[-1])
    elif rc < 0:
        record(cat, "QEMU trans ↔ opcodes.yaml", "FAIL",
               f"工具运行失败: {out}")
    else:
        record(cat, "QEMU trans ↔ opcodes.yaml", "FAIL", out)

    # --- LLVM lit pattern 数量（真断言：期望 53） ---
    # Source: tests/lit/MC/Dadao/*.s 中 # OBJ: 行数
    EXPECTED_LIT = 53
    lit_dir = os.path.join(REPO_ROOT, "tests", "lit", "MC", "Dadao")
    if os.path.isdir(lit_dir):
        lit_count = sum(
            1 for sf in glob.glob(os.path.join(lit_dir, "*.s"))
            for line in open(sf) if re.search(r"#\s*OBJ:", line)
        )
        if lit_count == EXPECTED_LIT:
            record(cat, "LLVM lit # OBJ: patterns", "PASS",
                   f"{lit_count} patterns")
        else:
            record(cat, "LLVM lit # OBJ: patterns", "FAIL",
                   f"期望 {EXPECTED_LIT} patterns，实际 {lit_count}")
    else:
        record(cat, "LLVM lit # OBJ: patterns", "FAIL",
               "tests/lit/MC/Dadao/ 目录不存在")

    # --- QEMU trans_* 定义数（真断言：期望 256） ---
    # Source: components/qemu/patches/*.patch 中 trans_* 函数定义数
    EXPECTED_TRANS = 256
    qemu_patches_dir = os.path.join(REPO_ROOT, "components", "qemu", "patches")
    trans_defs = set()
    if os.path.isdir(qemu_patches_dir):
        for pf in sorted(glob.glob(os.path.join(qemu_patches_dir, "*.patch"))):
            with open(pf, encoding="utf-8") as f:
                for line in f:
                    m = re.search(r'static\s+bool\s+(trans_\w+)\s*\(', line)
                    if m:
                        trans_defs.add(m.group(1))
    if len(trans_defs) == EXPECTED_TRANS:
        record(cat, "QEMU trans_* 定义数", "PASS",
               f"{len(trans_defs)} trans_* 函数")
    else:
        record(cat, "QEMU trans_* 定义数", "FAIL",
               f"期望 {EXPECTED_TRANS} trans_*，实际 {len(trans_defs)}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 72)
    print("INTEG-003t: 跨模块接口对齐核对")
    print("=" * 72)
    print()

    check_elf_fields()
    check_adr_alignment()
    check_schema_harness()
    check_opcodes_cross()

    # Print results grouped by category
    print("-" * 72)
    print(f"{'类别':<12} {'检查项':<42} {'判定':<8} {'说明'}")
    print("-" * 72)

    cat_counts: dict[str, dict[str, int]] = {}
    fail_count = manual_count = pass_count = 0

    for cat, item, status, detail in results:
        cc = cat_counts.setdefault(cat, {"PASS": 0, "FAIL": 0, "MANUAL": 0})
        cc[status] = cc.get(status, 0) + 1
        if status == "FAIL":
            fail_count += 1
        elif status == "MANUAL":
            manual_count += 1
        else:
            pass_count += 1
        di = item[:40] + ".." if len(item) > 42 else item
        dd = detail[:60] + ".." if len(detail) > 60 else detail
        print(f"{cat:<12} {di:<42} {status:<8} {dd}")

    print("-" * 72)
    total = len(results)
    print(f"总计: {total} 项 | PASS: {pass_count} | FAIL: {fail_count} | MANUAL: {manual_count}")
    print()
    print("逐类统计:")
    for cat in sorted(cat_counts):
        cc = cat_counts[cat]
        cat_total = sum(cc.values())
        print(f"  {cat}: {cat_total} 项 (PASS={cc.get('PASS',0)} FAIL={cc.get('FAIL',0)} MANUAL={cc.get('MANUAL',0)})")
    print()

    if fail_count > 0:
        print("=== FAIL 项汇总 ===")
        for cat, item, status, detail in results:
            if status == "FAIL":
                print(f"  [{cat}] {item}")
                if detail:
                    print(f"         → {detail}")
        print()
        return 1

    if manual_count > 0:
        print("=== 人工核对项 ===")
        for cat, item, status, detail in results:
            if status == "MANUAL":
                print(f"  [{cat}] {item}: {detail}")
        print()

    print("全部机械可判定项 PASS。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
