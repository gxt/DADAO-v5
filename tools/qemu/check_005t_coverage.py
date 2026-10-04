#!/usr/bin/env python3
"""Check QEMU-005t RD integer semantics coverage by reading translate.c.

Verifies that:
1. Every insn in the ISA vector files has a corresponding trans_* function
2. Implemented insns' trans_* functions contain real TCG (not just ILLI stubs)
3. Range-external instructions remain as ILLI stubs

Usage: python3 tools/qemu/check_005t_coverage.py
"""

import re
import sys
import os
import yaml

# Map vector file names to paths
VECTOR_FILES = {
    "reg-arith.yaml": "tests/vectors/isa/reg-arith.yaml",
    "reg-shift-extend.yaml": "tests/vectors/isa/reg-shift-extend.yaml",
    "reg-logic.yaml": "tests/vectors/isa/reg-logic.yaml",
    "reg-imm-block.yaml": "tests/vectors/isa/reg-imm-block.yaml",
    "reg-compare.yaml": "tests/vectors/isa/reg-compare.yaml",
    "reg-cond-assign.yaml": "tests/vectors/isa/reg-cond-assign.yaml",
}

# Instructions that should remain ILLI (not in 005t scope)
ILLI_INSTRUCTIONS = {
    # RF conditional assign (scope: fp)
    "cs.n_rrrr_rf", "cs.z_rrrr_rf", "cs.p_rrrr_rf", "cs.eq_rrrr_rf", "cs.ne_rrrr_rf",
    # RF immediate set (scope: fp)
    "set.w_rwii_rf",
}

# Instructions that should have real TCG (non-ILLI) implementations
IMPLEMENTED_INSTRUCTIONS = {
    # reg-arith (rd forms)
    "add.uo_rrrr_rd", "add.so_rrrr_rd", "sub.uo_rrrr_rd", "sub.so_rrrr_rd",
    "add.ub_orrr_rd", "add.sb_orrr_rd", "add.uw_orrr_rd", "add.sw_orrr_rd",
    "add.ut_orrr_rd", "add.st_orrr_rd",
    "sub.ub_orrr_rd", "sub.sb_orrr_rd", "sub.uw_orrr_rd", "sub.sw_orrr_rd",
    "sub.ut_orrr_rd", "sub.st_orrr_rd",
    "add.si_riii_rd",
    "mul.uo_rrrr_rd", "mul.so_rrrr_rd",
    "mul.ub_orrr_rd", "mul.sb_orrr_rd", "mul.uw_orrr_rd", "mul.sw_orrr_rd",
    "mul.ut_orrr_rd", "mul.st_orrr_rd",
    "div.ub_orrr_rd", "div.sb_orrr_rd", "div.uw_orrr_rd", "div.sw_orrr_rd",
    "div.ut_orrr_rd", "div.st_orrr_rd", "div.uo_orrr_rd", "div.so_orrr_rd",
    "rem.ub_orrr_rd", "rem.sb_orrr_rd", "rem.uw_orrr_rd", "rem.sw_orrr_rd",
    "rem.ut_orrr_rd", "rem.st_orrr_rd", "rem.uo_orrr_rd", "rem.so_orrr_rd",
    # reg-compare
    "cmp.ui_rrii_rd", "cmp.si_rrii_rd",
    "cmp.ub_orrr_rd", "cmp.sb_orrr_rd", "cmp.uw_orrr_rd", "cmp.sw_orrr_rd",
    "cmp.ut_orrr_rd", "cmp.st_orrr_rd", "cmp.uo_orrr_rd", "cmp.so_orrr_rd",
    # reg-logic
    "and.o_orrr_rd", "or.o_orrr_rd", "xor.o_orrr_rd", "xnor.o_orrr_rd",
    # SPEC-069t: narrow logic (and/or/xor/xnor .t/.w/.b) deleted
    # reg-shift-extend
    "shl.uo_orri_rd", "shl.uo_orrr_rd", "shr.uo_orri_rd", "shr.uo_orrr_rd", "shr.so_orri_rd", "shr.so_orrr_rd",
    "shl.ut_orri_rd", "shl.ut_orrr_rd", "shr.ut_orri_rd", "shr.ut_orrr_rd", "shr.st_orri_rd", "shr.st_orrr_rd",
    "shl.uw_orri_rd", "shl.uw_orrr_rd", "shr.uw_orri_rd", "shr.uw_orrr_rd", "shr.sw_orri_rd", "shr.sw_orrr_rd",
    "shl.ub_orri_rd", "shl.ub_orrr_rd", "shr.ub_orri_rd", "shr.ub_orrr_rd", "shr.sb_orri_rd", "shr.sb_orrr_rd",
    "ext.uo_orri_rd", "ext.uo_orrr_rd", "ext.so_orri_rd", "ext.so_orrr_rd",
    # SPEC-069t: narrow ext (ext.ut/st/uw/sw/ub/sb) deleted
    # reg-cond-assign
    "cs.n_rrrr_rd", "cs.z_rrrr_rd", "cs.p_rrrr_rd", "cs.eq_rrrr_rd", "cs.ne_rrrr_rd",
    # reg-imm-block (rd forms)
    "set.zw_rwii_rd", "set.ow_rwii_rd", "or.w_rwii_rd", "andn.w_rwii_rd",
    "rd2rd_orri_rd",
    # reg-imm-block (rb/ra forms — real TCG in QEMU)
    "add.si_riii_rb", "add.o_orrr_bbd", "sub.o_orrr_bbd",
    "cmp.uo_orrr_dbb", "or.w_rwii_rb", "andn.w_rwii_rb", "set.zw_rwii_rb",
    "ra2rd_orri_ra", "rb2rb_orri_rb", "rb2rd_orri_rb", "rd2ra_orri_ra", "rd2rb_orri_rb",
}


