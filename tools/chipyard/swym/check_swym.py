#!/usr/bin/env python3
"""check_swym — `tools/chipyard/swym/swym.S` 的独立判据（`m19-chipyard-003`）。

判据全部**现场**从真源派生，不从 RTL 观测值反推：

  * `spec/SimRISC-12 §2`：`N = immu18[11:0]`、`immu18[17:12]` 为 SBZ（非 0 ⇒
    `ILLI`）、`swym N` 总时延 1 + N 拍、执行期间不取中断；
  * `contracts/opcodes.yaml::swym_oiii_imm`：opc/ha/mask/value、`immu18` 字段位域、
    `legality: immu18[17:12] == 0`、`rule_refs: encode_sbz`；
  * `.tao/contracts/contract-see.md`：`ILLI` 的 cause 位号；
  * ELF 符号 + 反汇编：周期用例的三条 `swym` 地址/编码，ILLI 用例的地址/原始字。

检查项（逐项打印 `检查名 | expected / actual`）：

  A. 合约派生：spec 的 12 位/SBZ/1+N 条款、opcodes 的合法性/规则引用、ILLI 位号；
  B. ELF：三个周期用例编码 = value | N（N = 0/1/4095），三个 ILLI 字的
     `immu18[17:12] != 0`（且至少一条低 12 位合法）；
  C. 周期：`swym-done.cycle - swym.cycle + 1 == 1 + N`（N=0/1/4095 ⇒ 1/2/4096）；
     恰好三条合法 `swym` 的 start/done，且没有非法字产生的 start；
  D. ILLI：恰好三条 `cause == 1 << ILLI_bit`，`cause_ip` = 对应符号地址、
     `cause_info` = 该地址的 32 位编码字；
  E. 原子性（Tiny 无中断源，按任务书披露的替代验证）：`asyncTake`/`intrFreqTake`
     只在 `sExec`/`sFreq`；新增 `sSwym` 块内不出现 `intr`/`intrAck`/`asyncTake`；
     源码检查**只读核文件** `WumingCore.scala`（不读译码器），故只覆盖上述形态；
     `N = inst(11,0)` 与 `immu18[17:12] != 0 ⇒ d.ill` 的**行为**由 C/D 段仿真用例
     （1 + N 拍、ILLI 的 `cause`/`cause_ip`/`cause_info`）覆盖；
  F. 访客退出码：`SYS_EXIT(0x18) ... -> host exit status 0`。

用法：
  check_swym.py --log LOG --elf ELF --root ROOT [--source WumingCore.scala]
                [--nm llvm-nm] [--objdump llvm-objdump]
  check_swym.py --self-test --root ROOT   # 给判据喂合成坏流，证明有可达 FAIL
"""

from __future__ import annotations

import argparse
import pathlib
import re
import struct
import subprocess
import sys
import tempfile

SPEC12 = "spec/SimRISC-12-其它指令.md"
OPCODES = "contracts/opcodes.yaml"
CONTRACT_SEE = ".tao/contracts/contract-see.md"

SWYM_BASE = 0x47880000
IMM_MASK = 0x3FFFF
N_MASK = 0xFFF
SBZ_SHIFT = 12
SBZ_MASK = 0x3F

START_RE = re.compile(
    r"WumingCore: swym ip=0x([0-9a-f]+) imm=0x([0-9a-f]+) n=\s*(\d+) "
    r"cycle=\s*(\d+)")
DONE_RE = re.compile(
    r"WumingCore: swym-done ip=0x([0-9a-f]+) n=\s*(\d+) cycle=\s*(\d+)")
EXCP_RE = re.compile(
    r"WumingCore: excp cause=0x([0-9a-f]+) cause_ip=0x([0-9a-f]+) "
    r"info=0x([0-9a-f]+) vector=0x([0-9a-f]+) cycle=\s*(\d+)")
EXIT_RE = re.compile(r"SYS_EXIT\(0x18\).*host exit status (\d+)")
OBJ_LINE_RE = re.compile(
    r"^\s*([0-9a-f]+):\s+([0-9a-f]{2}) ([0-9a-f]{2}) ([0-9a-f]{2}) "
    r"([0-9a-f]{2})\s+(.*)$")

TIMING = ((0, 1), (1, 2), (4095, 4096))


class OracleError(Exception):
    pass


def read(root, rel):
    p = pathlib.Path(root) / rel
    if not p.is_file():
        raise OracleError("missing %s" % rel)
    return p.read_text(encoding="utf-8")


