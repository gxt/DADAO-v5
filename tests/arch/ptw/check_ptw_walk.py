#!/usr/bin/env python3
"""check_ptw_walk -- `tests/arch/ptw/ptw_walk.S` 的独立判据（`m16-chipyard-007`）。

探针把每个检查点 / 故障帧的 8 字节实测值写进结果缓冲（`__REC`）。本脚本**不保存
期望常量**，而是现场：

  * 从 `.tao/contracts/contract-see.md` §6.1/§6.1.1 解析 cause 大类与子原因位号，
    并与 `.tao/adr/adr-0056-*.md` 逐位互校（`AGENTS.md`「Independent oracle」）；
  * 从 `tests/arch/ptw/gen_ptw_walk_tables.py`（页表几何的单一真源）取 PA/VA/
    PTE 期望值，不复制任何索引或位域。

判据：
  * 记录数 == 31（`ptw_walk.S` 的记录顺序），每条 8 字节；
  * 每个检查点逐位等于期望；
  * 故障帧 = `CFXMEM`/`CFXPERM` 的 cause one-hot + 该 cause 独占 wyde 里的**一位**
    子原因（spec 顺序：缺页 → 小页缺失 → HSJU → R/W/X），`cause_info` = 访问 VA；
  * `CFXREG` 只有一个大类位、两个 wyde 全 0（`§3.6` (五)）；
  * `--log` 给出时，另比 A/D 回写事件：同一 PTE 上**恰好两次** `ad-wb`（clean 各一次），
    值依次为 A=1,D=0 与 A=1,D=1；`ad-fail` 为零（未注入时）。

用法：
  check_ptw_walk.py --stream <file> [--log <sim log>] [--root <repo>] [--expect-adwb]
  check_ptw_walk.py --self-test [--root <repo>]     # 合成坏流 ⇒ 每条断言都有可达 FAIL
"""

from __future__ import annotations

import argparse
import importlib.util
import pathlib
import re
import sys

_REPO = pathlib.Path(__file__).resolve().parents[3]
if str(_REPO / "tests" / "shared") not in sys.path:
    sys.path.insert(0, str(_REPO / "tests" / "shared"))
import signature                      # noqa: E402  (签名流机制：单一实现)

HERE = pathlib.Path(__file__).resolve().parent


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_geometry():
    return _load("ptw_walk_geometry", HERE / "gen_ptw_walk_tables.py")


def load_bit_parser():
    return _load("ptw_regs_bits", HERE / "check_ptw_regs.py")


def bit_table(root: pathlib.Path) -> dict:
    """Cause classes + sub-cause bits, parsed from the contract and cross-checked."""
    mod = load_bit_parser()
    return mod.bit_table(root)


# ---- the probe's record order (semantic names only; values are derived) ----
DATA_CHECKS = [
    "normal page payload",           # 1
    "PTE before clean (A=0,D=0)",    # 2
    "PTE after first clean (A=1)",   # 3
    "PTE after store (D still local)",  # 4
    "PTE after second clean (D=1)",  # 5
    "PTE after a clean with nothing pending",  # 6
    "stored value read back",         # 7
    "superpage fragment 0",           # 8
    "superpage fragment 1",           # 9
    "stub executed through a translation",  # 10
]

# (name, cause class, sub-cause name or None, va or None)
FAULTS = [
    ("L1 P=0, SP=0", "CFXMEM", "DGPTRAP", "VA_L1_NP"),
    ("L1 P=0, SP=1", "CFXMEM", "DSPTRAP", "VA_L1_SP"),
    ("L1 SPF bit = 0", "CFXMEM", "DSPFTRAP", "VA_L1_SPF"),
    ("L2 P=0", "CFXMEM", "DGPTRAP", "VA_L2B0"),
    ("L2 GPF bit = 0", "CFXMEM", "DGPFTRAP", "VA_L2B1"),
    ("HSJU = U only, running hypv", "CFXPERM", "NHPERM", "VA_L2B2"),
    ("store to W=0 page", "CFXPERM", "NWPERM", "VA_W0"),
    ("fetch from X=0 page", "CFXPERM", "NXPERM", "VA_NOX"),
    ("tlb_control scope = 11", "CFXREG", None, None),
]

N_RECORDS = len(DATA_CHECKS) + 2 * len(FAULTS) + 1 + 2


def expected_records(table: dict, geom, expect_adwb: bool) -> list:
    cls = table["class"]
    sub = table["sub"]
    cfxmem = 1 << cls["CFXMEM"]
    cfxperm = 1 << cls["CFXPERM"]
    cfxreg = 1 << cls["CFXREG"]
    recs = [geom.PAYLOAD,
            geom.DATA_PTE_A0D0,
            geom.DATA_PTE_A1D0,
            geom.DATA_PTE_A1D0,
            geom.DATA_PTE_A1D1,
            geom.DATA_PTE_A1D1,
            geom.STORE_VAL,
            geom.MAGIC0,
            geom.MAGIC1,
            geom.STUB_MARK]
    for _, cause, subname, va_name in FAULTS:
        base = cfxmem if cause == "CFXMEM" else cfxperm if cause == "CFXPERM" else cfxreg
        word = base | (0 if subname is None else 1 << sub[subname])
        recs.append(word)
        # `CFXREG`'s `cause_info` is the faulting instruction's encoding — the
        # checker cannot know the word, so it only rules on the class/structure.
        recs.append(0 if va_name is None else getattr(geom, va_name))
        if va_name is None:
            recs[-1] = None
    recs.append(geom.FRESH_MAGIC)          # check 20: the fresh page reads correctly
    if expect_adwb:
        recs += [cfxmem | (1 << sub["ADWBFAIL"]), geom.FRESH_PTE_PA]
    else:
        recs += [0, 0]
    if len(recs) != N_RECORDS:
        raise SystemExit("check_ptw_walk: expected %d records, built %d"
                         % (N_RECORDS, len(recs)))
    return recs


