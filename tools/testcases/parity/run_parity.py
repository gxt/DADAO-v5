#!/usr/bin/env python3
"""run_parity.py -- QEMU system <-> gem5 FS same-mode parity matrix.

Scope (ADR-0048 D1/D2/D5; task book §0/§1/§4):

  * pairing is **QEMU system profile X <-> gem5 FS profile X** (tiny/node);
  * a case is the same frozen ``case_id`` on both engines; the comparison is
    ``status`` (PASS/FAIL/...), the host exit code and the architecture-visible
    result.  Timing, performance and host log formatting are never compared;
  * hard gate: ``QEMU PASS => gem5 PASS`` with the same exit/visible result
    (``GEM5_ONLY_FAIL == 0``); ``QEMU_ONLY_FAIL`` is listed for a separate QEMU
    debug task but does not make this gate red;
  * case-level ``BLOCKED`` (a gem5 capability gap such as QEMU ``-icount``) is
    reported explicitly with a reason and never counted as PASS.

The driver reuses the existing engines instead of re-implementing them:

  inst      tools/qemu/semantics_gate.py --json-out   (QEMU and, via the shim,
            gem5 FS)
  arch      tools/testcases/arch/run_m5_e2e.py --json-out  (10 smoke) plus the
            13 ``ARCH_CFX_PROBES`` + ``min_rom_probe_046t`` run per check
  embench   tools/testcases/tset/embench/run_embench_e2e.py --json-out
  picolibc  tools/testcases/picolibc_tests.py --stage fast (Tiny only; the
            produced ELF is re-run on gem5 with the same argv)

Usage:

  python3 tools/testcases/parity/run_parity.py --profiles tiny,node \\
      --scopes inst,arch,embench,picolibc \\
      --qemu .dadao/cross-toolchain/bin/qemu-system-dadao \\
      --gem5 .work/source/gem5/build/DADAO/gem5.opt \\
      --gem5-config .work/source/gem5/configs/dadao/fs.py \\
      --work-dir /tmp/opencode/qemu-gem5-parity/run \\
      --json /tmp/opencode/qemu-gem5-parity/matrix.json \\
      --markdown /tmp/opencode/qemu-gem5-parity/matrix.md

Exit codes: 0 green (no red row); 1 parity red (subset violation / gem5-only
fail / unattributed DIFF / coverage gap); 2 setup error (missing engine,
BootROM, tool, zero cases, unknown option) or empty matrix.
"""

from __future__ import annotations

import argparse
import copy
import datetime as _dt
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(_HERE)))
for _sub in (("tools", "testcases", "lib"), ("tools", "testcases"),
             ("tools", "qemu"), ("tools", "testcases", "arch"),
             ("tools", "testcases", "tset", "embench"), ("tools", "infra")):
    _p = os.path.join(_REPO_ROOT, *_sub)
    if _p not in sys.path:
        sys.path.insert(0, _p)

import machine_profile  # noqa: E402
import paths as _paths  # noqa: E402
import run_qemu_test as harness  # noqa: E402

SHIM = os.path.join(_HERE, "qemu_gem5_shim.py")
SEMANTICS_GATE = os.path.join(_REPO_ROOT, "tools", "qemu", "semantics_gate.py")
RUN_M5 = os.path.join(_REPO_ROOT, "tools", "testcases", "arch", "run_m5_e2e.py")
RUN_EMBENCH = os.path.join(_REPO_ROOT, "tools", "testcases", "tset", "embench",
                           "run_embench_e2e.py")
PICOLIBC_TESTS = os.path.join(_REPO_ROOT, "tools", "testcases",
                              "picolibc_tests.py")
ARCH_DIR = os.path.join(_REPO_ROOT, "tools", "testcases", "arch")

SCOPES = ("inst", "arch", "embench", "picolibc")
PROFILES = ("tiny", "node")
STATUSES = ("PASS", "FAIL", "DEFERRED", "SKIP_PROFILE", "BLOCKED", "ERROR",
            "TIMEOUT", "N/A")
VERDICTS = ("AGREE_PASS", "AGREE_FAIL", "GEM5_ONLY_FAIL", "QEMU_ONLY_FAIL",
            "DIFF", "BLOCKED_SIDE", "N/A")
# Machine-fault exit codes (spec/Machine-v5 §7.1): other cfx 0x80-0xBF and
# monitor 0xC0-0xFF.  Guest PASS is 0x00-0x3F and guest FAIL 0x40-0x7F, so a
# process status is a machine fault iff it is >= 0x80.
def _is_machine_fault(rc):
    return 0x80 <= rc <= 0xFF

# Known, spec-attributed differences.  Only picolibc math_test is allowed (B7
# numeric difference carried from GEM5-015t); it must stay BLOCKED, never PASS.
PICOLIBC_KNOWN_BLOCKED = {
    "math_test": "B7 numeric difference (GEM5-015t leftover 1): QEMU 0 errors / "
                 "gem5 non-zero; not a FS path regression",
}

# gem5-side defects found by parity runs (QEMU passes, gem5 does not).  The fix
# belongs to components/gem5; register BLOCKED with a root cause and a separate
# gem5 task, never count as PASS.  `raw_status` keeps the raw gem5 verdict for
# audit.  The list is empty now that GEM5-018t fixed the semihosting defects;
# the mechanism is kept for future gem5-side defects (a registry entry whose
# gem5 side later PASSes is reported stale and must be removed).
KNOWN_GEM5_BLOCKED = {}


class SetupError(Exception):
    """Missing engine / tool / zero cases (exit 2)."""


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------

def _now():
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _md5(path):
    h = hashlib.md5()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _abspath(path):
    return path if os.path.isabs(path) else os.path.join(_REPO_ROOT, path)


def _require_file(path, what):
    if not os.path.isfile(path):
        raise SetupError(f"{what} not found: {path}")


def _require_exec(path, what):
    if not os.path.isfile(path) or not os.access(path, os.X_OK):
        raise SetupError(f"{what} not found / not executable: {path}")


def _run_logged(cmd, log_path, env=None, timeout=None):
    """Run ``cmd`` with combined output in ``log_path``; return rc (124 timeout)."""
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, "w", encoding="utf-8") as log:
        log.write("$ " + " ".join(cmd) + "\n")
        log.flush()
        try:
            proc = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT,
                                  env=env, timeout=timeout)
            rc = proc.returncode
        except subprocess.TimeoutExpired:
            log.write(f"\n[PARITY] TIMEOUT after {timeout}s\n")
            rc = 124
        except OSError as exc:
            log.write(f"\n[PARITY] OSError: {exc}\n")
            rc = 127
    with open(log_path, "a", encoding="utf-8") as log:
        log.write(f"\n[PARITY_EXIT] rc={rc}\n")
    return rc


def _cache_by_case(path, scope):
    with open(path, "r", encoding="utf-8") as fh:
        doc = json.load(fh)
    rows = doc.get("cases")
    if not isinstance(rows, list):
        raise SetupError(f"{path}: missing 'cases' list")
    out = {}
    for row in rows:
        cid = row.get("case_id")
        if cid in out:
            raise SetupError(f"{path}: duplicate case_id {cid}")
        out[cid] = row
    return out


def _engine_env(args, profile, gem5=False):
    env = dict(os.environ)
    env["DADAO_TEST_PROFILE"] = profile
    env["PARITY_GEM5"] = args.gem5
    env["PARITY_GEM5_CONFIG"] = args.gem5_config
    env["PARITY_GEM5_PROFILE"] = profile
    if profile == "node":
        # Node needs the 4 MiB BootROM; Tiny ELF runs carry their own crt and
        # must NOT get a --bootrom (fs.py rejects bootrom + ELF).
        env["PARITY_GEM5_BOOTROM"] = args.bootrom_node
    env["PARITY_WORK_ROOT"] = os.path.join(args.work_dir, "shim")
    if not gem5:
        env.pop("PARITY_GEM5", None)
    return env


# ---------------------------------------------------------------------------
# identity
# ---------------------------------------------------------------------------

def _tool(name):
    return str(_paths.host_toolchain_bin() / name)


def engine_identity(args):
    ident = {"generated_at": _now(), "engines": {}, "toolchain": {},
             "bootrom": {}, "paths": {}}
    _require_exec(args.qemu, "qemu-system-dadao")
    _require_file(args.gem5, "gem5.opt")
    _require_file(args.gem5_config, "gem5 fs.py")
    if "node" in args.profiles:
        _require_file(args.bootrom_node, "Node BootROM")
        if "inst" in args.scopes:
            _require_file(args.bootrom_node_inst, "Node inst BootROM")
    qver = subprocess.run([args.qemu, "--version"], capture_output=True,
                          text=True)
    ident["engines"]["qemu"] = {
        "path": os.path.abspath(args.qemu),
        "md5": _md5(args.qemu),
        "version": (qver.stdout or qver.stderr).strip().splitlines()[0]
                   if (qver.stdout or qver.stderr).strip() else "",
    }
    source_root = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(args.gem5_config))))
    commit = subprocess.run(["git", "-C", source_root, "rev-parse", "HEAD"],
                            capture_output=True, text=True)
    ident["engines"]["gem5"] = {
        "path": os.path.abspath(args.gem5),
        "md5": _md5(args.gem5),
        "config": os.path.abspath(args.gem5_config),
        "config_md5": _md5(args.gem5_config),
        "source": source_root,
        "source_commit": commit.stdout.strip() if commit.returncode == 0 else "",
    }
    for key, path in (("tiny", args.bootrom_tiny), ("node", args.bootrom_node),
                      ("node_inst", args.bootrom_node_inst)):
        if os.path.isfile(path):
            ident["bootrom"][key] = {"path": os.path.abspath(path),
                                     "md5": _md5(path),
                                     "size": os.path.getsize(path)}
        else:
            ident["bootrom"][key] = {"path": os.path.abspath(path),
                                     "md5": None, "size": None}
    for name in ("clang", "llc", "llvm-mc", "llvm-objcopy", "ld.lld"):
        path = _tool(name)
        ident["toolchain"][name] = {
            "path": path,
            "md5": _md5(path) if os.path.isfile(path) else None,
        }
    ident["paths"]["work_dir"] = os.path.abspath(args.work_dir)
    ident["paths"]["json"] = os.path.abspath(args.json) if args.json else None
    return ident


