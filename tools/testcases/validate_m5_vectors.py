#!/usr/bin/env python3
"""Validate the M5 (SEE / semihosting) L3 execution vectors under
``tests/llvm/codegen/m5/``.

This is the **independent oracle** required by ``spec/Process-05`` §2/§4 and the
project "Independent oracle" hard rule.  It **never** invokes ``llvm-mc``,
``llvm-objcopy`` or QEMU and imports no child-process module (the evidence
script greps this file for any such import and requires no hit).  Expected
values are re-derived on the host from

  * ``.tao/knowledge/contract-semihosting.md`` §3 (the authoritative service
    table: number -> name -> behaviour) and §1/§4/§5 (entry tag / return /
    SYS_EXIT), and
  * ``.tao/knowledge/contract-see.md`` §3 (cfx permission rules: reserved cfxha
    and instruction-mask forbids => ILLI; unimplemented cfx / non-existent or
    over-count register combination => CFXREG),

cross-checked against the machine-readable ``; @m5`` header embedded in every
vector source (service number, console data bytes, fault rule, expected cause,
exit / fail tokens).

Checks (all fail-closed, exit non-zero on any failure):

  1. ``m5/expected.yaml`` exists, parses, has ``schema == m5-vectors-v1``.
  2. Every program record has ``name`` / ``sources`` / ``category`` /
     ``expected_exit_code`` / ``coverage`` / ``derivation``; categories and
     coverage tokens come from a fixed vocabulary; exit codes fit in 0x00..0xFF.
  3. The declared program set matches the ``*.s`` files on disk exactly (no
     missing, no orphan, no reuse).
  4. Per program, the source's ``@m5`` header is parsed and the service / rule /
     cause / tokens are re-derived from the contracts; the manifest must agree.
  5. The vector source text really contains the declared operation, the service
     dispatch constant, the console data bytes and the exit / fail tokens (so a
     wrong assembly constant, a mutated service number or a changed cause is
     caught here, not only by the end-to-end driver).
  6. Suite coverage: semihosting console (WRITEC/WRITE0/WRITE), EXIT and
     EXIT_EXTENDED, cfx-level permission counter-examples (ILLI: reserved /
     mask; CFXREG: unimplemented / bad register combination) and general
     trap + escape.

A green validator is necessary but not sufficient: the true end-to-end execution
is owned by ``tools/integ/run_m5_e2e.py`` (and ``INTEG-020t`` for the gate).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
VEC_DIR = ROOT / "tests" / "llvm" / "codegen" / "m5"
EXPECTED_PATH = VEC_DIR / "expected.yaml"
CONTRACT_SEMIHOSTING = ROOT / ".tao" / "knowledge" / "contract-semihosting.md"

SCHEMA = "m5-vectors-v1"
CATEGORIES = {"semihosting", "permission", "trap"}

COVERAGE_VOCAB = {
    "semihosting.console", "semihosting.writec", "semihosting.write0",
    "semihosting.write", "semihosting.open",
    "semihosting.exit", "semihosting.exit_extended",
    "perm.illi.reserved", "perm.illi.mask",
    "perm.cfxreg.unimpl", "perm.cfxreg.combo",
    "trap.vector", "trap.escape",
    "adr0020.d1", "adr0020.d3", "adr0020.d8", "adr0020.d9", "adr0020.d10",
}

REQUIRED_COVERAGE = {
    "semihosting.writec", "semihosting.write0", "semihosting.write",
    "semihosting.exit", "semihosting.exit_extended",
    "perm.illi.reserved", "perm.illi.mask",
    "perm.cfxreg.unimpl", "perm.cfxreg.combo",
    "trap.vector", "trap.escape",
}

REQUIRED_FIELDS = ("name", "sources", "category", "expected_exit_code",
                   "coverage", "derivation")

# Cause ids (DADAO-12 §4 monitor exception table, one-hot).  Hand-derived from
# contract-see.md §3 + DADAO-12 §5; recorded here so the vectors and the manifest
# are checked against an independent value, not against each other only.
CAUSE_ID = {
    "CFXTRAP": 1 << 0,
    "CFXREG": 1 << 2,
    "ILLI": 1 << 8,
}

# contract-see.md §3 permission rules -> expected cause.  Citation:
#   reserved_cfxha     : "reserved cfxha (7-14, 19-61) 触发 ILLI"        [DADAO-12 §5]
#   mask_forbidden     : "cfxha 合法但指令 cfx mask 禁止亦触发 ILLI"     [DADAO-12 §3/§5]
#   unimplemented_cfx  : "访问未实现的核芯功能扩展 ... 触发 CFXREG"       [DADAO-22 §3]
#   bad_register_combo : non-existent / over-count register combination => CFXREG
#                        [DADAO-12 §3 rc >= scratch_regs_num; SimRISC-11 §特权指令]
RULE_CAUSE = {
    "reserved_cfxha": "ILLI",
    "mask_forbidden": "ILLI",
    "unimplemented_cfx": "CFXREG",
    "bad_register_combo": "CFXREG",
}

# Documented SYS_EXIT pass tokens (README-m5.md); the fail tokens are distinct
# so a wrong observation is never silently accepted.
PASS_TOKEN = {
    "m5_semi_writec": 0x40,
    "m5_semi_write0": 0x41,
    "m5_semi_write": 0x42,
    "m5_perm_reserved_illi": 0x50,
    "m5_perm_mask_illi": 0x51,
    "m5_perm_unimpl_cfxreg": 0x52,
    "m5_perm_badcombo_cfxreg": 0x53,
    "m5_trap_escape": 0x60,
}

M5_RE = re.compile(r"^;\s*@m5\s+([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$")
SVC_ROW_RE = re.compile(r"\|\s*`0x([0-9a-fA-F]{2})`\s*\|\s*`([A-Z0-9_]+)`\s*\|")


class Checker:
    def __init__(self) -> None:
        self.passes = 0
        self.fails: list[str] = []

    def check(self, name, cond, detail=""):
        if cond:
            self.passes += 1
            print(f"[PASS] {name}")
        else:
            self.fails.append(name)
            print(f"[FAIL] {name} {detail}".rstrip())
        return bool(cond)


def load_service_table():
    """Parse contract-semihosting.md §3 -> {number: name}.  Genuine contract
    read: the service table is the authoritative number<->name mapping."""
    text = CONTRACT_SEMIHOSTING.read_text(encoding="utf-8")
    table = {}
    for num, name in SVC_ROW_RE.findall(text):
        table[int(num, 16)] = name
    return table


def parse_m5_header(path: Path):
    """Parse the machine-readable `; @m5 key=value` header of a vector."""
    header = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        m = M5_RE.match(line)
        if m:
            header[m.group(1)] = m.group(2)
    return header


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def derive_console(service: int, console_data: str) -> str:
    """Derive the semihosting console bytes for a service from the data block.

    WRITEC (0x03) writes one byte; WRITE0 (0x04) writes up to the first NUL;
    WRITE (0x05) writes to a file, not the console (contract-semihosting §3).
    """
    raw = bytes.fromhex(console_data) if console_data else b""
    if service == 0x03:                     # SYS_WRITEC
        return raw[:1].decode("latin-1")
    if service == 0x04:                     # SYS_WRITE0
        nul = raw.find(b"\x00")
        return (raw if nul < 0 else raw[:nul]).decode("latin-1")
    return ""                               # SYS_WRITE / others: no console


def check_source(ck: Checker, rec, path: Path, services) -> None:
    name = rec["name"]
    header = parse_m5_header(path)
    if not ck.check(f"{name}:has-header", bool(header),
                    f"no @m5 header in {path.name}"):
        return
    ck.check(f"{name}:header-name", header.get("name") == name,
             f"header name {header.get('name')!r} != {name!r}")
    kind = header.get("kind")
    ck.check(f"{name}:header-kind-known", kind in CATEGORIES,
             f"unknown kind {kind!r}")

    src = norm(path.read_text(encoding="utf-8"))
    src_l = src.lower()

    # exit / fail tokens must equal the documented values and appear verbatim.
    exp_exit = rec["expected_exit_code"]
    if name in PASS_TOKEN:
        ck.check(f"{name}:exit-is-pass-token",
                 exp_exit == PASS_TOKEN[name],
                 f"expected_exit_code 0x{exp_exit:02x} != documented 0x{PASS_TOKEN[name]:02x}")
    hdr_exit = int(header.get("exit", "0"), 16)
    ck.check(f"{name}:manifest-exit==header", exp_exit == hdr_exit,
             f"manifest 0x{exp_exit:02x} != header 0x{hdr_exit:02x}")
    ck.check(f"{name}:src-has-exit-const",
             f"set.zw rd9, wp0, 0x{hdr_exit:04x}" in src_l,
             f"source lacks `set.zw rd9, wp0, 0x{hdr_exit:04x}`")
    if "fail_exit" in header:
        fe = int(header["fail_exit"], 16)
        ck.check(f"{name}:fail-token-distinct", fe != exp_exit,
                 "fail token equals the pass token")
        ck.check(f"{name}:src-has-fail-const",
                 f"set.zw rd9, wp0, 0x{fe:04x}" in src_l,
                 f"source lacks `set.zw rd9, wp0, 0x{fe:04x}`")

    # declared operation must appear verbatim (whitespace-normalised)
    if "op" in header:
        ck.check(f"{name}:src-has-op", norm(header["op"]) in src,
                 f"source lacks operation {header['op']!r}")

    if kind == "semihosting":
        svc = int(header.get("service", "0"), 16)
        svc_name = header.get("service_name", "")
        ck.check(f"{name}:service-in-contract", svc in services,
                 f"service 0x{svc:02x} not in contract-semihosting §3 table")
        ck.check(f"{name}:service-name", services.get(svc) == svc_name,
                 f"header name {svc_name!r} != contract {services.get(svc)!r}")
        ck.check(f"{name}:src-has-service-const",
                 f"set.zw rd16, wp0, 0x{svc:04x}" in src_l,
                 f"source lacks `set.zw rd16, wp0, 0x{svc:04x}`")
        # every console data byte must really be materialised in the source
        data = header.get("console_data", "")
        if data:
            missing = [b for b in bytes.fromhex(data)
                       if f"set.zw rd8, wp0, 0x00{b:02x}" not in src_l]
            ck.check(f"{name}:src-has-console-bytes", not missing,
                     f"console byte(s) not materialised: {missing}")
            derived = derive_console(svc, data)
            ck.check(f"{name}:console-derived",
                     rec.get("expected_console", "") == derived,
                     f"manifest console {rec.get('expected_console')!r} != derived {derived!r}")
        elif "expected_console" in rec:
            ck.check(f"{name}:console-empty",
                     rec["expected_console"] == "",
                     "console declared but no console_data in header")

    elif kind == "permission":
        rule = header.get("rule", "")
        ck.check(f"{name}:rule-known", rule in RULE_CAUSE,
                 f"unknown permission rule {rule!r}")
        derived = RULE_CAUSE.get(rule)
        ck.check(f"{name}:cause-derived", header.get("cause") == derived,
                 f"header cause {header.get('cause')!r} != derived {derived!r}")
        ck.check(f"{name}:manifest-cause",
                 rec.get("expected_cause") == derived,
                 f"manifest cause {rec.get('expected_cause')!r} != derived {derived!r}")
        if derived in CAUSE_ID:
            cid = CAUSE_ID[derived]
            ck.check(f"{name}:src-has-cause-const",
                     f"set.zw rd12, wp0, 0x{cid:04x}" in src_l,
                     f"source lacks `set.zw rd12, wp0, 0x{cid:04x}`")

    elif kind == "trap":
        derived = header.get("cause")
        ck.check(f"{name}:cause-cfxtrap", derived == "CFXTRAP",
                 f"trap cause {derived!r} != CFXTRAP")
        ck.check(f"{name}:manifest-cause",
                 rec.get("expected_cause") == "CFXTRAP",
                 f"manifest cause {rec.get('expected_cause')!r}")
        ck.check(f"{name}:src-has-cause-const",
                 f"set.zw rd12, wp0, 0x{CAUSE_ID['CFXTRAP']:04x}" in src_l,
                 "source lacks the CFXTRAP comparison constant")


def check_records(ck: Checker, programs):
    fields_ok = cats_ok = vocab_ok = range_ok = deriv_ok = src_ok = True
    names, sources_all = [], []
    for i, rec in enumerate(programs):
        if not isinstance(rec, dict):
            fields_ok = False
            continue
        for field in REQUIRED_FIELDS:
            if field not in rec:
                fields_ok = False
                print(f"       record #{i} missing field {field!r}")
        name = rec.get("name")
        if isinstance(name, str):
            names.append(name)
        if rec.get("category") not in CATEGORIES:
            cats_ok = False
            print(f"       record #{i} bad category {rec.get('category')!r}")
        cov = rec.get("coverage")
        if not (isinstance(cov, list) and cov):
            vocab_ok = False
            print(f"       record #{i} coverage must be a non-empty list")
        else:
            bad = [x for x in cov if not isinstance(x, str) or x not in COVERAGE_VOCAB]
            if bad:
                vocab_ok = False
                print(f"       record #{i} unknown coverage token(s): {bad}")
        code = rec.get("expected_exit_code")
        if isinstance(code, bool) or not isinstance(code, int) or not (0 <= code <= 0xFF):
            range_ok = False
            print(f"       record #{i} expected_exit_code out of 0x00..0xFF: {code!r}")
        deriv = rec.get("derivation")
        if not isinstance(deriv, str) or not deriv.strip():
            deriv_ok = False
            print(f"       record #{i} empty derivation")
        srcs = rec.get("sources")
        if not (isinstance(srcs, list) and len(srcs) >= 1
                and all(isinstance(s, str) for s in srcs)):
            src_ok = False
            print(f"       record #{i} requires >= 1 string source")
        else:
            sources_all.extend(srcs)

    ck.check("record-fields", fields_ok)
    ck.check("categories-known", cats_ok)
    ck.check("coverage-vocab", vocab_ok)
    ck.check("exit-code-range-0x00-0xff", range_ok)
    ck.check("derivation-nonempty", deriv_ok)
    ck.check("name-unique", len(names) == len(set(names)), "duplicate program names")
    ck.check("sources-present", src_ok)

    missing = [s for s in sources_all if not (VEC_DIR / s).is_file()]
    dup = len(sources_all) != len(set(sources_all))
    ck.check("sources-exist", not missing, f"missing={missing}")
    ck.check("sources-unique", not dup, "a source is listed by more than one program")

    files = sorted(p.name for p in VEC_DIR.glob("*.s"))
    ck.check("files-match", sorted(sources_all) == files,
             f"yaml={sorted(sources_all)} disk={files}")


def check_coverage(ck: Checker, programs):
    facts = {t: False for t in REQUIRED_COVERAGE}
    for rec in programs:
        if not isinstance(rec, dict):
            continue
        for tok in rec.get("coverage", []) or []:
            if tok in facts:
                facts[tok] = True
    for tok in sorted(REQUIRED_COVERAGE):
        ck.check(f"coverage[{tok}]", facts[tok], "required coverage token absent")


def main() -> int:
    ck = Checker()
    if not EXPECTED_PATH.is_file():
        ck.check("expected-file-exists", False, f"missing {EXPECTED_PATH}")
        return 1
    ck.check("expected-file-exists", True)
    try:
        data = yaml.safe_load(EXPECTED_PATH.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        ck.check("yaml-parses", False, f"{exc}")
        return 1
    ck.check("yaml-parses", True)
    ck.check("schema", isinstance(data, dict) and data.get("schema") == SCHEMA,
             f"schema != {SCHEMA!r}")
    programs = data.get("programs") if isinstance(data, dict) else None
    ck.check("programs-nonempty", isinstance(programs, list) and len(programs) > 0,
             "programs must be a non-empty list")
    if not isinstance(programs, list) or not programs:
        print("-" * 60)
        print(f"validate_m5_vectors: FAIL ({len(ck.fails)} failed, {ck.passes} passed)")
        return 1

    services = load_service_table()
    ck.check("contract-service-table", len(services) == 25,
             f"contract-semihosting §3 has {len(services)} services (expected 25)")

    check_records(ck, programs)
    check_coverage(ck, programs)

    for rec in programs:
        if not isinstance(rec, dict) or not isinstance(rec.get("name"), str):
            continue
        srcs = rec.get("sources")
        if not isinstance(srcs, list) or not srcs:
            continue
        path = VEC_DIR / srcs[0]
        if not path.is_file():
            ck.check(f"source-exists[{rec['name']}]", False, f"missing {path}")
            continue
        check_source(ck, rec, path, services)

    print("-" * 60)
    if ck.fails:
        print(f"validate_m5_vectors: FAIL ({len(ck.fails)} failed, {ck.passes} passed)")
        for name in ck.fails:
            print(f"  - {name}")
        return 1
    print(f"validate_m5_vectors: PASS ({ck.passes} checks)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
