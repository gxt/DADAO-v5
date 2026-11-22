#!/usr/bin/env python3
"""`tests/arch/umon/check_cfx02_regs.py` — cfx0/cfx2 寄存器面 + 两轴权限
RTL 探针判据（`m16-chipyard-019`）。

判据**不保存**寄存器复位值/位域/cfx 编号：每次运行现场从

  * `spec/DADAO-12-SEE-主管系统运行环境.md` §2.1（cfx0 无内部空间、smon 的
    64 KiB SRAM）与 §3.1/§3.3/§3.4（模式行 `switch_run_mode` 初值）、§3.6
    （异常帧/pending 初值）、§3.7（暂存寄存器数量 2..64）、§3.8（cg7 位域）
    解析；
  * `.tao/contracts/contract-see.md` §3（四类同步 mask / `cfx_intr_mask` /
    `global_cfx_intr_mask` 初值、`cg_reg_deleg` 复位与 bit3、smon/hmon 空间块、
    cfx0 无空间）与 §6.1（`CFXREG` 位号）解析；

再构造期望记录。探针只把实测值 `__REC` 进结果缓冲，因此判据与 RTL 不共享任何
期望常量（`AGENTS.md`「Independent oracle」）。

记录顺序 = `tests/arch/umon/cfx02_regs.S` 的 `__REC` 顺序：
  cfx0  A 模式行 / B 四 mask 独立 / C cg3 rc12 / D cg4·cg5·cg6·cg8
        E cg7 与空帧 / G 三个 CFXREG
  cfx2  F cg3·cg0·cg4·cg6·cg8·cg7 / G' 两个 CFXREG

`scratch_regs_num`（cg4 rc6）是规范允许 2..64 的实现自选值，探针只读回它；
判据按 §3.7 的范围校验（`range` 记录），不写死 Kaiwu-Vast 的选择。

用法：
  check_cfx02_regs.py --stream FILE [--root DIR]
  check_cfx02_regs.py --self-test [--root DIR]
  check_cfx02_regs.py --expected [--root DIR]
退出码：0 通过；1 判据失败；2 用法/合约解析错误。
"""
from __future__ import annotations

import argparse
import pathlib
import re
import struct
import sys

PATTERN64 = 0x123456789ABCDEF0
VECTOR_WRITE = 0x123456789ABCDEFF
VECTOR_READ = 0x123456789ABCDEFC
SCRATCH1 = 0x0F1E2D3C4B5A6978
ONES64 = 0xFFFFFFFFFFFFFFFF