# ---------------------------------------------------------------------------
# live case enumeration (coverage truth, never hardcoded)
# ---------------------------------------------------------------------------

def _inst_carriers():
    import semantics_gate
    vectors = os.path.join(_REPO_ROOT, "tests", "inst")
    carriers = []
    for d in semantics_gate.CARRIER_DIRS:
        full = os.path.join(vectors, d)
        if not os.path.isdir(full):
            raise SetupError(f"inst carrier dir missing: {full}")
        names = [n for n in sorted(os.listdir(full)) if n.endswith(".yaml")]
        if not names:
            raise SetupError(f"inst carrier dir empty: {full}")
        carriers.extend(os.path.join(d, n) for n in names)
    return carriers


def enumerate_inst(profile):
    """Return ordered case templates: case_id/status (pre-run)."""
    vectors = os.path.join(_REPO_ROOT, "tests", "inst")
    rows = []
    seen = set()
    for rel in _inst_carriers():
        cases = harness._load_cases(os.path.join(vectors, rel))
        for idx, case in enumerate(cases):
            cid = "inst/%s#%d:%s" % (rel, idx + 1, case.get("id"))
            if cid in seen:
                raise SetupError(f"duplicate inst case_id {cid}")
            seen.add(cid)
            if not harness.case_applies(case, profile):
                status = "SKIP_PROFILE"
            elif case.get("status", "active") == "deferred":
                status = "DEFERRED"
            else:
                status = "RUN"
            rows.append({"case_id": cid, "profile": profile, "scope": "inst",
                         "expected": status,
                         "vector": rel, "index": idx,
                         "id": case.get("id")})
    if not rows:
        raise SetupError("inst: zero live cases")
    return rows


def _parse_probe_list(path, profile="node"):
    env = dict(os.environ)
    env["DADAO_TEST_PROFILE"] = profile
    proc = subprocess.run([sys.executable, path, "--list"], capture_output=True,
                          text=True, env=env)
    if proc.returncode != 0:
        raise SetupError(f"probe --list failed rc={proc.returncode}: {path}")
    checks = []
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line or line.startswith("distinct service ids") \
                or line.startswith("required service ids"):
            continue
        name = line.split()[0]
        checks.append({"name": name, "icount": "[-icount]" in line,
                       "desc": line[len(name):].strip(" -")})
    if not checks:
        raise SetupError(f"probe --list returned zero checks: {path}")
    return checks


def _arch_probe_ids():
    makefile = os.path.join(_REPO_ROOT, "Makefile")
    with open(makefile, "r", encoding="utf-8") as fh:
        text = fh.read()
    m = re.search(r"^ARCH_CFX_PROBES\s*=\s*(.+)$", text, re.MULTILINE)
    if not m:
        raise SetupError("Makefile: ARCH_CFX_PROBES not found")
    ids = m.group(1).split()
    if not ids:
        raise SetupError("Makefile: ARCH_CFX_PROBES is empty")
    out = []
    for pid in ids:
        script = os.path.join(ARCH_DIR, "min_rom_probe_%s.py" % pid)
        if not os.path.isfile(script):
            raise SetupError(f"probe script missing: {script}")
        out.append({"id": pid, "script": script})
    script046 = os.path.join(ARCH_DIR, "min_rom_probe_046t.py")
    if not os.path.isfile(script046):
        raise SetupError(f"probe script missing: {script046}")
    out.append({"id": "min_rom_probe_046t", "script": script046})
    return out


def enumerate_arch(profile):
    if not machine_profile.load("node").get("arch", False):
        raise SetupError("machine-profiles.yaml: node.arch is false")
    expected = os.path.join(_REPO_ROOT, "tests", "arch", "umon", "expected.yaml")
    with open(expected, "r", encoding="utf-8") as fh:
        import yaml
        doc = yaml.safe_load(fh)
    programs = [p["name"] for p in doc.get("programs", [])]
    if not programs:
        raise SetupError(f"{expected}: zero arch smoke programs")
    rows = [{"case_id": "arch/umon/" + name, "profile": profile,
             "scope": "arch", "kind": "smoke", "name": name} for name in programs]
    for probe in _arch_probe_ids():
        for check in _parse_probe_list(probe["script"]):
            rows.append({"case_id": "arch/probe/%s/%s" % (probe["id"],
                                                          check["name"]),
                         "profile": profile, "scope": "arch", "kind": "probe",
                         "probe": probe["id"], "script": probe["script"],
                         "check": check["name"], "icount": check["icount"]})
    return rows


def _embench_src(args):
    return _abspath(args.embench_src)


def discover_benchmarks(args):
    src = os.path.join(_embench_src(args), "src")
    if not os.path.isdir(src):
        raise SetupError(f"embench source root missing: {src}")
    import glob
    found = [d for d in sorted(os.listdir(src))
             if os.path.isdir(os.path.join(src, d))
             and glob.glob(os.path.join(src, d, "*.c"))]
    if not found:
        raise SetupError(f"embench: zero benchmarks under {src}")
    return found


def enumerate_embench(args, profile):
    rows = []
    for bench in discover_benchmarks(args):
        for opt in ("0", "2"):
            rows.append({"case_id": "embench/%s-O%s" % (bench, opt),
                         "profile": profile, "scope": "embench",
                         "bench": bench, "opt": "O" + opt})
    return rows


def _picolibc_inventory():
    import picolibc_tests
    inv, _targets = picolibc_tests.load_inventory()
    reps = set(picolibc_tests.representative_names(inv))
    names = [e["name"] for e in inv if e["name"] in reps]
    if not names:
        raise SetupError("picolibc: zero representative cases")
    return names, picolibc_tests


def enumerate_picolibc():
    names, _mod = _picolibc_inventory()
    return [{"case_id": "picolibc/" + name, "profile": "tiny",
             "scope": "picolibc", "name": name} for name in names]


def enumerate_all(args):
    live = {}
    for profile in args.profiles:
        for scope in args.scopes:
            key = (profile, scope)
            if scope == "inst":
                live[key] = enumerate_inst(profile)
            elif scope == "arch":
                # Tiny arch is N/A by profile (tiny.arch=false); the same IDs
                # are enumerated so the matrix has no silent gap.
                if profile == "tiny" and not machine_profile.load("tiny").get(
                        "arch", False):
                    live[key] = enumerate_arch("node")
                    for row in live[key]:
                        row["profile"] = "tiny"
                        row["expected_status"] = "N/A"
                else:
                    live[key] = enumerate_arch(profile)
            elif scope == "embench":
                live[key] = enumerate_embench(args, profile)
            elif scope == "picolibc":
                if profile != "tiny":
                    live[key] = []  # Node picolibc is not run (profile table)
                else:
                    live[key] = enumerate_picolibc()
    return live


# ---------------------------------------------------------------------------
# engine runs
# ---------------------------------------------------------------------------

def _qemu_cmd(args):
    return os.path.abspath(args.qemu)


def _gem5_cmd(args):
    return SHIM


def _semantics_run(args, profile, engine, out_json, log_path):
    env = _engine_env(args, profile, gem5=(engine == "gem5"))
    trampoline = (args.bootrom_node_inst if profile == "node"
                  else args.bootrom_tiny)
    cmd = [sys.executable, SEMANTICS_GATE, "--profile", profile,
           "--gate-dir", os.path.join(args.work_dir,
                                      "gate-%s-%s" % (profile, engine)),
           "--qemu", _gem5_cmd(args) if engine == "gem5" else _qemu_cmd(args),
           "--trampoline", trampoline,
           "--jobs", str(args.jobs), "--json-out", out_json]
    rc = _run_logged(cmd, log_path, env=env, timeout=args.scope_timeout)
    if not os.path.isfile(out_json):
        raise SetupError(f"inst {profile}/{engine}: no JSON (rc={rc}); "
                         f"log {log_path}")
    return rc, _cache_by_case(out_json, "inst")


def _arch_smoke_run(args, profile, engine, out_json, log_path):
    env = _engine_env(args, profile, gem5=(engine == "gem5"))
    cmd = [sys.executable, RUN_M5, "--profile", profile,
           "--qemu", _gem5_cmd(args) if engine == "gem5" else _qemu_cmd(args),
           "--bootrom", args.bootrom_node,
           "--work-dir", os.path.join(args.work_dir,
                                      "arch-%s-%s" % (profile, engine)),
           "--timeout", str(min(args.timeout, 120)),
           "--json-out", out_json]
    rc = _run_logged(cmd, log_path, env=env, timeout=args.scope_timeout)
    if not os.path.isfile(out_json):
        raise SetupError(f"arch {profile}/{engine}: no JSON (rc={rc}); "
                         f"log {log_path}")
    return rc, _cache_by_case(out_json, "arch")


def _probe_run(args, profile, engine, probe, check, icount, log_path):
    if engine == "gem5" and icount:
        return {"status": "N/A", "exit": None,
                "arch_visible": {"check": check, "reason":
                                 "QEMU -icount has no gem5 atomic equivalent "
                                 "(task book §2); case not compared"},
                "note": "icount timing control unsupported on gem5 FS"}
    env = _engine_env(args, profile, gem5=(engine == "gem5"))
    env["DADAO_TEST_PROFILE"] = "node"
    cmd = [sys.executable, probe["script"], "--only", check,
           "--qemu", _gem5_cmd(args) if engine == "gem5" else _qemu_cmd(args)]
    rc = _run_logged(cmd, log_path, env=env, timeout=args.timeout + 30)
    passed = rc == 0
    status = "PASS" if passed else ("ERROR" if rc in (2, 124, 125, 127)
                                    else "FAIL")
    return {"status": status, "exit": rc,
            "arch_visible": {"check": check, "probe_rc": rc,
                             "probe": probe["probe"]},
            "note": f"probe {probe['probe']} --only {check} rc={rc}"}


