#!/usr/bin/env python3
"""check_vastdcache -- `tools/chipyard/dcache/vastdcache.S` 的独立判据（`m16-chipyard-009`）。

判据不保存期望常量：magic、PTE 值、组索引、cause one-hot 全部从
`gen_vastdcache_tables.py` 现场取（cause 再经 `tests/arch/ptw/check_ptw_regs.bit_table`
与 `contract-see §6.1` / `spec/DADAO-12 §3.6` 互校；扁平模型见 `ADR-0062`）。两处"机器码字"（`.stubdata`
的 8 B）由证据脚本从 ELF 取出后经 `--stub-word` 传入，判据不猜编码。

两层断言：
  * **结果缓冲**：35 条 8 字节记录逐条等于生成器算出的期望值
    （命中/8 路/LRU 重填/写回前后/PTW 新旧映射）；
  * **仿真日志**（`WumingCache[dcache]:` 事件）：
      - 同址 1 次缺失填充 + 4 次命中（计数不写死，按段内期望数比对）；
      - 所有数据行/新填行的事件 `idx` 恒为 64（同组；6 位索引注入即红）；
      - L9/L10 的受害者序列 = B1、B2（LRU；替换策略注入即红）；
      - 代码行的 dirty 写回恰好发生在「写后读命中」之后、重填之前
        （写穿注入即"淘汰前第二次跳转"读到新值 ⇒ 探针提前退出即红）；
      - PTW 对 PTE 行的访问是 `req=1` 的命中，且发生在核内 `write=1`
        命中之后（PTW 走 D-Cache 端口）。
"""

from __future__ import annotations

import argparse
import importlib.util
import pathlib
import re
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
DEFAULT_ROOT = HERE.parents[2]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_geometry():
    return _load("vastdcache_geometry", HERE / "gen_vastdcache_tables.py")


# 结果缓冲顺序 = `vastdcache.S` 的 `__REC`/`__CHECK_RD` 顺序（35 条）。
def expected_records(g, stub_word: int) -> list:
    recs = [g.M_A] * 5
    recs += [g.M_B[i] for i in range(8)]
    recs += [g.M_B[0], g.M_L9, g.M_B[7], g.M_L10, g.M_B[1]]
    recs += [stub_word, g.MARK_JUMP1, stub_word, g.MARK_JUMP2]
    recs += list(g.M_FRESH)
    recs += [g.MARK_JUMP3, stub_word]
    recs += [g.M_PAGE_OLD, g.M_PAGE_NEW, g.PTE_PAGE_NEW]
    return recs


N_BYTES = 35 * 8

# ---- 日志事件 -------------------------------------------------------------
EV = re.compile(
    r"^WumingCache\[dcache\]: (?P<kind>hit|fill-done|miss|wb|wb-fail|fill-fail|cmd|flush|wt-fail)"
    r"(?P<rest>.*)$")
KV = re.compile(r"(\w+)=\s*(0x[0-9a-f]+|\d+)")


def parse_events(path: pathlib.Path) -> list:
    events = []
    for line in path.read_text(errors="replace").splitlines():
        i = line.find("WumingCache[dcache]: ")
        if i < 0:
            continue
        m = EV.match(line[i:])
        if not m:
            continue
        rec = {"kind": m.group("kind")}
        for mm in KV.finditer(m.group("rest")):
            value = mm.group(2)
            rec[mm.group(1)] = int(value, 16) if value.startswith("0x") else int(value)
        events.append((line[i:], rec))
    return events


def find(events, kind, **kw):
    out = []
    for idx, (_, e) in enumerate(events):
        if e.get("kind") != kind:
            continue
        if all(e.get(k) == v for k, v in kw.items()):
            out.append(idx)
    return out