def unpack(data: bytes, count: int) -> list:
    """解析签名流（机制只有 `tests/shared/signature.py` 一份）。"""
    try:
        return signature.parse(data, count, sentinel=False)
    except signature.SignatureError as exc:
        raise SystemExit("check_ptw_walk: %s" % exc)


def structure_problems(recs: list, table: dict) -> list:
    """Cause-id layout rules (`DADAO-12` §3.6 (三)(四)(五))."""
    cls = table["class"]
    problems = []
    for i in range(len(DATA_CHECKS), len(DATA_CHECKS) + 2 * len(FAULTS), 2):
        cause = recs[i]
        klass = cause & 0xFFFF
        wyde2 = (cause >> 32) & 0xFFFF
        wyde3 = (cause >> 48) & 0xFFFF
        if klass not in (1 << cls["CFXMEM"], 1 << cls["CFXPERM"], 1 << cls["CFXREG"]):
            problems.append("record %d: unexpected cause class 0x%x" % (i, klass))
            continue
        if cause >> 16 & 0xFFFF:
            problems.append("record %d: [31:16] is not zero" % i)
        if klass == 1 << cls["CFXMEM"]:
            if wyde2:
                problems.append("record %d: CFXMEM with a non-zero wyde2" % i)
            if bin(wyde3).count("1") != 1:
                problems.append("record %d: CFXMEM wyde3 is not one-hot" % i)
        elif klass == 1 << cls["CFXPERM"]:
            if wyde3:
                problems.append("record %d: CFXPERM with a non-zero wyde3" % i)
            if bin(wyde2).count("1") != 1:
                problems.append("record %d: CFXPERM wyde2 is not one-hot" % i)
        else:
            if wyde2 or wyde3:
                problems.append("record %d: CFXREG with a non-zero sub-cause wyde" % i)
    return problems


# ---- A/D write-back events (simulator log) --------------------------------
_WB_RE = re.compile(r"WumingPtw: ad-wb kind=(\w+) op=(\d) pte=0x([0-9a-f]+) value=0x([0-9a-f]+)")
_FAIL_RE = re.compile(r"WumingPtw: ad-fail kind=(\w+) pte=0x([0-9a-f]+)")


def wb_problems(log_text: str, geom, expect_adwb: bool) -> list:
    problems = []
    wbs = [(m.group(1), int(m.group(2)), int(m.group(3), 16), int(m.group(4), 16))
           for m in _WB_RE.finditer(log_text)]
    fails = [(m.group(1), int(m.group(2), 16)) for m in _FAIL_RE.finditer(log_text)]
    data_wb = [w for w in wbs if w[2] == geom.DATA_PTE_PA]
    if len(data_wb) != 2:
        problems.append("data-page PTE write-backs: expected 2, saw %d" % len(data_wb))
    else:
        if data_wb[0][3] != geom.DATA_PTE_A1D0:
            problems.append("first write-back value 0x%x != 0x%x (A=1,D=0)"
                            % (data_wb[0][3], geom.DATA_PTE_A1D0))
        if data_wb[1][3] != geom.DATA_PTE_A1D1:
            problems.append("second write-back value 0x%x != 0x%x (A=1,D=1)"
                            % (data_wb[1][3], geom.DATA_PTE_A1D1))
    if expect_adwb:
        if not fails:
            problems.append("expected an ADWBFAIL write-back failure event, saw none")
        elif fails[0][1] != geom.FRESH_PTE_PA:
            problems.append("ADWBFAIL info 0x%x != fresh PTE 0x%x"
                            % (fails[0][1], geom.FRESH_PTE_PA))
    elif fails:
        problems.append("unexpected ADWBFAIL events: %r" % (fails,))
    return problems


def check(recs, expected, table, log_text, geom, expect_adwb, adwb_only=False):
    problems = []
    if len(recs) != len(expected):
        problems.append("record count %d != %d" % (len(recs), len(expected)))
    for i, (got, want) in enumerate(zip(recs, expected)):
        if want is not None and got != want:
            problems.append("record %d: 0x%016x != 0x%016x" % (i, got, want))
    if len(recs) >= len(expected) and not adwb_only:
        problems += structure_problems(recs, table)
    # The write-back event checks belong to the full image (the A/D case); the
    # ADWBFAIL image reports the failure through its exception frame instead.
    if log_text is not None and not adwb_only:
        problems += wb_problems(log_text, geom, expect_adwb)
    return problems


