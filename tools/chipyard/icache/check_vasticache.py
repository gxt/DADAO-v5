#!/usr/bin/env python3
"""check_vasticache -- `tools/chipyard/icache/vasticache.S` 的独立判据（`m16-chipyard-010`）。

判据不保存期望常量：块 magic、PTE、组索引与组号全部从
`gen_vasticache_tables.py` 现场取（该文件的 `check_geometry()` 另行独立
核一遍「A 行同组、C 行另一组、二者 6 位组相同」）。

三层断言：
  * **结果缓冲**：12 条 8 字节记录逐条等于被调代码块的 magic
    （证明 fill/命中取回的是正确的指令字节，而不是别的行）；
  * **仿真日志**（`WumingCache[icache]:` 事件，只取指令侧实例）：
      - 每个代码块（64 B = 8 beat）恰好 1 次 `fill-done`、7 次 `hit`
        （A1 被淘汰后重填 ⇒ 2 次填充；A3 末尾再访 ⇒ 命中 14 次）；
      - A1..A8 的缺失全部 `invalid=1`（8 路共存，无淘汰）；
        A9 的缺失 `victimLine` = A1、A1 重填的 `victimLine` = A2（LRU）；
      - 所有 A 行填充的 `idx` = 64；C1（PA[12:6] = 0）的 `idx` = 0，
        且其缺失 `invalid=1`（**不得**淘汰 A 组；6 位索引注入时它会落在
        A 组里并把 A3 挤掉 ⇒ A3 的填充计数与命中计数同时红）；
      - 没有任何 `write=1` / `wb` / `wt-fail` 事件（只读、无 dirty）；
      - 没有任何事件落在核内 SRAM 行（探针自身的取指不进缓存）；
  * **取指往返拍数**（`WumingCore: fetchresp ... latency=`，**不读缓存自己的
    日志**）：块首拍（缺失）≥ 10 拍，其余拍（命中）≤ 4 拍 —— 命中不访存。
"""

from __future__ import annotations

import argparse
import importlib.util
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
DEFAULT_ROOT = HERE.parents[2]

#: 每块 8 beat：1 次缺失 + 7 次命中；A1 被淘汰后重填一次，A3 末尾再访一次。
BEATS = 8
HITS_PER_VISIT = BEATS - 1
HIT_LATENCY_MAX = 4
MISS_LATENCY_MIN = 10


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_geometry():
    return _load("vasticache_geometry", HERE / "gen_vasticache_tables.py")


# 结果缓冲顺序 = `vasticache.S` 的 `__CHECK_RD`/`__REC` 顺序（12 条）。
def expected_records(g) -> list:
    a = g.M_A                     # A1..A9
    return [a[0]] + a[1:8] + [a[8], a[0], g.M_C, a[2]]


N_RECORDS = 12


# ---- 日志事件 -------------------------------------------------------------
EV = re.compile(
    r"^WumingCache\[icache\]: "
    r"(?P<kind>hit|fill-done|miss|wb|wb-fail|fill-fail|wt-fail|cmd|flush)"
    r"(?P<rest>.*)$")
KV = re.compile(r"(\w+)=\s*(0x[0-9a-f]+|\d+)")
# 核自己的取指往返拍数（独立于缓存日志）。
LAT = re.compile(r"WumingCore: fetchresp 0x(?P<addr>[0-9a-f]+) latency=\s*(?P<lat>\d+)")


def parse_events(path: pathlib.Path) -> list:
    events = []
    for line in path.read_text(errors="replace").splitlines():
        i = line.find("WumingCache[icache]: ")
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


def parse_latencies(path: pathlib.Path) -> list:
    out = []
    for line in path.read_text(errors="replace").splitlines():
        for m in LAT.finditer(line):
            out.append((int(m.group("addr"), 16), int(m.group("lat"))))
    return out


