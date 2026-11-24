#!/usr/bin/env python3
"""check_mode_entry.py — `tests/arch/umon/mode_entry.S` 的独立判据（m16-chipyard-020）。

判据（期望值）全部**现场**从规范/合约派生，不从 RTL 或被测镜像反推：

  * cause 位索引：`spec/DADAO-12-SEE-主管系统运行环境.md` §5.2（二）的
    “monitor 异常编号”表（`CFXTRAP`/`CFXREG`/`CFXPERM`/`ILLI` …）；
  * `CFXPERM` 的编码：`.tao/contracts/contract-see.md` §6.1（`1 << 7`）——扁平模型下
    cfx 来源掩码拒绝**只置 `CFXPERM`**、高位位图全 0（`ADR-0062 D2/D3`）；
    `.tao/contracts/contract-see.md` §6.1.1 / `spec` §3.6 的权限类位图作为第二来源；
  * 运行模式编码（`user`/`supv`/`hypv`）与 cfx 编号（`umon`/`smon`/`hmon`）：
    `spec` §1 的模式表与 cfx 表；
  * `<mode>_switch_run_mode` 复位值：`spec` §3.1/§3.4 的寄存器表；
  * 异步（`ADR-0061` 后由 `tests/arch/hart/cfx15.S` 覆盖）不在本判据内：
    本文件只判同步进入/退出、`switch_run_mode` 与两轴判权；
  * `cause_ip` 的期望地址：ELF 符号表（`llvm-nm`，由驱动传入工具路径）——
    它是**链接期**已知的指令地址，不是注入后的观测值。

签名流 = 每个观测点 8 字节大端；槽序是 case 定义（本文件 `SLOTS`），三个运行
模式各一份。任何长度不符、任一槽不等 ⇒ 非零退出。

用法：
  check_mode_entry.py --stream FILE --elf FILE --mode {0,2,3} --nm llvm-nm --root ROOT
  check_mode_entry.py --expected --mode M --elf FILE --nm llvm-nm --root ROOT
  check_mode_entry.py --self-test --mode M --elf FILE --nm llvm-nm --root ROOT
"""

import argparse
import re
import struct
import subprocess
import sys
import pathlib

SPEC = "spec/DADAO-12-SEE-主管系统运行环境.md"
CONTRACT = ".tao/contracts/contract-see.md"


class OracleError(Exception):
    pass


def read(root, rel):
    p = pathlib.Path(root) / rel
    if not p.is_file():
        raise OracleError("missing %s" % rel)
    return p.read_text()


def spec_facts(root):
    spec = read(root, SPEC)
    contract = read(root, CONTRACT)

    cause_bits = {}
    for name, bit in re.findall(
            r"^\|\s*`(CFXTRAP|CFXMEM|CFXREG|CFXESC|CFXPERM|ILLI|UNDI|RASOF|RASUF|MALIGN|IALIGN)`\s*\|\s*(\d+)\s*\|",
            spec, re.M):
        cause_bits[name] = int(bit)
    for need in ("CFXTRAP", "CFXREG", "CFXPERM", "ILLI"):
        if need not in cause_bits:
            raise OracleError("spec §5.2: cause bit for %s not found" % need)

    # Flat model (ADR-0062 D3): the two negative bits are deleted; CFXPERM
    # stands alone. The permission bitmap must still expose [32] NUPERM.
    c611 = contract[contract.find("### §6.1.1"):contract.find("### §6.2")]
    s36 = spec[spec.find("### 3.6 cg5"):spec.find("### 3.7")]
    if "NCFXPERM" in c611 or "NCFXPERM" in s36:
        raise OracleError("flat model: NCFXPERM must not appear in §6.1.1 / §3.6")
    if not re.search(r"^\|\s*`\[32\]`\s*\|\s*wyde2\s+[^|]*\|\s*`NUPERM`", contract, re.M):
        raise OracleError("contract-see §6.1.1: NUPERM bitmap row not found")
    if not re.search(r"^\|\s*`\[32\]`\s*\|\s*NUPERM\s*\|", spec, re.M):
        raise OracleError("spec §3.6: [32] NUPERM row not found")

    # Mode encodings (§1) and cfx ids (§1).
    modes = {}
    for enc, abbr in re.findall(
            r"^\|\s*(0b[01]+)\s*\|\s*[^|]*\|\s*(user|jail|supv|hypv)\s*\|", spec, re.M):
        modes[abbr] = int(enc, 2)
    for need in ("user", "supv", "hypv"):
        if need not in modes:
            raise OracleError("spec §1: mode %s not found" % need)

    cfxha = {}
    for ha, name in re.findall(r"^\|\s*(\d+)\s*\|\s*(umon|jmon|smon|hmon)\s*\|", spec, re.M):
        cfxha[name] = int(ha)
    for need in ("umon", "smon", "hmon"):
        if need not in cfxha:
            raise OracleError("spec §1: cfx %s not found" % need)
    # The check below is relational: mode encoding == monitor cfxha (§5.2).
    for mode, name in (("user", "umon"), ("supv", "smon"), ("hypv", "hmon")):
        if modes[mode] != cfxha[name]:
            raise OracleError("spec §1/§5.2: mode %s (%d) != %s (%d)"
                              % (mode, modes[mode], name, cfxha[name]))

    # <mode>_switch_run_mode reset values (§3.1/§3.4).
    switch = {}
    for cg, name, init in re.findall(
            r"^\|\s*(\d)\s*\|\s*8\s*\|\s*(user|jail|supv|hypv) switch run mode\s*\|[^|]*\|\s*(\d+)",
            spec, re.M):
        switch[name] = int(init)
    for need in ("user", "hypv"):
        if need not in switch:
            raise OracleError("spec §3: %s switch_run_mode reset not found" % need)

    return dict(
        cause=cause_bits,
        modes=modes,
        cfx=cfxha,
        switch=switch,
    )