def extract_insns_from_vector(filepath):
    """Extract all unique insn names from a vector YAML file."""
    if not os.path.exists(filepath):
        print(f"  WARNING: {filepath} not found")
        return set()
    with open(filepath) as f:
        data = yaml.safe_load(f)
    insns = set()
    if isinstance(data, list):
        for entry in data:
            if isinstance(entry, dict) and "id" in entry:
                insns.add(entry["id"])
    elif isinstance(data, dict):
        for entry in data.get("vectors", data.get("tests", [])):
            if isinstance(entry, dict) and "id" in entry:
                insns.add(entry["id"])
    return insns


def insn_to_trans_names(insn):
    """Convert insn name (e.g. 'ext.uo') to possible trans_* function names.
    Some insns have both orrr and orri forms (e.g. ext.uo -> trans_ext_uo_orrr, trans_ext_uo_orri).
    Returns list of possible trans_* names."""
    # Replace dots and dashes with underscores
    name = insn.replace(".", "_").replace("-", "_")
    base = f"trans_{name}"

    # For shift/extend operations, try orrr and orri suffixes
    prefixes_needing_suffix = [
        "trans_ext_", "trans_shl_", "trans_shr_",
    ]
    for prefix in prefixes_needing_suffix:
        if base.startswith(prefix):
            return [f"{base}_orrr", f"{base}_orri", base]

    return [base]


