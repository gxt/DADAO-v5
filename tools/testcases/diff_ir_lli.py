#!/usr/bin/env python3
"""diff_ir_lli.py -- value-level differential driver (TESTCASES-038t).

Runs the *same* LLVM IR module through two independent back-ends and compares
the **value-level** result, proving that the IR semantics are preserved between
them:

  host   (X86, upstream LLVM):  lli <ir>                      -> process exit code
  target (DADAO):               llc -march=dadao <ir>         -> <prog>.s
                                cat crt0.s <prog>.s           -> <prog>.s (single TU)
                                llvm-mc --triple=dadao -filetype=obj -> <prog>.o
                                llvm-objcopy -O binary --only-section=.text -> <prog>.bin
                                qemu-system-dadao -bios trampoline.bin \
                                    -kernel <prog>.bin -semihosting-config \
                                    enable=on,target=native -> process exit code

Value channel (frozen, see tests/llvm/ir-lli/README.md): the process exit code
== the low byte of the `i64` value returned by `@main`.  The startup stub
`tests/scripts/codegen_crt0.s` calls `@main` and reports the returned value
(`rd8`, the M6 ABI return register) through the semihosting `SYS_EXIT` service;
`lli` runs `@main` natively and the OS truncates its `i64` return to the low
byte.  Both sides therefore expose exactly the same value channel.

Judgement (fail-closed):
  * host exit == dadao exit for every `include` case   -> PASS
  * any mismatch / compile failure / timeout           -> FAIL
  * manifest set mismatch / missing IR / bad class     -> FAIL (structural)

Structural closure (lessons §8.35): the union of the manifest `include` and
`exclude` IR sets MUST equal every ``*.ll`` found on disk under `corpus_roots`,
and the two sets MUST be disjoint.  Any unclassified ``*.ll`` -> FAIL, so a
manifest entry cannot be deleted to silently shrink coverage.  Every compared
case is reported with its per-case hit (host/dadao values), so a "no error"
run is never mistaken for a live check (lessons §8.34).

Boundary (hard constraint): VALUE-LEVEL only.  Endianness / memory-layout class
modules are excluded (manifest `exclude`, classes `endianness` /
`memory-layout`).  This differential check does NOT serve as an
execution-semantics oracle -- the authoritative semantics come from the
independent oracles / execution vectors (see README).

Exit status:
  0  all structural + value checks pass
  1  at least one structural / value check FAILs
  2  setup error (missing tool / manifest / zero cases)

``--inject`` is a built-in counter-example self-test: after a green baseline it
flips one passing case's recorded host value in memory and requires the
comparison to FAIL (proving the comparison is live).  The verdict in inject
mode is the self-test itself.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.stderr.write("ERROR: PyYAML is required (used elsewhere in the repo)\n")
    sys.exit(2)

REPO_ROOT = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
)

# Install root (ADR-0016 D7/D9): resolve tools from the single source of truth
# instead of hardcoding .work/build.
sys.path.insert(0, os.path.join(REPO_ROOT, "tools", "infra"))
import paths as _dadao_paths  # noqa: E402

# Allowed exclusion classes.  `endianness` / `memory-layout` are the two
# classes the task boundary mandates; the others record IR that is not a
# self-contained single-TU value-level module for this pipeline.
CLASS_VOCAB = {
    "endianness": "observable value depends on memory byte order (host LE vs DADAO BE)",
    "memory-layout": "observable value depends on struct/aggregate memory layout",
    "needs-linker": "single module but needs the linker (e.g. a function-pointer reloc) -- not the flat-binary pipeline",
    "multi-tu": "references symbols defined in another translation unit (needs the linker)",
    "host-unsupported": "host `lli` cannot execute the module (crash / missing feature)",
    "no-value-entry": "no `i64 @main()` value channel (structural / FileCheck coverage module)",
}

HOST_TOOLS_BIN = str(_dadao_paths.host_tools_bin())
TARGET_TOOLS_BIN = str(_dadao_paths.host_toolchain_bin())

DEFAULT_LLI = os.path.join(HOST_TOOLS_BIN, "lli")
DEFAULT_LLC = os.path.join(TARGET_TOOLS_BIN, "llc")
DEFAULT_LLVM_MC = os.path.join(TARGET_TOOLS_BIN, "llvm-mc")
DEFAULT_LLVM_OBJCOPY = os.path.join(TARGET_TOOLS_BIN, "llvm-objcopy")
DEFAULT_QEMU = os.path.join(TARGET_TOOLS_BIN, "qemu-system-dadao")
DEFAULT_CRT0 = "tests/scripts/codegen_crt0.s"
DEFAULT_TRAMPOLINE = "tests/scripts/trampoline.bin"
DEFAULT_MANIFEST = "tests/llvm/ir-lli/manifest.yaml"
DEFAULT_WORK_DIR = str(_dadao_paths.test_artifacts_dir() / "ir-lli-diff")
DEFAULT_TIMEOUT = 30

# Marker substrings that mean `lli` failed to execute the module rather than
# returning a value (so an error exit code is never read as a program value).
_LLI_ERROR_MARKERS = ("error", "LLVM ERROR", "Failed to materialize",
                      "JIT session error")


def _norm(path: str) -> str:
    """Repo-root-relative forward-slash path (manifest spelling)."""
    return path.replace(os.sep, "/").strip("/")


def _abspath(path: str, corpus_root: str) -> str:
    if os.path.isabs(path):
        return path
    return os.path.join(corpus_root, path)


def _run(cmd, timeout=None):
    """Run cmd; return (rc, stdout, stderr, timed_out).

    rc is None on timeout.  The command's own exit code is captured directly
    (no shell pipe, so nothing can swallow it).
    """
    try:
        proc = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout
        )
        return (
            proc.returncode,
            proc.stdout.decode("utf-8", errors="replace"),
            proc.stderr.decode("utf-8", errors="replace"),
            False,
        )
    except subprocess.TimeoutExpired:
        return None, "", "", True


def _echo_cmd(cmd, verbose):
    if verbose:
        sys.stdout.write("      $ " + " ".join(cmd) + "\n")


def _require_exec(path: str, what: str) -> None:
    if not os.path.isfile(path) or not os.access(path, os.X_OK):
        sys.stderr.write(f"ERROR: {what} not found / not executable: {path}\n")
        sys.stderr.write("       run 'make install-host' first\n")
        sys.exit(2)


def _find_corpus(corpus_root: str, roots) -> set:
    """Every ``*.ll`` (repo-root-relative, forward slashes) under each root."""
    found = set()
    for root in roots:
        base = _abspath(root, corpus_root)
        if not os.path.isdir(base):
            continue
        for dirpath, _dirs, files in os.walk(base):
            for fn in files:
                if fn.endswith(".ll"):
                    rel = os.path.relpath(os.path.join(dirpath, fn), corpus_root)
                    found.add(_norm(rel))
    return found


def load_manifest(path: str):
    with open(path, "r", encoding="utf-8") as f:
        doc = yaml.safe_load(f)
    if not isinstance(doc, dict):
        sys.stderr.write(f"ERROR: {path}: not a mapping\n")
        sys.exit(2)
    roots = doc.get("corpus_roots")
    inc = doc.get("include")
    exc = doc.get("exclude")
    if not isinstance(roots, list) or not roots:
        sys.stderr.write(f"ERROR: {path}: missing 'corpus_roots'\n")
        sys.exit(2)
    if not isinstance(inc, list) or not inc:
        sys.stderr.write(f"ERROR: {path}: missing 'include'\n")
        sys.exit(2)
    if not isinstance(exc, list):
        sys.stderr.write(f"ERROR: {path}: missing 'exclude'\n")
        sys.exit(2)
    return roots, inc, exc


def structural_check(corpus_root, roots, inc, exc):
    """Return the list of structural errors.  Enforces the closed partition."""
    errors = []
    include_irs = []
    for e in inc:
        if not isinstance(e, dict) or "ir" not in e:
            errors.append(f"include entry without 'ir': {e!r}")
            continue
        include_irs.append(_norm(e["ir"]))
    exclude_irs = []
    for e in exc:
        if not isinstance(e, dict) or "ir" not in e:
            errors.append(f"exclude entry without 'ir': {e!r}")
            continue
        cls = e.get("class")
        reason = (e.get("reason") or "").strip()
        if cls not in CLASS_VOCAB:
            errors.append(f"exclude {e['ir']}: bad class {cls!r} (not in {sorted(CLASS_VOCAB)})")
        if not reason:
            errors.append(f"exclude {e['ir']}: empty reason")
        exclude_irs.append(_norm(e["ir"]))

    inc_set = set(include_irs)
    exc_set = set(exclude_irs)
    on_disk = _find_corpus(corpus_root, roots)

    overlap = inc_set & exc_set
    if overlap:
        errors.append(f"include/exclude overlap: {sorted(overlap)}")
    missing = (inc_set | exc_set) - on_disk
    if missing:
        errors.append(f"manifest lists IR not on disk: {sorted(missing)}")
    unclassified = on_disk - (inc_set | exc_set)
    if unclassified:
        errors.append(
            "unclassified *.ll under corpus_roots (add to include or exclude): "
            f"{sorted(unclassified)}"
        )

    sys.stdout.write(
        f"structural: on-disk={len(on_disk)} include={len(inc_set)} "
        f"exclude={len(exc_set)} unclassified={len(unclassified)} "
        f"overlap={len(overlap)} missing={len(missing)}\n"
    )
    return errors


def host_value(lli, ir_abs, timeout, verbose=False):
    """(value, reason).  value is None on failure."""
    cmd = [lli, ir_abs]
    _echo_cmd(cmd, verbose)
    rc, _out, err, timed = _run(cmd, timeout=timeout)
    if timed:
        return None, f"host lli timeout after {timeout}s"
    if rc is None:
        return None, "host lli gave no exit code"
    if rc < 0:
        return None, f"host lli killed by signal {-rc}"
    low = err.strip().lower()
    if any(m.lower() in low for m in _LLI_ERROR_MARKERS):
        return None, f"host lli error: {err.strip()[:200]}"
    return rc & 0xFF, "ok"


def target_value(tools, ir_abs, work_dir, stem, timeout, verbose=False):
    """(value, reason, steps).  steps = (llc_rc, mc_rc, objcopy_rc)."""
    prog_s = os.path.join(work_dir, stem + ".prog.s")
    comb_s = os.path.join(work_dir, stem + ".s")
    obj = os.path.join(work_dir, stem + ".o")
    binp = os.path.join(work_dir, stem + ".bin")

    # 1. llc -march=dadao <ir> -> <prog>.s   (the DADAO compile layer)
    cmd = [tools["llc"], "-march=dadao", ir_abs, "-o", prog_s]
    _echo_cmd(cmd, verbose)
    r_llc, _o, e_llc, t_llc = _run(cmd)
    if t_llc:
        return None, "llc timeout", (None, None, None)
    if r_llc != 0:
        return None, f"llc failed (rc={r_llc}): {e_llc.strip()[:200]}", (r_llc, None, None)

    # 2. cat crt0.s <prog>.s -> combined single TU .s
    try:
        with open(tools["crt0"], "rb") as fh:
            crt0_bytes = fh.read()
        with open(prog_s, "rb") as fh:
            prog_bytes = fh.read()
        with open(comb_s, "wb") as fh:
            fh.write(crt0_bytes)
            if not crt0_bytes.endswith(b"\n"):
                fh.write(b"\n")
            fh.write(prog_bytes)
    except OSError as exc:
        return None, f"concat failed: {exc}", (r_llc, None, None)

    # 3. llvm-mc --triple=dadao -filetype=obj -> .o
    cmd = [tools["llvm_mc"], "--triple=dadao", "-filetype=obj", comb_s, "-o", obj]
    _echo_cmd(cmd, verbose)
    r_mc, _o, e_mc, t_mc = _run(cmd)
    if t_mc:
        return None, "llvm-mc timeout", (r_llc, None, None)
    if r_mc != 0:
        return None, f"llvm-mc failed (rc={r_mc}): {e_mc.strip()[:200]}", (r_llc, r_mc, None)

    # 4. llvm-objcopy -O binary --only-section=.text -> .bin
    cmd = [tools["llvm_objcopy"], "-O", "binary", "--only-section=.text", obj, binp]
    _echo_cmd(cmd, verbose)
    r_cp, _o, e_cp, t_cp = _run(cmd)
    if t_cp:
        return None, "llvm-objcopy timeout", (r_llc, r_mc, None)
    if r_cp != 0:
        return None, f"llvm-objcopy failed (rc={r_cp}): {e_cp.strip()[:200]}", (r_llc, r_mc, r_cp)

    # 5. run under QEMU -> guest exit code
    cmd = [
        tools["qemu"], "-M", "dadao-m1",
        "-bios", tools["trampoline"], "-kernel", binp,
        "-semihosting-config", "enable=on,target=native",
        "-display", "none", "-nographic",
    ]
    _echo_cmd(cmd, verbose)
    r_q, _o, e_q, t_q = _run(cmd, timeout=timeout)
    if t_q:
        return None, f"qemu timeout after {timeout}s", (r_llc, r_mc, r_cp)
    if r_q is None:
        return None, "qemu gave no exit code", (r_llc, r_mc, r_cp)
    if r_q < 0:
        return None, f"qemu killed by signal {-r_q}", (r_llc, r_mc, r_cp)
    _ = e_q
    return r_q & 0xFF, "ok", (r_llc, r_mc, r_cp)


def compare_case(entry, tools, corpus_root, work_dir, timeout, verbose):
    """Return dict with name/host/dadao/match/reason/steps."""
    name = entry.get("name") or os.path.basename(entry["ir"])
    ir_rel = _norm(entry["ir"])
    ir_abs = _abspath(ir_rel, corpus_root)
    rec = {"name": name, "ir": ir_rel, "host": None, "dadao": None,
           "match": False, "reason": "", "steps": (None, None, None)}

    if not os.path.isfile(ir_abs):
        rec["reason"] = f"IR not found: {ir_abs}"
        return rec

    host, hreason = host_value(tools["lli"], ir_abs, timeout, verbose)
    if host is None:
        rec["reason"] = hreason
        return rec

    stem = os.path.splitext(os.path.basename(ir_rel))[0]
    dadao, treason, steps = target_value(
        tools, ir_abs, work_dir, stem, timeout, verbose)
    rec["steps"] = steps
    if dadao is None:
        rec["reason"] = treason
        rec["host"] = host
        return rec

    rec["host"] = host
    rec["dadao"] = dadao
    if host == dadao:
        rec["match"] = True
        rec["reason"] = "match"
    else:
        rec["reason"] = f"value mismatch (host={host} dadao={dadao})"
    return rec


def main():
    ap = argparse.ArgumentParser(
        description="value-level differential driver: host lli vs DADAO target (TESTCASES-038t)")
    ap.add_argument("--manifest", default=DEFAULT_MANIFEST)
    ap.add_argument("--corpus-root", default=None,
                    help="root that manifest paths are relative to (default: repo root)")
    ap.add_argument("--work-dir", default=DEFAULT_WORK_DIR)
    ap.add_argument("--lli", default=os.environ.get("LLI", DEFAULT_LLI))
    ap.add_argument("--llc", default=os.environ.get("LLC", DEFAULT_LLC))
    ap.add_argument("--llvm-mc", dest="llvm_mc", default=os.environ.get("LLVM_MC", DEFAULT_LLVM_MC))
    ap.add_argument("--llvm-objcopy", dest="llvm_objcopy",
                    default=os.environ.get("LLVM_OBJCOPY", DEFAULT_LLVM_OBJCOPY))
    ap.add_argument("--qemu", default=os.environ.get("QEMU_SYSTEM_DADAO", DEFAULT_QEMU))
    ap.add_argument("--crt0", default=DEFAULT_CRT0)
    ap.add_argument("--trampoline", default=DEFAULT_TRAMPOLINE)
    ap.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    ap.add_argument("--verbose", "-v", action="store_true")
    ap.add_argument("--inject", action="store_true",
                    help="counter-example self-test: flip one passing case's host "
                         "value and require the comparison to FAIL")
    args = ap.parse_args()

    corpus_root = _abspath(args.corpus_root, REPO_ROOT) if args.corpus_root else REPO_ROOT
    manifest_path = _abspath(args.manifest, corpus_root)
    work_dir = _abspath(args.work_dir, corpus_root)

    tools = {
        "lli": _abspath(args.lli, corpus_root),
        "llc": _abspath(args.llc, corpus_root),
        "llvm_mc": _abspath(args.llvm_mc, corpus_root),
        "llvm_objcopy": _abspath(args.llvm_objcopy, corpus_root),
        "qemu": _abspath(args.qemu, corpus_root),
        "crt0": _abspath(args.crt0, corpus_root),
        "trampoline": _abspath(args.trampoline, corpus_root),
    }

    _require_exec(tools["lli"], "lli")
    _require_exec(tools["llc"], "llc")
    _require_exec(tools["llvm_mc"], "llvm-mc")
    _require_exec(tools["llvm_objcopy"], "llvm-objcopy")
    _require_exec(tools["qemu"], "qemu-system-dadao")
    for key in ("crt0", "trampoline"):
        if not os.path.isfile(tools[key]):
            sys.stderr.write(f"ERROR: {key} not found: {tools[key]}\n")
            sys.exit(2)
    if not os.path.isfile(manifest_path):
        sys.stderr.write(f"ERROR: manifest not found: {manifest_path}\n")
        sys.exit(2)

    roots, inc, exc = load_manifest(manifest_path)
    os.makedirs(work_dir, exist_ok=True)

    sys.stdout.write(f"diff_ir_lli: manifest={_norm(os.path.relpath(manifest_path, corpus_root))} "
                     f"work_dir={work_dir}\n")

    # ---- structural closure (lessons §8.35) --------------------------------
    serrs = structural_check(corpus_root, roots, inc, exc)
    for err in serrs:
        sys.stdout.write(f"[FAIL] structural: {err}\n")
    if serrs:
        sys.stdout.write("diff_ir_lli: FAIL (structural)\n")
        return 1

    # ---- per-case value comparison ----------------------------------------
    sys.stdout.write(f"include cases: {len(inc)} (现场统计; 非写死)\n")
    records = []
    for entry in inc:
        rec = compare_case(entry, tools, corpus_root, work_dir, args.timeout, args.verbose)
        steps = rec["steps"]
        step_txt = ",".join("?" if s is None else str(s) for s in steps)
        if rec["match"]:
            sys.stdout.write(
                f"  [ok]   {rec['name']}  host={rec['host']} dadao={rec['dadao']} "
                f"[llc=mc=objcopy={step_txt}]\n")
        else:
            sys.stdout.write(
                f"  [FAIL] {rec['name']}  host={rec['host']} dadao={rec['dadao']} "
                f"({rec['reason']})\n")
        records.append(rec)

    # §8.34: every case must be a live hit (both values captured).
    hits = sum(1 for r in records if r["host"] is not None and r["dadao"] is not None)
    matched = sum(1 for r in records if r["match"])
    sys.stdout.write(
        f"hits: {hits}/{len(records)} compared (逐项命中; 现场统计), "
        f"matched: {matched}/{len(records)}\n")
    if hits != len(records):
        sys.stdout.write("[FAIL] some cases produced no live hit (host/dadao value missing)\n")

    # ---- built-in counter-example self-test -------------------------------
    if args.inject:
        passing = [r for r in records if r["match"]]
        if not passing:
            sys.stderr.write("INJECT: FAIL -- no baseline-PASSing case to inject into\n")
            return 2
        target = passing[0]
        original = target["host"]
        injected = (original + 1) & 0xFF
        sys.stdout.write(f"\nINJECT: case={target['name']} host {original} -> {injected}\n")
        if injected == target["dadao"]:
            sys.stderr.write("INJECT: FAIL -- injected value coincidentally equals dadao\n")
            return 1
        match = (injected == target["dadao"])
        sys.stdout.write(
            f"  injected comparison: host={injected} dadao={target['dadao']} "
            f"match={'PASS' if match else 'FAIL'}\n")
        if match:
            sys.stderr.write(
                "INJECT: FAIL -- comparison did NOT detect a wrong value "
                "(comparison is not live)\n")
            return 1
        sys.stdout.write("INJECT: PASS -- comparison correctly reported FAIL on a "
                         "wrong value\n")
        return 0

    if hits != len(records) or matched != len(records):
        sys.stdout.write("diff_ir_lli: FAIL\n")
        return 1
    sys.stdout.write("diff_ir_lli: PASS\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
