#!/usr/bin/env python3
"""Cross-check the DADAO syscall ABI facts that must not drift.

The facts, each derived from a different artefact:

1. **number table vs the locked snapshot** -- ``linux-user/dadao/syscall.tbl``
   must be byte-identical to the qemu tree's ``linux-user/riscv/syscall.tbl``,
   whose sha256 the contract pins (contract-syscall.md §1.2).  The expected
   digest is *read from the contract*, not from the tree.
2. **argument routing, four carriers** -- the guest stub decides where each
   argument goes (data bank rd16+ / address bank rb16+) from the syscall
   NUMBER, and every host must rebuild the positional list with the SAME mask:

   * musl ``arch/dadao/syscall_arch.h:__dadao_argmask`` (the C path),
   * QEMU ``linux-user/dadao/cpu_loop.c:dadao_argmask`` (the host path),
   * gem5 ``src/arch/dadao/se_workload.cc:dadaoArgmask`` (the SE path),
   * musl ``src/thread/dadao/syscall_cp.s`` (the cancellable path).

   The three tables must agree number for number; the asm dispatch must agree
   with them on every number it dispatches, and each of its blocks must move
   exactly the arguments its mask says.  The gem5 table is a *copy*, so a
   syscall added or re-masked on one side only fails this gate instead of
   reading the neighbouring bank; the only rows allowed beyond musl's are the
   two documented gem5-only numbers below.
3. **gem5 dispatch takes arguments through the table, never by hand** -- every
   ``case Sys*`` in ``SEWorkload::syscall`` must resolve to a table row, and no
   arm may read a bank directly: the only ``tc->getReg(rd(15))`` allowed is the
   syscall number itself.  A hand-written bank choice is exactly the defect
   GEM5-023t's fcntl arm hit.
4. **table completeness** -- every syscall name this libc can issue (the SYS_*
   names in musl's sources ∩ the names the port's ``bits/syscall.h.in``
   defines ∩ the locked number table) must have an entry.  An absent number
   silently falls back to "everything in RD", which is the defect ISS-249
   fixed; a number added to musl's sources later must not slip back in.
5. **AUDIT_ARCH_DADAO** -- preprocessed out of
   ``linux-user/dadao/target_syscall.h`` and compared with the contract's
   ruling (EM_DADAO | AUDIT_ARCH_64BIT, no AUDIT_ARCH_LE bit).
6. **routing covers six slots** -- masks are 6 bits wide and the C stub
   declares both last slots (rd21 / rb21); a seventh-argument syscall would
   otherwise be silently truncated.

Sources: the live component trees under ``.work/source/`` when they exist,
otherwise the committed patch set under ``components/`` -- so the gate also
runs on a fresh clone that has never executed ``make prepare`` (checks 1-3 and
6 work from patches; check 4 needs the musl sources and check 5 the qemu ones,
and either is reported SKIP).

Exit status: 0 only when every check passes.
"""
from __future__ import annotations

import hashlib
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
QEMU = ROOT / ".work" / "source" / "qemu"
MUSL = ROOT / ".work" / "source" / "musl"
CONTRACT = ROOT / ".tao" / "contracts" / "contract-syscall.md"

QEMU_PATCHES = ROOT / "components" / "qemu" / "patches"
MUSL_PATCHES = ROOT / "components" / "musl" / "patches"
GEM5 = ROOT / ".work" / "source" / "gem5"
GEM5_PATCHES = ROOT / "components" / "gem5" / "patches"

ABIS = {"common", "64", "riscv", "rlimit", "memfd_secret"}

# Rows the gem5 table carries that musl's sources never name: musl's table
# omits tgkill(2) altogether (all three arguments are scalars, so the default
# mask 0 is right) and has no __NR_time at all (musl routes time() through
# clock_gettime; gem5 still answers the legacy number for a guest that calls
# it directly).  Listed here so a *new* extra row is a gate failure, not a
# silent fork of the protocol.
GEM5_ONLY_MASKS = {131: 0x00, 1062: 0x01}

