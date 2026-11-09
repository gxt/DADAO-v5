#!/usr/bin/env python3
"""SE tset bidirectional parity report: gem5 SE vs QEMU user, static + dynamic.

This is the G3 (``ADR-0048 D4/D5``) aggregation step.  It does **not** run a
guest: the per-case evidence already lives in the two committed tset baselines

    * static  -- ``.tao/knowledge/refs/GEM5-021t-baseline-summary.json``
    * dynamic -- ``.tao/knowledge/refs/TESTCASES-104t-dynamic-summary.json``

and this script only *recomputes* every count from the per-case rows, joins the
two link modes, and forces an attribution on every non-``pass`` row:

* ``timeout``        -- budget expiry, never a capability gap, attributed to
                        the per-suite budget (``TESTCASES-103t``);
* ``blocked``        -- real capability gap; the evidence text must resolve to
                        an owner (``implementation`` / ``environment``), else the
                        report fails;
* ``gem5_only_fail`` -- QEMU passed, gem5 SE did not; each case must be in the
                        explicit registry below (issue id + owner + why);
* ``qemu_only_fail`` -- gem5 SE passed, QEMU did not; ``ADR-0048 D5`` forbids
                        accepting this as a gem5 win, so the registry is the
                        **only** way such a row may exist (empty today);
* ``both_non_pass``  -- both engines agree on the same non-pass verdict
                        (e.g. the admitted ``ISS-251`` known-fail); differing
                        non-pass verdicts are a ``diff`` and fail the report.

Nothing is trusted from the declared blocks: counts, cross tables, gap buckets
and totals are all recomputed and compared, so a stale or hand-edited baseline
is reported instead of being copied into the matrix.

Usage::

    python3 tools/testcases/parity/se_tset_matrix.py \\
        --json-out <runtime dir>/se-parity.json \\
        --markdown-out <runtime dir>/se-parity.md \\
        --matrix-section-out <runtime dir>/matrix-M11-SE.md

    --self-test     inject one counter-example per invariant (on copies) and
                    require each one to be detected; exit 0 only if all are.

Exit codes: 0 = report written, every invariant held; 1 = an invariant failed
(including an unattributed row); 2 = setup/IO error.

The committed report is copied from the runtime output (``cp``) by the task
evidence script; numbers are never typed by hand.
"""

from __future__ import annotations

import argparse
import copy
import datetime
import hashlib
import importlib.util
import json
import os
import re
import sys

REPO_ROOT = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))

SUITES = ("libc-test", "llvm-ts", "embench")
TRACKS = ("static", "dynamic")

DEFAULT_SOURCE = {
    "static": os.path.join(".tao", "knowledge", "refs",
                           "GEM5-021t-baseline-summary.json"),
    "dynamic": os.path.join(".tao", "knowledge", "refs",
                            "TESTCASES-104t-dynamic-summary.json"),
}

PASS = "pass"
NON_PASS = ("fail", "known-fail", "blocked")
TIMEOUT_CAPABILITY = "time budget"

# Owner vocabulary: which layer has to change (ADR-0048 D2/D5 wording).
OWNERS = ("spec", "implementation", "test asset", "environment", "budget")