def parse_trans_functions(translate_c_path):
    """Parse translate.c and its included .c.inc files to extract trans_* function bodies.
    Returns dict: trans_name -> (body_text, is_illi_stub)"""
    # Collect all source content: translate.c + insn_trans/*.c.inc
    insns_trans_dir = os.path.join(os.path.dirname(translate_c_path), "insn_trans")
    sources = ""
    if os.path.exists(insns_trans_dir):
        for fn in sorted(os.listdir(insns_trans_dir)):
            if fn.endswith(".c.inc"):
                with open(os.path.join(insns_trans_dir, fn)) as f:
                    sources += f.read() + "\n"
    with open(translate_c_path) as f:
        sources += f.read()

    # Find all trans_* functions and their bodies
    # Pattern: static bool trans_XXX(...) { ... }
    pattern = re.compile(
        r'(static\s+bool\s+(trans_\w+)\s*\([^)]*\)\s*\{)(.*?)\n\}',
        re.DOTALL
    )

    functions = {}
    for match in pattern.finditer(sources):
        full_header = match.group(1)
        trans_name = match.group(2)
        body = match.group(3)

        # Check if this is an ILLI stub (body is just gen_exception_illegal + return true)
        # Strip whitespace and comments for analysis
        body_stripped = re.sub(r'/\*.*?\*/', '', body, flags=re.DOTALL)  # remove comments
        body_stripped = re.sub(r'//.*$', '', body_stripped, flags=re.MULTILINE)  # remove line comments
        body_stripped = body_stripped.strip()

        # An ILLI stub has: gen_exception_illegal(ctx); return true;
        # Possibly with some whitespace/newlines
        is_illi = bool(re.match(
            r'gen_exception_illegal\s*\(\s*ctx\s*\)\s*;\s*return\s+true\s*;',
            body_stripped
        ))

        functions[trans_name] = (body, is_illi)

    return functions


def main():
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    os.chdir(repo_root)

    print("=" * 70)
    print("QEMU-005t RD Integer Semantics Coverage Check (code-level)")
    print("=" * 70)

    # Find translate.c
    translate_c = ".work/source/qemu/target/dadao/translate.c"
    if not os.path.exists(translate_c):
        print(f"ERROR: {translate_c} not found")
        return 1

    # Parse trans_* functions from translate.c
    trans_funcs = parse_trans_functions(translate_c)
    print(f"\nFound {len(trans_funcs)} trans_* functions in translate.c")

    # Collect all insns from vector files
    all_vector_insns = set()
    for name, path in VECTOR_FILES.items():
        insns = extract_insns_from_vector(path)
        print(f"\n{name}: {len(insns)} insns")
        for i in sorted(insns):
            print(f"  {i}")
        all_vector_insns.update(insns)

    print(f"\n{'=' * 70}")
    print(f"Total unique insns across all vector files: {len(all_vector_insns)}")

    # Check each insn
    errors = []
    implemented_ok = 0
    illi_ok = 0

    for insn in sorted(all_vector_insns):
        trans_names = insn_to_trans_names(insn)

        if insn in IMPLEMENTED_INSTRUCTIONS:
            # Should have real TCG implementation - check at least one trans_* exists and is non-ILLI
            found = False
            for trans_name in trans_names:
                if trans_name in trans_funcs:
                    body, is_illi = trans_funcs[trans_name]
                    if is_illi:
                        errors.append(f"  STUB: {insn} -> {trans_name}() is still an ILLI stub")
                    else:
                        implemented_ok += 1
                    found = True
                    break
            if not found:
                errors.append(f"  MISSING: {insn} -> none of {trans_names} found in translate.c")

        elif insn in ILLI_INSTRUCTIONS:
            # Should remain ILLI stub
            found = False
            for trans_name in trans_names:
                if trans_name in trans_funcs:
                    body, is_illi = trans_funcs[trans_name]
                    if not is_illi:
                        if insn == "swym":
                            illi_ok += 1
                        else:
                            errors.append(f"  CHANGED: {insn} -> {trans_name}() should be ILLI but has real TCG")
                    else:
                        illi_ok += 1
                    found = True
                    break
            if not found:
                # Some insns may not have a trans_* at all (handled by UNDI)
                illi_ok += 1
        else:
            errors.append(f"  UNKNOWN: {insn} not in either implemented or ILLI set")

    print(f"\n{'=' * 70}")
    print("Coverage Results:")
    print(f"  Implemented (non-ILLI, verified in translate.c): {implemented_ok}")
    print(f"  Expected ILLI (verified stubs):                  {illi_ok}")
    print(f"  Errors:                                          {len(errors)}")

    if errors:
        print(f"\n  ERRORS:")
        for e in errors:
            print(f"    {e}")
        return 1

    print(f"\n{'=' * 70}")
    print("PASS: All vector file insns verified against translate.c")
    return 0


if __name__ == "__main__":
    sys.exit(main())
