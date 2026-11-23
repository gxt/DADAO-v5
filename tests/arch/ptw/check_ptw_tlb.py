#!/usr/bin/env python3
"""check_ptw_tlb -- `tests/arch/ptw/ptw_tlb.S` 的独立判据（`m16-chipyard-008`）。

判据不保存期望常量：页表几何、PTE 值与数据 magic 全部从
`tests/arch/ptw/gen_ptw_tlb_tables.py` 现场取；cause 大类与子原因位号从
`.tao/contracts/contract-see.md` §6.1/§6.1.1 解析并与 `adr-0056` 逐位互校。

判据分两层：
  * **结果缓冲**（`__REC` 记录）：逐条等于生成器算出的期望值（命中读旧数据、
    淘汰后重步查读新数据、A/D 回写后的 PTE、双表失效矩阵）；
  * **仿真日志**（`WumingPtw:` 事件）：
      - `tlb-evict` 的受害者序列必须等于 LRU 模型的期望序列（`cp` 前后
        两侧都由生成器的 VA / 几何算出）；
      - 同一 PTE 的回写次数与值（OR 合并：I 先写 A、D 再写 A+D）；
      - 默认运行 `ad-fail` 为 0；注入运行（`--expect-adwb`）恰为两次且
        `cause_info` = 该 PTE 的物理地址。

用法：
  check_ptw_tlb.py --stream <file> --log <sim log> [--root <repo>]
  check_ptw_tlb.py --stream <file> --log <sim log> --or-only --expect-adwb
  check_ptw_tlb.py --self-test [--root <repo>]
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
    return _load("ptw_tlb_geometry", HERE / "gen_ptw_tlb_tables.py")


def bit_table(root: pathlib.Path) -> dict:
    """Cause classes + sub-cause bits, parsed from the contract (reuse the PTW
    checker's parser, which cross-checks `adr-0056`)."""
    mod = _load("ptw_regs_bits", HERE / "check_ptw_regs.py")
    return mod.bit_table(root)


PAGE_NORMAL = 1 << 16
PAGE_SUPER = 1 << 29


def tag(va: int, superpage: bool) -> int:
    return va & ~((PAGE_SUPER if superpage else PAGE_NORMAL) - 1)


def expected_full(g, table: dict) -> list:
    """Record order = the `__REC` calls of `ptw_tlb.S` (full image)."""
    recs = []
    # P1: fill / hit after a silent PTE change / invalid+VA re-walk
    recs += [g.M_P[1], g.M_P[1], g.M_P_NEW[1]]
    # P2: eight fills, P1 hit, P9 fill, P8 hit, P1 re-walk
    recs += [g.M_P[k] for k in range(1, 9)]
    recs += [g.M_P[1], g.M_P[9], g.M_P[8], g.M_P_NEW[1]]
    # P3: S1..S4, S1 hit, S5 fill, S2 re-walk, S1 hit
    recs += [g.M_SUPER[k] for k in range(1, 5)]
    recs += [g.M_SUPER[1], g.M_SUPER[5], g.M_SUPER2_NEW, g.M_SUPER[1]]
    # P4: I-only page, A only then A+D through the data table
    recs += [g.PX_PTE_A1D0, g.PX_PTE_A1D1]
    # P5: two clean frames (no fault), then the OR-merged PTE
    recs += [0, 0, 0, 0, g.OR_PTE_A1D1]
    # P6: invalid / clean / flush matrix
    for op in ("invalid", "clean", "flush"):
        if op == "invalid":
            recs += [g.PTE_PI, g.PTE_PD]
            recs += [g.PI_MARK_NEW, g.M_PD_NEW]
        elif op == "clean":
            recs += [g.PTE_PI | 0x8, g.PTE_PD | 0x8]
            recs += [g.PI_MARK_OLD, g.M_PD]
        else:
            recs += [g.PTE_PI | 0x8, g.PTE_PD | 0x8]
            recs += [g.PI_MARK_NEW, g.M_PD_NEW]
    # P7: invalid + scope=VA clears only the entry containing `start`
    recs += [g.M_P[1], g.M_P[2], g.M_P_NEW[1], g.M_P[2]]
    # P8: asidAny / G (the probe writes cfx_ptw_tlb_asid = 1 first)
    recs += [g.M_G, g.M_NG, g.PTE_G_NEW, g.M_G, g.M_NG_NEW,
             g.PTE_NG_A1, g.M_G_NEW, g.PTE_G_A1]
    return recs


def expected_or(g, table: dict, expect_adwb: bool) -> list:
    """`CASE_OR=1` image: two clean frames + the final PTE."""
    cfxmem = 1 << table["class"]["CFXMEM"]
    adwb = cfxmem | (1 << table["sub"]["ADWBFAIL"])
    if expect_adwb:
        return [adwb, g.PTE_PA_OR, adwb, g.PTE_PA_OR, g.OR_PTE_A1D0]
    return [0, 0, 0, 0, g.OR_PTE_A1D1]


# ---- log events ------------------------------------------------------------
_EVICT_RE = re.compile(
    r"WumingPtw: tlb-evict side=(\d) super=(\d) idx=\s*(\d+) va=0x([0-9a-f]+)")
_WB_RE = re.compile(
    r"WumingPtw: ad-wb kind=(\w+) op=(\d) pte=0x([0-9a-f]+) value=0x([0-9a-f]+)")
_FAIL_RE = re.compile(r"WumingPtw: ad-fail kind=(\w+) pte=0x([0-9a-f]+)")


def expected_evictions(g) -> list:
    """Victim sequence of the LRU model, derived from the probe's access order.

    P2: the P9 fill evicts P1 (LRU after P1 was re-touched and P2..P8 walked),
        the P1 re-fill evicts P2.
    P3: the S5 fill evicts S2 (S1 was re-touched), the S2 re-fill evicts S3.
    """
    return [tag(g.VA_P[1], False), tag(g.VA_P[2], False),
            tag(g.VA_SUPER[2], True), tag(g.VA_SUPER[3], True)]


def log_problems(log_text: str, g, table: dict, or_only: bool,
                 expect_adwb: bool) -> list:
    problems = []
    evicts = [(int(m.group(2)), int(m.group(4), 16))
              for m in _EVICT_RE.finditer(log_text)]
    wbs = [(m.group(1), int(m.group(2)), int(m.group(3), 16), int(m.group(4), 16))
           for m in _WB_RE.finditer(log_text)]
    fails = [(m.group(1), int(m.group(2), 16)) for m in _FAIL_RE.finditer(log_text)]

    or_wb = [w for w in wbs if w[2] == g.PTE_PA_OR]
    if expect_adwb:
        if len(fails) != 2:
            problems.append("ADWBFAIL events: expected 2, saw %d" % len(fails))
        for _, pa in fails:
            if pa != g.PTE_PA_OR:
                problems.append("ADWBFAIL cause_info 0x%x != OR PTE 0x%x"
                                % (pa, g.PTE_PA_OR))
    else:
        if fails:
            problems.append("unexpected ADWBFAIL events: %r" % (fails,))
        if len(or_wb) != 2:
            problems.append("OR-page write-backs: expected 2, saw %d" % len(or_wb))
        else:
            want = [g.OR_PTE_A1D0, g.OR_PTE_A1D1]
            for i, (w, want_v) in enumerate(zip(or_wb, want)):
                if w[3] != want_v:
                    problems.append(
                        "OR write-back %d value 0x%x != 0x%x (OR merge order)"
                        % (i, w[3], want_v))
    if not or_only:
        got = [va for _, va in evicts]
        want = expected_evictions(g)
        if got != want:
            problems.append("tlb-evict victim sequence %s != %s"
                            % ([hex(v) for v in got], [hex(v) for v in want]))
    return problems


def structure_problems(recs: list, table: dict, or_only: bool,
                       expect_adwb: bool) -> list:
    """`DADAO-12` §3.6 (三)(四)(五) on the recorded ADWBFAIL frames."""
    problems = []
    if expect_adwb and or_only:
        cls = table["class"]
        for i in (0, 2):
            cause = recs[i]
            klass = cause & 0xFFFF
            wyde2 = (cause >> 32) & 0xFFFF
            wyde3 = (cause >> 48) & 0xFFFF
            if klass != 1 << cls["CFXMEM"]:
                problems.append("record %d: frame class 0x%x is not CFXMEM" % (i, klass))
                continue
            if wyde2:
                problems.append("record %d: CFXMEM with a non-zero wyde2" % i)
            if bin(wyde3).count("1") != 1:
                problems.append("record %d: CFXMEM wyde3 is not one-hot" % i)
            # `sub` is the absolute bit number; the frame check reads wyde3.
            if wyde3 != 1 << (table["sub"]["ADWBFAIL"] - 48):
                problems.append("record %d: sub-cause is not [56] ADWBFAIL" % i)
    return problems


def unpack(data: bytes, count: int) -> list:
    """解析签名流（机制只有 `tests/shared/signature.py` 一份）。"""
    try:
        return signature.parse(data, count, sentinel=False)
    except signature.SignatureError as exc:
        raise SystemExit("check_ptw_tlb: %s" % exc)


def check(recs, expected, table, log_text, g, or_only, expect_adwb):
    problems = []
    if len(recs) != len(expected):
        problems.append("record count %d != %d" % (len(recs), len(expected)))
    for i, (got, want) in enumerate(zip(recs, expected)):
        if got != want:
            problems.append("record %d: 0x%016x != 0x%016x" % (i, got, want))
    problems += structure_problems(recs, table, or_only, expect_adwb)
    if log_text is not None:
        problems += log_problems(log_text, g, table, or_only, expect_adwb)
    return problems


def selftest(table: dict) -> int:
    g = load_geometry()
    full = expected_full(g, table)
    good_log = "\n".join(
        "WumingPtw: tlb-evict side=%d super=%d idx=%d va=0x%x"
        % (0, 1 if sup else 0, i, va)
        for i, (va, sup) in enumerate([(v, s) for v, s in zip(
            [tag(g.VA_P[1], False), tag(g.VA_P[2], False),
             tag(g.VA_SUPER[2], True), tag(g.VA_SUPER[3], True)],
            [False, False, True, True])]))
    good_log += "\nWumingPtw: ad-wb kind=cmd op=1 pte=0x%x value=0x%x" % (
        g.PTE_PA_OR, g.OR_PTE_A1D0)
    good_log += "\nWumingPtw: ad-wb kind=cmd op=1 pte=0x%x value=0x%x" % (
        g.PTE_PA_OR, g.OR_PTE_A1D1)

    cases = []

    def add(name, mutate):
        bad = list(full)
        mutate(bad)
        cases.append((name, bad, good_log))

    add("first fill wrong", lambda r: r.__setitem__(0, r[0] ^ 1))
    add("hit re-read the PTE", lambda r: r.__setitem__(1, g.M_P_NEW[1]))
    add("invalid did not re-walk", lambda r: r.__setitem__(2, g.M_P[1]))
    add("P8 was evicted", lambda r: r.__setitem__(13, g.M_P_NEW[8]))
    add("P1 was not the LRU victim", lambda r: r.__setitem__(14, g.M_P[1]))
    add("superpage LRU picked S1", lambda r: r.__setitem__(21, g.M_SUPER[2]))
    add("I side set D", lambda r: r.__setitem__(23, g.PX_PTE_A1D1))
    add("OR merge lost D", lambda r: r.__setitem__(29, g.OR_PTE_A1D0))
    add("invalid wrote back A/D", lambda r: r.__setitem__(30, g.PTE_PI | 0x8))
    add("clean did not write back I", lambda r: r.__setitem__(34, g.PTE_PI))
    add("clean dropped the entry", lambda r: r.__setitem__(36, g.PI_MARK_NEW))
    add("flush did not delete I", lambda r: r.__setitem__(40, g.PI_MARK_OLD))
    add("flush did not write back D", lambda r: r.__setitem__(39, g.PTE_PD))
    add("scope=VA cleared the neighbour", lambda r: r.__setitem__(45, g.M_P_NEW[2]))
    add("scope=VA did not clear P1", lambda r: r.__setitem__(44, g.M_P[1]))
    add("asidAny=0 flushed the G entry", lambda r: r.__setitem__(49, g.M_G_NEW))
    add("asidAny=0 cleared the matching G=0 entry", lambda r: r.__setitem__(50, g.M_NG))
    add("asidAny=1 did not flush the G entry", lambda r: r.__setitem__(52, g.M_G))
    add("G entry A/D not written back", lambda r: r.__setitem__(53, g.PTE_G_NEW))
    add("missing record", lambda r: r.pop())

    ok = 0
    surprises = 0
    for name, bad, log in cases:
        if check(bad, full, table, log, g, False, False):
            ok += 1
        else:
            print("  [FAIL] self-test: '%s' was not detected" % name)
            surprises += 1

    # log-level FAIL paths
    bad_logs = []
    bad_logs.append(("eviction order changed", good_log.replace(
        "va=0x%x" % tag(g.VA_P[1], False), "va=0x%x" % tag(g.VA_P[3], False), 1)))
    bad_logs.append(("only one OR write-back",
                     good_log.rsplit("\n", 1)[0]))
    bad_logs.append(("OR write-back overwrote A",
                     good_log.replace("value=0x%x" % g.OR_PTE_A1D1,
                                      "value=0x%x" % g.OR_PTE_A1D0)))
    bad_logs.append(("unexpected ADWBFAIL", good_log + "\nWumingPtw: ad-fail kind=cmd pte=0x%x"
                     % g.PTE_PA_OR))
    for name, log in bad_logs:
        if check(full, full, table, log, g, False, False):
            ok += 1
        else:
            print("  [FAIL] self-test: '%s' was not detected" % name)
            surprises += 1

    # injected mode: the failure frames are the expected difference
    or_good = expected_or(g, table, True)
    or_log = "\n".join("WumingPtw: ad-fail kind=cmd pte=0x%x" % g.PTE_PA_OR for _ in range(2))
    if not check(or_good, or_good, table, or_log, g, True, True):
        ok += 1
    else:
        print("  [FAIL] self-test: the injected ADWBFAIL stream does not pass")
        surprises += 1
    if not check(list(or_good), or_good, table, "\n".join(
            ["WumingPtw: ad-fail kind=cmd pte=0x%x" % g.PTE_PA_OR] * 1), g, True, True):
        print("  [FAIL] self-test: a single ADWBFAIL frame was not detected")
        surprises += 1
    else:
        ok += 1
    # the good full stream itself must pass
    if check(full, full, table, good_log, g, False, False):
        print("  [FAIL] self-test: the expected stream does not pass")
        surprises += 1
    else:
        ok += 1
    print("self-test: %d assertion(s) have a reachable FAIL, %d surprise(s)"
          % (ok, surprises))
    return 1 if surprises else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stream")
    ap.add_argument("--log")
    ap.add_argument("--root", default=None)
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--or-only", action="store_true",
                    help="stream from the CASE_OR=1 image")
    ap.add_argument("--expect-adwb", action="store_true",
                    help="the build under test fails the D-side clean write-back")
    args = ap.parse_args()

    root = pathlib.Path(args.root) if args.root else HERE.parent.parent.parent
    table = bit_table(root)
    g = load_geometry()
    if args.or_only:
        expected = expected_or(g, table, args.expect_adwb)
    else:
        expected = expected_full(g, table)

    if args.self_test:
        return selftest(table)
    if not args.stream:
        raise SystemExit("check_ptw_tlb: --stream is required")
    recs = unpack(pathlib.Path(args.stream).read_bytes(), len(expected))
    log_text = pathlib.Path(args.log).read_text(errors="replace") if args.log else None
    problems = check(recs, expected, table, log_text, g, args.or_only,
                     args.expect_adwb)
    for p in problems:
        print("  [FAIL] %s" % p)
    if problems:
        print("check_ptw_tlb: %d problem(s) in %d record(s)" % (len(problems), len(recs)))
        return 1
    print("check_ptw_tlb: %d record(s) match (evictions / A-D merge %s)"
          % (len(recs), "injected failure" if args.expect_adwb else "checked"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