def _load_baseline_module():
    """Import the per-track aggregator for its capability -> change table.

    Reusing one table keeps this report and the per-track baseline consistent;
    a local copy would be free to drift.
    """
    path = os.path.join(REPO_ROOT, "tools", "testcases", "tset",
                        "gem5-se-baseline", "run_gem5_se_baseline.py")
    spec = importlib.util.spec_from_file_location("gem5_se_baseline", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


BASELINE = _load_baseline_module()
CHANGE_SURFACE = BASELINE.CHANGE_SURFACE

# ---------------------------------------------------------------------------
# attribution registries
# ---------------------------------------------------------------------------

#: ``gem5_only_fail`` cases.  Key = (suite, case); an entry may apply in both
#: link modes.  ``owner`` is the layer that has to change, ``issue`` the ledger
#: id (``None`` = environment gap, documented by ``detail``).
GEM5_ONLY_FAIL = {
    # QEMU user-mode executes ``/bin/echo`` through the **host**; the guest root
    # has no DADAO ``/bin/echo``, so gem5 SE fails the exec (ENOEXEC).  Same
    # root cause in both link modes (dynamic fails earlier, in the loader).
    ("libc-test", "functional/popen"): dict(
        issue=None, owner="environment",
        detail="guest root has no DADAO /bin/sh|/bin/echo; QEMU user execs the "
               "host binary, gem5 SE cannot (ENOEXEC / host interp)"),
    ("libc-test", "functional/spawn"): dict(
        issue=None, owner="environment",
        detail="posix_spawnp('echo') -> no DADAO /bin/echo in the guest root"),
    ("libc-test", "functional/vfork"): dict(
        issue=None, owner="environment",
        detail="execl('/bin/echo') -> ENOEXEC; host binary cannot run under "
               "the DADAO ISA"),
    ("libc-test", "regression/execle-env"): dict(
        issue=None, owner="environment",
        detail="execle('echo') -> ENOEXEC; same missing guest-root tool"),
    # SE driver concatenates fd1/fd2 after the fact, losing the 2>&1 order
    # (ISS-357).  The guest output text itself is byte-identical.
    ("llvm-ts", "MultiSource/Benchmarks/FreeBench/analyzer"):
        dict(issue="ISS-357", owner="test asset",
             detail="stderr+stdout+exit equals the reference byte-for-byte; "
                    "driver captures fd1/fd2 separately"),
    ("llvm-ts", "MultiSource/Benchmarks/FreeBench/distray"):
        dict(issue="ISS-357", owner="test asset",
             detail="md5(stderr+stdout+exit 0) == reference md5"),
    ("llvm-ts", "MultiSource/Benchmarks/FreeBench/pifft"):
        dict(issue="ISS-357", owner="test asset",
             detail="stderr+stdout+exit equals the reference byte-for-byte"),
    ("llvm-ts", "MultiSource/Benchmarks/FreeBench/mason"):
        dict(issue="ISS-357", owner="test asset",
             detail="1200 s retest only; stderr+stdout+exit == reference"),
    ("llvm-ts", "MultiSource/Benchmarks/FreeBench/neural"):
        dict(issue="ISS-357", owner="test asset",
             detail="1200 s retest only; stderr+stdout+exit == reference"),
    ("llvm-ts", "MultiSource/Benchmarks/Prolangs-C/bison"):
        dict(issue="ISS-357", owner="test asset",
             detail="one stderr line sits mid-stream; any fd1/fd2 "
                    "concatenation order is wrong"),
    # unix-smail: the guest stdout is byte-identical to the reference line; the
    # exit code differs (69 vs 0) because deliver() pipes the letter to
    # /bin/lmail, then /bin/smail (return_mail).  QEMU user executes the host
    # binaries (missing -> the LOCAL branch resets exitstat to 0); gem5 SE
    # cannot load a host x86 ELF.  The -d control run (no mailer) exits 0.
    ("llvm-ts", "MultiSource/Benchmarks/Prolangs-C/unix-smail"):
        dict(issue=None, owner="environment",
             detail="deliver() execs /bin/lmail + /bin/smail via popen; no "
                    "DADAO mailer in the guest root, gem5 SE cannot run the "
                    "host ELF (QEMU user execs it, LOCAL branch resets 0); "
                    "-d control run: exit 0, full output"),
}

#: ``qemu_only_fail`` is empty by construction: ADR-0048 D5 says a gem5 pass
#: over a QEMU non-pass must be investigated, never accepted.  Any such row
#: fails the report until it is located in spec/implementation/test asset.
QEMU_ONLY_FAIL = {}

#: ``both_non_pass`` rows must have the **same** verdict on both engines.
BOTH_NON_PASS = {
    ("libc-test", "functional/strptime"): dict(
        issue="ISS-251", owner="spec",
        detail="musl strptime %s is parse-only; both engines report the same "
               "known-fail with the same basis"),
}

#: ``blocked`` evidence -> owner.  First match wins; no match is a failure.
BLOCKED_RULES = (
    (re.compile(r"syscall (\d+) \((\w+)\) not implemented"),
     "implementation", "SE syscall table: {name} ({num})"),
    (re.compile(r"ldso aborted before the program's own verdict"),
     "implementation", "ldso/search path: the DT_NEEDED object is not found"),
    (re.compile(r"non-guest simulation end"),
     "implementation", "SE loader/exit modelling: no guest status"),
    (re.compile(r"process\.cc:\d+: fatal: fatal condition \(seg\.base & 3\)"),
     "implementation",
     "SE loader: the BSS sub-segment base (p_vaddr + p_filesz) must be 4-byte "
     "aligned, but lld leaves p_filesz byte-aligned (segment 5); QEMU loads "
     "the same ELF -- byte-addressable .bss needs no word alignment"),
    (re.compile(r"image_file_data\.cc.*lib64/ld-linux"),
     "environment",
     "guest root has no DADAO /bin/sh; the exec falls back to the host ELF and "
     "its PT_INTERP (/lib64/ld-linux-x86-64.so.2)"),
)


class ReportError(Exception):
    pass


# ---------------------------------------------------------------------------
# loading + recomputation
# ---------------------------------------------------------------------------

def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_track(mode, path):
    if not os.path.isfile(path):
        raise ReportError(f"{mode}: baseline not found: {path}")
    with open(path, "r", encoding="utf-8") as fh:
        doc = json.load(fh)
    declared_mode = doc.get("link_mode", "static")
    if declared_mode != mode:
        raise ReportError(f"{mode}: {path} is a {declared_mode!r} baseline")
    for suite in SUITES:
        if suite not in doc.get("suites", {}):
            raise ReportError(f"{mode}: suite {suite!r} missing in {path}")
    return doc


def recompute_suite(doc, suite):
    """Recompute the declared counts / cross table for one suite."""
    data = doc["suites"][suite]
    rows = data["cases"]
    keys = [r["case"] for r in rows]
    if len(keys) != len(set(keys)):
        raise ReportError(f"{suite}: duplicate case ids in the per-case rows")

    q_counts, g_counts = {}, {}
    for row in rows:
        q_counts[row["qemu_status"]] = q_counts.get(row["qemu_status"], 0) + 1
        g_counts[row["gem5_status"]] = g_counts.get(row["gem5_status"], 0) + 1

    cross = {k: [] for k in (
        "both_pass", "gem5_only_fail", "qemu_only_fail", "gem5_blocked",
        "gem5_timeout", "gem5_blocked_real", "blocked_but_qemu_pass",
        "timeout_but_qemu_pass", "blocked_real_but_qemu_pass",
        "qemu_blocked_gem5_pass", "both_non_pass", "diff")}
    for row in rows:
        q, g = row["qemu_status"], row["gem5_status"]
        name = row["case"]
        if q == PASS and g == PASS:
            cross["both_pass"].append(name)
        elif g == "blocked":
            cross["gem5_blocked"].append(name)
            timeout = row.get("gem5_capability") == TIMEOUT_CAPABILITY
            cross["gem5_timeout" if timeout else "gem5_blocked_real"].append(
                name)
            if q == PASS:
                cross["blocked_but_qemu_pass"].append(name)
                cross["timeout_but_qemu_pass" if timeout
                      else "blocked_real_but_qemu_pass"].append(name)
        elif g in ("fail", "known-fail") and q == PASS:
            cross["gem5_only_fail"].append(name)
        elif g == PASS and q in NON_PASS:
            cross["qemu_only_fail"].append(name)
            if q == "blocked":
                cross["qemu_blocked_gem5_pass"].append(name)
        elif q in NON_PASS and g in NON_PASS:
            if q == g:
                cross["both_non_pass"].append(name)
            else:
                cross["diff"].append(name)
    return rows, q_counts, g_counts, cross


def _compare_block(mode, suite, what, declared, actual, errors):
    """Compare a declared sub-count block with the recomputed one.

    Only the keys the baseline declares are compared (llvm-ts carries extra
    oracle-census keys that are not status counts).
    """
    if not isinstance(declared, dict):
        return
    for key, want in declared.items():
        if key not in actual:
            continue
        got = actual[key]
        if got != want:
            errors.append(f"{mode}/{suite}: {what}[{key}] declared {want} but "
                          f"recomputed {got}")


def recompute_track(mode, doc):
    """Validate one baseline and return its recomputed view."""
    errors = []
    suites = {}
    totals = dict(qemu_pass=0, gem5_pass=0, both_pass=0, blocked=0,
                  blocked_all=0, timeout=0, blocked_but_qemu_pass=0,
                  blocked_real_but_qemu_pass=0, timeout_but_qemu_pass=0,
                  gem5_only_fail=0, qemu_only_fail=0)
    for suite in SUITES:
        data = doc["suites"][suite]
        rows, q_counts, g_counts, cross = recompute_suite(doc, suite)
        _compare_block(mode, suite, "qemu counts",
                       data.get("qemu", {}).get("counts", {}), q_counts, errors)
        _compare_block(mode, suite, "gem5 counts",
                       data.get("gem5", {}).get("counts", {}), g_counts, errors)
        declared_cross = data.get("cross_counts", {})
        actual_cross = {k: len(v) for k, v in cross.items() if k != "diff"}
        _compare_block(mode, suite, "cross", declared_cross, actual_cross,
                       errors)
        declared_lists = data.get("cross", {})
        for key, names in cross.items():
            want = declared_lists.get(key)
            if want is None:
                continue
            if sorted(want) != sorted(names):
                errors.append(f"{mode}/{suite}: cross list {key} declared "
                              f"{len(want)} case(s) but recomputed {len(names)}")
        suites[suite] = dict(
            rows=rows, qemu_counts=q_counts, gem5_counts=g_counts,
            cross={k: sorted(v) for k, v in cross.items()},
            qemu_driver=data.get("qemu", {}),
            gem5_driver=data.get("gem5", {}),
            total=len(rows),
            discovered=data.get("gem5", {}).get("discovered"),
        )
        totals["qemu_pass"] += q_counts.get(PASS, 0)
        totals["gem5_pass"] += g_counts.get(PASS, 0)
        totals["both_pass"] += len(cross["both_pass"])
        totals["blocked"] += len(cross["gem5_blocked_real"])
        totals["blocked_all"] += len(cross["gem5_blocked"])
        totals["timeout"] += len(cross["gem5_timeout"])
        totals["blocked_but_qemu_pass"] += len(cross["blocked_but_qemu_pass"])
        totals["timeout_but_qemu_pass"] += len(cross["timeout_but_qemu_pass"])
        totals["blocked_real_but_qemu_pass"] += len(
            cross["blocked_real_but_qemu_pass"])
        totals["gem5_only_fail"] += len(cross["gem5_only_fail"])
        totals["qemu_only_fail"] += len(cross["qemu_only_fail"])
        if cross["diff"]:
            errors.append(f"{mode}/{suite}: DIFF row(s): {cross['diff']}")

    buckets = {}
    for suite in SUITES:
        for row in suites[suite]["rows"]:
            if row["gem5_status"] != "blocked":
                continue
            if row.get("gem5_capability") == TIMEOUT_CAPABILITY:
                continue
            cap = row.get("gem5_capability") or "unattributed"
            buckets.setdefault(cap, []).append((suite, row["case"]))
    declared_gap = {e["capability"]: e["blocked_cases"]
                    for e in doc.get("gap_inventory", [])}
    for cap, cases in buckets.items():
        want = declared_gap.get(cap)
        if want is None:
            errors.append(f"{mode}: gap bucket {cap!r} not in the declared "
                          f"gap_inventory")
        elif want != len(cases):
            errors.append(f"{mode}: gap bucket {cap!r} declared {want} but "
                          f"recomputed {len(cases)}")
    for cap in declared_gap:
        if cap not in buckets:
            errors.append(f"{mode}: declared gap bucket {cap!r} has no case")

    _compare_block(mode, "(totals)", "totals", doc.get("totals", {}), totals,
                   errors)
    return dict(suites=suites, totals=totals, buckets=buckets, errors=errors,
                doc=doc)


# ---------------------------------------------------------------------------
# attribution
# ---------------------------------------------------------------------------

def attribute_blocked(row):
    reason = row.get("gem5_reason") or ""
    for pattern, owner, detail in BLOCKED_RULES:
        m = pattern.search(reason)
        if not m:
            continue
        if m.groups():
            return dict(owner=owner, issue=None,
                        detail=detail.format(num=m.group(1), name=m.group(2)))
        return dict(owner=owner, issue=None, detail=detail)
    return None


def _check_owner(entry, where, errors):
    if entry.get("owner") not in OWNERS:
        errors.append(f"{where}: owner {entry.get('owner')!r} is outside "
                      f"{OWNERS}")
    return entry.get("owner") in OWNERS


def build_attribution(mode, track):
    """Every non-pass row gets exactly one attribution entry."""
    errors = []
    entries = dict(gem5_only_fail=[], qemu_only_fail=[], blocked=[],
                   timeout=[], both_non_pass=[])
    for suite in SUITES:
        for row in track["suites"][suite]["rows"]:
            q, g = row["qemu_status"], row["gem5_status"]
            name = row["case"]
            if q == PASS and g == PASS:
                continue
            if g == "blocked":
                if row.get("gem5_capability") == TIMEOUT_CAPABILITY:
                    entries["timeout"].append(dict(
                        mode=mode, suite=suite, case=name, qemu_status=q,
                        owner="budget", issue=None,
                        detail="budget expiry, not a verdict"))
                    continue
                if not row.get("gem5_capability"):
                    errors.append(f"{mode}/{suite}/{name}: blocked without a "
                                  f"capability label")
                    continue
                attr = attribute_blocked(row)
                if attr is None:
                    errors.append(f"{mode}/{suite}/{name}: blocked but the "
                                  f"evidence maps to no owner: "
                                  f"{(row.get('gem5_reason') or '')!r}")
                    continue
                _check_owner(attr, f"{mode}/{suite}/{name}", errors)
                attr.update(mode=mode, suite=suite, case=name,
                            qemu_status=q,
                            capability=row.get("gem5_capability"),
                            change_surface=CHANGE_SURFACE.get(
                                row.get("gem5_capability"),
                                CHANGE_SURFACE.get("other", "")),
                            evidence=row.get("gem5_reason"))
                entries["blocked"].append(attr)
                continue
            if q == PASS and g in ("fail", "known-fail"):
                attr = GEM5_ONLY_FAIL.get((suite, name))
                if attr is None:
                    errors.append(f"{mode}/{suite}/{name}: gem5_only_fail "
                                  f"(gem5={g}, qemu=pass) has no attribution "
                                  f"entry")
                    continue
                _check_owner(attr, f"{mode}/{suite}/{name}", errors)
                entries["gem5_only_fail"].append(dict(
                    attr, mode=mode, suite=suite, case=name, gem5_status=g,
                    gem5_exit=row.get("gem5_exit"),
                    evidence=row.get("gem5_reason")))
                continue
            if g == PASS and q in NON_PASS:
                attr = QEMU_ONLY_FAIL.get((suite, name))
                if attr is None:
                    errors.append(f"{mode}/{suite}/{name}: qemu_only_fail "
                                  f"(qemu={q}, gem5=pass) is not located in "
                                  f"spec/implementation/test asset")
                    continue
                _check_owner(attr, f"{mode}/{suite}/{name}", errors)
                entries["qemu_only_fail"].append(dict(
                    attr, mode=mode, suite=suite, case=name, qemu_status=q,
                    evidence=row.get("qemu_reason")))
                continue
            if q in NON_PASS and g in NON_PASS:
                if q != g:
                    errors.append(f"{mode}/{suite}/{name}: verdict diff "
                                  f"(qemu={q}, gem5={g})")
                    continue
                attr = BOTH_NON_PASS.get((suite, name))
                if attr is None:
                    errors.append(f"{mode}/{suite}/{name}: both non-pass "
                                  f"({q}) without an admitted basis")
                    continue
                _check_owner(attr, f"{mode}/{suite}/{name}", errors)
                entries["both_non_pass"].append(dict(
                    attr, mode=mode, suite=suite, case=name, status=q))
                continue
            errors.append(f"{mode}/{suite}/{name}: unclassified "
                          f"(qemu={q}, gem5={g})")
    for key in entries:
        entries[key].sort(key=lambda e: (e["suite"], e["case"]))
    return entries, errors


# ---------------------------------------------------------------------------
# static vs dynamic join
# ---------------------------------------------------------------------------

def _owner_map(attributions):
    """(mode, suite, case) -> (owner, issue) for every attributed row."""
    out = {}
    for key in ("gem5_only_fail", "qemu_only_fail", "blocked", "timeout",
                "both_non_pass"):
        for entry in attributions.get(key, []):
            out[(entry["mode"], entry["suite"], entry["case"])] = (
                entry.get("owner"), entry.get("issue"))
    return out


def join_modes(tracks, owners=None):
    """Compare the same case across link modes."""
    owners = owners or {}
    errors = []
    rows = []
    for suite in SUITES:
        s_rows = {r["case"]: r for r in
                  tracks["static"]["suites"][suite]["rows"]}
        d_rows = {r["case"]: r for r in
                  tracks["dynamic"]["suites"][suite]["rows"]}
        for name in sorted(set(s_rows) | set(d_rows)):
            s, d = s_rows.get(name), d_rows.get(name)
            if s is None or d is None:
                rows.append(dict(
                    suite=suite, case=name,
                    static="absent" if s is None else s["gem5_status"],
                    dynamic="absent" if d is None else d["gem5_status"],
                    kind="case_set"))
                continue
            s_status, d_status = s["gem5_status"], d["gem5_status"]
            if s_status == d_status:
                kind = "same"
            elif s_status == PASS:
                kind = "static_pass_dynamic_not"
            elif d_status == PASS:
                kind = "dynamic_pass_static_not"
            else:
                # A different non-pass verdict is acceptable only when both
                # modes name the same owner (e.g. static reaches the verdict
                # and fails, dynamic cannot even load).
                s_owner = owners.get(("static", suite, name))
                d_owner = owners.get(("dynamic", suite, name))
                if s_owner and d_owner and s_owner[0] == d_owner[0]:
                    kind = "same_owner_diff"
                else:
                    kind = "both_non_pass_diff"
                    errors.append(f"{suite}/{name}: static={s_status} but "
                                  f"dynamic={d_status} (neither passes, "
                                  f"owners {s_owner} vs {d_owner})")
            rows.append(dict(suite=suite, case=name, static=s_status,
                             dynamic=d_status, kind=kind))
    return rows, errors


# ---------------------------------------------------------------------------
# timeout retest (longer budget, separate from the main counts)
# ---------------------------------------------------------------------------

def recheck_summary(doc):
    """Validate the optional 1200 s retest block (static baseline)."""
    out = {}
    errors = []
    for suite, block in (doc.get("timeout_recheck") or {}).items():
        cases = block.get("cases", [])
        passed = list(block.get("passed", []))
        still = list(block.get("still_blocked", []))
        other = list(block.get("other", []))
        if block.get("total") != len(cases):
            errors.append(f"timeout_recheck/{suite}: total "
                          f"{block.get('total')} != {len(cases)} case rows")
        if len(passed) + len(still) + len(other) != len(cases):
            errors.append(f"timeout_recheck/{suite}: "
                          f"{len(passed)}+{len(still)}+{len(other)} != "
                          f"{len(cases)}")
        for name in other:
            if (suite, name) not in GEM5_ONLY_FAIL:
                errors.append(f"timeout_recheck/{suite}/{name}: turned "
                              f"non-pass under the longer budget without an "
                              f"attribution entry")
        out[suite] = dict(timeout_seconds=block.get("timeout_seconds"),
                          total=len(cases), passed=sorted(passed),
                          still_blocked=sorted(still), other=sorted(other))
    return out, errors


# ---------------------------------------------------------------------------
# report rendering
# ---------------------------------------------------------------------------

def _counts_line(track, suite):
    data = track["suites"][suite]
    q = data["qemu_counts"]
    g = data["gem5_counts"]
    declared_skip = q.get("excluded", g.get("excluded"))
    if declared_skip is None:
        discovered = data["discovered"] or data["total"]
        declared_skip = max(0, discovered - data["total"])
    return dict(
        total=data["total"],
        discovered=data["discovered"],
        qemu_pass=q.get(PASS, 0),
        qemu_fail=q.get("fail", 0),
        gem5_pass=g.get(PASS, 0),
        both_pass=len(data["cross"]["both_pass"]),
        gem5_fail=g.get("fail", 0),
        gem5_known_fail=g.get("known-fail", 0),
        gem5_blocked=len(data["cross"]["gem5_blocked_real"]),
        gem5_timeout=len(data["cross"]["gem5_timeout"]),
        gem5_only_fail=len(data["cross"]["gem5_only_fail"]),
        qemu_only_fail=len(data["cross"]["qemu_only_fail"]),
        skipped=declared_skip,
    )


def build_report(tracks, attributions, cross_rows, source_paths, errors):
    report = dict(
        task="INTEG-059t",
        generated_utc=datetime.datetime.now(datetime.timezone.utc)
        .strftime("%Y-%m-%dT%H:%M:%SZ"),
        scope="libc-test / llvm-ts / embench, static + dynamic, gem5 SE vs "
              "QEMU user (ADR-0048 D4/D5)",
        sources={},
        tracks={},
        cross_mode=dict(same=0, case_set=0, static_pass_dynamic_not=[],
                        dynamic_pass_static_not=[], same_owner_diff=[],
                        both_non_pass_diff=[]),
        attribution=attributions,
        timeout_recheck={},
        new_findings=[],
        known_items={},
        checks=dict(errors=errors, ok=not errors),
    )
    for mode in TRACKS:
        path = source_paths[mode]
        report["sources"][mode] = dict(
            path=os.path.relpath(path, REPO_ROOT),
            sha256=_sha256(path),
            generated_utc=tracks[mode]["doc"].get("generated_utc"),
            link_mode=tracks[mode]["doc"].get("link_mode", "static"),
        )
        report["tracks"][mode] = dict(
            totals=tracks[mode]["totals"],
            suites={s: _counts_line(tracks[mode], s) for s in SUITES},
            gap_inventory=[dict(capability=cap, blocked_cases=len(cases),
                                cases=[f"{s}:{c}" for s, c in sorted(cases)])
                           for cap, cases in
                           sorted(tracks[mode]["buckets"].items())],
            timeout_by_suite={
                s: len(tracks[mode]["suites"][s]["cross"]["gem5_timeout"])
                for s in SUITES},
        )
    for row in cross_rows:
        bucket = row["kind"]
        if bucket in ("same", "case_set"):
            report["cross_mode"][bucket] += 1
        else:
            report["cross_mode"][bucket].append(
                f"{row['suite']}:{row['case']} (static={row['static']}, "
                f"dynamic={row['dynamic']})")
    recheck, _recheck_errs = recheck_summary(tracks["static"]["doc"])
    report["timeout_recheck"] = recheck
    align = [e for e in attributions["blocked"]
             if "BSS sub-segment" in (e.get("detail") or "")]
    if align:
        report["new_findings"].append(dict(
            title="gem5 SE loader rejects a byte-aligned .bss sub-segment",
            owner="implementation",
            scope="components/gem5 (`src/arch/dadao/process.cc` PT_LOAD "
                  "walk: `(seg.base & 3) != 0`)",
            cases=sorted(f"{e['mode']}:{e['suite']}:{e['case']}"
                         for e in align),
            note="lld leaves p_filesz byte-aligned, so the uninitialised "
                 "sub-segment starts at p_vaddr + p_filesz (e.g. 0x53de6); "
                 "QEMU user loads the same ELF.  Byte-addressable .bss needs "
                 "no word alignment, so this is a loader restriction, not a "
                 "guest defect.  Ledger id not allocated (out of this task "
                 "file's range)."))
    report["known_items"] = dict(
        ISS_357=dict(
            status="open", scope="gem5/testcases",
            cases=sorted(
                [f"{e['mode']}:{e['suite']}:{e['case']}"
                 for e in attributions["gem5_only_fail"]
                 if e.get("issue") == "ISS-357"]
                + [f"static(retest):{suite}:{name}"
                   for suite, block in report["timeout_recheck"].items()
                   for name in block["other"]]),
            note="SE output capture loses the fd1/fd2 write order; recorded "
                 "as fail, never as a capability gap"),
        ISS_343=dict(
            status="closed (QEMU-084t)", scope="qemu", cases=[],
            note="rlimit no-op: no tset case in the non-pass lists is "
                 "attributed to it; not rewritten as pass"),
        environment_gap=dict(
            cases=sorted(
                [f"{e['mode']}:{e['suite']}:{e['case']}"
                 for e in attributions["gem5_only_fail"]
                 if e.get("owner") == "environment"]
                + [f"{e['mode']}:{e['suite']}:{e['case']}"
                   for e in attributions["blocked"]
                   if e.get("owner") == "environment"]),
            note="no DADAO /bin/sh / /bin/echo (/bin/lmail, /bin/smail) in "
                 "the guest root; QEMU user executes the host binary"),
        picolibc_B7=dict(
            status="blocked", scope="parity FS matrix",
            note="math_test stays BLOCKED; not part of the SE tset tracks and "
                 "never counted as pass"),
    )
    return report


def render_markdown(report):
    lines = []
    add = lines.append
    add("# SE tset bidirectional parity: gem5 SE vs QEMU user "
        "(static + dynamic)")
    add("")
    add("> Generated by `tools/testcases/parity/se_tset_matrix.py` from the "
        "two committed tset baselines; every count is recomputed from the "
        "per-case rows, never typed by hand (`ADR-0048 D2/D4/D5`).")
    add(f"> Generated: {report['generated_utc']}. Scope: {report['scope']}.")
    add("")
    add("## Sources")
    add("")
    for mode in TRACKS:
        src = report["sources"][mode]
        add(f"- {mode}: `{src['path']}` sha256 `{src['sha256'][:16]}` "
            f"(baseline generated {src['generated_utc']})")
    add("")
    add("## Counts per track x suite")
    add("")
    add("| track | suite | total | qemu_pass | qemu_fail | gem5_pass | "
        "gem5_fail | gem5_only_fail | qemu_only_fail | blocked | timeout | "
        "skipped |")
    add("| --- | --- | " + " | ".join(["---"] * 10) + " |")
    for mode in TRACKS:
        for suite in SUITES:
            c = report["tracks"][mode]["suites"][suite]
            add(f"| {mode} | {suite} | {c['total']} | {c['qemu_pass']} | "
                f"{c['qemu_fail']} | {c['gem5_pass']} | {c['gem5_fail']} | "
                f"{c['gem5_only_fail']} | {c['qemu_only_fail']} | "
                f"{c['gem5_blocked']} | {c['gem5_timeout']} | "
                f"{c['skipped']} |")
    add("")
    add("`blocked` excludes `timeout` (budget expiry, not a capability gap); "
        "`skipped` = discovered - executed with the driver's declared "
        "exclusion reasons.")
    add("")
    add("## Totals (recomputed)")
    add("")
    add("| track | qemu_pass | gem5_pass | both_pass | blocked | timeout | "
        "gem5_only_fail | qemu_only_fail |")
    add("| --- | " + " | ".join(["---"] * 7) + " |")
    for mode in TRACKS:
        t = report["tracks"][mode]["totals"]
        add(f"| {mode} | {t['qemu_pass']} | {t['gem5_pass']} | "
            f"{t['both_pass']} | {t['blocked']} | {t['timeout']} | "
            f"{t['gem5_only_fail']} | {t['qemu_only_fail']} |")
    add("")
    add("## gem5_only_fail (QEMU passed, gem5 SE did not)")
    add("")
    entries = report["attribution"]["gem5_only_fail"]
    if entries:
        add("| track | suite | case | gem5 | attribution | owner | evidence |")
        add("| --- | --- | --- | --- | --- | --- | --- |")
        for e in entries:
            ev = (e.get("evidence") or "").replace("|", "\\|")[:120]
            add(f"| {e['mode']} | {e['suite']} | `{e['case']}` | "
                f"{e['gem5_status']}/{e.get('gem5_exit')} | "
                f"{e.get('issue') or 'environment gap'} | {e['owner']} | "
                f"{ev} |")
    else:
        add("(none)")
    add("")
    add("## qemu_only_fail (gem5 SE passed, QEMU did not)")
    add("")
    entries = report["attribution"]["qemu_only_fail"]
    if entries:
        for e in entries:
            add(f"- {e['mode']}:{e['suite']}:{e['case']} — owner {e['owner']}")
    else:
        add("(none)")
    add("")
    add("Per `ADR-0048 D5` this direction is never accepted as a gem5 win; any "
        "row must name its owner (`spec` / `implementation` / `test asset`).")
    add("")
    add("## blocked (real capability gaps; timeout excluded)")
    add("")
    add("| track | suite | case | capability | owner | change surface |")
    add("| --- | --- | --- | --- | --- | --- |")
    for e in report["attribution"]["blocked"]:
        add(f"| {e['mode']} | {e['suite']} | `{e['case']}` | "
            f"{e.get('capability')} | {e['owner']} | {e.get('detail')} |")
    add("")
    add("## timeout (budget expiry; not a verdict)")
    add("")
    for mode in TRACKS:
        for suite in SUITES:
            names = sorted(e["case"] for e in report["attribution"]["timeout"]
                           if e["mode"] == mode and e["suite"] == suite)
            if names:
                add(f"- {mode} / {suite} ({len(names)}): "
                    + ", ".join(f"`{n}`" for n in names))
    add("")
    add("## both_non_pass (same verdict on both engines)")
    add("")
    for e in report["attribution"]["both_non_pass"]:
        add(f"- {e['mode']}:{e['suite']}:{e['case']} = {e['status']} "
            f"({e.get('issue') or 'admitted'}; {e['detail']})")
    add("")
    add("## static vs dynamic join")
    add("")
    cm = report["cross_mode"]
    add(f"- same gem5 verdict in both modes: {cm['same']}")
    add(f"- case-set differences (declared per-mode scope): {cm['case_set']}")
    add(f"- pass in static, not in dynamic: "
        f"{len(cm['static_pass_dynamic_not'])}")
    for item in cm["static_pass_dynamic_not"]:
        add(f"  - {item}")
    add(f"- pass in dynamic, not in static: "
        f"{len(cm['dynamic_pass_static_not'])}")
    for item in cm["dynamic_pass_static_not"]:
        add(f"  - {item}")
    add(f"- neither passes, same owner (expected mode difference): "
        f"{len(cm['same_owner_diff'])}")
    for item in cm["same_owner_diff"]:
        add(f"  - {item}")
    add(f"- neither passes with differing verdicts/owners: "
        f"{len(cm['both_non_pass_diff'])}")
    add("")
    add("## timeout retest under a longer budget (static track)")
    add("")
    if not report["timeout_recheck"]:
        add("(not run)")
    for suite, block in sorted(report["timeout_recheck"].items()):
        add(f"- {suite} ({block['total']} case(s) at "
            f"{block['timeout_seconds']} s): passed "
            f"{len(block['passed'])}, still timeout "
            f"{len(block['still_blocked'])}, turned non-pass "
            f"{len(block['other'])}")
        if block["still_blocked"]:
            add("  - still timeout: "
                + ", ".join(f"`{n}`" for n in block["still_blocked"]))
        if block["other"]:
            add("  - turned non-pass: "
                + ", ".join(f"`{n}`" for n in block["other"])
                + " (all `ISS-357` output-order cases, see above)")
    add("")
    add("The retest is a separate budget experiment; it does not change the "
        "main counts above (`TESTCASES-103t`).")
    add("")
    add("## New findings (no ledger id yet)")
    add("")
    if not report["new_findings"]:
        add("(none)")
    for item in report["new_findings"]:
        add(f"- {item['title']} — owner {item['owner']}; scope "
            f"{item['scope']}; {len(item['cases'])} case(s): "
            + ", ".join(f"`{c}`" for c in item["cases"]))
        add(f"  {item['note']}")
    add("")
    add("## Known items (recorded, never rewritten as PASS)")
    add("")
    ki = report["known_items"]
    add(f"- `ISS-357` ({ki['ISS_357']['status']}): "
        f"{len(ki['ISS_357']['cases'])} case(s) — "
        + (", ".join(f"`{c}`" for c in ki["ISS_357"]["cases"]) or "—"))
    add(f"- `ISS-343` ({ki['ISS_343']['status']}): no tset case attributed.")
    add(f"- environment gap: {len(ki['environment_gap']['cases'])} row(s) — "
        + (", ".join(f"`{c}`" for c in ki["environment_gap"]["cases"]) or "—"))
    add(f"- picolibc `math_test` B7 ({ki['picolibc_B7']['status']}): stays "
        f"BLOCKED in the FS matrix; not part of these tracks.")
    add("")
    add("## Checks")
    add("")
    if report["checks"]["ok"]:
        add("- every declared count/cross/total matches the recomputed value")
        add("- every non-pass row carries an owner; `qemu_only_fail` = 0")
    else:
        for err in report["checks"]["errors"]:
            add(f"- FAIL: {err}")
    add("")
    return "\n".join(lines) + "\n"


def render_matrix_section(report):
    """Compact SE block for `docs/TestReports/M11-三平台一致矩阵.md`."""
    lines = ["## SE tset matrix (gem5 SE vs QEMU user; static + dynamic)", ""]
    add = lines.append
    add("> Generated by `tools/testcases/parity/se_tset_matrix.py` from the "
        "committed tset baselines; counts recomputed from the per-case rows.")
    add("")
    add("| track | suite | total | qemu_pass | qemu_fail | gem5_pass | "
        "gem5_fail | gem5_only_fail | qemu_only_fail | blocked | timeout | "
        "skipped |")
    add("| --- | --- | " + " | ".join(["---"] * 10) + " |")
    for mode in TRACKS:
        for suite in SUITES:
            c = report["tracks"][mode]["suites"][suite]
            add(f"| {mode} | {suite} | {c['total']} | {c['qemu_pass']} | "
                f"{c['qemu_fail']} | {c['gem5_pass']} | {c['gem5_fail']} | "
                f"{c['gem5_only_fail']} | {c['qemu_only_fail']} | "
                f"{c['gem5_blocked']} | {c['gem5_timeout']} | "
                f"{c['skipped']} |")
    add("")
    add("### gem5_only_fail (QEMU passed, gem5 SE did not)")
    add("")
    entries = report["attribution"]["gem5_only_fail"]
    if entries:
        for e in entries:
            add(f"- {e['mode']}:{e['suite']}:`{e['case']}` — "
                f"{e.get('issue') or 'environment gap'} ({e['owner']})")
    else:
        add("(none)")
    add("")
    add("### qemu_only_fail (gem5 SE passed, QEMU did not)")
    add("")
    entries = report["attribution"]["qemu_only_fail"]
    if entries:
        for e in entries:
            add(f"- {e['mode']}:{e['suite']}:`{e['case']}` — {e['owner']}")
    else:
        add("(none)")
    add("")
    add("### blocked (real capability gaps; timeout excluded)")
    add("")
    blocked_by = {}
    for e in report["attribution"]["blocked"]:
        blocked_by.setdefault((e["mode"], e.get("capability")), []).append(
            e["case"])
    for (mode, cap), cases in sorted(blocked_by.items()):
        add(f"- {mode} / {cap} ({len(cases)}): "
            + ", ".join(f"`{c}`" for c in sorted(cases)))
    add("")
    add("### timeout (budget expiry, not a verdict)")
    add("")
    for mode in TRACKS:
        for suite in SUITES:
            names = sorted(e["case"] for e in report["attribution"]["timeout"]
                           if e["mode"] == mode and e["suite"] == suite)
            if names:
                add(f"- {mode} / {suite} ({len(names)}): "
                    + ", ".join(f"`{n}`" for n in names))
    add("")
    add("Full per-case attribution and the static/dynamic join: "
        "`.tao/knowledge/refs/INTEG-059t-se-parity-summary.md`.")
    add("")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# snapshot composition (FS matrix + picolibc block + SE section)
# ---------------------------------------------------------------------------

#: Legacy carry path: picolibc rows copied verbatim from the previous accepted
#: snapshot.  Kept for snapshots whose B7 registration is still pending (the
#: ruling is ``GEM5-033t``; live regeneration uses ``picolibc_json`` below).
CARRY_NOTE = (
    "> The current engine build reports `math_test` as 0 errors / exit 0",
    "> on gem5 (reproduced twice: see the SE parity report).  That",
    "> contradicts the `B7` registration, so per the task constraint the",
    "> registration is **not** rewritten to PASS and these rows are the",
    "> previous accepted snapshot's, not this run's.  Ruling pending.",
)

_PICOLIBC_COUNT_KEYS = ("total", "agree_pass", "agree_fail", "gem5_only_fail",
                        "qemu_only_fail", "diff", "deferred", "skip_profile",
                        "blocked", "n_a")

_VERDICT_BUCKET = {"AGREE_PASS": "agree_pass", "AGREE_FAIL": "agree_fail",
                   "GEM5_ONLY_FAIL": "gem5_only_fail",
                   "QEMU_ONLY_FAIL": "qemu_only_fail", "DIFF": "diff",
                   "BLOCKED_SIDE": "blocked", "N/A": "n_a"}


def picolibc_block_from_json(path):
    """Build the snapshot's picolibc block from a live run_parity JSON.

    Counts are recomputed from the per-case rows and compared against the
    JSON's declared counts (no hand-typed numbers); ``math_test`` must be PASS
    on both engines with a zero-error guest summary in the gem5 note.
    """
    with open(path, "r", encoding="utf-8") as fh:
        doc = json.load(fh)
    rows = [r for r in doc.get("cases") or [] if r.get("scope") == "picolibc"]
    if not rows:
        raise ReportError(f"picolibc: no rows in {path}")
    counts = {k: 0 for k in _PICOLIBC_COUNT_KEYS}
    detail = []
    for row in rows:
        if row.get("profile") != "tiny":
            raise ReportError(f"picolibc: non-tiny row {row.get('case_id')}")
        counts["total"] += 1
        verdict = row.get("verdict")
        key = _VERDICT_BUCKET.get(verdict)
        if verdict == "N/A":
            qs = row["qemu"]["status"]
            if qs in ("DEFERRED", "SKIP_PROFILE"):
                key = None
            if qs == "DEFERRED":
                counts["deferred"] += 1
            if qs == "SKIP_PROFILE":
                counts["skip_profile"] += 1
        if key is None and verdict != "N/A":
            raise ReportError(f"picolibc: bad verdict {verdict!r} for "
                              f"{row.get('case_id')}")
        if key:
            counts[key] += 1
        if verdict != "AGREE_PASS":
            note = (row.get("attribution") or row.get("note") or "")
            detail.append("| %s | %s | `%s` | %s/%s | %s/%s | %s | %s |" % (
                row["profile"], row["scope"], row["case_id"],
                row["qemu"]["status"], row["qemu"].get("exit"),
                row["gem5"]["status"], row["gem5"].get("exit"),
                verdict, note.replace("|", "/")))
    declared = (doc.get("counts") or {}).get("tiny/picolibc")
    if declared is None:
        raise ReportError(f"picolibc: no declared tiny/picolibc counts in "
                          f"{path}")
    want = {k: declared.get(k) for k in _PICOLIBC_COUNT_KEYS}
    if want != counts:
        raise ReportError("picolibc: declared counts differ from the rows: "
                          f"{want} != {counts}")
    math = [r for r in rows if r["case_id"].endswith("/math_test")]
    if len(math) != 1:
        raise ReportError("picolibc: expected exactly one math_test row")
    math = math[0]
    if math["qemu"]["status"] != "PASS" or math["gem5"]["status"] != "PASS":
        raise ReportError("picolibc/math_test: not PASS on both engines "
                          f"(QEMU {math['qemu']['status']} / gem5 "
                          f"{math['gem5']['status']})")
    m = re.search(r"Tested (\d+) functions, (\d+) errors",
                  math["gem5"].get("note") or "")
    if not m or int(m.group(1)) <= 0 or int(m.group(2)) != 0:
        raise ReportError("picolibc/math_test: gem5 note lacks a zero-error "
                          f"guest summary ({math['gem5'].get('note')!r})")
    counts_row = "| tiny | picolibc | " + " | ".join(
        str(counts[k]) for k in _PICOLIBC_COUNT_KEYS) + " |"
    block = ["## picolibc (live regeneration; B7 closed)", "",
             "> Regenerated by `tools/testcases/parity/run_parity.py "
             "--profiles tiny --scopes picolibc`; counts are derived from the "
             "run JSON, never typed by hand.",
             ">",
             "> `picolibc/math_test` is PASS on both engines (gem5 guest: "
             f"`{m.group(0)}`). The B7 difference was fixed by `INTEG-058t`, "
             "located by `GEM5-032t`, and deregistered by `GEM5-033t`.",
             "",
             "| profile | scope | total | agree_pass | agree_fail | "
             "gem5_only_fail | qemu_only_fail | diff | deferred | "
             "skip_profile | blocked | N/A |",
             "| --- | --- | " + " | ".join(["---"] * 10) + " |",
             counts_row,
             "",
             "| profile | scope | case_id | QEMU | gem5 | verdict | "
             "attribution / note |",
             "| --- | --- | --- | --- | --- | --- | --- |"]
    block += detail
    block += ["",
              "`picolibc/math_test` is PASS on both engines; the B7 "
              "registration is removed (`GEM5-033t`)."]
    return block


def compose_snapshot(fs_md_path, carry_from, section_text, picolibc_json=None):
    """FS markdown + picolibc block + SE section -> one snapshot."""
    with open(fs_md_path, "r", encoding="utf-8") as fh:
        fs_lines = fh.read().rstrip("\n").splitlines()
    if picolibc_json:
        # Drop any previous picolibc / SE sections from the FS input so the
        # regenerated blocks below are the only ones in the snapshot.
        for i, line in enumerate(fs_lines):
            if line.startswith("## picolibc") \
                    or line.startswith("## SE tset matrix"):
                fs_lines = fs_lines[:i]
                break
        # A run_parity markdown may carry picolibc rows inline; the block below
        # is the only place they may appear in the snapshot.
        fs_lines = [ln for ln in fs_lines
                    if not ln.startswith("| tiny | picolibc |")]
        fs_lines = "\n".join(fs_lines).rstrip("\n").splitlines()
    header = [ln for ln in fs_lines if ln.startswith("| profile | scope | "
                                                     "total |")]
    if not header:
        raise ReportError(f"compose: no counts table header in {fs_md_path}")
    if picolibc_json:
        block = picolibc_block_from_json(picolibc_json)
    else:
        with open(carry_from, "r", encoding="utf-8") as fh:
            old = fh.read().splitlines()
        carry = [ln for ln in old if ln.startswith("| tiny | picolibc |")]
        # Column-count separation, no literal numbers: the counts row has the
        # 12-column schema, each detail row the 7-column one.
        counts_rows = [ln for ln in carry if ln.count("|") == 13]
        detail_rows = [ln for ln in carry if ln.count("|") == 8]
        if len(counts_rows) != 1 or len(detail_rows) != 3:
            raise ReportError(
                f"compose: {carry_from} carries {len(counts_rows)} picolibc "
                f"counts row(s) and {len(detail_rows)} detail row(s), want 1 + 3")
        block = ["## picolibc (carried from the previous snapshot; B7 unchanged)",
                 ""]
        block += list(CARRY_NOTE)
        block += ["",
                  "| profile | scope | total | agree_pass | agree_fail | "
                  "gem5_only_fail | qemu_only_fail | diff | deferred | "
                  "skip_profile | blocked | N/A |",
                  "| --- | --- | " + " | ".join(["---"] * 10) + " |",
                  counts_rows[0],
                  "",
                  "| profile | scope | case_id | QEMU | gem5 | verdict | "
                  "attribution / note |",
                  "| --- | --- | --- | --- | --- | --- | --- |"]
        block += detail_rows
        block += ["",
                  "`picolibc/math_test` stays `BLOCKED` (`B7` numeric difference, "
                  "`GEM5-015t` leftover 1) and is never written as PASS in this "
                  "snapshot."]
    return "\n".join(fs_lines) + "\n\n" + "\n".join(block) + "\n\n" \
        + section_text.rstrip("\n") + "\n"


# ---------------------------------------------------------------------------
# analysis driver + self-test
# ---------------------------------------------------------------------------

def analyse_docs(docs):
    tracks = {}
    errors = []
    for mode in TRACKS:
        track = recompute_track(mode, docs[mode])
        errors.extend(track["errors"])
        tracks[mode] = track
    attributions = {}
    for mode in TRACKS:
        entries, errs = build_attribution(mode, tracks[mode])
        errors.extend(errs)
        for key, rows in entries.items():
            attributions.setdefault(key, []).extend(rows)
    for key in ("gem5_only_fail", "qemu_only_fail", "blocked", "timeout",
                "both_non_pass"):
        attributions.setdefault(key, [])
        attributions[key].sort(key=lambda e: (e["mode"], e["suite"], e["case"]))
    cross_rows, xerrs = join_modes(tracks, _owner_map(attributions))
    errors.extend(xerrs)
    for mode in TRACKS:
        _recheck, rerrs = recheck_summary(docs[mode])
        errors.extend(rerrs)
    return tracks, attributions, cross_rows, errors


def analyse(source_paths):
    docs = {mode: load_track(mode, source_paths[mode]) for mode in TRACKS}
    return analyse_docs(docs), docs


def write_json(path, report):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=1)
        fh.write("\n")