def check(records, events, g, stub_word: int) -> list:
    fails = []
    exp = expected_records(g, stub_word)
    if len(records) != len(exp):
        fails.append("records: got %d, expected %d" % (len(records), len(exp)))
    for i, (got, want) in enumerate(zip(records, exp)):
        if got != want:
            fails.append("record %d: 0x%016x != 0x%016x" % (i, got, want))

    A = g.PA_A
    B = g.PA_B
    code = g.PA_CODE
    l2 = g.PA_L2
    # A：1 次填充 + 4 次命中
    n_fill_a = len(find(events, "fill-done", line=A))
    n_hit_a = len(find(events, "hit", line=A))
    if n_fill_a != 1:
        fails.append("A: fill events %d != 1" % n_fill_a)
    if n_hit_a != 4:
        fails.append("A: hit events %d != 4" % n_hit_a)

    # 所有数据/填充行都在第 64 组（6 位索引注入 ⇒ 这里红）；页表行不进这个集
    data_lines = set([A] + list(B) + [g.PA_L9, g.PA_L10] + list(g.PA_FRESH) + [code])
    idx_fills = [e.get("idx") for _, e in events
                 if e.get("kind") == "fill-done" and e.get("line") in data_lines]
    bad_idx = [v for v in idx_fills if v != 64]
    if bad_idx:
        fails.append("falls outside group 64: %r" % sorted(set(bad_idx)))

    # LRU 替换序列：L9 淘汰 B1、L10 淘汰 B2
    seq = []
    for line in (g.PA_L9, g.PA_L10, code):
        m = find(events, "miss", line=line)
        if not m:
            continue
        victim = events[m[0]][1].get("victimLine")
        seq.append((line, victim))
    if len(seq) < 2:
        fails.append("miss events missing for L9/L10 (%r)" % (seq,))
    else:
        if seq[0][1] != B[1]:
            fails.append("L9 victim 0x%x != B1 0x%x" % (seq[0][1] or 0, B[1]))
        if seq[1][1] != B[2]:
            fails.append("L10 victim 0x%x != B2 0x%x" % (seq[1][1] or 0, B[2]))

    # 写回时机：代码行 store 后命中、再淘汰写回、再重填
    hit_code = find(events, "hit", line=code)
    wb_code = find(events, "wb", line=code)
    fill_code = find(events, "fill-done", line=code)
    if not hit_code:
        fails.append("code line has no read hit after the store")
    if len(wb_code) != 1:
        fails.append("code line write-backs %d != 1" % len(wb_code))
    if len(fill_code) != 2:
        fails.append("code line fills %d != 2 (allocate + refill)" % len(fill_code))
    if hit_code and wb_code and wb_code[0] < hit_code[0]:
        fails.append("write-back happens before the 写后读命中")
    if wb_code and len(fill_code) >= 2 and fill_code[1] < wb_code[0]:
        fails.append("refill happens before the write-back")
    # 写穿注入会提前让取指读到 trap：探针不会走到第二条记录，stream 已判红；
    # 这里再核「写回前 dirty 行只被命中过，未在总线上落过 store」。

    # PTW 端口：核内写 PTE 命中 → PTW 的读也命中同一行
    wr = [i for i in find(events, "hit", line=l2)
          if events[i][1].get("write") == 1 and events[i][1].get("req") == 0]
    rd_ptw = [i for i in find(events, "hit", line=l2)
              if events[i][1].get("req") == 1]
    if not wr:
        fails.append("no core write hit on the PTE line")
    if not rd_ptw:
        fails.append("no PTW read hit on the PTE line")
    if wr and rd_ptw and not any(i > wr[0] for i in rd_ptw):
        fails.append("no PTW read hit after the core PTE write")
    if not find(events, "fill-done", line=g.PA_PAGE_NEW):
        fails.append("the rewritten PTE never reached the new target")

    # 任何总线失败都必须为 0
    for kind in ("wb-fail", "fill-fail", "wt-fail"):
        n = len(find(events, kind))
        if n:
            fails.append("%s events %d != 0" % (kind, n))
    return fails