def _embench_run(args, profile, engine, out_json, log_path, wrapper_log):
    env = _engine_env(args, profile, gem5=(engine == "gem5"))
    if engine == "gem5":
        qemu = _gem5_cmd(args)
    elif profile == "node":
        qemu = os.path.join(args.work_dir, "wrappers", "qemu-node-embench.py")
        env["PARITY_QEMU_REAL"] = _qemu_cmd(args)
        env["PARITY_QEMU_BOOTROM"] = os.path.abspath(args.bootrom_node)
        env["PARITY_WRAPPER_LOG"] = wrapper_log
    else:
        qemu = _qemu_cmd(args)
    cmd = [sys.executable, RUN_EMBENCH, "--profile", profile,
           "--qemu", qemu, "--opt", "O0,O2",
           "--work-dir", os.path.join(args.work_dir,
                                      "emb-%s-%s" % (profile, engine)),
           "--timeout", str(args.timeout), "--json-out", out_json]
    rc = _run_logged(cmd, log_path, env=env, timeout=args.scope_timeout)
    if not os.path.isfile(out_json):
        raise SetupError(f"embench {profile}/{engine}: no JSON (rc={rc}); "
                         f"log {log_path}")
    return rc, _cache_by_case(out_json, "embench")


def _make_embench_wrapper(args):
    path = os.path.join(args.work_dir, "wrappers", "qemu-node-embench.py")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("""#!/usr/bin/env python3
\"\"\"QEMU Node embench wrapper (generated by run_parity.py).

The embench driver is Tiny-shaped: it always passes `-M dadao-m1`.  For the
Node matrix run the evidence layer rewrites that machine into
`dadao-m1,profile=node,bootrom-image=...` and leaves every other argv item
untouched.  Each rewritten argv is logged as JSON for the parity matrix.
\"\"\"
import json, os, subprocess, sys
real = os.environ["PARITY_QEMU_REAL"]
rom = os.environ["PARITY_QEMU_BOOTROM"]
log = os.environ["PARITY_WRAPPER_LOG"]
args = sys.argv[1:]
out, i, replaced = [], 0, False
while i < len(args):
    a = args[i]
    if a in ("-M", "-machine") and i + 1 < len(args) \\
            and args[i + 1].split(",")[0] == "dadao-m1":
        out += ["-machine", "dadao-m1,profile=node,bootrom-image=" + rom]
        replaced = True
        i += 2
        continue
    out.append(a)
    i += 1
if not replaced:
    sys.stderr.write("qemu-node-embench: ERROR: no -M/-machine dadao-m1 in argv\\n")
    sys.exit(2)
with open(log, "a", encoding="utf-8") as fh:
    fh.write(json.dumps({"argv": out}) + "\\n")
sys.exit(subprocess.call([real] + out))
""")
    os.chmod(path, 0o755)
    return path