def _find(docs, mode, suite, case):
    for row in docs[mode]["suites"][suite]["cases"]:
        if row["case"] == case:
            return row
    raise ReportError(f"injection target missing: {suite}/{case}")


def _injections(docs):
    """One counter-example per invariant; every one must be reported."""
    cases = []

    def run(name, mutate, needle):
        local = copy.deepcopy(docs)
        mutate(local)
        _tracks, _attrs, _rows, errs = analyse_docs(local)
        hit = any(needle in e for e in errs)
        cases.append((name, hit, needle, errs[:2]))

    # 1. a gem5_only_fail that is in no registry entry must fail
    def inject_unattributed_fail(d):
        r = _find(d, "static", "libc-test", "functional/argv")
        r["gem5_status"] = "fail"
        r["gem5_exit"] = 1
    run("gem5_only_fail without attribution",
        inject_unattributed_fail, "has no attribution entry")

    # 2. a qemu_only_fail must fail (the registry is empty by design)
    def inject_qemu_only(d):
        r = _find(d, "dynamic", "embench", "crc32-O0")
        r["qemu_status"] = "fail"
    run("qemu_only_fail must be located",
        inject_qemu_only, "is not located in spec/implementation/test asset")

    # 3. a drifted declared count must fail
    def inject_count(d):
        d["static"]["suites"]["llvm-ts"]["qemu"]["counts"]["pass"] -= 1
    run("declared count drift", inject_count, "declared")

    # 4. a blocked row without a capability label must fail
    def inject_blocked_no_cap(d):
        r = _find(d, "dynamic", "libc-test", "functional/ipc_msg")
        r["gem5_capability"] = None
    run("blocked without capability",
        inject_blocked_no_cap, "blocked without a capability label")

    # 5. blocked evidence that maps to no owner must fail
    def inject_blocked_reason(d):
        r = _find(d, "dynamic", "libc-test", "functional/ipc_msg")
        r["gem5_reason"] = "something unexplained happened"
    run("blocked evidence with no owner",
        inject_blocked_reason, "maps to no owner")

    # 6. diverging non-pass verdicts are a diff, not agreement
    def inject_verdict_diff(d):
        r = _find(d, "static", "libc-test", "functional/strptime")
        r["gem5_status"] = "fail"
    run("non-pass verdict diff", inject_verdict_diff, "verdict diff")

    # 7. a stale cross list (membership changed, count unchanged) must fail
    def inject_cross_list(d):
        rows = d["dynamic"]["suites"]["libc-test"]["cross"]["both_pass"]
        rows[0] = rows[1]
    run("cross list membership drift",
        inject_cross_list, "cross list both_pass")

    # 8. a gap bucket count drift must fail
    def inject_gap_bucket(d):
        for entry in d["dynamic"]["gap_inventory"]:
            if entry["capability"] == "SysV IPC":
                entry["blocked_cases"] -= 1
    run("gap bucket count drift", inject_gap_bucket, "gap bucket")

    return cases


