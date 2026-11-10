#!/usr/bin/env python3
"""m13-testcases-003: case lists of the 3600 s long tail (static / dynamic).

The long tail is *defined by the archived results*, one row per case:

* ``static``  -- ``m13-001-static-3600s-full.json``  (m13-testcases-001)
* ``dynamic`` -- ``m13-002-dynamic-3600s-full.json`` (m13-testcases-002)

A case is in the list exactly when its own row says ``gem5_klass == "blocked"``
-- the recorded "still timed out at 3600 s" outcome.  Nothing here re-derives a
verdict, adds a case or drops one: the rows are the source, and every count
printed by this script is counted from them on this run (no expected total is
written into the code).

Output shape is the one ``run_engine_ratio.py --case-list <file> --selection
recheck`` reads, so the same file can drive the 7200 s rerun:

    {"link_mode": "...",
     "timeout_recheck": {"<suite>": {"still_blocked": ["<case id>", ...]}}}

Each mode gets a *full* list plus ``--shards N`` per-node shards (round-robin
over the sorted ``(suite, case)`` order, so the shard sizes differ by at most
one and both suites are spread over the shards).  Every written file is
re-read through ``run_engine_ratio``'s own loader before the run succeeds --
a file that loader cannot select the intended ids from is a hard error.

    python3 tools/testcases/tset/gem5-se-baseline/make_blocked_case_lists.py \
        --out-dir <runtime dir>/lists --shards 2

Nothing here changes a case, an expectation, a source or a gate.
"""

from __future__ import annotations

import argparse
import datetime
import importlib.util
import json
import os
import sys

REPO_ROOT = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", ".."))

SUITES = ("libc-test", "llvm-ts")

DEFAULT_REFS = {
    "static": ".tao/knowledge/refs/m13-001-static-3600s-full.json",
    "dynamic": ".tao/knowledge/refs/m13-002-dynamic-3600s-full.json",
}

TASK = "m13-testcases-003"


def abspath(path: str) -> str:
    return path if os.path.isabs(path) else os.path.join(REPO_ROOT, path)


def iso_utc() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def ratio_module(repo_root: str = REPO_ROOT):
    """`run_engine_ratio` by path -- the loader that must accept our files."""
    path = os.path.join(repo_root, "tools", "testcases", "tset",
                        "gem5-se-baseline", "run_engine_ratio.py")
    spec = importlib.util.spec_from_file_location("_m13_ratio_loader", path)
    if spec is None or spec.loader is None:      # pragma: no cover - fixed path
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_blocked(path: str):
    """``(link_mode, rows)`` of the blocked rows of one archived result.

    ``link_mode`` comes from the record itself; the m13-001 record predates the
    field and is a static run (its selection is the GEM5-021t static recheck),
    which is stated here once instead of being guessed per row.  A record
    without rows is an error: an empty list would silently shrink the work.
    """
    with open(path, "r") as fh:
        record = json.load(fh)
    rows = record.get("rows")
    if not rows:
        raise ValueError(f"{os.path.basename(path)}: no rows in the record")
    blocked = [row for row in rows if row.get("gem5_klass") == "blocked"]
    if not blocked:
        raise ValueError(f"{os.path.basename(path)}: no blocked row")
    mode = record.get("link_mode")
    if mode not in (None, "static", "dynamic"):
        raise ValueError(f"{os.path.basename(path)}: unknown link_mode {mode!r}")
    if mode is None:
        mode = "static"
    for row in blocked:
        if not row.get("case") or not row.get("suite"):
            raise ValueError(f"{os.path.basename(path)}: row without case/suite: "
                             f"{row!r}")
    return mode, blocked


def group(rows):
    """``{suite: [case ids]}`` in the sorted ``(suite, case)`` order."""
    selection = {}
    for row in sorted(rows, key=lambda r: (r["suite"], r["case"])):
        selection.setdefault(row["suite"], []).append(row["case"])
    for suite, ids in selection.items():
        if len(ids) != len(set(ids)):
            raise ValueError(f"{suite}: duplicate case id in the recorded rows")
    return selection