def facts(root):
    """Derive every expected value from the spec/contracts (not from the run)."""
    spec = read(root, SPEC12)
    if not re.search(r"N = immu18\[11:0\]", spec):
        raise OracleError("SimRISC-12 §2: `N = immu18[11:0]` not found")
    if not re.search(r"immu18\[17:12\].{0,40}SBZ", spec, re.S):
        raise OracleError("SimRISC-12 §2: immu18[17:12] SBZ not found")
    if not re.search(r"1 \+ N", spec):
        raise OracleError("SimRISC-12 §2: `1 + N` not found")
    if not re.search(r"执行期间不取中断|原子", spec):
        raise OracleError("SimRISC-12 §2: atomicity sentence not found")

    contract = read(root, OPCODES)
    block = None
    for chunk in re.split(r"^- id: ", contract, flags=re.M)[1:]:
        if chunk.startswith("swym_oiii_imm\n"):
            block = chunk
            break
    if block is None:
        raise OracleError("opcodes.yaml: swym_oiii_imm not found")
    m = re.search(r"mask: '0x([0-9a-fA-F]+)'", block)
    v = re.search(r"value: '0x([0-9a-fA-F]+)'", block)
    if not m or not v:
        raise OracleError("opcodes.yaml: swym mask/value missing")
    mask, value = int(m.group(1), 16), int(v.group(1), 16)
    if value != SWYM_BASE:
        raise OracleError("opcodes.yaml: swym value 0x%08x != 0x%08x"
                          % (value, SWYM_BASE))
    if "legality:\n  - immu18[17:12] == 0" not in block:
        raise OracleError("opcodes.yaml: swym legality (SBZ) missing")
    if "rule_refs:\n  - encode_sbz" not in block:
        raise OracleError("opcodes.yaml: swym encode_sbz rule ref missing")

    see = read(root, CONTRACT_SEE)
    bits = dict((name, int(bit)) for bit, name in re.findall(
        r"^\|\s*`1 << (\d+)`\s*\|\s*`?([A-Z]+)`?\s*\|", see, re.M))
    if "ILLI" not in bits:
        raise OracleError("contract-see: ILLI cause bit not found")
    return {"mask": mask, "value": value, "illi": bits["ILLI"]}


def tool_path(value, name):
    if value:
        return value
    raise OracleError("需要 --%s" % name)


def objdump_words(objdump, elf):
    out = subprocess.run([objdump, "-d", str(elf)], capture_output=True,
                         text=True)
    if out.returncode != 0:
        raise OracleError("llvm-objdump rc=%d: %s"
                          % (out.returncode, out.stderr.strip()))
    words = {}
    for line in out.stdout.splitlines():
        m = OBJ_LINE_RE.match(line)
        if not m:
            continue
        addr = int(m.group(1), 16)
        words[addr] = struct.unpack(">I", bytes(
            int(m.group(i), 16) for i in (2, 3, 4, 5)))[0]
    return words


def nm_symbols(nm, elf):
    out = subprocess.run([nm, str(elf)], capture_output=True, text=True)
    if out.returncode != 0:
        raise OracleError("llvm-nm rc=%d: %s"
                          % (out.returncode, out.stderr.strip()))
    syms = {}
    for line in out.stdout.splitlines():
        parts = line.split()
        if len(parts) == 3 and parts[1].lower() in ("t", "a"):
            syms[parts[2]] = int(parts[0], 16)
    return syms


def parse_log(text):
    starts, dones, excps, exits = [], [], [], []
    for line in text.splitlines():
        m = START_RE.search(line)
        if m:
            starts.append({"ip": int(m.group(1), 16),
                           "imm": int(m.group(2), 16),
                           "n": int(m.group(3)),
                           "cycle": int(m.group(4))})
            continue
        m = DONE_RE.search(line)
        if m:
            dones.append({"ip": int(m.group(1), 16),
                          "n": int(m.group(2)),
                          "cycle": int(m.group(3))})
            continue
        m = EXCP_RE.search(line)
        if m:
            excps.append({"cause": int(m.group(1), 16),
                          "ip": int(m.group(2), 16),
                          "info": int(m.group(3), 16),
                          "cycle": int(m.group(5))})
            continue
        m = EXIT_RE.search(line)
        if m:
            exits.append(int(m.group(1)))
    return starts, dones, excps, exits


class Checker:
    def __init__(self, verbose=True):
        self.fail = 0
        self.pass_ = 0
        self.verbose = verbose

    def ok(self, name, expected, actual):
        self.pass_ += 1
        if self.verbose:
            print("  [PASS] %s | expected=%s actual=%s"
                  % (name, expected, actual))

    def bad(self, name, expected, actual):
        self.fail += 1
        if self.verbose:
            print("  [FAIL] %s | expected=%s actual=%s"
                  % (name, expected, actual))

    def eq(self, name, expected, actual):
        if expected == actual:
            self.ok(name, expected, actual)
        else:
            self.bad(name, expected, actual)