def _read(path: pathlib.Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise SystemExit("check_cfx02_regs: cannot read %s: %s" % (path, exc))


def _need(pattern: str, text: str, what: str, flags=0):
    m = re.search(pattern, text, flags)
    if not m:
        raise SystemExit("check_cfx02_regs: %s not found" % what)
    return m


def parse(root: pathlib.Path) -> dict:
    see_spec = _read(root / "spec" / "DADAO-12-SEE-主管系统运行环境.md")
    see = _read(root / ".tao" / "contracts" / "contract-see.md")

    # cfx0 umon: no internal space (`DADAO-12 §2.1` first paragraph).
    _need(r"`cfx0`（umon）没有内部地址空间", see_spec,
          "DADAO-12 §2.1 cfx0 no-space sentence")
    umon_id = 0

    # cfx2 smon: the §2.1 table row carries number, base and size.
    m = _need(r"\|\s*(\d+)\s*\|\s*smon\s*\|\s*`0x([0-9a-fA-F_]+)`\s*\|\s*"
              r"(\d+)\s*KiB\s*\|\s*SRAM", see_spec, "DADAO-12 §2.1 smon row")
    smon_id = int(m.group(1))
    smon_base = int(m.group(2).replace("_", ""), 16)
    smon_size = int(m.group(3)) << 10
    if smon_id != 2:
        raise SystemExit("check_cfx02_regs: smon is cfx%s, expected 2" % smon_id)
    del m

    # Four sync masks (ordinary cfx) and the two all-ones masks (`contract-see §3`).
    m = _need(r"四类同步 mask 初值：power 与普通 cfx `0x([0-9a-fA-F_]+)`",
              see, "contract-see §3 mask reset")
    mask_reset = int(m.group(1).replace("_", ""), 16)
    _need(r"`cfx_intr_mask`/`global_cfx_intr_mask` 初值全 1", see,
          "contract-see §3 all-ones masks")

    # cg_reg_deleg: reset all ones, bit3 hardware-fixed 1.
    _need(r"`cfx_⟨cfxname⟩_hypv_cg_reg_deleg`（`cg3 rc12`，复位全 1、RW）", see,
          "contract-see §3 cg_reg_deleg reset")
    _need(r"`bit3` 硬件固定 1", see, "contract-see §3 cg_reg_deleg bit3")

    # switch_run_mode reset per mode row (`DADAO-12` §3.1/§3.3/§3.4 tables).
    def mode_switch(cg: int) -> int:
        m = _need(r"^\|\s*%d\s*\|\s*8\s*\|[^|\n]*\|[^|\n]*\|\s*(\d+)"
                  % cg, see_spec,
                  "DADAO-12 cg%d rc8 switch_run_mode row" % cg, re.M)
        return int(m.group(1))

    # excp_vector write drops the low two bits (`DADAO-12` §3.4).
    _need(r"值\[1:0\]`?\s*←\s*0|`value\[1:0\]`?\s*←\s*0", see_spec,
          "DADAO-12 §3.4 vector low-bit drop")

    # cg7 bit fields (`DADAO-12` §3.8).
    _need(r"`bit0 = exists`.*?`bit1 = SRAM`", see_spec,
          "DADAO-12 §3.8 desc bits", re.S)
    desc = (1 << 0) | (1 << 1)
    _need(r"`bit0 = R`、`bit1 = W`、`bit2 = X`", see_spec,
          "DADAO-12 §3.8 attr bits")
    attr = (1 << 0) | (1 << 1) | (1 << 2)

    # Scratch count range (`DADAO-12` §3.7).
    _need(r"至少 2 个、最多 64 个", see_spec, "DADAO-12 §3.7 scratch range")

    # Cause bits (`contract-see` §6.1 / §6.1.1).
    m = _need(r"\|\s*`1 << (\d+)`\s*\|\s*`CFXREG`", see, "contract-see CFXREG bit")
    cfxreg_bit = int(m.group(1))

    return {
        "umon": umon_id,
        "smon": smon_id,
        "smon_base": smon_base,
        "smon_size": smon_size,
        "mask_reset": mask_reset,
        "ones": ONES64,
        "switch": {cg: mode_switch(cg) for cg in (0, 1, 2, 3)},
        "desc": desc,
        "attr": attr,
        "cfxreg": 1 << cfxreg_bit,
    }


def expected_records(root: pathlib.Path) -> list:
    c = parse(root)
    mask = c["mask_reset"]
    ones = c["ones"]
    umon = c["umon"]
    smon = c["smon"]
    smon_start = c["smon_base"] - (smon << 42)
    cfxreg = c["cfxreg"]
    sw = c["switch"]

    recs = [
        # ---- cfx0 A ----
        ("umon cg2 rc0 cfxtrap reset", mask, "exact"),
        ("umon cg0 rc4 intr mask reset", ones, "exact"),
        ("umon cg1 rc8 switch reset", sw[1], "exact"),
        ("umon cg2 rc10 vector reset", 0, "exact"),
        ("umon cg2 rc10 vector write drops low 2", VECTOR_READ, "exact"),
        # ---- cfx0 B ----
        ("umon cg0 rc2 mask write", PATTERN64, "exact"),
        ("umon cg3 rc0 mask reset", mask, "exact"),
        ("umon cg3 rc2 mask reset (independent rc)", mask, "exact"),
        # ---- cfx0 C ----
        ("umon cg3 rc12 deleg reset", ones, "exact"),
        ("umon cg3 rc12 bit3 fixed 1", 0x8, "exact"),
        # ---- cfx0 D ----
        ("umon cg4 rc0 cfx_id", umon, "exact"),
        ("umon cg4 rc2 trap_num", 0, "exact"),
        ("umon cg4 rc3 excp_sync_num", 0, "exact"),
        ("umon cg4 rc4 excp_async_num", 0, "exact"),
        ("umon cg4 rc5 escape_num", 0, "exact"),
        ("umon cg4 rc6 scratch_regs_num", 2, "range"),
        ("umon cg5 rc5 pending reset", 0, "exact"),
        ("umon cg5 rc5 write/read", PATTERN64, "exact"),
        ("umon cg6 rc0 write/read", PATTERN64, "exact"),
        ("umon cg6 rc1 write/read", SCRATCH1, "exact"),
        ("umon cg8 rc1 global mask reset", ones, "exact"),
        ("umon cg8 rc1 write/read", PATTERN64, "exact"),
        # ---- cfx0 E ----
        ("umon cg7 rc0 no space", 0, "exact"),
        ("umon cg7 rc1 no space", 0, "exact"),
        ("umon cg7 rc2 no space", 0, "exact"),
        ("umon cg7 rc3 no space", 0, "exact"),
        ("umon cg5 rc0 prev_mode reset", 0, "exact"),
        ("umon cg5 rc2 cause_id reset", 0, "exact"),
        # ---- cfx0 G/H ----
        ("CFXREG umon cg0 rc9 reserved", cfxreg, "exact"),
        ("CFXREG umon cg4 rc7 reserved", cfxreg, "exact"),
        ("CFXREG umon write cg4 rc0 (RO)", cfxreg, "exact"),
        # ---- cfx2 F ----
        ("smon cg3 rc0 cfxtrap reset", mask, "exact"),
        ("smon cg3 rc4 intr mask reset", ones, "exact"),
        ("smon cg3 rc8 switch reset", sw[3], "exact"),
        ("smon cg3 rc10 vector reset = SRAM start", c["smon_base"], "exact"),
        ("smon cg0 rc8 switch reset", sw[0], "exact"),
        ("smon cg3 rc12 deleg reset", ones, "exact"),
        ("smon cg4 rc0 cfx_id", smon, "exact"),
        ("smon cg4 rc6 scratch_regs_num", 2, "range"),
        ("smon cg6 rc0 write/read", PATTERN64, "exact"),
        ("smon cg8 rc1 global mask reset", ones, "exact"),
        ("smon cg7 rc0 desc exists|SRAM", c["desc"], "exact"),
        ("smon cg7 rc1 start", smon_start, "exact"),
        ("smon cg7 rc2 size", c["smon_size"], "exact"),
        ("smon cg7 rc3 attr R|W|X", c["attr"], "exact"),
        # ---- cfx2 G'/H' ----
        ("CFXREG smon cg5 rc6 reserved", cfxreg, "exact"),
        ("CFXREG smon cg8 rc2 reserved", cfxreg, "exact"),
    ]
    return recs


def unpack(data: bytes):
    if len(data) % 8:
        return None
    return [struct.unpack(">Q", data[i:i + 8])[0]
            for i in range(0, len(data), 8)]


def check(recs, expected: list) -> list:
    if recs is None:
        return ["stream is not a whole number of 8-byte records"]
    fails = []
    if len(recs) != len(expected):
        fails.append("records: got %d, expected %d" % (len(recs), len(expected)))
    for i, ((name, want, kind), got) in enumerate(zip(expected, recs)):
        if kind == "range":
            if not (2 <= got <= 64):
                fails.append("record %d (%s): 0x%016x outside 2..64" % (i, name, got))
        elif got != want:
            fails.append("record %d (%s): 0x%016x != 0x%016x" % (i, name, got, want))
    return fails


def self_test(root: pathlib.Path) -> int:
    exp = expected_records(root)
    base = [v for _, v, _ in exp]
    fails = check(base, exp)
    print("  [%s] control stream accepted" % ("PASS" if not fails else "FAIL"))
    if fails:
        for f in fails:
            print("      %s" % f)
        return 1
    bad = 0
    for i, (name, _, kind) in enumerate(exp):
        mutated = list(base)
        # A range record must be mutated out of range, every other record by
        # one bit: both must be rejected or the assertion has no FAIL path.
        mutated[i] = 1 if kind == "range" else mutated[i] ^ 1
        if not check(mutated, exp):
            print("  [FAIL] record %d mutation not rejected (%s)" % (i, name))
            bad += 1
    print("  [%s] every record mutation rejected (%d records)"
          % ("PASS" if not bad else "FAIL", len(exp)))
    for label, recs in (("short stream", base[:-1]), ("long stream", base + [0]),
                        ("non-record-aligned", None)):
        rejected = bool(check(recs, exp))
        if not rejected:
            print("  [FAIL] %s not rejected" % label)
            bad += 1
        else:
            print("  [PASS] %s rejected" % label)
    print("check_cfx02_regs: self-test %s (%d records)"
          % ("PASS" if not bad else "FAIL", len(exp)))
    return 0 if not bad else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--stream", default=None, help="探针结果缓冲（8 B/记录）")
    ap.add_argument("--root", default=None, help="仓库根（缺省 = 本文件上三级）")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--expected", action="store_true")
    args = ap.parse_args()

    root = pathlib.Path(args.root).resolve() if args.root else \
        pathlib.Path(__file__).resolve().parents[3]
    try:
        exp = expected_records(root)
    except SystemExit as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if args.self_test:
        return self_test(root)
    if args.expected:
        for i, (name, value, kind) in enumerate(exp):
            shown = "2..64" if kind == "range" else "0x%016x" % value
            print("%2d %-52s %s" % (i, name, shown))
        return 0
    if not args.stream:
        ap.error("--stream is required unless --self-test/--expected")

    data = pathlib.Path(args.stream).read_bytes()
    recs = unpack(data)
    fails = check(recs, exp)
    if fails:
        print("check_cfx02_regs: FAIL")
        for f in fails:
            print("  [FAIL] %s" % f)
        return 1
    print("check_cfx02_regs: PASS (%d records, %d bytes)"
          % (len(exp), len(data)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