def flatten(selection):
    return [(suite, cid) for suite in sorted(selection)
            for cid in selection[suite]]


def split_shards(selection, shards: int):
    """Round-robin shards over the sorted order; sizes differ by <= 1."""
    if shards < 1:
        raise ValueError(f"--shards must be >= 1 (got {shards})")
    buckets = [[] for _ in range(shards)]
    for index, item in enumerate(flatten(selection)):
        buckets[index % shards].append(item)
    out = []
    for bucket in buckets:
        one = {}
        for suite, cid in bucket:
            one.setdefault(suite, []).append(cid)
        out.append(one)
    return out


def count(selection):
    by_suite = {suite: len(ids) for suite, ids in sorted(selection.items())}
    return dict(total=sum(by_suite.values()), by_suite=by_suite)


def write_case_list(path, link_mode, selection, meta):
    record = dict(
        case_list=True,
        task=TASK,
        generated_utc=iso_utc(),
        link_mode=link_mode,
        selection_field="timeout_recheck.<suite>.still_blocked",
        source=meta["source"],
        shard=meta.get("shard"),
        shards=meta.get("shards"),
        counts=count(selection),
        timeout_recheck={suite: dict(still_blocked=list(ids))
                         for suite, ids in selection.items()},
    )
    with open(path, "w") as fh:
        json.dump(record, fh, indent=2)
        fh.write("\n")
    return record


def verify_case_list(path, link_mode, selection, loader):
    """Re-read a written file through ``run_engine_ratio`` and compare.

    The loader is the consumer, so the comparison is against what the 7200 s
    run will actually select -- not against our own serializer.
    """
    suites = sorted(selection)
    got = loader.load_selection(path, suites, "recheck")
    want = {suite: list(selection[suite]) for suite in suites}
    if got != want:
        raise AssertionError(f"{os.path.basename(path)}: loader selection "
                             f"{got!r} != intended {want!r}")
    record_mode = loader.record_link_mode(path)
    conflict = loader.link_mode_conflict(record_mode, link_mode)
    if conflict:
        raise AssertionError(f"{os.path.basename(path)}: {conflict}")
    return got


def emit_mode(mode, ref, out_dir, shards, loader):
    link_mode, rows = load_blocked(ref)
    if link_mode != mode:
        raise ValueError(f"{os.path.basename(ref)}: link_mode {link_mode!r} != "
                         f"requested {mode!r}")
    selection = group(rows)
    unknown = sorted(set(selection) - set(SUITES))
    if unknown:
        raise ValueError(f"{os.path.basename(ref)}: unknown suite(s) {unknown}")
    full = count(selection)
    print(f"{mode}: blocked={full['total']} "
          f"({', '.join(f'{s} {n}' for s, n in full['by_suite'].items())}) "
          f"source={os.path.basename(ref)}", flush=True)

    written = []
    path = os.path.join(out_dir, f"{mode}-full.json")
    write_case_list(path, link_mode, selection,
                    dict(source=os.path.basename(ref), shard=None,
                         shards=shards))
    verify_case_list(path, link_mode, selection, loader)
    written.append((path, full))
    print(f"  full  -> {os.path.basename(path)} total={full['total']}",
          flush=True)

    for index, shard in enumerate(split_shards(selection, shards), start=1):
        one = count(shard)
        path = os.path.join(out_dir, f"{mode}-shard{index}of{shards}.json")
        write_case_list(path, link_mode, shard,
                        dict(source=os.path.basename(ref), shard=index,
                             shards=shards))
        verify_case_list(path, link_mode, shard, loader)
        written.append((path, one))
        print(f"  shard {index}/{shards} -> {os.path.basename(path)} "
              f"total={one['total']} ("
              + ", ".join(f"{s} {n}" for s, n in one["by_suite"].items())
              + ")", flush=True)

    # Shards must partition the full list: same ids, no duplicate, no loss.
    flat_written = []
    for _, shard in enumerate(split_shards(selection, shards), start=1):
        for suite in sorted(shard):
            flat_written.extend((suite, cid) for cid in shard[suite])
    if sorted(flat_written) != sorted(flatten(selection)):
        raise AssertionError(f"{mode}: shards do not partition the full list")
    return dict(mode=mode, link_mode=link_mode, full=full,
                shards=[count(s) for s in split_shards(selection, shards)],
                files=[p for p, _ in written])