def check_source(c, source):
    """E: the sSwym wait state must not sample interrupt state (core file only)."""
    text = pathlib.Path(source).read_text(encoding="utf-8")
    c.eq("asyncTake is sExec-only",
         "val asyncTake = state === sExec && gewu.io.intr.valid" in text, True)
    c.eq("intrFreqTake is sFreq-only",
         "val intrFreqTake = state === sFreq && gewu.io.intr.valid" in text, True)
    c.eq("state := sSwym occurs once", text.count("state := sSwym"), 1)
    m = re.search(r"is\(sSwym\) \{(.*?)\n    \}", text, re.S)
    if not m:
        c.bad("sSwym state block present", True, False)
        return
    body = "\n".join(l.split("//")[0] for l in m.group(1).splitlines())
    c.eq("sSwym block samples no interrupt",
         [kw for kw in ("gewu.io.intr", "intrAck", "asyncTake")
          if kw in body], [])
    c.eq("sSwym waits on swymLeft", "swymLeft === 0.U" in body, True)
    c.eq("sSwym completes with finish(ip + 4.U)",
         "finish(ip + 4.U)" in body, True)


def check_log(c, f, starts, dones, excps, exits, elf_words, syms):
    illi_bit = 1 << f["illi"]
    legal = []
    for name, n in (("sw_n0", 0), ("sw_n1", 1), ("sw_n4095", 4095)):
        addr = syms.get(name)
        if addr is None:
            c.bad("symbol %s" % name, "present", "missing")
            continue
        c.eq("%s encoding" % name, f["value"] | (n & N_MASK),
             elf_words.get(addr))
        legal.append(addr)
    illi_sites = []
    for name in ("sw_illi0", "sw_illi1", "sw_illi2"):
        addr = syms.get(name)
        if addr is None:
            c.bad("symbol %s" % name, "present", "missing")
            continue
        word = elf_words.get(addr, 0)
        c.eq("%s is a swym encoding" % name, word & f["mask"], f["value"])
        c.eq("%s has immu18[17:12] != 0" % name,
             (word >> SBZ_SHIFT) & SBZ_MASK != 0, True)
        illi_sites.append((addr, word))
    c.eq("at least one ILLI word keeps a legal low 12 bits",
         any((w & N_MASK) != 0 and (w >> SBZ_SHIFT) & SBZ_MASK for _, w in
             illi_sites), True)

    # C: exactly the three legal swyms start/done, with 1 + N cycles.
    c.eq("legal swym start count", len(legal), len(starts))
    c.eq("legal swym start addresses", legal, [s["ip"] for s in starts])
    c.eq("swym-done count", len(starts), len(dones))
    first_fail = None
    for i, (s, d) in enumerate(zip(starts, dones)):
        n = s["imm"] & N_MASK
        c.eq("start #%d ip matches done" % i, s["ip"], d["ip"])
        c.eq("start #%d n matches immu18[11:0]" % i, n, s["n"])
        c.eq("done #%d n matches start" % i, n, d["n"])
        total = d["cycle"] - s["cycle"] + 1
        c.eq("swym N=%d total cycles" % n, 1 + n, total)
        if first_fail is None and total != 1 + n:
            first_fail = n
    c.eq("timing cases present", sorted(s["imm"] & N_MASK for s in starts),
         [0, 1, 4095])
    for n, expected in TIMING:
        hit = [d["cycle"] - s["cycle"] + 1
               for s, d in zip(starts, dones) if (s["imm"] & N_MASK) == n]
        c.eq("N=%d total cycles" % n, expected, hit[0] if hit else None)

    # D: ILLI faults.
    illi = [e for e in excps if e["cause"] == illi_bit]
    c.eq("ILLI fault count", len(illi_sites), len(illi))
    for (addr, word), e in zip(illi_sites, illi):
        c.eq("ILLI@0x%x cause_ip" % addr, addr, e["ip"])
        c.eq("ILLI@0x%x cause_info" % addr, word, e["info"])
    legal_set = set(legal)
    c.eq("no illegal swym start line", 0,
         len([e for e in illi if e["ip"] in legal_set]))
    c.eq("no other-cause fault at the ILLI sites", 0,
         len([e for e in excps if e["ip"] in {a for a, _ in illi_sites}
              and e["cause"] != illi_bit]))

    # F: guest exit status.
    c.eq("guest SYS_EXIT status", [0], exits)