GUEST_TABLE = ("arch/dadao/syscall_arch.h", MUSL, MUSL_PATCHES)
HOST_TABLE = ("linux-user/dadao/cpu_loop.c", QEMU, QEMU_PATCHES)
SE_TABLE = ("src/arch/dadao/se_workload.cc", GEM5, GEM5_PATCHES)
GUEST_CP = ("src/thread/dadao/syscall_cp.s", MUSL, MUSL_PATCHES)
SYSCALL_TBL = ("linux-user/dadao/syscall.tbl", QEMU, QEMU_PATCHES)
TARGET_SYSCALL_H = QEMU / "linux-user" / "dadao" / "target_syscall.h"
PORT_NR_H = ("arch/dadao/bits/syscall.h.in", MUSL, MUSL_PATCHES)

results: list[tuple[str, str, str, bool]] = []
skipped: list[str] = []


def check(name: str, expected, actual, ok: bool | None = None) -> None:
    if ok is None:
        ok = expected == actual
    results.append((name, str(expected), str(actual), bool(ok)))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: expected={expected} actual={actual}")


def skip(name: str, why: str) -> None:
    skipped.append(f"{name} ({why})")
    print(f"[SKIP] {name}: {why}")


def patch_added_lines(patch: Path) -> str:
    """Reconstruct a new file from its `new file mode` diff."""
    out = []
    for line in patch.read_text().splitlines():
        if line.startswith("+++") or line.startswith("---"):
            continue
        if line.startswith("+"):
            out.append(line[1:])
    return "\n".join(out) + "\n"


def source(spec: tuple[str, Path, Path]) -> tuple[str, str]:
    """(text, origin) for a component file: the live tree, else its patch."""
    rel, tree_root, patch_root = spec
    live = tree_root / rel
    if live.exists():
        return live.read_text(), "tree"
    patch = patch_root / (rel + ".patch")
    if patch.exists():
        return patch_added_lines(patch), "patch"
    raise SystemExit(f"cannot read {rel}: neither {live} nor {patch} exists")


def contract_sha256(path: str) -> str:
    for line in CONTRACT.read_text().splitlines():
        if path in line and "sha256" not in line:
            for cell in (c.strip().strip("`") for c in line.split("|")):
                if re.fullmatch(r"[0-9a-f]{64}", cell):
                    return cell
    raise SystemExit(f"cannot find the pinned sha256 of {path} in the contract")


def tbl_numbers(text: str) -> dict[str, int]:
    nums: dict[str, int] = {}
    for line in text.splitlines():
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 3 or parts[1] not in ABIS:
            continue
        nums[parts[2]] = int(parts[0], 0)
    return nums


def parse_c_table(text: str, prefix: str) -> dict[str, int]:
    """name -> mask out of a switch of `case <prefix><name>:` + `return 0xNN;`."""
    table: dict[str, int] = {}
    for block in re.finditer(
            r"((?:[ \t]*case[ \t]+" + prefix + r"\w+[ \t]*:[^\n]*\n)+)"
            r"[ \t]*return[ \t]+(0x[0-9A-Fa-f]+|\d+);", text):
        mask = int(block.group(2), 0)
        for name in re.findall(prefix + r"(\w+)[ \t]*:", block.group(1)):
            if name in table:
                check(f"routing table: duplicate case {prefix}{name}",
                      "unique", "duplicate")
            table[name] = mask
    return table


CP_DISPATCH_RE = re.compile(
    r"set\.zw\s+rd9,\s+wp0,\s+(0x[0-9A-Fa-f]+|\d+)\s*\n"
    r"\s*br\.eq\s+\{rd16, rd9\}\?,\s*\[rb0,\s*\.Lm([0-9a-fA-F]+)\]")
CP_LABEL_RE = re.compile(r"^\.Lm([0-9a-fA-F]+):$", re.M)