# ---------------------------------------------------------------------------
# self-test (synthetic records; no archived result and no run needed)
# ---------------------------------------------------------------------------
def _synthetic(path, link_mode, rows):
    with open(path, "w") as fh:
        json.dump(dict(link_mode=link_mode, rows=rows), fh, indent=2)
    return path


def self_test(tmpdir):
    os.makedirs(tmpdir, exist_ok=True)
    checks = []

    def check(name, want, got):
        checks.append((name, want, got))

    loader = ratio_module()
    rows = ([dict(suite="libc-test", case=f"functional/{n}", gem5_klass="blocked")
             for n in ("b", "a")]
            + [dict(suite="libc-test", case="functional/pass", gem5_klass="pass")]
            + [dict(suite="llvm-ts", case=f"MultiSource/Benchmarks/X/{n}",
                   gem5_klass="blocked") for n in ("q", "p", "r")]
            + [dict(suite="llvm-ts", case="MultiSource/Benchmarks/X/fail",
                   gem5_klass="fail")])
    ref = _synthetic(os.path.join(tmpdir, "static.json"), "static", rows)
    mode, blocked = load_blocked(ref)
    check("link mode from record", "static", mode)
    check("only blocked rows", 5, len(blocked))
    selection = group(blocked)
    check("grouped by suite", {"libc-test": 2, "llvm-ts": 3},
          {s: len(v) for s, v in selection.items()})
    check("sorted within suite", ["functional/a", "functional/b"],
          selection["libc-test"])
    check("count total", 5, count(selection)["total"])

    shards = split_shards(selection, 2)
    check("shard sizes differ by <= 1", True,
          max(len(v) for v in shards) - min(len(v) for v in shards) <= 1)
    flat = sorted((s, c) for shard in shards for s in shard for c in shard[s])
    check("shards partition the list", sorted(flatten(selection)), flat)
    check("shard 1 of 5/2", 3, sum(len(v) for v in shards[0].values()))
    check("shard 2 of 5/2", 2, sum(len(v) for v in shards[1].values()))

    out = os.path.join(tmpdir, "lists")
    os.makedirs(out, exist_ok=True)
    result = emit_mode("static", ref, out, 2, loader)
    check("emit keeps every id", 5, result["full"]["total"])
    check("shard totals sum to full", 5, sum(s["total"] for s in result["shards"]))
    loaded = loader.load_selection(os.path.join(out, "static-shard1of2.json"),
                                   sorted(selection), "recheck")
    check("loader accepts a written shard", 3,
          sum(len(v) for v in loaded.values()))
    check("loader sees the link mode", "static",
          loader.record_link_mode(os.path.join(out, "static-full.json")))

    # reachable FAIL path: flip one blocked row to "pass" -- the derived set
    # must change, and the shard partition check must then disagree with the
    # original id set.
    flipped_rows = [dict(row) for row in rows]
    for row in flipped_rows:
        if row["case"] == "functional/a":
            row["gem5_klass"] = "pass"
    flipped = _synthetic(os.path.join(tmpdir, "flipped.json"), "static",
                         flipped_rows)
    _, flipped_blocked = load_blocked(flipped)
    check("flipped class shrinks the set", 4, len(flipped_blocked))
    check("flipped set differs", True,
          group(flipped_blocked) != selection)

    # a duplicate (suite, case) row must be refused, not counted twice
    dup_rows = rows + [dict(suite="libc-test", case="functional/a",
                            gem5_klass="blocked")]
    dup = _synthetic(os.path.join(tmpdir, "dup.json"), "static", dup_rows)
    try:
        group(load_blocked(dup)[1])
        check("duplicate id refused", "ValueError", "no exception")
    except ValueError:
        check("duplicate id refused", "ValueError", "ValueError")

    # a record with no rows must be refused (an empty list is not a run)
    empty = os.path.join(tmpdir, "empty.json")
    with open(empty, "w") as fh:
        json.dump(dict(rows=[]), fh)
    try:
        load_blocked(empty)
        check("empty record refused", "ValueError", "no exception")
    except ValueError:
        check("empty record refused", "ValueError", "ValueError")

    # a link-mode mismatch between the record and the requested mode is fatal
    try:
        emit_mode("dynamic", ref, out, 2, loader)
        check("mode mismatch refused", "ValueError", "no exception")
    except ValueError:
        check("mode mismatch refused", "ValueError", "ValueError")

    failed = 0
    for name, want, got in checks:
        ok = want == got
        failed += 0 if ok else 1
        print(f"self-test {'PASS' if ok else 'FAIL'} {name}: "
              f"expected={want!r} actual={got!r}")
    print(f"self-test: {len(checks) - failed}/{len(checks)} checks passed")
    return 0 if failed == 0 else 1