def visit_plan(g) -> list:
    """Probe visit order + LRU residency (8 ways, group = PA[12:6]).

    Independent of the RTL: a plain LRU model over the probe's fixed visit
    order (`vasticache.S`: A1, A2..A8, A9, A1, C1, A3).  Returns
    ``[(line_base, resident_before)]`` — a resident line is a hit, otherwise a
    miss that evicts the least recently used line of its group.
    """
    order = [g.PA_A[0]] + list(g.PA_A[1:8]) + [g.PA_A[8], g.PA_A[0], g.PA_C, g.PA_A[2]]
    groups = {}
    plan = []
    for pa in order:
        grp = (pa >> 6) & 0x7F
        ways = groups.setdefault(grp, [])
        hit = pa in ways
        if hit:
            ways.remove(pa)
        else:
            if len(ways) == 8:
                ways.pop()
        ways.insert(0, pa)
        # 取指日志里的地址是 VA（模型用 PA 算组号）
        plan.append((g.VA_BASE + pa, hit))
    return plan


def find(events, kind, **kw):
    out = []
    for idx, (_, e) in enumerate(events):
        if e.get("kind") != kind:
            continue
        if all(e.get(k) == v for k, v in kw.items()):
            out.append(idx)
    return out


def check(records, events, latencies, g) -> list:
    fails = []
    exp = expected_records(g)
    if len(records) != len(exp):
        fails.append("records: got %d, expected %d" % (len(records), len(exp)))
    for i, (got, want) in enumerate(zip(records, exp)):
        if got != want:
            fails.append("record %d: 0x%016x != 0x%016x" % (i, got, want))

    a = g.PA_A                        # A1..A9, one 64 B line each
    c = g.PA_C
    # 每条线：填充/命中次数（A1 被淘汰后重填，A3 末尾再访）
    exp_fill = {pa: 1 for pa in a}
    exp_hit = {pa: HITS_PER_VISIT for pa in a}
    exp_fill[a[0]] = 2                # A1：首次填充 + 淘汰后重填
    exp_hit[a[0]] = 2 * HITS_PER_VISIT
    exp_hit[a[2]] = HITS_PER_VISIT + BEATS  # A3：首次 7 命中 + 末尾再访 8 拍全命中
    exp_fill[c] = 1
    exp_hit[c] = HITS_PER_VISIT

    for pa in a + [c]:
        nf = len(find(events, "fill-done", line=pa))
        if nf != exp_fill[pa]:
            fails.append("line 0x%x: fills %d != %d" % (pa, nf, exp_fill[pa]))
        nh = len(find(events, "hit", line=pa))
        if nh != exp_hit[pa]:
            fails.append("line 0x%x: hits %d != %d" % (pa, nh, exp_hit[pa]))

    # 8 路共存：A2..A8 的缺失都不得淘汰（invalid=1）；A9 起才淘汰
    for pa in a[1:8]:
        miss = find(events, "miss", line=pa)
        if len(miss) != 1:
            fails.append("line 0x%x: miss events %d != 1" % (pa, len(miss)))
            continue
        e = events[miss[0]][1]
        if e.get("invalid") != 1:
            fails.append("line 0x%x: miss reports invalid=%r (a way was evicted "
                         "before the 9th line)" % (pa, e.get("invalid")))
        if e.get("victimLine") != (64 << 6):
            fails.append("line 0x%x: miss victimLine 0x%x != 0x%x (invalid victim)"
                         % (pa, e.get("victimLine") or 0, 64 << 6))

    # LRU：A9 淘汰 A1；A1 的第二次缺失（重填）淘汰 A2
    m9 = find(events, "miss", line=a[8])
    m1 = find(events, "miss", line=a[0])
    if not m9:
        fails.append("A9: no miss event")
    else:
        e = events[m9[0]][1]
        if e.get("victimLine") != a[0] or e.get("invalid") != 0:
            fails.append("A9 victim 0x%x invalid=%r != A1 0x%x (LRU order)"
                         % (e.get("victimLine") or 0, e.get("invalid"), a[0]))
    if len(m1) != 2:
        fails.append("A1: %d miss events != 2 (initial fill + refill)" % len(m1))
    else:
        e = events[m1[1]][1]
        if e.get("victimLine") != a[1] or e.get("invalid") != 0:
            fails.append("A1-refill victim 0x%x invalid=%r != A2 0x%x (LRU order)"
                         % (e.get("victimLine") or 0, e.get("invalid"), a[1]))

    # C1 落在另一个组：不得淘汰 A 组里的任何行
    miss_c = find(events, "miss", line=c)
    if len(miss_c) != 1:
        fails.append("line 0x%x: miss events %d != 1" % (c, len(miss_c)))
    else:
        e = events[miss_c[0]][1]
        if e.get("invalid") != 1:
            fails.append("C1 (group 0) evicted a line (invalid=%r): a 6-bit group "
                         "index would put it in the A lines' group" % e.get("invalid"))

    # 组索引：A 行 64、C1 0；缺失/填充/命中事件都必须一致
    for pa in a:
        for kind in ("miss", "fill-done", "hit"):
            for _, e in events:
                if e.get("kind") == kind and e.get("line") == pa and e.get("idx") != 64:
                    fails.append("%s on 0x%x reports idx=%r != 64"
                                 % (kind, pa, e.get("idx")))
                    break
    for _, e in events:
        if e.get("line") == c and e.get("kind") in ("miss", "fill-done", "hit"):
            if e.get("idx") != 0:
                fails.append("%s on C1 reports idx=%r != 0" % (e.get("kind"), e.get("idx")))

    # 只读：没有任何写事件，也没有写回/写穿路径
    n_write = sum(1 for _, e in events if e.get("write") == 1)
    if n_write:
        fails.append("read-only cache shows %d write=1 event(s)" % n_write)
    for kind in ("wb", "wb-fail", "wt-fail", "cmd", "flush"):
        n = len(find(events, kind))
        if n:
            fails.append("%s events %d != 0 (read-only, no dirty line)" % (kind, n))

    # 核内 SRAM 的取指不进缓存：没有事件落在 PA RAM（2 GiB）之外的核内窗口
    for text, e in events:
        line = e.get("line")
        if line is not None and line >= 0x8000_0000:
            fails.append("cache event for a core-internal line: %s" % text)
            break

    # 取指往返拍数（核自己的计数器，不读缓存日志）：块首拍在「该行不在缓存里」
    # 的访问上慢（≥ MISS_LATENCY_MIN），其余拍一律快（≤ HIT_LATENCY_MAX）。
    # 每次访问是缺失还是命中由 `visit_plan` 的 LRU 模型按几何算出。
    plan = visit_plan(g)
    per_line = {}
    for pa, hit in plan:
        per_line.setdefault(pa, []).append(hit)
    all_blocks = list(g.VA_A) + [g.VA_C]
    if not latencies:
        fails.append("no fetchresp latency records")
    seen = {}
    for addr, lat in latencies:
        base = next((b for b in all_blocks if 0 <= addr - b < 64), None)
        if base is None:
            continue
        if addr == base:
            k = seen.get(base, 0)
            seen[base] = k + 1
            classes = per_line.get(base, [])
            is_hit = classes[k] if k < len(classes) else None
            if is_hit is True and lat > HIT_LATENCY_MAX:
                fails.append("hit visit fetch 0x%x (visit %d) latency %d > %d"
                             % (addr, k + 1, lat, HIT_LATENCY_MAX))
            elif is_hit is False and lat < MISS_LATENCY_MIN:
                fails.append("miss visit fetch 0x%x (visit %d) latency %d < %d"
                             % (addr, k + 1, lat, MISS_LATENCY_MIN))
        elif lat > HIT_LATENCY_MAX:
            fails.append("beat fetch 0x%x latency %d > %d"
                         % (addr, lat, HIT_LATENCY_MAX))
    return fails


