#!/usr/bin/env python3
"""`check_cfx5_maint.py` — cfx5 维护命令 RTL 探针判据（`m16-chipyard-017`）。

判据由两层组成：

  * **结果缓冲**：顺序 = `cfx5_maint.S` 的 `__REC`，期望值由
    `gen_cfx5_maint_tables.expected_records()` 现场算出（控制字/CFXREG 位号
    从 `contract-cache` / `contract-see` 解析，不复制位域）；记录本身来自
    探针的独立观测通道（取指端口执行到的立即数 / D 侧重填值）；
  * **仿真日志**：`WumingCache[icache|dcache]` 的 `cmd`/`hit`/`miss` 事件，
    断言「invalidate 不写回」「I|clean 不进 I 侧且 I 行仍在」「flush 写回后
    行被删除」「PA 区间只命中区间内的行」「enable=0 时命令根本没有发出」等
    只有日志才看得到的时序事实。

用法：
  check_cfx5_maint.py --stream FILE --log FILE [--root DIR]
  check_cfx5_maint.py --self-test --log FILE [--root DIR]
  check_cfx5_maint.py --expected [--root DIR]
退出码：0 通过；1 判据失败；2 用法/合约解析错误。
"""
from __future__ import annotations

import argparse
import pathlib
import re
import struct
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
DEFAULT_ROOT = ROOT


def _load(name, path):
    import importlib.util
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


GEN = _load("cfx5_maint_geometry", HERE / "gen_cfx5_maint_tables.py")
ORACLE = _load("cfx5_maint_records", HERE / "check_cfx5_regs.py")


def expected_records(root: pathlib.Path) -> list:
    return GEN.expected_records(root)


# ---------------------------------------------------------------------------
# 日志解析
# ---------------------------------------------------------------------------
LOG_RE = re.compile(r"^WumingCache\[(icache|dcache)\]: (\S+)(.*)$")


def parse_log(text: str) -> list:
    """>> [(side, kind, fields, raw)] in log order (`cycle` keeps the order)."""
    events = []
    for line in text.splitlines():
        m = LOG_RE.match(line)
        if not m:
            continue
        side, kind, rest = m.group(1), m.group(2), m.group(3)
        fields = {}
        for key, value in re.findall(r"(\w+)=\s*(\S+)", rest):
            if value.startswith("0x"):
                try:
                    fields[key] = int(value, 16)
                except ValueError:
                    fields[key] = value
            else:
                try:
                    fields[key] = int(value)
                except ValueError:
                    fields[key] = value
        events.append((side, kind, fields, line))
    return events


def _cyc(ev):
    value = ev[2].get("cycle")
    return value if isinstance(value, int) else -1


def _cmds(events, side):
    return [e for e in events if e[0] == side and e[1] == "cmd"]


def _find(events, side, kind, **want):
    out = []
    for ev in events:
        if ev[0] != side or ev[1] != kind:
            continue
        if all(ev[2].get(k) == v for k, v in want.items()):
            out.append(ev)
    return out