def selftest(recs, expected, table, geom):
    """Feed synthetic bad streams: every assertion must have a reachable FAIL."""
    cases = []

    def add(name, mutate):
        bad = list(expected)
        mutate(bad)
        cases.append((name, bad))

    add("payload wrong", lambda r: r.__setitem__(0, r[0] ^ 1))
    add("PTE A bit before clean", lambda r: r.__setitem__(1, r[1] | 0x8))
    add("first clean wrote D", lambda r: r.__setitem__(2, r[2] | 0x4))
    add("store wrote D eagerly", lambda r: r.__setitem__(3, r[3] | 0x4))
    add("second clean missed D", lambda r: r.__setitem__(4, r[4] & ~0x4))
    add("stored value lost", lambda r: r.__setitem__(6, 0))
    add("superpage fragment 1 wrong", lambda r: r.__setitem__(8, 0))
    add("stub not executed", lambda r: r.__setitem__(9, 0))
    add("wrong missing-page class", lambda r: r.__setitem__(10, r[10] ^ (1 << 52)))
    add("HSJU reported as CFXMEM", lambda r: r.__setitem__(20, 1 << 1 | 1 << 52))
    add("perm sub-cause in the wrong wyde", lambda r: r.__setitem__(22, 1 << 7 | 1 << 37 << 48))
    add("NXPERM missing", lambda r: r.__setitem__(24, 1 << 7 | 1 << 36 << 32))
    add("CFXREG with a sub-cause", lambda r: r.__setitem__(26, 1 << 2 | 1 << 48))
    add("fresh page wrong", lambda r: r.__setitem__(28, 0))
    add("missing record", lambda r: r.pop())
    bad_log = "WumingPtw: ad-wb kind=cmd op=1 pte=0x%x value=0x%x\n" % (
        geom.DATA_PTE_PA, geom.DATA_PTE_A1D0)
    bad_log += "WumingPtw: ad-wb kind=cmd op=1 pte=0x%x value=0x%x\n" % (
        geom.DATA_PTE_PA, geom.DATA_PTE_A1D0)
    bad_log += "WumingPtw: ad-wb kind=replace pte=0x%x value=0x%x\n" % (
        geom.DATA_PTE_PA, geom.DATA_PTE_A1D1)

    ok = 0
    bad_count = 0
    for name, bad in cases:
        got = check(bad, expected, table, None, geom, False)
        if got:
            ok += 1
        else:
            print("  [FAIL] self-test: '%s' was not detected" % name)
            bad_count += 1
    # the write-back event check has its own FAIL paths
    for name, log, expect in [
            ("three write-backs", bad_log, False),
            ("wrong first value", bad_log.replace("value=0x%x" % geom.DATA_PTE_A1D0,
                                                  "value=0x%x" % geom.DATA_PTE_A1D1), False),
            ("missing ADWBFAIL", bad_log, True)]:
        if wb_problems(log, geom, expect):
            ok += 1
        else:
            print("  [FAIL] self-test: '%s' was not detected" % name)
            bad_count += 1
    # the good stream itself must pass
    if check(recs, expected, table, None, geom, False):
        print("  [FAIL] self-test: the expected stream does not pass")
        bad_count += 1
    else:
        ok += 1
    print("self-test: %d assertion(s) have a reachable FAIL, %d surprise(s)" % (ok, bad_count))
    return 1 if bad_count else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stream")
    ap.add_argument("--log")
    ap.add_argument("--root", default=None)
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--adwb-only", action="store_true",
                    help="stream from the CASE_ADWB=1 image (records: fresh magic + frame)")
    ap.add_argument("--expect-adwb", action="store_true",
                    help="the build under test forces page-table writes to fail")
    args = ap.parse_args()

    root = pathlib.Path(args.root) if args.root else HERE.parent.parent.parent
    table = bit_table(root)
    geom = load_geometry()
    expected = expected_records(table, geom, args.expect_adwb)
    if args.adwb_only:
        cfxmem = 1 << table["class"]["CFXMEM"]
        expected = [geom.FRESH_MAGIC]
        expected += ([cfxmem | (1 << table["sub"]["ADWBFAIL"]), geom.FRESH_PTE_PA]
                     if args.expect_adwb else [0, 0])

    if args.self_test:
        return selftest(expected, expected, table, geom)
    if not args.stream:
        raise SystemExit("check_ptw_walk: --stream is required")
    recs = unpack(pathlib.Path(args.stream).read_bytes(), len(expected))
    log_text = pathlib.Path(args.log).read_text(errors="replace") if args.log else None
    problems = check(recs, expected, table, log_text, geom, args.expect_adwb,
                     adwb_only=args.adwb_only)
    for p in problems:
        print("  [FAIL] %s" % p)
    if problems:
        print("check_ptw_walk: %d problem(s) in %d record(s)" % (len(problems), len(recs)))
        return 1
    print("check_ptw_walk: %d record(s) match (A/D write-backs %s)"
          % (len(recs), "expected (injected failure)" if args.expect_adwb else "2, no failure"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