def parse_stream(path: pathlib.Path) -> list:
    data = path.read_bytes()
    return [int.from_bytes(data[i:i + 8], "big")
            for i in range(0, len(data) - len(data) % 8, 8)]


# ---- 结构断言（Vast FIRRTL）------------------------------------------------
def structure(fir: pathlib.Path) -> list:
    """The I instance has no dirty state and no write-back datapath, the D
    instance has both, and both are 8 x 128 arrays of the same class."""
    text = fir.read_text(errors="replace")
    fails = []
    mi = re.search(r"inst icache of (\S+)", text)
    md = re.search(r"inst dcache of (\S+)", text)
    if not mi or not md:
        return ["instances icache/dcache not found in the FIRRTL"]
    if mi.group(1) == md.group(1):
        fails.append("icache and dcache are the same module (not parameterised)")

    def module_text(name):
        m = re.search(r"^\s*module %s :" % re.escape(name), text, re.M)
        if not m:
            return ""
        start = m.end()
        nxt = re.search(r"^\s*module \S+ :", text[start:], re.M)
        return text[start:start + (nxt.start() if nxt else len(text) - start)]

    i_body, d_body = module_text(mi.group(1)), module_text(md.group(1))
    if not i_body or not d_body:
        return fails + ["module body not found for icache/dcache"]

    # 结构：I 实例里 `dirty` 出现 0 次（tag bundle 没有该字段）；D 实例有
    # （bundle 字段类型里可见 `dirty : UInt<1>`）。写回路径 = `WumingCache[...]:
    # wb` / `wb-fail` 打印，I 实例里一条都不生成。
    def dirty_mentions(body):
        return len(re.findall(r"\bdirty\b", body))

    def wb_printfs(body):
        return len(re.findall(r"WumingCache\[[a-z]+\]: wb", body))

    if dirty_mentions(i_body) != 0:
        fails.append("I instance mentions `dirty` %d time(s) (must be 0: no dirty bit)"
                     % dirty_mentions(i_body))
    if dirty_mentions(d_body) == 0:
        fails.append("D instance has no dirty state (control failed)")
    if wb_printfs(i_body) != 0:
        fails.append("I instance still generates the write-back datapath (%d printf(s))"
                     % wb_printfs(i_body))
    if wb_printfs(d_body) == 0:
        fails.append("D instance has no write-back datapath (control failed)")
    # 8 路 x 128 组：两个实例都是 8 个 `UInt<64>[8] [128]` 数据阵列
    for label, body in (("icache", i_body), ("dcache", d_body)):
        dims = re.findall(r"^\s*smem lineStore_\d+ : UInt<\d+>\[(\d+)\] \[(\d+)\]",
                          body, re.M)
        if len(dims) != 8:
            fails.append("%s: %d line arrays (expected 8 ways)" % (label, len(dims)))
        elif any(int(w) != 8 or int(sets) != 128 for w, sets in dims):
            fails.append("%s: line array shape %r != [8 ways] [128 groups]"
                         % (label, sorted(set(dims))))
    return fails


