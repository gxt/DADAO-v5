#!/usr/bin/env python3
"""Build and run the DADAO riscv-tests port on QEMU system and gem5 FS.

For every `class: port` entry in tests/riscv-tests/inventory.yaml it

  1. emits the DADAO assembly from the committed case YAML (tools/.../gen.py),
  2. assembles it flat with llvm-mc + llvm-objcopy (raw -kernel image),
  3. runs the same image on both engines with semihosting enabled,
  4. compares host exit code and the printed signature region.

Engines use the same Tiny profile and the same raw image; the gem5 path goes
through tools/testcases/parity/qemu_gem5_shim.py so the two command lines are
the same subset (ADR-0048 D1/D2).  Nothing here re-derives an expected value:
the oracle is the committed case YAML (itself cross-checked against an
independent RISC-V semantics model by verify_cases.py).

Exit: 0 all cases PASS and engines agree; 1 any FAIL/DIFF; 2 setup error.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.stderr.write("ERROR: PyYAML is required\n")
    sys.exit(2)

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO_ROOT, "tools", "testcases", "riscv_tests"))
sys.path.insert(0, os.path.join(REPO_ROOT, "tools", "testcases", "lib"))
sys.path.insert(0, os.path.join(REPO_ROOT, "tools", "infra"))

import gen  # noqa: E402
import paths as _paths  # noqa: E402

TOOLCHAIN = _paths.host_toolchain_bin()
LLVM_MC = str(TOOLCHAIN / "llvm-mc")
LLVM_OBJCOPY = str(TOOLCHAIN / "llvm-objcopy")
QEMU = str(TOOLCHAIN / "qemu-system-dadao")
GEM5 = os.path.join(REPO_ROOT, ".work", "source", "gem5", "build", "DADAO",
                    "gem5.opt")
SHIM = os.path.join(REPO_ROOT, "tools", "testcases", "parity",
                    "qemu_gem5_shim.py")
TRAMPOLINE = os.path.join(REPO_ROOT, "tools", "testcases", "lib",
                          "trampoline.bin")
TINY_BOOTROM = str(_paths.test_artifacts_dir() / "bootrom" / "bootrom.bin")

ENTRY = 0xFFFFFF010100
EXIT_BLOCK = 0xFFFFFF7E0000
RAW_PREFIX = 0x100
ROM_SIZE = 0x10000
TIMEOUT = 120


def md5(path: str) -> str:
    h = hashlib.md5()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def fingerprint() -> dict:
    def first(path, pattern=None):
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    line = line.strip()
                    if pattern is None or line.startswith(pattern):
                        return line
        except OSError:
            return ""
        return ""

    def version(exe, flag):
        try:
            p = subprocess.run([exe, flag], stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, timeout=20)
            text = p.stdout.decode("utf-8", "replace")
            for line in text.splitlines():
                if "version" in line.lower() and "copyright" not in line.lower():
                    return line.strip()
            return text.splitlines()[0].strip() if text else "unknown"
        except Exception:
            return "unknown"

    return {
        "cpu": first("/proc/cpuinfo", "model name"),
        "kernel": platform.release(),
        "qemu": version(QEMU, "--version") if os.path.isfile(QEMU) else "missing",
        "gem5": version(GEM5, "--version") if os.path.isfile(GEM5) else "missing",
        "llvm_mc_md5": md5(LLVM_MC) if os.path.isfile(LLVM_MC) else "missing",
        "qemu_md5": md5(QEMU) if os.path.isfile(QEMU) else "missing",
        "gem5_md5": md5(GEM5) if os.path.isfile(GEM5) else "missing",
    }


def load_inventory(only: str | None) -> list[dict]:
    path = os.path.join(REPO_ROOT, "tests", "riscv-tests", "inventory.yaml")
    with open(path, "r", encoding="utf-8") as fh:
        doc = yaml.safe_load(fh)
    entries = [e for e in doc["entries"] if e["class"] == "port"]
    if only:
        entries = [e for e in entries
                   if only in (e["name"], f"{e['suite']}/{e['name']}")]
        if not entries:
            raise SystemExit(f"run: no port entry matches {only!r}")
    return entries


def run(cmd, timeout=TIMEOUT):
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       timeout=timeout)
    text = (p.stdout + p.stderr).decode("utf-8", "replace")
    return p.returncode, text


def parse_console(text: str, count: int) -> tuple[bool, list[str], str]:
    lines = [x.strip() for x in text.splitlines() if x.strip()]
    if not lines or lines[0] != "SIG":
        return False, [], f"console missing SIG header ({lines[:2]!r})"
    body = lines[1:]
    if len(body) != count:
        return False, body, f"signature has {len(body)} row(s), want {count}"
    for row in body:
        if len(row) != 16 or any(c not in "0123456789abcdef" for c in row):
            return False, body, f"bad signature row {row!r}"
    return True, body, ""


def build_image(entry: dict, work: str, inject: str | None) -> tuple[str, list[str]]:
    case_file = os.path.join(REPO_ROOT, "tests", "riscv-tests",
                             entry["cases"])
    doc = gen.load_case_file(case_file)
    asm, expected, _meta = gen.render(doc, inject=inject)
    if inject == "host":
        expected[0] ^= 1
    name = f"{entry['suite']}-{entry['name']}"
    asm_path = os.path.join(work, name + ".s")
    with open(asm_path, "w", encoding="utf-8") as fh:
        fh.write(asm)
    obj = os.path.join(work, name + ".o")
    raw = os.path.join(work, name + ".bin")
    rc, err = run([LLVM_MC, "--triple=dadao-unknown-elf",
                   "-I", os.path.join(REPO_ROOT, "tests", "shared", "asm"),
                   "-I", os.path.join(REPO_ROOT, "tests", "riscv-tests",
                                      "framework"),
                   "--defsym", f"ENTRY={ENTRY:#x}",
                   "--defsym", f"EXIT_BLOCK={EXIT_BLOCK:#x}",
                   "-filetype=obj", asm_path, "-o", obj])
    if rc != 0:
        raise SystemExit(f"run: llvm-mc failed for {name}: {err.strip()}")
    rc, err = run([LLVM_OBJCOPY, "-O", "binary", "--only-section=.text",
                   obj, raw])
    if rc != 0:
        raise SystemExit(f"run: llvm-objcopy failed for {name}: {err.strip()}")
    with open(raw, "rb") as fh:
        blob = fh.read()
    image = os.path.join(work, name + ".img")
    with open(image, "wb") as fh:
        fh.write(b"\0" * RAW_PREFIX + blob)
    return image, [f"{v:016x}" for v in expected]


def ensure_bootrom(work: str) -> str:
    if not os.path.isfile(TINY_BOOTROM):
        raise SystemExit(f"run: Tiny bootrom missing: {TINY_BOOTROM}")
    with open(TINY_BOOTROM, "rb") as fh:
        data = fh.read()
    if len(data) > ROM_SIZE:
        raise SystemExit("run: Tiny bootrom larger than 64 KiB")
    out = os.path.join(work, "bootrom64k.bin")
    with open(out, "wb") as fh:
        fh.write(data + b"\0" * (ROM_SIZE - len(data)))
    return out


def engine_runs(image: str, bootrom: str, work: str, name: str):
    qemu_console = os.path.join(work, name + ".qemu.console")
    gem5_console = os.path.join(work, name + ".gem5.console")
    qemu_cmd = [QEMU, "-M", "dadao-tiny", "-bios", TRAMPOLINE,
                "-kernel", image, "-nographic",
                "-semihosting-config",
                "enable=on,target=native,chardev=semi",
                "-chardev", f"file,id=semi,path={qemu_console}"]
    gem5_cmd = [sys.executable, SHIM, "-M", "dadao-tiny", "-bios", bootrom,
                "-kernel", image,
                "-semihosting-config",
                "enable=on,target=native,chardev=semi",
                "-chardev", f"file,id=semi,path={gem5_console}"]
    qrc, qerr = run(qemu_cmd)
    grc, gerr = run(gem5_cmd, timeout=300)
    return (qrc, qerr, qemu_console), (grc, gerr, gem5_console)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--only", default=None,
                    help="one suite/name or name (default: all port entries)")
    ap.add_argument("--work-dir", default="/tmp/opencode/m13-integ-004/run")
    ap.add_argument("--json", default=None)
    ap.add_argument("--inject", choices=("guest", "host"), default=None,
                    help="evidence counter-example: guest corrupts the guest "
                         "comparison, host corrupts the host oracle")
    ap.add_argument("--keep", action="store_true",
                    help="keep the work directory (never the default for CI)")
    args = ap.parse_args(argv)

    for exe, what in ((LLVM_MC, "llvm-mc"), (LLVM_OBJCOPY, "llvm-objcopy"),
                      (QEMU, "qemu-system-dadao"), (GEM5, "gem5.opt"),
                      (SHIM, "qemu_gem5_shim.py")):
        if not os.path.isfile(exe):
            sys.stderr.write(f"run: ERROR: {what} missing: {exe}\n")
            sys.stderr.write("     run 'make install-host' / 'make build-gem5'\n")
            return 2
    if not os.path.isfile(TRAMPOLINE):
        sys.stderr.write(f"run: ERROR: trampoline missing: {TRAMPOLINE}\n")
        return 2

    work = args.work_dir
    if os.path.isdir(work):
        shutil.rmtree(work)
    os.makedirs(work, exist_ok=True)
    bootrom = ensure_bootrom(work)

    entries = load_inventory(args.only)
    results = []
    failed = 0
    gem5_version = ""
    for entry in entries:
        name = f"{entry['suite']}-{entry['name']}"
        image, expected = build_image(entry, work, args.inject)
        (qrc, qerr, qcon), (grc, gerr, gcon) = engine_runs(
            image, bootrom, work, name)
        m = re.search(r"gem5 version (\S+)", gerr)
        if m and not gem5_version:
            gem5_version = m.group(1)
        qok, qsig, qwhy = (False, [], "console missing")
        gok, gsig, gwhy = (False, [], "console missing")
        if os.path.isfile(qcon):
            with open(qcon, "r", encoding="utf-8", errors="replace") as fh:
                qok, qsig, qwhy = parse_console(fh.read(), len(expected))
        if os.path.isfile(gcon):
            with open(gcon, "r", encoding="utf-8", errors="replace") as fh:
                gok, gsig, gwhy = parse_console(fh.read(), len(expected))
        qpass = qrc == 0 and qok and qsig == expected
        gpass = grc == 0 and gok and gsig == expected
        if qpass and gpass:
            status = "AGREE_PASS"
        elif qrc == grc and qsig == gsig and qsig:
            status = "AGREE_FAIL"          # both engines same wrong result
        else:
            status = "DIFF"
        if status != "AGREE_PASS":
            failed += 1
        results.append({
            "case": name,
            "status": status,
            "cases": len(expected),
            "qemu": {"exit": qrc, "signature_ok": qok and qsig == expected,
                     "reason": qwhy or qerr.strip()[-200:]},
            "gem5": {"exit": grc, "signature_ok": gok and gsig == expected,
                     "reason": gwhy or gerr.strip()[-200:]},
            "signature_match": qsig == gsig,
        })
        print(f"[{'PASS' if status == 'AGREE_PASS' else 'FAIL'}] {name}: "
              f"{status} (qemu rc={qrc}, gem5 rc={grc}, "
              f"cases={len(expected)}, sig_equal={qsig == gsig})")

    doc = {
        "task": "m13-integ-004",
        "inject": args.inject,
        "fingerprint": {**fingerprint(),
                        "gem5": gem5_version or "unknown"},
        "total": len(results),
        "passed": len(results) - failed,
        "failed": failed,
        "results": results,
    }
    if args.json:
        os.makedirs(os.path.dirname(os.path.abspath(args.json)), exist_ok=True)
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(doc, fh, indent=2)
            fh.write("\n")
    if not args.keep:
        shutil.rmtree(work, ignore_errors=True)
    print(f"run_riscv_tests: {'PASS' if failed == 0 else 'FAIL'} "
          f"({len(results) - failed}/{len(results)} case(s) AGREE_PASS)")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
