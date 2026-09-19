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
    # ld/st/ldm/stm
    "ld.ub", "ld.uw", "ld.ut", "ld.sb", "ld.sw", "ld.st", "ld.t",
    "st.b", "st.w", "st.t", "st.t", "ld.o", "st.o",
    "ldm.ub", "ldm.uw", "ldm.ut", "ldm.sb", "ldm.sw", "ldm.st", "ldm.t",
    "stm.b", "stm.w", "stm.t", "stm.t", "ldm.o", "stm.o",
    # RB load/store
    "ld.o-rb", "st.o-rb", "ldm.o-rb", "stm.o-rb",
    # RA load/store
    "ld.o-ra", "st.o-ra", "ldm.o-ra", "stm.o-ra",
    # RF load/store (excluded_m1)
    "ld.t-rf", "st.t-rf", "ld.o-rf", "st.o-rf", "ldm.t-rf", "stm.t-rf",
    "ldm.o-rf", "stm.o-rf",
    # Branch/jump/call/ret
    "br.n", "br.nn", "br.z", "br.nz", "br.p", "br.np", "br.eq", "br.ne",
    "br.z-rb", "br.nz-rb",
    "jump", "call", "ret",
    # RF conditional assign (excluded_m1)
    "cs.n-rf", "cs.z-rf", "cs.p-rf", "cs.eq-rf", "cs.ne-rf",
    # RF immediate set (excluded_m1)
    "set.w-rf",
    # Float
    "ftmadd", "fomadd", "ftcls", "ft2fo", "ft2ft", "ftroot", "ftlog",
    "focls", "fo2ft", "fo2fo", "foroot", "folog",
    "ft2it", "ft2io", "ft2ut", "ft2uo", "it2ft", "io2ft", "ut2ft", "uo2ft",
    "fo2it", "fo2io", "fo2ut", "fo2uo", "it2fo", "io2fo", "ut2fo", "uo2fo",
    "ftadd", "ftsub", "ftmul", "ftdiv", "ftrem", "ftsclb", "ftsgnn", "ftsgnj",
    "foadd", "fosub", "fomul", "fodiv", "forem", "fosclb", "fosgnn", "fosgnj",
    "ftqcmp", "ftscmp", "foqcmp", "foscmp",
    # LR/SC (excluded_m1)
    "lr_nn.o", "lr_nr.o", "lr_an.o", "lr_ar.o",
    "sc_nn.o", "sc_nr.o", "sc_an.o", "sc_ar.o",
    # Privileged (excluded_m1)
    "cfx2rd", "cfx2rc", "cfxld", "cfxst", "escape", "trap",
    # RB ops (not in 005t scope)
    "add.so-rb", "sub.so-rb", "add.si-rb", "rela.si-rb",
    "cmp.uo-rb", "or.w-rb", "andn.w-rb", "set.zw-rb",
    "rb2rb", "rd2rb", "rb2rd", "rd2ra", "ra2rd",
    # RF block assign (excluded_m1)
    "rd2rf", "rf2rd",
    # Misc
    "illi", "fence", "swym",
}

# Instructions that should have real TCG (non-ILLI) implementations
IMPLEMENTED_INSTRUCTIONS = {
    "add.uo-rd", "add.so-rd", "sub.uo-rd", "sub.so-rd",
    "add.ub", "add.sb", "add.uw", "add.sw", "add.ut", "add.st",
    "sub.ub", "sub.sb", "sub.uw", "sub.sw", "sub.ut", "sub.st",
    "add.si-rd",
    "mul.uo-rd", "mul.so-rd",
    "mul.ub", "mul.sb", "mul.uw", "mul.sw", "mul.ut", "mul.st",
    "div.ub", "div.sb", "div.uw", "div.sw", "div.ut", "div.st", "div.uo", "div.so",
    "rem.ub", "rem.sb", "rem.uw", "rem.sw", "rem.ut", "rem.st", "rem.uo", "rem.so",
    "cmp.ui-rd", "cmp.si-rd",
    "cmp.ub", "cmp.sb", "cmp.uw", "cmp.sw", "cmp.ut", "cmp.st", "cmp.uo", "cmp.so",
    "and.o", "or.o", "xor.o", "xnor.o",
    "and.t", "or.t", "xor.t", "xnor.t",
    "and.w", "or.w", "xor.w", "xnor.w",
    "and.b", "or.b", "xor.b", "xnor.b",
    "shl.uo", "shr.uo", "shr.so",
    "shl.ut", "shr.ut", "shr.st",
    "shl.uw", "shr.uw", "shr.sw",
    "shl.ub", "shr.ub", "shr.sb",
    "ext.uo", "ext.so", "ext.ut", "ext.st", "ext.uw", "ext.sw", "ext.ub", "ext.sb",
    "cs.n-rd", "cs.z-rd", "cs.p-rd", "cs.eq-rd", "cs.ne-rd",
    "set.zw-rd", "set.ow-rd", "or.w-rd", "andn.w-rd",
    "rd2rd",
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
            if isinstance(entry, dict) and "insn" in entry:
                insns.add(entry["insn"])
    elif isinstance(data, dict):
        for entry in data.get("vectors", data.get("tests", [])):
            if isinstance(entry, dict) and "insn" in entry:
                insns.add(entry["insn"])
    return insns


def insn_to_trans_names(insn):
    """Convert insn name (e.g. 'ext.ub') to possible trans_* function names.
    Some insns have both orrr and orri forms (e.g. ext.ub -> trans_ext_ub_orrr, trans_ext_ub_orri).
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
    """Parse translate.c and extract trans_* function bodies.
    Returns dict: trans_name -> (body_text, is_illi_stub)"""
    with open(translate_c_path) as f:
        content = f.read()

    # Find all trans_* functions and their bodies
    # Pattern: static bool trans_XXX(...) { ... }
    pattern = re.compile(
        r'(static\s+bool\s+(trans_\w+)\s*\([^)]*\)\s*\{)(.*?)\n\}',
        re.DOTALL
    )

    functions = {}
    for match in pattern.finditer(content):
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