# ---- 自检：每条断言都要有可达 FAIL ------------------------------------------
def self_test(g) -> int:
    lines = []
    cyc = 0

    def ev(text):
        nonlocal cyc
        cyc += 1
        lines.append("%s cycle=%d" % (text, cyc))

    def fill(pa, idx, victim=0, victim_line=None, invalid=1):
        # 无效条目的 victimLine = tag(0) ## idx ## 0 ⇒ idx << 6
        vline = (idx << 6) if victim_line is None else victim_line
        ev("WumingCache[icache]: miss line=0x%x idx=%d victim=%d victimLine=0x%x "
           "invalid=%d write=0 req=0" % (pa, idx, victim, vline, invalid))
        ev("WumingCache[icache]: fill-done line=0x%x idx=%d way=%d write=0 req=0"
           % (pa, idx, victim))

    def visit(pa, idx, n=HITS_PER_VISIT):
        for _ in range(n):
            ev("WumingCache[icache]: hit line=0x%x idx=%d way=0 beat=0 write=0 req=0"
               % (pa, idx))

    a = g.PA_A
    fill(a[0], 64); visit(a[0], 64)
    for pa in a[1:8]:
        fill(pa, 64); visit(pa, 64)
    fill(a[8], 64, 0, a[0], 0); visit(a[8], 64)      # A9 淘汰 A1
    fill(a[0], 64, 1, a[1], 0); visit(a[0], 64)      # A1 重填，淘汰 A2
    fill(g.PA_C, 0); visit(g.PA_C, 0)                # C1：另一个组
    visit(a[2], 64, BEATS)                           # A3 仍命中（8 拍全命中）

    log = pathlib.Path("/tmp/opencode/check-vasticache-selftest/selftest.log")
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text("\n".join(lines) + "\n")

    # 取指拍数：按 LRU 模型生成每次访问的块首拍（缺失慢、命中快）+ 其余拍
    lat = []
    for base, is_hit in visit_plan(g):
        lat.append("WumingCore: fetchresp 0x%x latency=%d" % (base, 1 if is_hit else 41))
        for b in range(1, BEATS):
            lat.append("WumingCore: fetchresp 0x%x latency=1" % (base + 8 * b))
    latlog = log.parent / "selftest-lat.log"
    latlog.write_text("\n".join(lat) + "\n")

    good = expected_records(g)
    base_events = parse_events(log)
    base_lat = parse_latencies(latlog)

    def run(recs=None, evs=None, lats=None):
        return check(good if recs is None else recs,
                     base_events if evs is None else evs,
                     base_lat if lats is None else lats, g)

    def clone(evs):
        return [(t, dict(e)) for t, e in evs]

    cases = []
    cases.append(("good stream/log", run(), False))
    bad = list(good); bad[4] ^= 1
    cases.append(("record 4 corrupted", run(recs=bad), True))
    cases.append(("records short", run(recs=good[:-1]), True))

    e = clone(base_events)
    hit_a1 = [i for i, (_, r) in enumerate(e) if r.get("kind") == "hit" and r.get("line") == a[0]]
    e.pop(hit_a1[0])
    cases.append(("one A1 hit removed", run(evs=e), True))

    e = clone(base_events)
    for _, r in e:
        if r.get("idx") == 64:
            r["idx"] = 32
    cases.append(("group index changed", run(evs=e), True))

    e = clone(base_events)
    for _, r in e:
        if r.get("victimLine") == a[0]:
            r["victimLine"] = a[4]
    cases.append(("victim sequence changed", run(evs=e), True))

    # 6 位组索引：C1 落进 A 组、淘汰 A3 ⇒ A3 重填 + C1 缺失不再 invalid
    e = clone(base_events)
    e.append(("WumingCache[icache]: miss line=0x%x idx=0 way=3 beat=0 write=0" % a[2],
              {"kind": "miss", "line": a[2], "idx": 0, "invalid": 0}))
    cases.append(("6-bit index refills A3", run(evs=e), True))

    e = clone(base_events)
    for _, r in e:
        if r.get("line") == g.PA_C and r.get("kind") == "miss":
            r["invalid"] = 0
    cases.append(("C1 evicted an A line", run(evs=e), True))

    e = clone(base_events)
    e.append(("WumingCache[icache]: hit line=0x%x idx=64 way=0 beat=0 write=1 req=0"
              % a[1], {"kind": "hit", "line": a[1], "idx": 64, "write": 1}))
    cases.append(("write=1 event", run(evs=e), True))

    e = clone(base_events)
    e.append(("WumingCache[icache]: wb line=0x%x idx=64 way=0 beats=8" % a[1],
              {"kind": "wb", "line": a[1], "idx": 64}))
    cases.append(("write-back event", run(evs=e), True))

    e = clone(base_events)
    e.append(("WumingCache[icache]: fill-done line=0x%x idx=64 way=0 write=0 req=0"
              % g.SRAM_LINE, {"kind": "fill-done", "line": g.SRAM_LINE, "idx": 64}))
    cases.append(("core-internal line cached", run(evs=e), True))

    lats = [(addr, 40 if addr == g.VA_A[1] + 8 else lat) for addr, lat in base_lat]
    cases.append(("hit latency as slow as a miss", run(lats=lats), True))
    lats = [(addr, 1 if addr == g.VA_A[2] else lat) for addr, lat in base_lat]
    cases.append(("miss visit as fast as a hit", run(lats=lats), True))

    lats = [(addr, 1 if addr == g.VA_A[0] else lat) for addr, lat in base_lat]
    cases.append(("miss latency as fast as a hit", run(lats=lats), True))

    bad_n = 0
    for name, fails, want_fail in cases:
        got = bool(fails)
        if got != want_fail:
            bad_n += 1
            print("  [SURPRISE] %-32s want_fail=%s got=%r" % (name, want_fail, fails))
        else:
            print("  [ok] %-32s want_fail=%s first=%s"
                  % (name, want_fail, (fails[0] if fails else "-")))
    print("check_vasticache --self-test: %d case(s), %d surprise(s)"
          % (len(cases), bad_n))
    return 0 if bad_n == 0 else 1