def check_log(events, g) -> list:
    """The cache-log half of the criterion.  `g` = the geometry module."""
    fails = []
    pa_code, pa_r0, pa_r1, pa_d = g.PA_CODE, g.PA_R0, g.PA_R1, g.PA_D
    mmio_line = g.MMIO_LINE

    dcmds = _cmds(events, "dcache")
    icmds = _cmds(events, "icache")

    # 1. A reserved scope must never reach either cache (the core rejects it
    #    as CFXREG; the cache also asserts).
    bad = [e for e in dcmds + icmds if e[2].get("scope") == 3]
    if bad:
        fails.append("%d command(s) with reserved scope 3 reached a cache" % len(bad))

    # 2. invalidate never writes back (CACHE-20); a write-back followed by a
    #    drop would log both op=2 and wb=1.
    bad = [e for e in dcmds + icmds if e[2].get("op") == 2 and e[2].get("wb") == 1]
    if bad:
        fails.append("%d invalidate command(s) wrote a line back" % len(bad))

    # 3. I-side clean is a no-op (CACHE-19): the core must not even issue it.
    bad = [e for e in icmds if e[2].get("op") == 1]
    if bad:
        fails.append("%d clean command(s) reached the instruction cache" % len(bad))

    # 4. The first D|clean|single line of the code line, the I-side window and
    #    the I|invalidate after it: the fetch between them must be an icache
    #    HIT with no icache command in between (the I line survived I|clean).
    d_clean = _find(events, "dcache", "cmd", op=1, scope=1, line=pa_code, wb=1)
    i_inval = _find(events, "icache", "cmd", op=2, scope=1, line=pa_code)
    if not d_clean:
        fails.append("no dcache clean-with-writeback for the code line")
    if not i_inval:
        fails.append("no icache invalidate of the code line")
    if d_clean and i_inval:
        c0, c1 = _cyc(d_clean[0]), _cyc(i_inval[0])
        if not (c0 < c1):
            fails.append("the icache invalidate is not after the D clean")
        hits = [e for e in _find(events, "icache", "hit", line=pa_code)
                if c0 < _cyc(e) < c1]
        if not hits:
            fails.append("the fetch after I|clean did not hit the I line "
                         "(clean must be a no-op)")
        icmd_between = [e for e in icmds if c0 < _cyc(e) < c1]
        if icmd_between:
            fails.append("an icache command ran between the D clean and the "
                         "I invalidate (I|clean must be a no-op)")
        fills = [e for e in _find(events, "icache", "miss", line=pa_code)
                 if _cyc(e) > c1]
        if not fills:
            fails.append("the fetch after I|invalidate did not miss the I line")
    # 5. D|invalidate|single line is issued exactly once for the code line:
    #    the enable=0 copy must be skipped by the core (CACHE-08).
    inv_single = _find(events, "dcache", "cmd", op=2, scope=1, line=pa_code)
    if len(inv_single) != 1:
        fails.append("dcache invalidate-single of the code line ran %d times, "
                     "expected 1 (the enable=0 one must not be issued)"
                     % len(inv_single))

    # 6. D|flush|single line writes back and drops: the later D read of the
    #    code line must miss.
    flushes = _find(events, "dcache", "cmd", op=3, scope=1, line=pa_code)
    if not flushes:
        fails.append("no dcache flush of the code line")
    elif not [e for e in _find(events, "dcache", "miss", line=pa_code)
              if _cyc(e) > _cyc(flushes[0])]:
        fails.append("the D read after flush did not miss (line was not dropped)")

    # 7. PA range: both lines of the range are enumerated, and only them.
    for pa, name in ((pa_r0, "R0"), (pa_r1, "R1")):
        inv = _find(events, "dcache", "cmd", op=2, scope=2, line=pa)
        if not inv:
            fails.append("range invalidate did not enumerate %s" % name)
        if not _find(events, "dcache", "cmd", op=1, scope=2, line=pa, wb=1):
            fails.append("range clean did not write %s back" % name)
        if not _find(events, "dcache", "cmd", op=3, scope=2, line=pa, wb=1):
            fails.append("range flush did not write %s back" % name)
        if inv and not [e for e in _find(events, "dcache", "miss", line=pa)
                        if _cyc(e) > _cyc(inv[0])]:
            fails.append("the D read of %s after range invalidate did not miss"
                         % name)

    # 8. `all`: invalidate drops without write-back, clean writes the D line
    #    back, flush writes it back and the next read misses.
    if not _find(events, "dcache", "cmd", op=2, scope=0):
        fails.append("no dcache invalidate-all enumeration")
    if not _find(events, "dcache", "cmd", op=1, scope=0, line=pa_d, wb=1):
        fails.append("invalidate-/clean-all did not write the D line back")
    fl_all = _find(events, "dcache", "cmd", op=3, scope=0, line=pa_d, wb=1)
    if not fl_all:
        fails.append("flush-all did not write the D line back")
    elif not [e for e in _find(events, "dcache", "miss", line=pa_d)
              if _cyc(e) > _cyc(fl_all[0])]:
        fails.append("the D read after flush-all did not miss")

    # 9. The no-line / MMIO command is a miss and reports no write-back.
    mmio = _find(events, "dcache", "cmd", op=2, scope=1, line=mmio_line)
    if not mmio:
        fails.append("the no-line invalidate did not reach the dcache")
    elif mmio[0][2].get("miss") != 1:
        fails.append("the no-line invalidate was not reported as a miss")

    # 10. Enable test: the clean after re-enabling must still find the dirty
    #     line (its write-back is logged after the enable=0 window).
    cl_code = _find(events, "dcache", "cmd", op=1, scope=1, line=pa_code, wb=1)
    if len(cl_code) < 5:
        fails.append("only %d clean-with-writeback events for the code line; "
                     "the enable=0 no-op window lost the dirty line"
                     % len(cl_code))

    # 11. `cache_addr_start` = 56-bit PA (CACHE-18 / ISS-534): the single-line
    #     invalidate at PA_HIGH must be logged with the FULL line address and
    #     reported as a miss; no command may use its low-48 alias (PA_D).
    high_line = g.PA_HIGH & ~0x3F
    high = _find(events, "dcache", "cmd", op=2, scope=1, line=high_line)
    if not high:
        fails.append("the 56-bit addr_start invalidate was not logged at "
                     "%#x (truncated to 48 bits?)" % high_line)
    elif high[0][2].get("miss") != 1:
        fails.append("the 56-bit addr_start invalidate was not a miss")
    aliases = _find(events, "dcache", "cmd", op=2, scope=1, line=pa_d)
    # A_D 只在 D 侧单行 flush 时被 invalidate；F2 之后不得再有别名命令。
    if high:
        last_high = _cyc(high[0])
        if any(_cyc(e) > last_high for e in aliases):
            fails.append("a command used the low-48 alias of the 56-bit "
                         "addr_start (line %#x) after F2" % pa_d)
    return fails