def _last_wrapper_machine(wrapper_log):
    if not os.path.isfile(wrapper_log):
        return None
    last = None
    with open(wrapper_log, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                last = line
    if not last:
        return None
    try:
        argv = json.loads(last).get("argv", [])
    except ValueError:
        return None
    for i, tok in enumerate(argv):
        if tok in ("-M", "-machine") and i + 1 < len(argv):
            return argv[i + 1]
    return None


def _picolibc_run(args, log_path):
    qwork = os.path.join(args.work_dir, "picolibc-qemu")
    qjson = os.path.join(args.work_dir, "picolibc-qemu.json")
    env = _engine_env(args, "tiny")
    cmd = [sys.executable, PICOLIBC_TESTS, "--stage", "fast",
           "--profile", "tiny", "--work-dir", qwork, "--jobs",
           str(args.jobs), "--json", qjson]
    rc = _run_logged(cmd, log_path, env=env, timeout=args.scope_timeout)
    if not os.path.isfile(qjson):
        raise SetupError(f"picolibc QEMU: no JSON (rc={rc}); log {log_path}")
    with open(qjson, "r", encoding="utf-8") as fh:
        doc = json.load(fh)
    results = doc.get("results")
    if not isinstance(results, list) or not results:
        raise SetupError(f"picolibc QEMU: empty results in {qjson}")
    return rc, doc, qwork, qjson


def _classify_gem5_picolibc(name, rc, mod):
    if name in PICOLIBC_KNOWN_BLOCKED and rc != 0:
        return "BLOCKED", PICOLIBC_KNOWN_BLOCKED[name]
    if rc == 0:
        return "PASS", "exit 0"
    if rc == 77:
        return "N/A", "picolibc self-skip (exit 77)"
    if _is_machine_fault(rc):
        return "BLOCKED", "machine fault 0x%02X" % rc
    return "FAIL", "exit %s" % rc


def _picolibc_gem5(args, qdoc, qwork, log_path):
    import picolibc_tests as mod
    out = {}
    for entry in qdoc["results"]:
        name = entry["name"]
        if entry["status"] in ("excluded", "blocked"):
            continue  # no comparable ELF run
        elf = os.path.join(qwork, name + ".elf")
        if not os.path.isfile(elf):
            out[name] = {"status": "ERROR", "exit": None,
                         "arch_visible": {"elf": None},
                         "note": "ELF missing despite QEMU run"}
            continue
        argv = (mod.SEMIHOST_ARGV
                if name in getattr(mod, "SEMIHOST_ARGS_TESTS", set()) else None)
        cmd = [_gem5_cmd(args), "-M", "dadao-m1", "-kernel", elf,
               "-display", "none", "-nographic", "-monitor", "none"]
        cfg = "enable=on,target=native"
        if argv:
            cfg += "".join(",arg=" + a for a in argv)
        cmd += ["-semihosting-config", cfg]
        env = _engine_env(args, "tiny", gem5=True)
        timeout = mod.SLOW_TESTS.get(name, mod.DEFAULT_TIMEOUT) \
            if hasattr(mod, "SLOW_TESTS") else args.timeout
        timeout = max(timeout, args.timeout)
        rc = _run_logged(cmd, os.path.join(log_path, name + ".log"), env=env,
                         timeout=timeout)
        if rc == 124:
            if name in PICOLIBC_KNOWN_BLOCKED:
                status, why = "BLOCKED", (PICOLIBC_KNOWN_BLOCKED[name] +
                                          " (gem5 did not finish within "
                                          f"{timeout}s)")
            else:
                status, why = "TIMEOUT", "gem5 timeout"
        else:
            status, why = _classify_gem5_picolibc(name, rc, mod)
        out[name] = {"status": status, "exit": rc,
                     "arch_visible": {"elf": os.path.basename(elf),
                                      "elf_md5": _md5(elf),
                                      "argv": argv, "rc": rc},
                     "note": why}
    return out


# ---------------------------------------------------------------------------
# row assembly
# ---------------------------------------------------------------------------

def _rec(status, exit_code, visible, machine="", note="", wrapper=None):
    rec = {"status": status, "exit": exit_code,
           "arch_visible": visible or {}, "machine": machine, "note": note}
    if wrapper is not None:
        rec["wrapper"] = wrapper
    return rec


def build_rows(args, live):
    rows = []
    sources = {"runs": [], "picolibc_json": None}
    wrapper_log = os.path.join(args.work_dir, "wrapper-node-embench.jsonl")
    if "embench" in args.scopes and "node" in args.profiles:
        _make_embench_wrapper(args)
        if os.path.exists(wrapper_log):
            os.remove(wrapper_log)

    for profile in args.profiles:
        for scope in args.scopes:
            key = (profile, scope)
            templates = live[key]
            if not templates:
                continue
            if scope == "inst":
                qjson = os.path.join(args.work_dir, f"inst-{profile}-qemu.json")
                gjson = os.path.join(args.work_dir, f"inst-{profile}-gem5.json")
                qrc, qmap = _semantics_run(
                    args, profile, "qemu", qjson,
                    os.path.join(args.work_dir, "logs",
                                 f"inst-{profile}-qemu.log"))
                grc, gmap = _semantics_run(
                    args, profile, "gem5", gjson,
                    os.path.join(args.work_dir, "logs",
                                 f"inst-{profile}-gem5.log"))
                sources["runs"] += [
                    {"engine": "qemu", "profile": profile, "scope": "inst",
                     "rc": qrc, "json": qjson, "log":
                     os.path.join(args.work_dir, "logs",
                                  f"inst-{profile}-qemu.log")},
                    {"engine": "gem5", "profile": profile, "scope": "inst",
                     "rc": grc, "json": gjson, "log":
                     os.path.join(args.work_dir, "logs",
                                  f"inst-{profile}-gem5.log")},
                ]
                for t in templates:
                    q = qmap.get(t["case_id"])
                    g = gmap.get(t["case_id"])
                    machine = ("dadao-m1,profile=node,bootrom-image=" +
                               os.path.abspath(args.bootrom_node)
                               if profile == "node" else
                               "dadao-m1 -bios " + os.path.abspath(
                                   args.bootrom_tiny))
                    qr = _rec(q["status"], q.get("exit"),
                              q.get("arch_visible"), machine,
                              q.get("note", "")) if q else _rec(
                        "ERROR", None, {}, machine,
                        "missing from QEMU semantics_gate JSON")
                    gr = _rec(g["status"], g.get("exit"),
                              g.get("arch_visible"),
                              "gem5 --profile " + profile, g.get("note", "")) \
                        if g else _rec(
                        "ERROR", None, {}, "gem5 --profile " + profile,
                        "missing from gem5 semantics_gate JSON")
                    rows.append(_row(t, qr, gr))
            elif scope == "arch":
                if profile == "tiny":
                    for t in templates:
                        rows.append(_row(
                            t, _rec("N/A", None, {"basis":
                                 "tests/shared/machine-profiles.yaml "
                                 "tiny.arch=false (Tiny has no cfx)"},
                                    ""),
                            _rec("N/A", None, {"basis":
                                 "tests/shared/machine-profiles.yaml "
                                 "tiny.arch=false"}, ""),
                            note="arch is Node-only (profile Tiny arch=false)"))
                    continue
                qjson = os.path.join(args.work_dir, f"arch-{profile}-qemu.json")
                gjson = os.path.join(args.work_dir, f"arch-{profile}-gem5.json")
                qrc, qmap = _arch_smoke_run(
                    args, profile, "qemu", qjson,
                    os.path.join(args.work_dir, "logs",
                                 f"arch-{profile}-qemu.log"))
                grc, gmap = _arch_smoke_run(
                    args, profile, "gem5", gjson,
                    os.path.join(args.work_dir, "logs",
                                 f"arch-{profile}-gem5.log"))
                sources["runs"] += [
                    {"engine": "qemu", "profile": profile, "scope": "arch",
                     "rc": qrc, "json": qjson, "log":
                     os.path.join(args.work_dir, "logs",
                                  f"arch-{profile}-qemu.log")},
                    {"engine": "gem5", "profile": profile, "scope": "arch",
                     "rc": grc, "json": gjson, "log":
                     os.path.join(args.work_dir, "logs",
                                  f"arch-{profile}-gem5.log")},
                ]
                machine = ("dadao-m1,profile=node,bootrom-image=" +
                           os.path.abspath(args.bootrom_node))
                for t in templates:
                    if t["kind"] == "smoke":
                        q = qmap.get(t["case_id"])
                        g = gmap.get(t["case_id"])
                        qr = _rec(q["status"], q.get("exit"),
                                  q.get("arch_visible"), machine,
                                  q.get("note", "")) if q else _rec(
                            "ERROR", None, {}, machine,
                            "missing from QEMU run_m5_e2e JSON")
                        gr = _rec(g["status"], g.get("exit"),
                                  g.get("arch_visible"),
                                  "gem5 --profile node", g.get("note", "")) \
                            if g else _rec(
                            "ERROR", None, {}, "gem5 --profile node",
                            "missing from gem5 run_m5_e2e JSON")
                    else:
                        qr = _probe_run(
                            args, profile, "qemu", t, t["check"],
                            t["icount"],
                            os.path.join(args.work_dir, "logs",
                                         f"probe-{t['probe']}-{t['check']}"
                                         "-qemu.log"))
                        gr = _probe_run(
                            args, profile, "gem5", t, t["check"],
                            t["icount"],
                            os.path.join(args.work_dir, "logs",
                                         f"probe-{t['probe']}-{t['check']}"
                                         "-gem5.log"))
                        qr.setdefault("machine", machine)
                        gr.setdefault("machine", "gem5 --profile node")
                    rows.append(_row(t, qr, gr))
            elif scope == "embench":
                qjson = os.path.join(args.work_dir,
                                     f"emb-{profile}-qemu.json")
                gjson = os.path.join(args.work_dir,
                                     f"emb-{profile}-gem5.json")
                qrc, qmap = _embench_run(
                    args, profile, "qemu", qjson,
                    os.path.join(args.work_dir, "logs",
                                 f"emb-{profile}-qemu.log"), wrapper_log)
                grc, gmap = _embench_run(
                    args, profile, "gem5", gjson,
                    os.path.join(args.work_dir, "logs",
                                 f"emb-{profile}-gem5.log"), wrapper_log)
                sources["runs"] += [
                    {"engine": "qemu", "profile": profile, "scope": "embench",
                     "rc": qrc, "json": qjson, "log":
                     os.path.join(args.work_dir, "logs",
                                  f"emb-{profile}-qemu.log")},
                    {"engine": "gem5", "profile": profile, "scope": "embench",
                     "rc": grc, "json": gjson, "log":
                     os.path.join(args.work_dir, "logs",
                                  f"emb-{profile}-gem5.log")},
                ]
                qmachine = "dadao-m1"
                gmachine = "gem5 --profile " + profile
                qwrap = None
                if profile == "node":
                    qmachine = _last_wrapper_machine(wrapper_log) or ""
                    qwrap = "qemu-node-embench.py"
                    gmachine += " (PARITY_GEM5_PROFILE=node)"
                for t in templates:
                    q = qmap.get(t["case_id"])
                    g = gmap.get(t["case_id"])
                    qr = _rec(q["status"], q.get("exit"),
                              q.get("arch_visible"), qmachine,
                              q.get("note", ""), qwrap) if q else _rec(
                        "ERROR", None, {}, qmachine,
                        "missing from QEMU embench JSON", qwrap)
                    gr = _rec(g["status"], g.get("exit"),
                              g.get("arch_visible"), gmachine,
                              g.get("note", "")) if g else _rec(
                        "ERROR", None, {}, gmachine,
                        "missing from gem5 embench JSON")
                    rows.append(_row(t, qr, gr))
            elif scope == "picolibc":
                qrc, qdoc, qwork, qjson = _picolibc_run(
                    args, os.path.join(args.work_dir, "logs",
                                       "picolibc-qemu.log"))
                sources["picolibc_json"] = qjson
                sources["runs"].append(
                    {"engine": "qemu", "profile": profile, "scope": "picolibc",
                     "rc": qrc, "json": qjson, "log":
                     os.path.join(args.work_dir, "logs",
                                  "picolibc-qemu.log")})
                gmap = _picolibc_gem5(
                    args, qdoc, qwork,
                    os.path.join(args.work_dir, "picolibc-gem5-logs"))
                sources["runs"].append(
                    {"engine": "gem5", "profile": profile,
                     "scope": "picolibc", "rc": None,
                     "json": None, "log": os.path.join(
                         args.work_dir, "picolibc-gem5-logs")})
                qmap = {c["case_id"]: c for c in
                        [{"case_id": "picolibc/" + r["name"],
                          "status": {"pass": "PASS", "fail": "FAIL",
                                     "excluded": "N/A",
                                     "blocked": "BLOCKED"}[r["status"]],
                          "exit": (0 if r["status"] == "pass" else
                                   (77 if r["status"] == "excluded" else None)),
                          "arch_visible": {"qemu_class": r["status"],
                                           "reason": r["reason"]},
                          "note": r["reason"]} for r in qdoc["results"]]}
                for t in templates:
                    name = t["name"]
                    q = qmap.get(t["case_id"])
                    g = gmap.get(name)
                    if q is None:
                        qr = _rec("ERROR", None, {}, "",
                                  "missing from picolibc QEMU JSON")
                    else:
                        qr = _rec(q["status"], q.get("exit"),
                                  q.get("arch_visible"), "dadao-m1",
                                  q.get("note", ""))
                    if g is None:
                        if q and q["status"] in ("N/A", "PASS", "BLOCKED"):
                            gr = _rec(
                                "N/A", None, {"basis":
                                              "QEMU result has no comparable "
                                              "ELF (excluded/blocked)"}, "",
                                "not compared")
                        else:
                            gr = _rec("ERROR", None, {}, "",
                                      "missing gem5 picolibc result")
                    else:
                        gr = _rec(g["status"], g.get("exit"),
                                  g.get("arch_visible"),
                                  "gem5 --profile tiny", g.get("note", ""))
                    rows.append(_row(t, qr, gr,
                                     note="picolibc side evidence (not in the "
                                          "hard subset)"))
    return rows, sources


def _row(template, qrec, grec, note=""):
    return {"case_id": template["case_id"], "profile": template["profile"],
            "scope": template["scope"], "qemu": qrec, "gem5": grec,
            "verdict": "", "attribution": "", "note": note}


# ---------------------------------------------------------------------------
# verdict / judging
# ---------------------------------------------------------------------------

def _norm_visible(scope, rec):
    """Architecture-visible result used for equality (no timings/logs)."""
    av = rec.get("arch_visible") or {}
    if scope == "inst":
        return {"expected_fault": av.get("expected_fault")}
    if scope == "arch":
        return {"console_expected": av.get("console_expected"),
                "console_actual": av.get("console_actual"),
                "console_ok": av.get("console_ok"),
                "bootrom_ok": av.get("bootrom_ok"),
                "probe_rc": av.get("probe_rc")}
    if scope == "embench":
        return {"guest_exit": av.get("guest_exit")}
    return {}


def _verdict(scope, q, g):
    qs, gs = q["status"], g["status"]
    if qs == "N/A" and gs == "N/A":
        return "N/A"
    if qs == "N/A" or gs == "N/A":
        return "BLOCKED_SIDE" if (qs == "N/A" or gs == "N/A") else "DIFF"
    if qs == "DEFERRED" and gs == "DEFERRED":
        return "N/A"
    if qs == "SKIP_PROFILE" and gs == "SKIP_PROFILE":
        return "N/A"
    if qs == "BLOCKED" or gs == "BLOCKED":
        return "BLOCKED_SIDE"
    if qs == "PASS" and gs == "PASS":
        if q.get("exit") != g.get("exit"):
            return "DIFF"
        return "AGREE_PASS" if _norm_visible(scope, q) == _norm_visible(
            scope, g) else "DIFF"
    if qs == "PASS" and gs != "PASS":
        return "GEM5_ONLY_FAIL"
    if gs == "PASS" and qs != "PASS":
        return "QEMU_ONLY_FAIL"
    # both non-PASS: agreement when exit and visible result match
    if q.get("exit") == g.get("exit") and _norm_visible(
            scope, q) == _norm_visible(scope, g):
        return "AGREE_FAIL"
    return "DIFF"


def _assign_confidence(row):
    scope = row["scope"]
    q = row["qemu"]
    g = row["gem5"]
    if row.get("attribution"):
        return
    if g.get("status") == "BLOCKED" and g.get("note"):
        row["attribution"] = "gem5-capability: " + g["note"]
    elif g.get("status") == "N/A" and g.get("note"):
        row["attribution"] = "N/A: " + g["note"]
    if scope == "picolibc" and row["case_id"].endswith("/math_test"):
        row["attribution"] = "gem5 B7 numeric difference (GEM5-015t)"


def counts_for(rows):
    keys = ("total", "agree_pass", "agree_fail", "gem5_only_fail",
            "qemu_only_fail", "diff", "deferred", "skip_profile", "blocked",
            "n_a")
    out = {}
    for row in rows:
        key = (row["profile"], row["scope"])
        c = out.setdefault(key, {k: 0 for k in keys})
        c["total"] += 1
        v = row["verdict"]
        if v == "AGREE_PASS":
            c["agree_pass"] += 1
        elif v == "AGREE_FAIL":
            c["agree_fail"] += 1
        elif v == "GEM5_ONLY_FAIL":
            c["gem5_only_fail"] += 1
        elif v == "QEMU_ONLY_FAIL":
            c["qemu_only_fail"] += 1
        elif v == "DIFF":
            c["diff"] += 1
        elif v == "BLOCKED_SIDE":
            c["blocked"] += 1
        elif v == "N/A":
            if row["qemu"]["status"] not in ("DEFERRED", "SKIP_PROFILE"):
                c["n_a"] += 1
        qs = row["qemu"]["status"]
        if qs == "DEFERRED":
            c["deferred"] += 1
        if qs == "SKIP_PROFILE":
            c["skip_profile"] += 1
    return out


def _check_coverage(rows, live):
    errs = []
    seen = set()
    for row in rows:
        key = (row["case_id"], row["profile"])
        if key in seen:
            errs.append(f"duplicate row {row['profile']}/{row['case_id']}")
        seen.add(key)
        cid = row["case_id"]
        if not cid or "/" not in cid:
            errs.append(f"malformed case_id {cid!r}")
        if row["profile"] not in PROFILES or row["scope"] not in SCOPES:
            errs.append(f"bad row profile/scope {row['profile']}/{row['scope']}")
        if not isinstance(row.get("qemu"), dict) or not isinstance(
                row.get("gem5"), dict):
            errs.append(f"{cid}: missing engine record")
        for side in ("qemu", "gem5"):
            st = row[side].get("status")
            if st not in STATUSES:
                errs.append(f"{cid}: bad {side}.status {st!r}")
    for key, templates in live.items():
        profile, scope = key
        want = [t["case_id"] for t in templates]
        if not want:
            continue
        want_map = {cid: i for i, cid in enumerate(want)}
        got = [r["case_id"] for r in rows
               if r["profile"] == profile and r["scope"] == scope]
        missing = sorted(set(want) - set(got))
        extra = sorted(set(got) - set(want))
        if missing:
            errs.append(f"{profile}/{scope}: {len(missing)} missing case(s), "
                        f"e.g. {missing[:3]}")
        if extra:
            errs.append(f"{profile}/{scope}: {len(extra)} extra case(s), "
                        f"e.g. {extra[:3]}")
        if len(got) != len(set(got)):
            errs.append(f"{profile}/{scope}: duplicate case rows")
        if scope == "inst":
            for t in templates:
                matching = [r for r in rows
                            if r["profile"] == profile
                            and r["case_id"] == t["case_id"]]
                if not matching:
                    continue
                row = matching[0]
                exp = t.get("expected", "RUN")
                if exp == "SKIP_PROFILE" and row["qemu"]["status"] != \
                        "SKIP_PROFILE":
                    errs.append(f"{t['case_id']}: expected SKIP_PROFILE, got "
                                f"{row['qemu']['status']}")
                if exp == "DEFERRED" and row["qemu"]["status"] != "DEFERRED":
                    errs.append(f"{t['case_id']}: expected DEFERRED, got "
                                f"{row['qemu']['status']}")
                if exp == "RUN" and row["qemu"]["status"] in ("DEFERRED",
                                                              "SKIP_PROFILE"):
                    errs.append(f"{t['case_id']}: unexpectedly "
                                f"{row['qemu']['status']}")
        if scope == "arch":
            for t in templates:
                matching = [r for r in rows
                            if r["profile"] == profile
                            and r["case_id"] == t["case_id"]]
                if not matching:
                    continue
                row = matching[0]
                if t.get("icount") and row["gem5"]["status"] != "N/A":
                    errs.append(f"{t['case_id']}: -icount check must stay N/A "
                                f"on gem5, got {row['gem5']['status']}")
                if profile == "tiny" and (
                        row["qemu"]["status"] != "N/A"
                        or row["gem5"]["status"] != "N/A"):
                    errs.append(f"{t['case_id']}: tiny/arch must be N/A, got "
                                f"QEMU {row['qemu']['status']} / gem5 "
                                f"{row['gem5']['status']}")
        if scope == "embench":
            benches = sorted({r["case_id"].rsplit("-O", 1)[0] for r in rows
                              if r["profile"] == profile
                              and r["scope"] == "embench"})
            # executed == discovered is enforced by the row count vs templates
            if len(got) != len(want):
                errs.append(f"{profile}/embench: executed {len(got)} != "
                            f"discovered {len(want)}")
        if scope == "picolibc":
            for row in rows:
                if row["profile"] != profile or row["scope"] != "picolibc":
                    continue
                name = row["case_id"].split("/", 1)[1]
                q, g = row["qemu"], row["gem5"]
                if name in PICOLIBC_KNOWN_BLOCKED:
                    if q["status"] != "PASS":
                        errs.append(f"picolibc/{name}: QEMU baseline is not "
                                    f"PASS ({q['status']})")
                    if g["status"] != "BLOCKED":
                        errs.append(f"picolibc/{name}: gem5 must stay BLOCKED "
                                    f"(B7), got {g['status']} (blocked "
                                    f"masquerade)")
                elif q["status"] == "PASS" and g["status"] == "N/A":
                    errs.append(f"picolibc/{name}: gem5 not compared")
                elif q["status"] == "N/A" and g["status"] == "PASS":
                    errs.append(f"picolibc/{name}: gem5 PASS but QEMU "
                                f"excluded")
    return errs


def _check_machines(rows):
    errs = []
    for row in rows:
        profile, scope = row["profile"], row["scope"]
        qm = (row["qemu"].get("machine") or "")
        gm = (row["gem5"].get("machine") or "")
        if scope == "embench" and profile == "node":
            if "profile=node" not in qm:
                errs.append(f"{row['case_id']}: Node embench QEMU machine "
                            f"lacks profile=node (wrapper not applied): "
                            f"{qm!r}")
            if row["qemu"].get("wrapper") != "qemu-node-embench.py":
                errs.append(f"{row['case_id']}: Node embench wrapper not "
                            f"recorded")
            if "profile node" not in gm and "profile=node" not in gm:
                errs.append(f"{row['case_id']}: gem5 Node embench run not "
                            f"recorded as node: {gm!r}")
        if scope == "arch" and profile == "node":
            if "profile=node" not in qm:
                errs.append(f"{row['case_id']}: Node arch QEMU machine lacks "
                            f"profile=node")
    return errs


def _check_picolibc(rows):
    errs = []
    for row in rows:
        if row["scope"] != "picolibc":
            continue
        name = row["case_id"].split("/", 1)[1]
        q, g = row["qemu"], row["gem5"]
        if name in PICOLIBC_KNOWN_BLOCKED:
            if q["status"] != "PASS":
                errs.append(f"picolibc/{name}: QEMU baseline is not PASS "
                            f"({q['status']})")
            if g["status"] != "BLOCKED":
                errs.append(f"picolibc/{name}: gem5 must stay BLOCKED (B7), "
                            f"got {g['status']} (blocked masquerade)")
        elif q["status"] == "PASS" and g["status"] == "N/A":
            errs.append(f"picolibc/{name}: gem5 not compared")
        elif q["status"] == "N/A" and g["status"] == "PASS":
            errs.append(f"picolibc/{name}: gem5 PASS but QEMU excluded")
    return errs


def _apply_known_blocked(row):
    """Reclassify registry-listed QEMU-PASS/gem5-fail rows as BLOCKED (gem5).

    The raw engine status is preserved in ``raw_status``; a registry entry that
    unexpectedly PASSes is a stale-registry error (see judge).
    """
    reason = KNOWN_GEM5_BLOCKED.get(row["case_id"])
    if not reason:
        return None
    g = row["gem5"]
    if row["qemu"]["status"] != "PASS":
        return None
    if g["status"] == "PASS":
        return "stale"
    if g["status"] == "BLOCKED":
        if not str(row.get("attribution", "")).startswith("gem5-defect"):
            row["attribution"] = ("gem5-defect (separate gem5 task): " +
                                  reason)
        return None
    g["raw_status"] = g["status"]
    g["status"] = "BLOCKED"
    g["note"] = reason
    row["attribution"] = "gem5-defect (separate gem5 task): " + reason
    return None


def judge(rows, live=None, strict_coverage=True):
    """Recompute verdicts and return (errors, counts).  Never trusts a stored
    verdict: a mismatch between stored and recomputed verdict is an error."""
    errs = []
    if not rows:
        return ["zero cases"], {}
    for row in rows:
        stale = _apply_known_blocked(row)
        if stale:
            errs.append(f"{row['case_id']}: KNOWN_GEM5_BLOCKED is stale "
                        f"(gem5 now PASS); remove the registry entry")
        _assign_confidence(row)
        want = _verdict(row["scope"], row["qemu"], row["gem5"])
        if row.get("verdict") and row["verdict"] != want:
            errs.append(f"{row['case_id']}: stored verdict {row['verdict']} != "
                        f"recomputed {want}")
        row["verdict"] = want
        if want == "GEM5_ONLY_FAIL":
            errs.append(f"GEM5_ONLY_FAIL {row['case_id']}: QEMU "
                        f"{row['qemu']['status']}/exit={row['qemu'].get('exit')}"
                        f" gem5 {row['gem5']['status']}/exit="
                        f"{row['gem5'].get('exit')} ({row['gem5'].get('note')})")
        elif want == "DIFF":
            if not row.get("attribution"):
                errs.append(f"DIFF (unattributed) {row['case_id']}: "
                            f"QEMU {row['qemu']['status']}/"
                            f"{row['qemu'].get('exit')} vs gem5 "
                            f"{row['gem5']['status']}/"
                            f"{row['gem5'].get('exit')}")
        elif want == "QEMU_ONLY_FAIL":
            row["note"] = (row.get("note") or "") + \
                " [handoff: separate QEMU debug task]"
    if strict_coverage and live is not None:
        errs += _check_coverage(rows, live)
    errs += _check_machines(rows)
    errs += _check_picolibc(rows)
    return errs, counts_for(rows)


# ---------------------------------------------------------------------------
# outputs
# ---------------------------------------------------------------------------

def _row_sort(rows):
    rows.sort(key=lambda r: (r["profile"], r["scope"], r["case_id"]))


def write_matrix_json(path, rows, ident, counts, sources):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    payload = {
        "schema": 1,
        "generated_at": ident.get("generated_at"),
        "engines": ident.get("engines", {}),
        "toolchain": ident.get("toolchain", {}),
        "bootrom": ident.get("bootrom", {}),
        "profiles": sorted({r["profile"] for r in rows}),
        "scopes": sorted({r["scope"] for r in rows}),
        "counts": {"%s/%s" % k: v for k, v in sorted(counts.items())},
        "sources": sources,
        "cases": rows,
    }
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=1, sort_keys=True)
        fh.write("\n")