def structure_self_test(g) -> int:
    """`--structure` 的判据自检：合成两份 FIRRTL，一份正确、一份 I 侧带 dirty。

    这是「结构断言可达 FAIL」的**判据侧**证据；真 RTL 侧的可达 FAIL 由证据
    脚本的注入（I 侧改 `withDirty = true`）给出。
    """
    arrays = "".join(
        "    smem lineStore_%d : UInt<64>[8] [128] @[x]\n" % i for i in range(8))
    good = """\
  module WumingCore :
    inst dcache of WumingCache @[x]
    inst icache of WumingCache_1 @[x]

  module WumingCache :
""" + arrays + """\
    regreset tagStore_0_0 : { valid : UInt<1>, dirty : UInt<1>, tag : UInt<35>}, clock, reset, UInt<1>(0h0)
    printf(clock, UInt<1>(0h1), "WumingCache[dcache]: wb line=0x%x")

  module WumingCache_1 :
""" + arrays + """\
    regreset tagStore_0_0 : { valid : UInt<1>, tag : UInt<35>}, clock, reset, UInt<1>(0h0)
"""
    bad = good.replace(
        "    regreset tagStore_0_0 : { valid : UInt<1>, tag : UInt<35>}",
        "    regreset tagStore_0_0 : { valid : UInt<1>, dirty : UInt<1>, tag : UInt<35>}")
    import tempfile
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="vasticache-struct-"))
    fg = tmp / "good.fir"
    fb = tmp / "bad.fir"
    fg.write_text(good)
    fb.write_text(bad)
    bad_n = 0
    fails = structure(fg)
    if fails:
        bad_n += 1
        print("  [SURPRISE] good FIRRTL flagged: %r" % fails)
    else:
        print("  [ok] good FIRRTL accepted")
    fails = structure(fb)
    if not fails:
        bad_n += 1
        print("  [SURPRISE] dirty-on-I FIRRTL not flagged")
    elif not any("mentions `dirty`" in f for f in fails):
        bad_n += 1
        print("  [SURPRISE] dirty-on-I flagged for the wrong reason: %r" % fails)
    else:
        print("  [ok] dirty-on-I flagged: %s" % fails[0])
    print("check_vasticache --structure-test: 2 case(s), %d surprise(s)" % bad_n)
    return 0 if bad_n == 0 else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stream", type=pathlib.Path)
    ap.add_argument("--log", type=pathlib.Path)
    ap.add_argument("--root", type=pathlib.Path, default=DEFAULT_ROOT)
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--structure", type=pathlib.Path)
    ap.add_argument("--structure-test", action="store_true")
    ap.add_argument("--geometry", action="store_true")
    args = ap.parse_args(argv)
    g = load_geometry()
    g.check_geometry()
    if args.geometry:
        print("check_vasticache: geometry ok (A1..A9 group 64, C1 group 0)")
        return 0
    if args.self_test:
        return self_test(g)
    if args.structure_test:
        return structure_self_test(g)
    if args.structure:
        fails = structure(args.structure)
        if fails:
            for f in fails:
                print("  [FAIL] " + f)
            print("check_vasticache --structure: %d problem(s)" % len(fails))
            return 1
        print("check_vasticache --structure: I instance has no dirty register and "
              "no write-back datapath; D instance has both; 8 x 128 line arrays")
        return 0
    if not args.stream or not args.log:
        ap.error("--stream and --log are required")
    records = parse_stream(args.stream)
    events = parse_events(args.log)
    latencies = parse_latencies(args.log)
    fails = check(records, events, latencies, g)
    if fails:
        for f in fails:
            print("  [FAIL] " + f)
        print("check_vasticache: %d problem(s)" % len(fails))
        return 1
    print("check_vasticache: %d record(s) match; group 64 for A lines / 0 for C1; "
          "victim sequence=%s->%s; hit latency <= %d, miss latency >= %d"
          % (len(records), hex(g.PA_A[0]), hex(g.PA_A[1]),
             HIT_LATENCY_MAX, MISS_LATENCY_MIN))
    return 0


if __name__ == "__main__":
    sys.exit(main())