def parse_cp_asm(text: str) -> tuple[dict[int, int], dict[int, tuple[int, int]]]:
    """(number -> mask, mask -> (rd2rb count, rd2rd count)) out of the stub."""
    dispatch = {int(m.group(1), 0): int(m.group(2), 16)
                for m in CP_DISPATCH_RE.finditer(text)}
    blocks: dict[int, tuple[int, int]] = {}
    marks = list(CP_LABEL_RE.finditer(text))
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        body = text[m.end():end]
        blocks[int(m.group(1), 16)] = (body.count("rd2rb"), body.count("rd2rd"))
    return dispatch, blocks


def musl_issue_names() -> set[str]:
    """Every syscall name musl's sources can name."""
    names: set[str] = set()
    direct = re.compile(r"\bSYS_([a-z0-9_]+)")
    sock = re.compile(r"\b_*socketcall(?:_cp)?\(\s*([a-z0-9_]+)")
    for d in ("src", "arch/dadao", "ldso"):
        for p in (MUSL / d).rglob("*"):
            if p.suffix not in (".c", ".h", ".in", ".s", ".S"):
                continue
            t = p.read_text(errors="replace")
            names.update(direct.findall(t))
            names.update(n for n in sock.findall(t) if n != "nm")
    names.discard("")
    return names


def port_nr_names(text: str) -> set[str]:
    return set(re.findall(r"^#define\s+__NR_([a-z0-9_]+)\s", text, re.M))


SE_CASE_RE = re.compile(r"case (\d+): /\* (\w+)")
SE_RETURN_RE = re.compile(r"^[ \t]*return (0x[0-9a-fA-F]+);")
SE_DISPATCH_RE = re.compile(r"^      case (Sys\w+):", re.M)
SE_BANK_READ_RE = re.compile(r"getReg\((rd|rb)\((\d+)\)\)")
# tc->getReg(rd(15)) is the syscall number itself; every *argument* must come
# through SyscallArgs, so any other direct bank read in the dispatch is the
# hand-written bank choice this gate exists to forbid.
SE_ALLOWED_BANK_READS = {("rd", 15)}


def parse_se_table(text: str) -> dict[int, tuple[str, int]]:
    """number -> (comment name, mask) out of gem5's dadaoArgmask()."""
    start = text.find("dadaoArgmask(uint64_t nr)")
    if start < 0:
        raise SystemExit("cannot find dadaoArgmask() in the gem5 SE workload")
    table: dict[int, tuple[str, int]] = {}
    pending: list[tuple[int, str]] = []
    for line in text[start:].splitlines():
        m = SE_CASE_RE.search(line)
        if m:
            pending.append((int(m.group(1)), m.group(2)))
            continue
        m = SE_RETURN_RE.match(line)
        if m and pending:
            mask = int(m.group(1), 0)
            for nr, name in pending:
                if nr in table:
                    check(f"gem5 routing table: duplicate case {nr}",
                          "unique", "duplicate")
                table[nr] = (name, mask)
            pending = []
    return table


def parse_se_dispatch(text: str) -> tuple[dict[str, int | None], str]:
    """(case name -> number constant, the dispatch body)."""
    start = text.find("SEWorkload::syscall(ThreadContext *tc)")
    if start < 0:
        raise SystemExit("cannot find SEWorkload::syscall() in the gem5 tree")
    body = text[start:]
    constants = {name: int(value, 0) for name, value in
                 re.findall(r"constexpr uint64_t (Sys\w+) = (\d+);", text)}
    names = SE_DISPATCH_RE.findall(body)
    return {name: constants.get(name) for name in names}, body


def preprocess_audit_arch() -> int:
    """Evaluate AUDIT_ARCH_DADAO with the host C compiler."""
    src = (f'#include <stdio.h>\n#include "{TARGET_SYSCALL_H}"\n'
           'int main(void) { printf("%x\\n", (unsigned)AUDIT_ARCH_DADAO); return 0; }\n')
    with tempfile.TemporaryDirectory() as tmp:
        f = Path(tmp) / "audit.c"
        exe = Path(tmp) / "audit"
        f.write_text(src)
        r = subprocess.run(["cc", "-I", str(QEMU), str(f), "-o", str(exe)],
                           capture_output=True, text=True)
        if r.returncode != 0:
            raise SystemExit(f"cc failed: {r.stderr}")
        out = subprocess.run([str(exe)], capture_output=True, text=True)
    return int(out.stdout.strip(), 16)