def _non_agree(rows):
    return [r for r in rows if r["verdict"] != "AGREE_PASS"]


def write_markdown(path, ident, rows, counts):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    lines = ["# M11 QEMU system <-> gem5 FS parity matrix", ""]
    lines.append("> Generated by `tools/testcases/parity/run_parity.py`; "
                 "counts are derived from the rows, never typed by hand.")
    lines.append("> Pairing: QEMU system ↔ gem5 FS only (ADR-0048 D1/D2). "
                 "Timing/performance/log format are not compared.")
    lines.append("")
    lines.append("## Engine / toolchain identity")
    lines.append("")
    q = ident["engines"]["qemu"]
    g = ident["engines"]["gem5"]
    lines.append(f"- QEMU: `{q['path']}` md5 `{q['md5']}` version "
                 f"`{q.get('version','')}`")
    lines.append(f"- gem5: `{g['path']}` md5 `{g['md5']}`; config "
                 f"`{g['config']}` md5 `{g['config_md5']}`; source "
                 f"`{g.get('source_commit','')}`")
    for name, info in ident.get("bootrom", {}).items():
        lines.append(f"- BootROM `{name}`: `{info['path']}` md5 `{info['md5']}` "
                     f"size {info['size']}")
    tool = ", ".join(f"{k}=`{v['md5']}`" for k, v in
                     ident.get("toolchain", {}).items())
    lines.append(f"- Toolchain md5: {tool}")
    lines.append("")
    lines.append("## Counts per profile x scope")
    lines.append("")
    lines.append("| profile | scope | total | agree_pass | agree_fail | "
                 "gem5_only_fail | qemu_only_fail | diff | deferred | "
                 "skip_profile | blocked | N/A |")
    lines.append("| --- | --- | " + " | ".join(["---"] * 10) + " |")
    keys = ("total", "agree_pass", "agree_fail", "gem5_only_fail",
            "qemu_only_fail", "diff", "deferred", "skip_profile", "blocked",
            "n_a")
    for (profile, scope), c in sorted(counts.items()):
        lines.append("| %s | %s | %s |" % (
            profile, scope, " | ".join(str(c[k]) for k in keys)))
    lines.append("")
    lines.append("Cells not run by profile design: `tiny/arch` is N/A "
                 "(`machine-profiles.yaml` `tiny.arch=false`); `node/picolibc` "
                 "is not run (`node.picolibc=false`).")
    lines.append("")
    lines.append("## Non-AGREE_PASS rows")
    lines.append("")
    bad = _non_agree(rows)
    if not bad:
        lines.append("None.")
    else:
        lines.append("| profile | scope | case_id | QEMU | gem5 | verdict | "
                     "attribution / note |")
        lines.append("| --- | --- | --- | --- | --- | --- | --- |")
        for r in bad:
            note = (r.get("attribution") or r.get("note") or "").replace(
                "|", "/")
            lines.append("| %s | %s | `%s` | %s/%s | %s/%s | %s | %s |" % (
                r["profile"], r["scope"], r["case_id"],
                r["qemu"]["status"], r["qemu"].get("exit"),
                r["gem5"]["status"], r["gem5"].get("exit"),
                r["verdict"], note))
    lines.append("")
    lines.append("## N/A / BLOCKED basis")
    lines.append("")
    if any(r["profile"] == "tiny" and r["scope"] == "arch" for r in rows):
        lines.append("- `tiny/arch`: `tests/shared/machine-profiles.yaml` "
                     "`tiny.arch=false` (Tiny has no cfx/monitor).")
    icount = [r for r in rows if (r["gem5"].get("arch_visible") or {}).get(
        "check") and "icount" in (r["gem5"].get("note") or "")]
    if icount:
        lines.append(f"- {len(icount)} arch probe check(s) are N/A on gem5: "
                     "QEMU `-icount` has no atomic-model equivalent (task "
                     "book §2).")
    if any(r["case_id"].endswith("/math_test") for r in rows):
        lines.append("- `picolibc/math_test`: BLOCKED, B7 numeric difference "
                     "(GEM5-015t leftover 1); never written as PASS and not in "
                     "the hard subset.")
    gem5_defects = [r for r in rows
                    if r["case_id"] in KNOWN_GEM5_BLOCKED
                    and r["gem5"]["status"] == "BLOCKED"]
    if gem5_defects:
        lines.append("- %d gem5 defect row(s) (%s): QEMU PASS / gem5 non-PASS, "
                     "registered BLOCKED with `raw_status` kept for audit and "
                     "handed to a separate gem5 task." % (
                         len(gem5_defects),
                         ", ".join("`%s`" % r["case_id"].rsplit("/", 1)[-1]
                                   for r in gem5_defects)))
    lines.append("")
    lines.append("## Evidence pointers")
    lines.append("")
    lines.append("- JSON: `%s`" % (ident.get("paths", {}).get("json") or ""))
    lines.append("- Work dir: `%s`" % ident.get("paths", {}).get("work_dir"))
    lines.append("- Evidence script: see `tools/testcases/parity/README.md`「证据与快照」")
    lines.append("")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
        fh.write("\n")


