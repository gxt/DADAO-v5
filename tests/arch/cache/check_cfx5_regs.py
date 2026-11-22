#!/usr/bin/env python3
"""`tests/arch/cache/check_cfx5_regs.py` — cfx5 寄存器面 RTL 探针判据
（`m16-chipyard-016`）。

判据**不保存**存在值/位域/指令编码常量：每次运行现场从

  * `.tao/contracts/contract-cache.md`（CACHE-03/06/07/09/12/13/14/18/27）解析
    寄存器行、I/D 位、`addr_start` 宽度、控制字编码与 no-op/非法规则；
  * `.tao/contracts/contract-see.md` §6.1 解析 `CFXREG` 的大类位号；
  * `contracts/opcodes.yaml` 解析 `cfx2rd`/`cfx2rc` 的 `opc` 与字段位域，

再构造期望记录。探针只把实测值 `__REC` 进结果缓冲，因此判据与 RTL 不共享任何
期望常量（`AGENTS.md`「Independent oracle」）。

记录顺序 = `tests/arch/cache/cfx5_regs.S` 的 `__REC` 顺序：
  A 寄存器值（exist/enable/start/size）
  B no-op 与合法命令的「到达见证」（写不得报异常）
  C 四个非法访问的 `excp_cause_id` + `excp_cause_info`（CFXREG + 指令编码）

用法：
  check_cfx5_regs.py --stream FILE [--root DIR]
  check_cfx5_regs.py --self-test [--root DIR]
  check_cfx5_regs.py --expected [--root DIR]
退出码：0 通过；1 判据失败；2 用法/合约解析错误。
"""
from __future__ import annotations

import argparse
import pathlib
import re
import struct
import sys

import yaml

# 探针到达见证（不是语义期望：只证明执行流没有被异常带走）。
WITNESS = [0xC0DE0001, 0xC0DE0002, 0xC0DE0003, 0xC0DE0004, 0xC0DE0005]
# `cfx5_regs.S` 里 `cache_ctrl` 写入使用的 `rd` 字段（指令编码的一部分）。
CTRL_WRITE_RD = 6
CTRL_READ_RD = 5
EXIST_WRITE_RD = 6