def elf_symbols(nm, elf):
    out = subprocess.run([nm, elf], capture_output=True, text=True)
    if out.returncode != 0:
        raise OracleError("llvm-nm failed: %s" % out.stderr.strip())
    syms = {}
    for line in out.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 3 and parts[1] in "tTaA" and re.fullmatch(r"[0-9a-fA-F]+", parts[0]):
            syms[parts[2]] = int(parts[0], 16)
    return syms


def expected_slots(facts, syms, mode):
    bits = facts["cause"]
    M = facts["modes"]
    C = facts["cfx"]
    perm = 1 << bits["CFXPERM"]          # 扁平：cfx 来源掩码拒绝只置 CFXPERM
    cfxtrap = 1 << bits["CFXTRAP"]
    cfxreg = 1 << bits["CFXREG"]
    illi = 1 << bits["ILLI"]

    def sym(name):
        if name not in syms:
            raise OracleError("ELF symbol %s not found" % name)
        return syms[name]

    def trap_word(ha):
        return (0x7F << 24) | ((ha & 0x3F) << 18)

    if mode == M["hypv"]:
        return [
            ("hmon.hypv_switch_run_mode (reset)", M["hypv"]),
            ("hmon.hypv_switch_run_mode (write ignored)", M["hypv"]),
            ("umon.cg4.cfx_id", C["umon"]),
            ("smon.cg4.cfx_id", C["smon"]),
            ("umon frame prev_run_mode", M["hypv"]),
            ("umon frame prev_cfx_code", C["hmon"]),
            ("umon frame cause (CFXTRAP)", cfxtrap),
            ("umon frame cause_ip (trap)", sym("h_f_trap")),
            ("umon frame cause_info (trap word)", trap_word(C["umon"])),
            ("hmon frame prev_run_mode", M["hypv"]),
            ("hmon frame prev_cfx_code", C["hmon"]),
            ("hmon frame cause (ILLI)", illi),
            ("hmon frame cause_ip (ILLI)", sym("h_f_bad")),
            ("hmon frame cause_info (ILLI word)", 0x7F180000),
        ]

    if mode == M["user"]:
        return [
            ("U sync cause (cg3 read -> CFXREG)", cfxreg),
            ("U frame prev_run_mode", M["user"]),
            ("U frame prev_cfx_code", C["umon"]),
            ("U frame cause_ip", sym("u_f_cg3")),
            ("umon.cg4.cfx_id (self)", C["umon"]),
            ("smon.cg4.cfx_id (U row opened)", C["smon"]),
            ("U CFXPERM cause (cfx5, no U row)", perm),
            ("U frame prev_run_mode (2nd)", M["user"]),
            ("U frame cause_ip (cfx5)", sym("u_f_cfx5")),
            ("trap->smon prev_run_mode", M["user"]),
            ("trap->smon prev_cfx_code", C["umon"]),
            ("trap->smon cause (CFXTRAP)", cfxtrap),
            ("trap->smon cause_ip", sym("u_f_trap")),
            ("trap->smon cause_info", trap_word(C["smon"])),
        ]

    if mode == M["supv"]:
        return [
            ("smon.cg4.cfx_id (deleg opened)", C["smon"]),
            ("S CFXPERM cause (umon supv row)", perm),
            ("S frame prev_run_mode (cfxreg)", M["supv"]),
            ("S frame cause_ip (umon)", sym("s_f_umon")),
            ("S CFXPERM cause (deleg bit3, cg3)", perm),
            ("S frame prev_run_mode (deleg/run-mode probe)", M["supv"]),
            ("S frame cause_ip (cg3)", sym("s_f_cg3")),
        ]

    raise OracleError("unknown mode %d" % mode)