def _strip_time(doc):
    doc = copy.deepcopy(doc)
    doc.pop("generated_at", None)
    if isinstance(doc.get("engines"), dict):
        for v in doc["engines"].values():
            if isinstance(v, dict):
                v.pop("started", None)
    return json.dumps(doc, sort_keys=True)


# ---------------------------------------------------------------------------
# self-test / inject / matrix-only
# ---------------------------------------------------------------------------

def _synth_rows():
    good = []
    good.append(_row({"case_id": "inst/base/x.yaml#1:add", "profile": "tiny",
                      "scope": "inst"},
                     _rec("PASS", 0, {"expected_fault": None},
                          "dadao-m1 -bios t", ""),
                     _rec("PASS", 0, {"expected_fault": None},
                          "gem5 tiny", "")))
    good.append(_row({"case_id": "arch/umon/m5_semi_writec",
                      "profile": "node", "scope": "arch"},
                     _rec("PASS", 64, {"console_expected": "41",
                                       "console_actual": "41",
                                       "console_ok": True,
                                       "bootrom_ok": True,
                                       "machine": "dadao-m1,profile=node"},
                          "dadao-m1,profile=node", ""),
                     _rec("PASS", 64, {"console_expected": "41",
                                       "console_actual": "41",
                                       "console_ok": True,
                                       "bootrom_ok": True},
                          "gem5 node", "")))
    good.append(_row({"case_id": "embench/crc32-O0", "profile": "node",
                      "scope": "embench"},
                     _rec("PASS", 0, {"guest_exit": 0},
                          "dadao-m1,profile=node", "",
                          "qemu-node-embench.py"),
                     _rec("PASS", 0, {"guest_exit": 0},
                          "gem5 --profile node", "")))
    good.append(_row({"case_id": "picolibc/math_test", "profile": "tiny",
                      "scope": "picolibc"},
                     _rec("PASS", None, {"qemu_class": "pass"}, "", ""),
                     _rec("BLOCKED", 1, {}, "", "B7 numeric difference (B7)")))
    good.append(_row({"case_id": "inst/base/x.yaml#2:qonly",
                      "profile": "tiny", "scope": "inst"},
                     _rec("FAIL", 1, {"expected_fault": None}, "", ""),
                     _rec("PASS", 0, {"expected_fault": None}, "", "")))
    return good