def parse_stream(path: pathlib.Path) -> list:
    data = path.read_bytes()
    return [int.from_bytes(data[i:i + 8], "big")
            for i in range(0, len(data) - len(data) % 8, 8)]


# ---- 自检：每条断言都要有可达 FAIL ------------------------------------------
def self_test(g, root: pathlib.Path) -> int:
    stub = 0x123456789ABCDEF0
    lines = []
    cyc = 0

    def ev(text):
        nonlocal cyc
        cyc += 1
        lines.append(text + " cycle=%d" % cyc)

    # 合成一段"好"日志：事件顺序与探针一致（只覆盖判据读取的事件面）。
    ev("WumingCache[dcache]: miss line=0x%x idx=64 victim=0 victimLine=0x0 invalid=1 write=0 req=0" % g.PA_A)
    ev("WumingCache[dcache]: fill-done line=0x%x idx=64 way=0 write=0 req=0" % g.PA_A)
    for _ in range(4):
        ev("WumingCache[dcache]: hit line=0x%x idx=64 way=0 beat=0 write=0 req=0" % g.PA_A)
    for i, pa in enumerate(g.PA_B):
        ev("WumingCache[dcache]: fill-done line=0x%x idx=64 way=%d write=0 req=0" % (pa, i))
    ev("WumingCache[dcache]: hit line=0x%x idx=64 way=0 beat=0 write=0 req=0" % g.PA_B[0])
    ev("WumingCache[dcache]: miss line=0x%x idx=64 victim=1 victimLine=0x%x invalid=0 write=0 req=0"
       % (g.PA_L9, g.PA_B[1]))
    ev("WumingCache[dcache]: fill-done line=0x%x idx=64 way=1 write=0 req=0" % g.PA_L9)
    ev("WumingCache[dcache]: hit line=0x%x idx=64 way=7 beat=0 write=0 req=0" % g.PA_B[7])
    ev("WumingCache[dcache]: miss line=0x%x idx=64 victim=2 victimLine=0x%x invalid=0 write=0 req=0"
       % (g.PA_L10, g.PA_B[2]))
    ev("WumingCache[dcache]: fill-done line=0x%x idx=64 way=2 write=0 req=0" % g.PA_L10)
    ev("WumingCache[dcache]: fill-done line=0x%x idx=64 way=2 write=0 req=0" % g.PA_B[1])
    ev("WumingCache[dcache]: fill-done line=0x%x idx=64 way=3 write=1 req=0" % g.PA_CODE)
    ev("WumingCache[dcache]: hit line=0x%x idx=64 way=3 beat=0 write=1 req=0" % g.PA_CODE)
    ev("WumingCache[dcache]: hit line=0x%x idx=64 way=3 beat=0 write=0 req=0" % g.PA_CODE)
    for i, pa in enumerate(g.PA_FRESH):
        ev("WumingCache[dcache]: fill-done line=0x%x idx=64 way=%d write=0 req=0" % (pa, i % 8))
    ev("WumingCache[dcache]: wb line=0x%x idx=64 way=3 beats=8" % g.PA_CODE)
    ev("WumingCache[dcache]: fill-done line=0x%x idx=64 way=4 write=0 req=0" % g.PA_CODE)
    ev("WumingCache[dcache]: fill-done line=0x%x idx=0 way=4 write=0 req=1" % g.PA_L2)
    ev("WumingCache[dcache]: hit line=0x%x idx=0 way=4 beat=7 write=1 req=0" % g.PA_L2)
    ev("WumingCache[dcache]: hit line=0x%x idx=0 way=4 beat=7 write=0 req=1" % g.PA_L2)
    ev("WumingCache[dcache]: fill-done line=0x%x idx=0 way=5 write=0 req=0" % g.PA_PAGE_NEW)

    log = pathlib.Path(tempfile.mkdtemp(prefix="check-vastdcache-selftest-")) / "selftest.log"
    log.write_text("\n".join(lines) + "\n")

    good = expected_records(g, stub)
    base = parse_events(log)

    def run(recs, evs):
        return check(recs, evs, g, stub)

    def clone(evs):
        return [(t, dict(e)) for t, e in evs]

    cases = []
    cases.append(("good stream/log", run(good, base), False))
    bad = list(good); bad[5] ^= 1
    cases.append(("record 5 corrupted", run(bad, base), True))
    bad = list(good); bad[-1] ^= 1 << 40
    cases.append(("record 34 (PTE) corrupted", run(bad, base), True))
    cases.append(("records short", run(good[:-1], base), True))

    e = clone(base)
    a_hits = [i for i, (_, r) in enumerate(e)
              if r.get("kind") == "hit" and r.get("line") == g.PA_A]
    e.pop(a_hits[0])
    cases.append(("one A hit removed", run(good, e), True))

    e = clone(base)
    for t, r in e:
        if "idx" in r:
            r["idx"] = 32
    cases.append(("group index changed", run(good, e), True))

    e = clone(base)
    for _, r in e:
        if r.get("victimLine") == g.PA_B[1]:
            r["victimLine"] = g.PA_B[3]
    cases.append(("victim sequence changed", run(good, e), True))

    e = clone(base)
    wb_at = next(i for i, (_, r) in enumerate(e) if r.get("kind") == "wb")
    item = e.pop(wb_at)
    hit_at = next(i for i, (_, r) in enumerate(e)
                  if r.get("kind") == "hit" and r.get("line") == g.PA_CODE)
    e.insert(hit_at, item)
    cases.append(("write-back before read hit", run(good, e), True))

    e = clone(base)
    e = [x for x in e if not (x[1].get("kind") == "hit" and x[1].get("req") == 1)]
    cases.append(("PTW read hit removed", run(good, e), True))

    e = clone(base)
    e.append(("WumingCache[dcache]: wb-fail kind=evict line=0x0", {"kind": "wb-fail"}))
    cases.append(("bus failure event", run(good, e), True))

    e = clone(base)
    e = [x for x in e if not (x[1].get("kind") == "fill-done"
                              and x[1].get("line") == g.PA_PAGE_NEW)]
    cases.append(("new PTE target never filled", run(good, e), True))

    bad = 0
    for name, fails, want_fail in cases:
        got = bool(fails)
        if got != want_fail:
            bad += 1
            print("  [SURPRISE] %-32s want_fail=%s got=%r" % (name, want_fail, fails))
        else:
            print("  [ok] %-32s want_fail=%s first=%s"
                  % (name, want_fail, (fails[0] if fails else "-")))
    print("check_vastdcache --self-test: %d case(s), %d surprise(s)" % (len(cases), bad))
    return 0 if bad == 0 else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stream", type=pathlib.Path)
    ap.add_argument("--log", type=pathlib.Path)
    ap.add_argument("--stub-word", type=lambda s: int(s, 0))
    ap.add_argument("--root", type=pathlib.Path, default=DEFAULT_ROOT)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args(argv)
    g = load_geometry()
    g.check_geometry()
    if args.self_test:
        return self_test(g, args.root)
    if not args.stream or not args.log or args.stub_word is None:
        ap.error("--stream, --log and --stub-word are required")
    records = parse_stream(args.stream)
    events = parse_events(args.log)
    fails = check(records, events, g, args.stub_word)
    if fails:
        for f in fails:
            print("  [FAIL] " + f)
        print("check_vastdcache: %d problem(s)" % len(fails))
        return 1
    print("check_vastdcache: %d record(s) match, group=64, victim sequence=%s, "
          "write-back after read hit, PTW read hit on the PTE line"
          % (len(records), hex(g.PA_B[1]) + "->" + hex(g.PA_B[2])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