def main() -> int:
    ap = argparse.ArgumentParser(
        description=f"{TASK}: case lists of the 3600 s long tail")
    ap.add_argument("--mode", choices=("static", "dynamic", "both"),
                    default="both")
    ap.add_argument("--out-dir", default=None,
                    help="runtime directory for the generated lists "
                         "(required unless --self-test)")
    ap.add_argument("--shards", type=int, default=2,
                    help="per-node shards per mode (default 2)")
    ap.add_argument("--static-ref", default=DEFAULT_REFS["static"])
    ap.add_argument("--dynamic-ref", default=DEFAULT_REFS["dynamic"])
    ap.add_argument("--self-test", action="store_true",
                    help="check the derivation/shard/loader round-trip on "
                         "synthetic records (writes only under --out-dir)")
    ap.add_argument("--print-suites", default=None, metavar="CASE_LIST",
                    help="print the suites a generated case list carries "
                         "(comma separated) and exit; a shard may hold only "
                         "one of the two suites, and the 7200 s runner needs "
                         "exactly that set")
    args = ap.parse_args()

    if args.print_suites:
        try:
            with open(abspath(args.print_suites), "r") as fh:
                record = json.load(fh)
            suites = sorted((record.get("timeout_recheck") or {}))
        except (OSError, ValueError) as exc:
            sys.stderr.write(f"ERROR: {exc}\n")
            return 2
        if not suites:
            sys.stderr.write(f"ERROR: {args.print_suites} carries no suite\n")
            return 2
        print(",".join(suites))
        return 0

    if args.self_test:
        if not args.out_dir:
            sys.stderr.write("ERROR: --self-test needs --out-dir\n")
            return 2
        return self_test(abspath(args.out_dir))

    if not args.out_dir:
        sys.stderr.write("ERROR: --out-dir is required\n")
        return 2
    out_dir = abspath(args.out_dir)
    os.makedirs(out_dir, exist_ok=True)
    try:
        loader = ratio_module()
        modes = (["static", "dynamic"] if args.mode == "both" else [args.mode])
        results = []
        for mode in modes:
            ref = abspath(args.static_ref if mode == "static"
                          else args.dynamic_ref)
            results.append(emit_mode(mode, ref, out_dir, args.shards, loader))
    except (OSError, ValueError, KeyError, AssertionError) as exc:
        sys.stderr.write(f"ERROR: {exc}\n")
        return 2

    total = sum(item["full"]["total"] for item in results)
    print(f"case lists: {len(results)} mode(s), {total} case(s) over "
          f"{args.shards} shard(s) each; out-dir={os.path.basename(out_dir)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