def _mutations(rows):
    """Return [(name, mutate_fn, expected_rc)] on a deep copy of real rows."""
    out = []

    def pick(pred):
        for r in rows:
            if pred(r):
                return r
        return None

    agree_pass = pick(lambda r: r["verdict"] == "AGREE_PASS")
    agree_arch = pick(lambda r: r["verdict"] == "AGREE_PASS"
                      and r["scope"] == "arch")
    node_emb = pick(lambda r: r["verdict"] == "AGREE_PASS"
                    and r["scope"] == "embench" and r["profile"] == "node")
    pico = pick(lambda r: r["case_id"].endswith("/math_test"))

    def subset(doc):
        doc["cases"][0]["gem5"]["status"] = "FAIL"
        doc["cases"][0]["gem5"]["exit"] = 1

    if agree_pass:
        def subset_target(doc):
            r = next(x for x in doc["cases"]
                     if x["case_id"] == agree_pass["case_id"]
                     and x["profile"] == agree_pass["profile"])
            r["gem5"]["status"] = "FAIL"
            r["gem5"]["exit"] = (r["gem5"].get("exit") or 0) + 1
        out.append(("subset_violation", subset_target))

        def exit_mismatch(doc):
            r = next(x for x in doc["cases"]
                     if x["case_id"] == agree_pass["case_id"]
                     and x["profile"] == agree_pass["profile"])
            r["gem5"]["exit"] = (r["gem5"].get("exit") or 0) + 1
        out.append(("exit_mismatch", exit_mismatch))

        def qonly_mislabel(doc):
            r = next(x for x in doc["cases"]
                     if x["case_id"] == agree_pass["case_id"]
                     and x["profile"] == agree_pass["profile"])
            r["qemu"]["status"] = "FAIL"
            r["qemu"]["exit"] = 1
            r["gem5"]["status"] = "PASS"
            r["gem5"]["exit"] = 0
            r["verdict"] = "AGREE_PASS"
            r["note"] = "injected qemu-only-fail mislabel"
        out.append(("qemu_only_fail_mislabel", qonly_mislabel))
    if agree_arch:
        def visible(doc):
            r = next(x for x in doc["cases"]
                     if x["case_id"] == agree_arch["case_id"]
                     and x["profile"] == agree_arch["profile"])
            av = r["gem5"]["arch_visible"]
            av["console_actual"] = "42"
        out.append(("arch_visible_mismatch", visible))

    def drop_row(doc):
        doc["cases"].pop(0)
    out.append(("coverage_drop_row", drop_row))

    def dup_row(doc):
        doc["cases"].append(copy.deepcopy(doc["cases"][0]))
    out.append(("coverage_duplicate_row", dup_row))

    if node_emb:
        def profile_leak(doc):
            r = next(x for x in doc["cases"]
                     if x["case_id"] == node_emb["case_id"]
                     and x["profile"] == "node")
            r["qemu"].pop("wrapper", None)
            r["qemu"]["machine"] = "dadao-m1"
        out.append(("node_embench_no_wrapper", profile_leak))

    tiny_row = pick(lambda r: r["profile"] == "tiny" and r["scope"] != "arch")
    if tiny_row:
        def tiny_runs_node(doc):
            r = next(x for x in doc["cases"]
                     if x["case_id"] == tiny_row["case_id"]
                     and x["profile"] == "tiny")
            r["profile"] = "node"
        out.append(("tiny_profile_leak", tiny_runs_node))

    if pico:
        def blocked_as_pass(doc):
            r = next(x for x in doc["cases"]
                     if x["case_id"] == pico["case_id"])
            r["gem5"]["status"] = "PASS"
            r["gem5"]["exit"] = 0
            r["verdict"] = ""
        out.append(("blocked_as_pass", blocked_as_pass))

    def empty(doc):
        doc["cases"] = []
    out.append(("empty_matrix", empty))
    return out


def run_inject(doc, live):
    """Mutate real matrix rows; each mutation must be detected; then restore."""
    base_errors, _ = judge(doc["cases"], live, strict_coverage=True)
    if base_errors:
        print("INJECT: FAIL -- baseline matrix is not green: "
              + "; ".join(base_errors[:3]))
        return 1
    failures = []
    for name, mutate in _mutations(doc["cases"]):
        broken = copy.deepcopy(doc)
        mutate(broken)
        errs, _ = judge(broken["cases"], live, strict_coverage=True)
        detected = bool(errs)
        print(f"INJECT {name}: {'PASS (detected)' if detected else 'FAIL (not detected)'}"
              + (f" -> {errs[0]}" if detected else ""))
        if not detected:
            failures.append(name)
    if failures:
        print("INJECT: FAIL -- undetected mutations: " + ", ".join(failures))
        return 1
    print("INJECT: PASS -- every injected counter-example was detected")
    return 0


def self_test():
    rows = _synth_rows()
    live = {}
    for row in rows:
        live.setdefault((row["profile"], row["scope"]), []).append(
            {"case_id": row["case_id"], "profile": row["profile"],
             "scope": row["scope"]})
    errs, _ = judge(copy.deepcopy(rows), live, strict_coverage=True)
    if errs:
        print("SELF-TEST: FAIL -- synthetic baseline red: " + "; ".join(errs))
        return 1
    doc = {"cases": rows}
    rc = run_inject(doc, live)
    if rc == 0:
        print("SELF-TEST: PASS")
    return rc


def matrix_only(args):
    _require_file(args.matrix_only, "matrix JSON")
    with open(args.matrix_only, "r", encoding="utf-8") as fh:
        doc = json.load(fh)
    rows = doc.get("cases")
    if not isinstance(rows, list) or not rows:
        print("run_parity: ERROR: matrix has zero cases", file=sys.stderr)
        return 2
    live = enumerate_all(args)
    errs, counts = judge(rows, live, strict_coverage=True)
    _row_sort(rows)
    if args.direct_check:
        derr = direct_check(args, rows)
        if derr:
            for e in derr:
                print("FAIL: " + e)
            print("matrix-only: direct-check FAIL")
            return 1
        print("direct-check: PASS")
    if args.inject:
        return run_inject(doc, live)
    if args.markdown:
        ident = {"generated_at": doc.get("generated_at"), "engines":
                 doc.get("engines", {}), "toolchain": doc.get("toolchain", {}),
                 "bootrom": doc.get("bootrom", {}),
                 "paths": doc.get("sources", {}).get("paths", {})}
        ident["paths"].setdefault("json", os.path.abspath(args.matrix_only))
        write_markdown(args.markdown, ident, rows, counts)
    if args.json:
        ident = {"generated_at": doc.get("generated_at"), "engines":
                 doc.get("engines", {}), "toolchain": doc.get("toolchain", {}),
                 "bootrom": doc.get("bootrom", {}),
                 "paths": doc.get("sources", {}).get("paths", {})}
        ident["paths"].setdefault("json", os.path.abspath(args.matrix_only))
        write_matrix_json(args.json, rows, ident, counts,
                          doc.get("sources", {}))
    if args.repro_check:
        if not args.json:
            print("run_parity: ERROR: --repro-check requires --json",
                  file=sys.stderr)
            return 2
        with open(args.json, "r", encoding="utf-8") as fh:
            first = _strip_time(json.load(fh))
        rows2 = copy.deepcopy(rows)
        _e2, counts2 = judge(rows2, live, strict_coverage=True)
        _row_sort(rows2)
        tmp = os.path.join(args.work_dir, "repro-matrix.json")
        ident2 = {"generated_at": doc.get("generated_at"), "engines":
                  doc.get("engines", {}), "toolchain": doc.get("toolchain", {}),
                  "bootrom": doc.get("bootrom", {}),
                  "paths": doc.get("sources", {}).get("paths", {})}
        write_matrix_json(tmp, rows2, ident2, counts2, doc.get("sources", {}))
        with open(tmp, "r", encoding="utf-8") as fh:
            second = _strip_time(json.load(fh))
        os.remove(tmp)
        if first != second:
            print("repro-check: FAIL")
            return 1
        print("repro-check: PASS (rejudge+reserialise byte-identical apart "
              "from generated_at)")
    for e in errs:
        print("FAIL: " + e)
    print(f"matrix-only: {len(rows)} rows, "
          f"{'FAIL' if errs else 'PASS'}")
    return 1 if errs else 0


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def parse_args(argv):
    ap = argparse.ArgumentParser(
        description="QEMU system <-> gem5 FS same-mode parity")
    ap.add_argument("--profiles", default="tiny,node")
    ap.add_argument("--scopes", default="inst,arch,embench,picolibc")
    ap.add_argument("--qemu", default=".dadao/cross-toolchain/bin/"
                                     "qemu-system-dadao")
    ap.add_argument("--gem5", default=".work/source/gem5/build/DADAO/gem5.opt")
    ap.add_argument("--gem5-config",
                    default=".work/source/gem5/configs/dadao/fs.py")
    ap.add_argument("--bootrom-tiny", default="tools/testcases/lib/"
                                              "trampoline.bin")
    ap.add_argument("--bootrom-node",
                    default=".dadao/tests/bootrom/step5/"
                            "bootrom_step5.bin")
    ap.add_argument("--bootrom-node-inst",
                    default=".dadao/tests/bootrom/step5/"
                            "bootrom_step5_inst.bin",
                    help="Node inst matrix BootROM (Makefile NODE_BOOTROM_INST)")
    ap.add_argument("--embench-src", default=".work/source/embench-iot")
    ap.add_argument("--work-dir",
                    default="/tmp/opencode/qemu-gem5-parity/run")
    ap.add_argument("--jobs", type=int, default=8)
    ap.add_argument("--timeout", type=int, default=600,
                    help="per-guest timeout (seconds)")
    ap.add_argument("--scope-timeout", type=int, default=14400,
                    help="whole-driver timeout (seconds)")
    ap.add_argument("--json", default=None)
    ap.add_argument("--markdown", default=None)
    ap.add_argument("--only", default=None, help="filter to one case_id")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--inject", action="store_true")
    ap.add_argument("--matrix-only", default=None)
    ap.add_argument("--repro-check", action="store_true")
    ap.add_argument("--allow-repo-write", action="store_true")
    ap.add_argument("--direct-check", action="store_true")
    args = ap.parse_args(argv)

    args.profiles = [p.strip() for p in args.profiles.split(",") if p.strip()]
    args.scopes = [s.strip() for s in args.scopes.split(",") if s.strip()]
    bad = [p for p in args.profiles if p not in PROFILES]
    if bad:
        ap.error(f"unknown profile(s): {bad}")
    bad = [s for s in args.scopes if s not in SCOPES]
    if bad:
        ap.error(f"unknown scope(s): {bad}")
    if args.profiles == ["node"] and "picolibc" in args.scopes:
        ap.error("picolibc is Tiny-only (node.picolibc=false)")
    return args