# ---------------------------------------------------------------------------
# 结果缓冲判据
# ---------------------------------------------------------------------------
def unpack(data: bytes):
    if len(data) % 8:
        return None
    return [struct.unpack(">Q", data[i:i + 8])[0]
            for i in range(0, len(data), 8)]


def check_records(recs, expected: list) -> list:
    if recs is None:
        return ["stream is not a whole number of 8-byte records"]
    fails = []
    if len(recs) != len(expected):
        fails.append("records: got %d, expected %d" % (len(recs), len(expected)))
    for i, ((name, want), got) in enumerate(zip(expected, recs)):
        if got != want:
            fails.append("record %d (%s): 0x%016x != 0x%016x"
                         % (i, name, got, want))
    return fails


def self_test(root: pathlib.Path, log_text: str) -> int:
    exp = expected_records(root)
    base = [v for _, v in exp]
    fails = check_records(base, exp)
    print("  [%s] control record stream accepted" % ("PASS" if not fails else "FAIL"))
    bad = 1 if fails else 0
    for i in range(len(exp)):
        mutated = list(base)
        mutated[i] ^= 1
        if not check_records(mutated, exp):
            print("  [FAIL] record %d mutation not rejected (%s)" % (i, exp[i][0]))
            bad += 1
    print("  [%s] every record mutation rejected (%d records)"
          % ("PASS" if not bad else "FAIL", len(exp)))

    events = parse_log(log_text)
    g = GEN
    ctl = check_log(events, g)
    print("  [%s] control log accepted" % ("PASS" if not ctl else "FAIL"))
    if ctl:
        for f in ctl:
            print("      %s" % f)
        bad += 1

    def mutated_log(name, fn):
        nonlocal bad
        text = fn(log_text)
        if text == log_text:
            print("  [FAIL] log mutation %r changed nothing" % name)
            bad += 1
            return
        got = check_log(parse_log(text), g)
        if not got:
            print("  [FAIL] log mutation %r not rejected" % name)
            bad += 1
        else:
            print("  [PASS] log mutation %r rejected (%s)" % (name, got[0]))

    def add_wb(text):
        # Make the invalidate of the code line look like a write-back.
        pat = re.compile(r"(WumingCache\[dcache\]: cmd op=2 scope=1 line=0x0*%x [^\n]*?)( cycle=)"
                         % g.PA_CODE)
        return pat.sub(r"\1 wb=1\2", text, count=1)

    def drop_i_hit(text):
        # Remove the icache hit that proves I|clean kept the line: the check
        # must then fail (no hit between the D clean and the I invalidate).
        return re.sub(r"^WumingCache\[icache\]: hit line=0x0*%x[^\n]*\n" % g.PA_CODE,
                      "", text, flags=re.M)

    def dup_inval(text):
        # A second dcache invalidate-single of the code line means the enable=0
        # gate failed.
        pat = re.compile(r"^(WumingCache\[dcache\]: cmd op=2 scope=1 line=0x0*%x[^\n]*)$"
                         % g.PA_CODE, re.M)
        m = pat.search(text)
        return text if not m else text[:m.end()] + "\n" + m.group(1) + text[m.end():]

    def drop_flush_wb(text):
        # Remove the flush write-back of the code line: flush must write back.
        pat = re.compile(r"^WumingCache\[dcache\]: cmd op=3 scope=1 line=0x0*%x[^\n]* wb=1[^\n]*\n"
                         % g.PA_CODE, re.M)
        return pat.sub("", text, count=1)

    def truncate_high(text):
        # Log the 56-bit single-line command at its low-48 alias: the new
        # `CACHE-18` assertion must reject it (ISS-534).
        return re.sub(r"(cmd op=2 scope=1 line=0x0*%x)" % (g.PA_HIGH & ~0x3F),
                      "cmd op=2 scope=1 line=0x%x" % (g.PA_D & ~0x3F),
                      text, count=1)

    mutated_log("invalidate writes back", add_wb)
    mutated_log("I|clean did not keep the line (no fetch hit)", drop_i_hit)
    mutated_log("enable=0 invalidate still issued", dup_inval)
    mutated_log("flush does not write back", drop_flush_wb)
    mutated_log("56-bit addr_start logged truncated", truncate_high)
    print("check_cfx5_maint: self-test %s" % ("PASS" if not bad else "FAIL"))
    return 0 if not bad else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--stream", default=None)
    ap.add_argument("--log", default=None)
    ap.add_argument("--root", default=None)
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--expected", action="store_true")
    args = ap.parse_args()

    root = pathlib.Path(args.root).resolve() if args.root else DEFAULT_ROOT
    try:
        exp = expected_records(root)
    except SystemExit as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if args.expected:
        for i, (name, value) in enumerate(exp):
            print("%2d %-56s 0x%016x" % (i, name, value))
        return 0
    if args.self_test:
        if not args.log:
            ap.error("--self-test needs --log (the baseline simulation log)")
        return self_test(root, pathlib.Path(args.log).read_text(
            encoding="utf-8", errors="replace"))
    if not args.stream or not args.log:
        ap.error("--stream and --log are required unless --self-test/--expected")

    fails = check_records(unpack(pathlib.Path(args.stream).read_bytes()), exp)
    events = parse_log(pathlib.Path(args.log).read_text(
        encoding="utf-8", errors="replace"))
    fails += check_log(events, GEN)
    if fails:
        print("check_cfx5_maint: FAIL")
        for f in fails:
            print("  [FAIL] %s" % f)
        return 1
    print("check_cfx5_maint: PASS (%d records, %d cache events)"
          % (len(exp), len(events)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