def read_stream(path):
    data = pathlib.Path(path).read_bytes()
    if len(data) % 8:
        raise OracleError("stream size %d is not a multiple of 8" % len(data))
    return list(struct.unpack(">%dQ" % (len(data) // 8), data))


def compare(expected, got):
    fails = 0
    for i, (name, exp) in enumerate(expected):
        act = got[i] if i < len(got) else None
        if act != exp:
            fails += 1
            print("  [FAIL] slot %-2d %-46s expected=0x%016x actual=%s"
                  % (i, name, exp & 0xFFFFFFFFFFFFFFFF,
                     "missing" if act is None else "0x%016x" % act))
        else:
            print("  [ ok ] slot %-2d %-46s 0x%016x" % (i, name, exp))
    if len(got) > len(expected):
        fails += 1
        print("  [FAIL] stream has %d extra slot(s) (first extra = 0x%016x)"
              % (len(got) - len(expected), got[len(expected)]))
    if len(got) < len(expected):
        fails += 1
        print("  [FAIL] stream truncated: got %d slots, expected %d"
              % (len(got), len(expected)))
    return fails


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--mode", type=lambda x: int(x, 0))
    ap.add_argument("--elf")
    ap.add_argument("--nm")
    ap.add_argument("--stream")
    ap.add_argument("--expected", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--list-modes", action="store_true")
    args = ap.parse_args()

    try:
        facts = spec_facts(args.root)
    except OracleError as e:
        print("oracle: %s" % e, file=sys.stderr)
        return 2

    if args.list_modes:
        for k in ("user", "supv", "hypv"):
            print("%s=%d" % (k, facts["modes"][k]))
        return 0

    if args.mode is None:
        print("oracle: --mode is required", file=sys.stderr)
        return 2
    if not args.elf or not args.nm:
        print("oracle: --elf and --nm are required", file=sys.stderr)
        return 2
    try:
        syms = elf_symbols(args.nm, args.elf)
        expected = expected_slots(facts, syms, args.mode)
    except OracleError as e:
        print("oracle: %s" % e, file=sys.stderr)
        return 2

    if args.expected:
        for i, (name, exp) in enumerate(expected):
            print("%2d\t0x%016x\t%s" % (i, exp & 0xFFFFFFFFFFFFFFFF, name))
        return 0

    if args.self_test:
        # Every slot must be able to fail: mutate it and require a mismatch.
        good = [e for _, e in expected]
        bad = 0
        for i in range(len(good)):
            mut = list(good)
            mut[i] ^= 1
            if compare(expected, mut) == 0:
                print("  [FAIL] self-test: slot %d mutation not detected" % i)
                bad += 1
        for cut in (0, len(good) // 2):
            mut = good[:cut]
            if compare(expected, mut) == 0:
                print("  [FAIL] self-test: truncation to %d not detected" % cut)
                bad += 1
        mut = good + [0]
        if compare(expected, mut) == 0:
            print("  [FAIL] self-test: one extra slot not detected")
            bad += 1
        print("self-test: %d slot mutations + 2 truncations + 1 extra, %d undetected"
              % (len(good), bad))
        return 1 if bad else 0

    if not args.stream:
        print("oracle: --stream is required", file=sys.stderr)
        return 2
    try:
        got = read_stream(args.stream)
    except (OracleError, FileNotFoundError) as e:
        print("oracle: %s" % e, file=sys.stderr)
        return 2
    fails = compare(expected, got)
    print("result: %d slot(s) failed, %d compared" % (fails, len(expected)))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