# ---------------------------------------------------------------------------
# 合约 / opcode 现场解析
# ---------------------------------------------------------------------------
def _read(path: pathlib.Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise SystemExit("check_cfx5_regs: cannot read %s: %s" % (path, exc))


def parse_cache_contract(root: pathlib.Path) -> dict:
    text = _read(root / ".tao" / "contracts" / "contract-cache.md")
    m = re.search(r"cfx_cache`?\s*/\s*cfx(\d+)", text)
    if not m:
        raise SystemExit("check_cfx5_regs: contract-cache title lacks the cfx number")
    cfxha = int(m.group(1))
    rows = {}
    for m in re.finditer(
            r"`(cfx_cache_[a-z_]+)`\s*=\s*`cg(\d+) rc(\d+)`（([^）]*)）", text):
        rows[m.group(1)] = (int(m.group(2)), int(m.group(3)), m.group(4))
    for name in ("cfx_cache_exist", "cfx_cache_enable", "cfx_cache_ctrl",
                 "cfx_cache_addr_start", "cfx_cache_addr_size"):
        if name not in rows:
            raise SystemExit("check_cfx5_regs: contract-cache CACHE-03 missing %s"
                             % name)
    expect_attr = {
        "cfx_cache_exist": "RO", "cfx_cache_enable": "RW",
        "cfx_cache_ctrl": "WO", "cfx_cache_addr_start": "RW",
        "cfx_cache_addr_size": "RW"}
    for name, attr in expect_attr.items():
        if attr not in rows[name][2]:
            raise SystemExit("check_cfx5_regs: %s attr %r lacks %r"
                             % (name, rows[name][2], attr))

    def need(pattern: str, what: str):
        m = re.search(pattern, text, re.S)
        if not m:
            raise SystemExit("check_cfx5_regs: contract-cache %s not found" % what)
        return m

    m = need(r"CACHE-06.*?bit(\d+) = 有 I-cache、bit(\d+) = 有 D-cache",
             "CACHE-06 I/D bits")
    exist_bits = {"I": int(m.group(1)), "D": int(m.group(2))}

    m = need(r"`cache_exist` 读回 `0b([01]+)`", "CACHE-27 exist value")
    exist_value = int(m.group(1), 2)
    derived = (1 << exist_bits["I"]) | (1 << exist_bits["D"])
    if exist_value != derived:
        raise SystemExit("check_cfx5_regs: CACHE-27 exist 0b%s != CACHE-06 bits %#x"
                         % (m.group(1), derived))

    need(r"CACHE-07.*?复位后每一位等于对应的 `cache_exist` 位",
         "CACHE-07 reset = exist")
    need(r"CACHE-07.*?`cache_exist` 位为 0 的位置写 1 \*\*无效果\*\*、读回 0",
         "CACHE-07 absent-side mask")

    m = need(r"CACHE-18.*?`PA\[(\d+):0\]`", "CACHE-18 PA width")
    pa_bits = int(m.group(1)) + 1
    m = need(r"CACHE-18.*?`\[(\d+):(\d+)\]` 保留、读 0、写忽略",
             "CACHE-18 reserved high bits")
    if int(m.group(2)) != pa_bits:
        raise SystemExit("check_cfx5_regs: CACHE-18 reserved field starts at %s, "
                         "PA width is %d" % (m.group(2), pa_bits))

    m = need(r"`cfx_cache_ctrl\[1:0\]` 操作 =(.*?)；", "CACHE-09 op")
    ops = {name: int(bits, 2) for bits, name in
           re.findall(r"`(\d\d) = ([a-z]+)`", m.group(1))}
    m = need(r"`\[3:2\]` 范围 =(.*?)；", "CACHE-09 scope")
    scopes = {name: int(bits, 2) for bits, name in
              re.findall(r"`(\d\d) = ([A-Za-z0-9_ 单行区间]+)`", m.group(1))}
    m = need(r"`\[15:14\]` 选择（(.*?)）", "CACHE-09 side select")
    sel_bits = {}
    for bit, side in re.findall(r"bit(\d+) = ([ID])", m.group(1)):
        sel_bits[side] = int(bit)
    if set(sel_bits) != {"I", "D"}:
        raise SystemExit("check_cfx5_regs: CACHE-09 side select lacks I/D")

    need(r"CACHE-12.*?`\[15:14\] = 00` 无条件 no-op", "CACHE-12 select no-op")
    need(r"CACHE-12.*?\*\*不检查\*\*范围编码", "CACHE-12 no range check")
    need(r"CACHE-13.*?`op = none` 无条件 no-op", "CACHE-13 op no-op")
    need(r"CACHE-14.*?`\[3:2\] = 11`，或 `PA 区间` 且 `addr_size = 0` ⇒ `CFXREG`",
         "CACHE-14 illegal rule")

    for name in ("none", "clean", "invalidate", "flush"):
        if name not in ops:
            raise SystemExit("check_cfx5_regs: CACHE-09 op %r missing" % name)
    for name in ("all", "PA 单行", "PA 区间", "reserved"):
        if name not in scopes:
            raise SystemExit("check_cfx5_regs: CACHE-09 scope %r missing" % name)

    return {
        "rows": rows,
        "cfxha": cfxha,
        "exist_bits": exist_bits,
        "exist_value": exist_value,
        "pa_bits": pa_bits,
        "ops": ops,
        "scopes": scopes,
        "sel_bits": sel_bits,
    }


def parse_cfxreg_bit(root: pathlib.Path) -> int:
    text = _read(root / ".tao" / "contracts" / "contract-see.md")
    m = re.search(r"\|\s*`1 << (\d+)`\s*\|\s*`CFXREG`", text)
    if not m:
        raise SystemExit("check_cfx5_regs: contract-see §6.1 CFXREG row not found")
    return int(m.group(1))


def _bits_lo_hi(spec: str) -> tuple:
    m = re.fullmatch(r"\[(\d+):(\d+)\]", spec.strip())
    if not m:
        raise SystemExit("check_cfx5_regs: unsupported field bits %r" % spec)
    return int(m.group(2)), int(m.group(1))


def parse_opcode(root: pathlib.Path, ident: str) -> dict:
    path = root / "contracts" / "opcodes.yaml"
    try:
        data = yaml.safe_load(_read(path))
    except yaml.YAMLError as exc:
        raise SystemExit("check_cfx5_regs: cannot parse %s: %s" % (path, exc))
    for entry in data:
        if isinstance(entry, dict) and entry.get("id") == ident:
            value = int(str(entry["value"]), 16)
            mask = int(str(entry["mask"]), 16)
            if value & ~mask:
                raise SystemExit("check_cfx5_regs: %s value outside mask" % ident)
            return {"value": value, "mask": mask,
                    "fields": entry.get("fields", [])}
    raise SystemExit("check_cfx5_regs: opcodes.yaml missing %s" % ident)


def encode(op: dict, **fields) -> int:
    """Place values by the field bit ranges declared in `contracts/opcodes.yaml`."""
    word = op["value"]
    for field in op["fields"]:
        role = field.get("role")
        if role not in fields:
            raise SystemExit("check_cfx5_regs: no value for field %r" % field.get("name"))
        lo, hi = _bits_lo_hi(field["bits"])
        value = int(fields[role])
        if value < 0 or value >= (1 << (hi - lo + 1)):
            raise SystemExit("check_cfx5_regs: %r value %#x does not fit %s"
                             % (role, value, field["bits"]))
        word |= value << lo
    return word


# ---------------------------------------------------------------------------
# 期望记录（顺序 = 探针 `__REC`）
# ---------------------------------------------------------------------------
def expected_records(root: pathlib.Path) -> list:
    c = parse_cache_contract(root)
    cfxreg = 1 << parse_cfxreg_bit(root)
    cfx2rd = parse_opcode(root, "cfx2rd_crrr_cfx")
    cfx2rc = parse_opcode(root, "cfx2rc_crrr_cfx")

    rows = c["rows"]
    exist = c["exist_value"]
    pa_mask = (1 << c["pa_bits"]) - 1
    sel = c["sel_bits"]
    pattern = 0x123456789ABCDEF0

    ha = c["cfxha"]
    cg = rows["cfx_cache_exist"][0]

    def cfx(rc=0, rd=0, write=False):
        return encode(cfx2rc if write else cfx2rd,
                      cfxcode=ha, cfx_cg=cg, cfx_rc=rc, dst=rd)

    ctrl_rc = rows["cfx_cache_ctrl"][1]
    exist_rc = rows["cfx_cache_exist"][1]
    recs = [
        ("exist (RO)", exist),
        ("enable reset", exist),
        ("enable <- 0", 0),
        ("enable <- 1", 1),
        ("enable <- 3", 3),
        ("enable <- all ones (masked by exist)", exist),
        ("addr_start <- all ones", pa_mask),
        ("addr_start <- pattern", pattern & pa_mask),
        ("addr_size <- pattern", pattern),
        ("no-op: sel=00 op=flush scope=reserved", WITNESS[0]),
        ("no-op: sel=11 op=none scope=range size=0", WITNESS[1]),
        ("write: sel=11 op=clean scope=all", WITNESS[2]),
        ("write: sel=I op=invalidate scope=line", WITNESS[3]),
        ("write: sel=D op=flush scope=range size=1", WITNESS[4]),
        ("CFXREG: illegal ctrl encoding (cause_id)", cfxreg),
        ("CFXREG: illegal ctrl encoding (cause_info)",
         cfx(write=True, rc=ctrl_rc, rd=CTRL_WRITE_RD)),
        ("CFXREG: read cache_ctrl (cause_id)", cfxreg),
        ("CFXREG: read cache_ctrl (cause_info)",
         cfx(write=False, rc=ctrl_rc, rd=CTRL_READ_RD)),
        ("CFXREG: write cache_exist (cause_id)", cfxreg),
        ("CFXREG: write cache_exist (cause_info)",
         cfx(write=True, rc=exist_rc, rd=EXIST_WRITE_RD)),
        ("CFXREG: reserved rc on cfx5 (cause_id)", cfxreg),
        ("CFXREG: reserved rc on cfx5 (cause_info)",
         cfx(write=False, rc=1, rd=5)),
    ]
    return recs


# ---------------------------------------------------------------------------
# 判据
# ---------------------------------------------------------------------------
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
        fails.append("records: got %d, expected %d"
                     % (len(recs), len(expected)))
    for i, ((name, want), got) in enumerate(zip(expected, recs)):
        if got != want:
            fails.append("record %d (%s): 0x%016x != 0x%016x"
                         % (i, name, got, want))
    # 故障记录的结构规则（contract-see §6.1）：cause_id 低 16 位恰一位；
    # CFXREG 无子原因 ⇒ wyde2/wyde3 全 0；cause_info 是 32 位指令编码。
    cfxreg_bit = None
    for i, (name, want) in enumerate(expected):
        if name.startswith("CFXREG") and name.endswith("(cause_id)"):
            cfxreg_bit = want
            break
    if cfxreg_bit is None:
        fails.append("expected records are missing the CFXREG cause_id")
    else:
        for i, (name, _) in enumerate(expected):
            if not name.startswith("CFXREG") or i >= len(recs):
                continue
            got = recs[i]
            if name.endswith("(cause_id)"):
                if got & 0xFFFF != cfxreg_bit or got >> 16 != 0:
                    fails.append("record %d (%s): 0x%016x is not a clean CFXREG id"
                                 % (i, name, got))
            elif not (0 < got <= 0xFFFFFFFF):
                fails.append("record %d (%s): 0x%016x is not a 32-bit instruction"
                             % (i, name, got))
    return fails


def self_test(root: pathlib.Path) -> int:
    exp = expected_records(root)
    base = [v for _, v in exp]
    fails = check(base, exp)
    print("  [%s] control stream accepted" % ("PASS" if not fails else "FAIL"))
    if fails:
        for f in fails:
            print("      %s" % f)
        return 1
    bad = 0
    for i in range(len(exp)):
        mutated = list(base)
        mutated[i] ^= 1
        if not check(mutated, exp):
            print("  [FAIL] record %d mutation not rejected (%s)" % (i, exp[i][0]))
            bad += 1
    print("  [%s] every record mutation rejected (%d records)"
          % ("PASS" if not bad else "FAIL", len(exp)))
    cases = [
        ("short stream", base[:-1]),
        ("long stream", base + [0]),
    ]
    for name, recs in cases:
        if not check(recs, exp):
            print("  [FAIL] %s not rejected" % name)
            bad += 1
        else:
            print("  [PASS] %s rejected" % name)
    if check(None, exp) == []:
        print("  [FAIL] non-record-aligned stream not rejected")
        bad += 1
    else:
        print("  [PASS] non-record-aligned stream rejected")
    print("check_cfx5_regs: self-test %s (%d records)"
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
        for i, (name, value) in enumerate(exp):
            print("%2d %-48s 0x%016x" % (i, name, value))
        return 0
    if not args.stream:
        ap.error("--stream is required unless --self-test/--expected")

    data = pathlib.Path(args.stream).read_bytes()
    recs = unpack(data)
    fails = check(recs, exp)
    if fails:
        print("check_cfx5_regs: FAIL")
        for f in fails:
            print("  [FAIL] %s" % f)
        return 1
    print("check_cfx5_regs: PASS (%d records, %d bytes)"
          % (len(exp), len(data)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