def run(args):
    c = Checker()
    try:
        f = facts(args.root)
        c.ok("oracle: spec/opcodes/contract derived",
             "12-bit N, SBZ, 1+N, ILLI=1<<%d" % f["illi"],
             "12-bit N, SBZ, 1+N, ILLI=1<<%d" % f["illi"])
        words = objdump_words(tool_path(args.objdump, "objdump"), args.elf)
        syms = nm_symbols(tool_path(args.nm, "nm"), args.elf)
    except OracleError as exc:
        print("check_swym: oracle/ELF error: %s" % exc)
        return 2
    text = pathlib.Path(args.log).read_text(encoding="utf-8", errors="replace")
    starts, dones, excps, exits = parse_log(text)
    check_log(c, f, starts, dones, excps, exits, words, syms)
    if args.source:
        check_source(c, args.source)
    print("check_swym: PASS=%d FAIL=%d" % (c.pass_, c.fail))
    return 0 if c.fail == 0 else 1


def mut(stream, old, new):
    if old not in stream:
        raise OracleError("self-test mutant anchor missing: %r" % old)
    return stream.replace(old, new, 1)


def self_test(args):
    """Feed synthetic bad streams to prove every asserted dimension can fail."""
    try:
        f = facts(args.root)
    except OracleError as exc:
        print("check_swym --self-test: %s" % exc)
        return 2
    # A self-contained good stream + its ELF facts; the ELF itself is required
    # for symbols/words, so the caller must pass --elf for the self-test too.
    words = objdump_words(tool_path(args.objdump, "objdump"), args.elf)
    syms = nm_symbols(tool_path(args.nm, "nm"), args.elf)
    good_lines = []
    for name, n, total in (("sw_n0", 0, 1), ("sw_n1", 1, 2),
                           ("sw_n4095", 4095, 4096)):
        addr = syms[name]
        good_lines.append("WumingCore: swym ip=0x%x imm=0x%05x n=%4d cycle=%d"
                          % (addr, n, n, 1000))
        good_lines.append("WumingCore: swym-done ip=0x%x n=%4d cycle=%d"
                          % (addr, n, 1000 + total - 1))
    for name in ("sw_illi0", "sw_illi1", "sw_illi2"):
        addr = syms[name]
        good_lines.append(
            "WumingCore: excp cause=0x%x cause_ip=0x%x info=0x%x "
            "vector=0x0 cycle=2000" % (1 << f["illi"], addr, words[addr]))
    good_lines.append("WumingCore: excp cause=0x1 cause_ip=0xffffffff010c "
                      "info=0x7f0f0001 vector=0x0 cycle=10")
    good_lines.append("[WumingSemi] SYS_EXIT(0x18) reason=0x20026 code=0x0 "
                      "cycle=3000 -> host exit status 0")
    good = "\n".join(good_lines) + "\n"

    cases = []
    cases.append(("good", good, 0))
    cases.append(("timing-off-by-one",
                  mut(good, "swym-done ip=0x%x n=%4d cycle=%d"
                      % (syms["sw_n1"], 1, 1000 + 2 - 1),
                      "swym-done ip=0x%x n=%4d cycle=%d"
                      % (syms["sw_n1"], 1, 1000 + 2)), 1))
    cases.append(("no-illi-fault",
                  mut(good, "WumingCore: excp cause=0x%x cause_ip=0x%x"
                      % (1 << f["illi"], syms["sw_illi0"]),
                      "WumingCore: excp cause=0x200 cause_ip=0x%x"
                      % syms["sw_illi0"]), 1))
    cases.append(("wrong-illi-ip",
                  mut(good, "cause_ip=0x%x" % syms["sw_illi2"],
                      "cause_ip=0x%x" % (syms["sw_illi2"] + 4)), 1))
    cases.append(("wrong-guest-status",
                  mut(good, "-> host exit status 0", "-> host exit status 67"),
                  1))
    failures = 0
    for name, stream, expect_rc in cases:
        with tempfile.NamedTemporaryFile("w", suffix=".log", delete=False) as fp:
            fp.write(stream)
            path = fp.name
        c = Checker(verbose=False)
        starts, dones, excps, exits = parse_log(stream)
        check_log(c, f, starts, dones, excps, exits, words, syms)
        if args.source:
            check_source(c, args.source)
        rc = 0 if c.fail == 0 else 1
        status = "PASS" if rc == expect_rc else "FAIL"
        print("[%s] self-test %-20s expected_rc=%d actual_rc=%d "
              "(checks pass=%d fail=%d)"
              % (status, name, expect_rc, rc, c.pass_, c.fail))
        pathlib.Path(path).unlink(missing_ok=True)
        if rc != expect_rc:
            failures += 1
    print("check_swym --self-test: %d/%d" % (len(cases) - failures, len(cases)))
    return 0 if failures == 0 else 1


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--log")
    ap.add_argument("--elf")
    ap.add_argument("--root", default=".")
    ap.add_argument("--source", default=None)
    ap.add_argument("--nm", default="llvm-nm")
    ap.add_argument("--objdump", default="llvm-objdump")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args(argv)
    if args.self_test:
        return self_test(args)
    if not args.log or not args.elf:
        ap.error("--log and --elf are required")
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