def main() -> int:
    tbl_text, tbl_origin = source(SYSCALL_TBL)
    print(f"# source mode: number table from {tbl_origin}")

    # 1. number table
    pinned = contract_sha256("linux-user/riscv/syscall.tbl")
    actual = hashlib.sha256(tbl_text.encode()).hexdigest()
    check("number table == contract §1.2 snapshot", pinned, actual)
    nums = tbl_numbers(tbl_text)

    # 2. routing tables
    guest_text, guest_origin = source(GUEST_TABLE)
    host_text, host_origin = source(HOST_TABLE)
    cp_text, cp_origin = source(GUEST_CP)
    print(f"# routing carriers: guest={guest_origin} host={host_origin} "
          f"asm={cp_origin}")

    guest = parse_c_table(guest_text, "SYS_")
    host = parse_c_table(host_text, "TARGET_NR_")
    check("guest routing table non-empty", "True", str(bool(guest)))
    check("host routing table non-empty", "True", str(bool(host)))
    check("routing: same number set (host vs guest stub)",
          sorted(guest), sorted(host))
    mismatch = [n for n in sorted(set(host) & set(guest))
                if guest[n] != host[n]]
    for name in mismatch:
        print(f"[FAIL] routing mask {name}: guest={guest[name]:#04x} "
              f"host={host[name]:#04x}")
    check("routing: every shared entry has the same mask",
          f"{len(set(host) & set(guest))} equal", f"{len(mismatch)} unequal",
          not mismatch)
    bad_width = [n for n, m in guest.items() if m < 0 or m > 0x3f]
    check("routing: masks are 6 bits wide (max 6 arguments)",
          "[]", str(bad_width))
    check("routing: the C stub declares the last slot pair (rd21/rb21)",
          "rd21 rb21", "rd21 rb21" if ("rd21" in guest_text and
                                       "rb21" in guest_text) else "missing")

    # 3. cancellable stub
    dispatch, blocks = parse_cp_asm(cp_text)
    check("routing: cancellable stub dispatch non-empty", "True",
          str(bool(dispatch)))
    unknown = [nr for nr in dispatch if not any(v == nr for v in nums.values())]
    for nr in sorted(unknown):
        check(f"routing: cp asm number {nr} exists in the locked table",
              "a name", "no name")
    for nr, mask in sorted(dispatch.items()):
        name = next((n for n, v in nums.items() if v == nr), None)
        if name is None:
            check(f"routing: cp asm number {nr} exists in the locked table",
                  "a name", "no name")
            continue
        if name not in guest:
            check(f"routing: cp asm number {nr} ({name}) is in the guest table",
                  "present", "absent")
            continue
        check(f"routing: cp asm mask {name} ({nr}) == guest table",
              f"{guest[name]:#04x}", f"{mask:#04x}")
    for mask in sorted(set(dispatch.values())):
        if mask not in blocks:
            check(f"routing: cp asm block for mask {mask:#04x}", "present",
                  "absent")
            continue
        ptrs = bin(mask).count("1")
        check(f"routing: cp asm block {mask:#04x} moves {ptrs} rb + "
              f"{6 - ptrs} rd", f"({ptrs}, {6 - ptrs})", str(blocks[mask]))
    unused = sorted(set(blocks) - set(dispatch.values()))
    check("routing: cp asm has no unused mask block", "[]", str(unused))

    # 3b. gem5 SE carrier -- the same table, and a dispatch that uses it
    se_text, se_origin = source(SE_TABLE)
    print(f"# gem5 SE carrier: {se_origin}")
    se = parse_se_table(se_text)
    check("gem5 routing table non-empty", "True", str(bool(se)))
    unmapped = sorted(set(guest) - set(nums))
    check("routing: every musl table name is in the locked number table",
          "[]", str(unmapped))
    musl_by_nr = {nums[name]: mask for name, mask in guest.items()
                  if name in nums}
    expected = dict(musl_by_nr)
    expected.update(GEM5_ONLY_MASKS)
    check("gem5 routing: same number set as musl (+ documented extras)",
          sorted(expected), sorted(se))
    wrong = [nr for nr in sorted(set(se) & set(expected))
             if se[nr][1] != expected[nr]]
    for nr in wrong:
        print(f"[FAIL] gem5 routing mask {se[nr][0]} ({nr}): "
              f"musl={expected[nr]:#04x} gem5={se[nr][1]:#04x}")
    check("gem5 routing: every shared entry has the same mask",
          f"{len(set(se) & set(expected))} equal", f"{len(wrong)} unequal",
          not wrong)
    name_by_nr: dict[int, str] = {}
    for name, nr in nums.items():
        name_by_nr.setdefault(nr, name)
    # A right mask attached to the wrong comment is a stale copy, not a right
    # row: the comment must name the syscall the locked table gives that
    # number.
    misnamed = [f"{nr}: {name} != {name_by_nr[nr]}"
                for nr, (name, _mask) in sorted(se.items())
                if nr in musl_by_nr and name != name_by_nr[nr]]
    check("gem5 routing: every row comment names its number", "[]",
          str(misnamed))
    extras = sorted(set(se) - set(musl_by_nr))
    check("gem5 routing: rows beyond musl's are exactly the documented pair",
          sorted(GEM5_ONLY_MASKS), extras)
    extra_names = sorted(se[nr][0] for nr in extras if nr in se)
    check("gem5 routing: the extra rows are named", ["tgkill", "time"],
          extra_names)

    dispatch, se_body = parse_se_dispatch(se_text)
    check("gem5 dispatch: case list non-empty", "True", str(bool(dispatch)))
    unbound = sorted(name for name, nr in dispatch.items() if nr is None)
    check("gem5 dispatch: every case has a number constant", "[]",
          str(unbound))
    missing = sorted(f"{name} ({nr})" for name, nr in dispatch.items()
                     if nr is not None and nr not in se)
    for item in missing:
        print(f"[FAIL] gem5 dispatch case without a routing row: {item}")
    check("gem5 dispatch: every dispatched number has a routing row", "[]",
          str(missing))
    direct = sorted({f"{bank}({idx})" for bank, idx in
                     SE_BANK_READ_RE.findall(se_body)
                     if (bank, int(idx)) not in SE_ALLOWED_BANK_READS})
    for item in direct:
        print(f"[FAIL] gem5 dispatch reads a bank by hand: tc->getReg({item})")
    check("gem5 dispatch: no arm reads an argument bank by hand", "[]",
          str(direct))

    # 4. completeness -- needs musl's sources
    if (MUSL / "src").exists():
        port_text, _ = source(PORT_NR_H)
        issue = musl_issue_names() & port_nr_names(port_text) & set(nums)
        check("routing: every syscall musl can issue has an entry",
              sorted(issue), sorted(guest))
    else:
        skip("routing completeness", "musl sources not checked out")

    # 5. audit arch
    if TARGET_SYSCALL_H.exists():
        value = preprocess_audit_arch()
        check("AUDIT_ARCH_DADAO == EM_DADAO | AUDIT_ARCH_64BIT",
              hex(0x0DA0 | 0x80000000), hex(value))
        check("AUDIT_ARCH_DADAO has no AUDIT_ARCH_LE bit", 0,
              value & 0x40000000)
    else:
        skip("AUDIT_ARCH_DADAO", "qemu sources not checked out")

    bad = [r for r in results if not r[3]]
    print(f"\n{len(results) - len(bad)}/{len(results)} checks passed"
          + (f"; {len(skipped)} skipped" if skipped else ""))
    for item in skipped:
        print(f"  SKIP {item}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