def self_test(source_paths):
    docs = {mode: load_track(mode, source_paths[mode]) for mode in TRACKS}
    cases = _injections(docs)
    ok = True
    for name, hit, needle, errs in cases:
        if hit:
            print(f"INJECT {name}: PASS (detected)")
        else:
            ok = False
            print(f"INJECT {name}: FAIL (not detected; expected {needle!r}; "
                  f"errors={errs})")
    # sanity: the untouched baselines must pass
    _tracks, _attrs, _rows, errs = analyse_docs(docs)
    if errs:
        ok = False
        print(f"BASELINE: FAIL ({len(errs)} issue(s)): {errs[:2]}")
    else:
        print("BASELINE: PASS (clean baselines produce no error)")
    print("SELF-TEST: " + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="SE tset bidirectional parity report (INTEG-059t)")
    ap.add_argument("--static-json", default=DEFAULT_SOURCE["static"])
    ap.add_argument("--dynamic-json", default=DEFAULT_SOURCE["dynamic"])
    ap.add_argument("--json-out", default=None)
    ap.add_argument("--markdown-out", default=None)
    ap.add_argument("--matrix-section-out", default=None)
    ap.add_argument("--compose-out", default=None,
                    help="write the combined matrix-M11.md snapshot")
    ap.add_argument("--fs-matrix", default=None,
                    help="run_parity.py markdown for --compose-out")
    ap.add_argument("--carry-from", default=None,
                    help="previous snapshot whose picolibc rows are carried "
                         "into --compose-out (legacy B7-pending path)")
    ap.add_argument("--picolibc-json", default=None,
                    help="live run_parity.py JSON (--profiles tiny --scopes "
                         "picolibc); regenerates the picolibc block from it")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args(argv)

    source_paths = {
        "static": os.path.join(REPO_ROOT, args.static_json),
        "dynamic": os.path.join(REPO_ROOT, args.dynamic_json),
    }
    try:
        if args.self_test:
            return self_test(source_paths)
        (tracks, attributions, cross_rows, errors), _docs = analyse(
            source_paths)
        report = build_report(tracks, attributions, cross_rows, source_paths,
                              errors)
        md = render_markdown(report)
        section = render_matrix_section(report)
        if args.json_out:
            write_json(args.json_out, report)
            print(f"json: {args.json_out}")
        if args.markdown_out:
            os.makedirs(os.path.dirname(os.path.abspath(args.markdown_out)),
                        exist_ok=True)
            with open(args.markdown_out, "w", encoding="utf-8") as fh:
                fh.write(md)
            print(f"markdown: {args.markdown_out}")
        if args.matrix_section_out:
            os.makedirs(os.path.dirname(
                os.path.abspath(args.matrix_section_out)), exist_ok=True)
            with open(args.matrix_section_out, "w", encoding="utf-8") as fh:
                fh.write(section)
            print(f"matrix section: {args.matrix_section_out}")
        if args.compose_out:
            if not (args.fs_matrix
                    and (args.carry_from or args.picolibc_json)):
                raise ReportError("--compose-out needs --fs-matrix and either "
                                  "--carry-from or --picolibc-json")
            composed = compose_snapshot(args.fs_matrix, args.carry_from,
                                        section, args.picolibc_json)
            os.makedirs(os.path.dirname(os.path.abspath(args.compose_out)),
                        exist_ok=True)
            with open(args.compose_out, "w", encoding="utf-8") as fh:
                fh.write(composed)
            print(f"composed snapshot: {args.compose_out}")
        if not (args.json_out or args.markdown_out or
                args.matrix_section_out or args.compose_out):
            sys.stdout.write(md)
        if errors:
            for err in errors:
                print("FAIL: " + err)
            print(f"se_tset_matrix: FAIL ({len(errors)} issue(s))")
            return 1
        print("se_tset_matrix: PASS")
        return 0
    except ReportError as exc:
        print(f"se_tset_matrix: BLOCKED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