def _guard_repo_write(args):
    repo = os.path.abspath(_REPO_ROOT)
    for value in (args.json, args.markdown):
        if not value:
            continue
        path = os.path.abspath(value)
        if path.startswith(repo + os.sep) and not args.allow_repo_write:
            raise SetupError(f"refusing to write inside the repo without "
                             f"--allow-repo-write: {value}")


def main(argv=None):
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        _guard_repo_write(args)
        if args.self_test:
            return self_test()
        if args.matrix_only:
            return matrix_only(args)
        if args.inject:
            print("run_parity: ERROR: --inject requires --matrix-only "
                  "<matrix.json>", file=sys.stderr)
            return 2
        live = enumerate_all(args)
        if args.list:
            for (profile, scope), templates in sorted(live.items()):
                print(f"{profile}/{scope}: {len(templates)} case(s)")
                for t in templates:
                    extra = ""
                    if t.get("expected"):
                        extra = f" [{t['expected']}]"
                    elif t.get("icount"):
                        extra = " [icount]"
                    print(f"  {t['case_id']}{extra}")
            return 0
        os.makedirs(args.work_dir, exist_ok=True)
        ident = engine_identity(args)
        rows, sources = build_rows(args, live)
        if args.only:
            rows = [r for r in rows if r["case_id"] == args.only]
            if not rows:
                raise SetupError(f"--only {args.only!r}: no such case_id")
        # baseline verdicts (so inject/consistency sees a normal matrix)
        errs, counts = judge(rows, live, strict_coverage=not args.only)
        _row_sort(rows)
        counts = counts_for(rows)
        sources["paths"] = {"work_dir": os.path.abspath(args.work_dir),
                            "json": os.path.abspath(args.json)
                            if args.json else None}
        if args.json:
            write_matrix_json(args.json, rows, ident, counts, sources)
        if args.markdown:
            write_markdown(args.markdown, ident, rows, counts)
        if args.direct_check:
            derr = direct_check(args, rows)
            if derr:
                print("direct-check: FAIL -- " + "; ".join(derr))
                return 1
            print("direct-check: PASS")
        if args.repro_check:
            if not args.json:
                raise SetupError("--repro-check requires --json")
            with open(args.json, "r", encoding="utf-8") as fh:
                first = _strip_time(json.load(fh))
            rows2 = copy.deepcopy(rows)
            _errs2, counts2 = judge(rows2, live,
                                    strict_coverage=not args.only)
            _row_sort(rows2)
            tmp = os.path.join(args.work_dir, "repro-matrix.json")
            write_matrix_json(tmp, rows2, ident, counts2, sources)
            with open(tmp, "r", encoding="utf-8") as fh:
                second = _strip_time(json.load(fh))
            os.remove(tmp)
            if first != second:
                print("repro-check: FAIL")
                return 1
            print("repro-check: PASS (rejudge+reserialise is byte-identical "
                  "apart from generated_at)")
        for e in errs:
            print("FAIL: " + e)
        if errs:
            print(f"run_parity: FAIL ({len(errs)} issue(s))")
            return 1
        print("run_parity: PASS")
        return 0
    except SetupError as exc:
        print(f"run_parity: BLOCKED/setup error: {exc}", file=sys.stderr)
        return 2


# ---------------------------------------------------------------------------
# direct gem5 runs (bypass the shim), proving the matrix is not mapping-only
# ---------------------------------------------------------------------------

def _run_gem5_direct(args, profile, extra, log_path, bootrom=None):
    env = _engine_env(args, profile, gem5=True)
    cmd = [os.path.abspath(args.gem5), "--outdir",
           os.path.join(args.work_dir, "direct-out", profile),
           os.path.abspath(args.gem5_config), "--profile", profile]
    if bootrom is None and profile == "node":
        bootrom = os.path.abspath(args.bootrom_node)
    if bootrom:
        cmd += ["--bootrom", os.path.abspath(bootrom)]
    cmd += extra
    return _run_logged(cmd, log_path, env=env, timeout=args.timeout)


def direct_check(args, rows):
    """Run at least one inst/arch/embench case directly through gem5.opt.

    Uses the same artifacts the mapped run used (inst rebuild is deterministic;
    arch/embench artifacts persist in the driver work dirs), so a mismatch with
    the shim exit is a mapping-layer bug.
    """
    errs = []
    picked = {}
    for row in rows:
        if row["scope"] not in ("inst", "arch", "embench"):
            continue
        if row["scope"] == "arch" and not row["case_id"].startswith(
                "arch/umon/"):
            continue  # direct-check uses an arch smoke case, not a probe check
        if row["scope"] == "arch" and not (
                row["gem5"].get("arch_visible") or {}).get("console_expected"):
            continue  # prefer a console-bearing smoke case so the evidence file
                      # proves console capture as well as exit propagation
        if row["gem5"]["status"] in ("PASS", "FAIL") \
                and row["scope"] not in picked:
            picked[row["scope"]] = row
    for scope in ("inst", "arch", "embench"):
        if scope not in picked:
            errs.append(f"direct-check: no comparable {scope} row found "
                        f"(cannot prove the scope bypasses the shim)")
    # inst: rebuild the exact case binary and run gem5 directly
    row = picked.get("inst")
    if row:
        rel = row["case_id"].split("#", 1)[0][len("inst/"):]
        ordinal = int(re.search(r"#(\d+):", row["case_id"]).group(1))
        env = _engine_env(args, row["profile"])
        old = os.environ.get("DADAO_TEST_PROFILE")
        os.environ["DADAO_TEST_PROFILE"] = row["profile"]
        try:
            import shutil as _sh
            from build_test_binary import set_profile as _set_profile
            _set_profile(row["profile"])
            bin_path, _case = harness.build_binary(
                os.path.join(_REPO_ROOT, "tests", "inst", rel), ordinal - 1)
            dest = os.path.join(args.work_dir, "direct", "inst.bin")
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            _sh.copyfile(bin_path, dest)
            os.unlink(bin_path)
        finally:
            if old is None:
                os.environ.pop("DADAO_TEST_PROFILE", None)
            else:
                os.environ["DADAO_TEST_PROFILE"] = old
        extra = ["--kernel", dest]
        if row["profile"] == "tiny":
            direct_bootrom = os.path.abspath(args.bootrom_tiny)
        else:
            direct_bootrom = os.path.abspath(args.bootrom_node_inst)
        rc = _run_gem5_direct(args, row["profile"], extra,
                              os.path.join(args.work_dir, "direct",
                                           "inst.log"),
                              bootrom=direct_bootrom)
        if rc != row["gem5"]["exit"]:
            errs.append(f"inst direct exit {rc} != matrix {row['gem5']['exit']}"
                        f" ({row['case_id']})")
        else:
            print(f"direct-check inst {row['case_id']}: exit {rc} == matrix")
    # arch smoke: reuse the bin produced by the mapped gem5 run
    row = picked.get("arch")
    if row and row["case_id"].startswith("arch/umon/"):
        name = row["case_id"].rsplit("/", 1)[1]
        bin_path = os.path.join(args.work_dir, "arch-node-gem5", name + ".bin")
        if not os.path.isfile(bin_path):
            errs.append(f"arch direct: artifact missing {bin_path}")
        else:
            console = os.path.join(args.work_dir, "direct", name + ".console")
            trace = os.path.join(args.work_dir, "direct", name + ".cpu.log")
            rc = _run_gem5_direct(
                args, "node",
                ["--kernel", bin_path, "--console-out", console,
                 "--trace-cpu", trace],
                os.path.join(args.work_dir, "direct", name + ".log"))
            for path, what in ((console, "console"), (trace, "trace")):
                if not os.path.isfile(path) or os.path.getsize(path) == 0:
                    errs.append(f"arch direct: {what} evidence missing/empty "
                                f"{path}")
            if rc != row["gem5"]["exit"]:
                errs.append(f"arch direct exit {rc} != matrix "
                            f"{row['gem5']['exit']} ({name})")
            else:
                print(f"direct-check arch {name}: exit {rc} == matrix "
                      f"(console={console}, trace={trace})")
    # embench: reuse the ELF produced by the mapped gem5 run
    row = picked.get("embench")
    if row:
        bench = row["case_id"].split("/", 1)[1].rsplit("-O", 1)[0]
        opt = row["case_id"].rsplit("-O", 1)[1]
        elf = os.path.join(args.work_dir, "emb-%s-gem5" % row["profile"],
                           "O" + opt, bench, bench + ".elf")
        if not os.path.isfile(elf):
            errs.append(f"embench direct: artifact missing {elf}")
        else:
            rc = _run_gem5_direct(
                args, row["profile"], ["--kernel", elf],
                os.path.join(args.work_dir, "direct",
                             f"{bench}-O{opt}.log"))
            if rc != row["gem5"]["exit"]:
                errs.append(f"embench direct exit {rc} != matrix "
                            f"{row['gem5']['exit']} ({row['case_id']})")
            else:
                print(f"direct-check embench {row['case_id']}: exit {rc} == "
                      f"matrix")
    return errs


if __name__ == "__main__":
    sys.exit(main())
