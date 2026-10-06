# L3 execution vectors — M4 (multi-TU / multi-section ELF link)

Source IR vectors for the **M4** end-to-end test (IR → codegen per TU → `ld.lld`
→ ELF → QEMU), owned by `TESTCASES-030t` and wired into a gate by `INTEG-016t`.

They live under `tests/llvm/codegen/m4/`, i.e. **the same tree as the M3 L3
vectors**, but use a **separate manifest** (`m4/expected.yaml`).  The M3 driver
(`tools/integ/run_codegen_e2e.py`) reads only `tests/llvm/codegen/expected.yaml`
and never recurses into `m4/`, so these vectors do **not** enter the M3 gate.
This directory is not yet wired into `make check` / `make test-elf` either —
`INTEG-016t` adds that gate.

## Conventions

- A *program* is a set of **translation units** (`.ll` files) listed in the
  `sources:` field of `m4/expected.yaml` (link order).  Every program has
  **>= 2 TUs** — a symbol defined in one TU is called/read from another, which
  is what forces real link-time relocations.
- Every program defines `define i64 @main()`.  `crt0` (`tests/scripts/codegen_crt0.s`,
  linked by `ld.lld`) calls it and writes the returned value to the exit port
  `0xffff_8000_0000`; the **guest exit code is the low byte** of that value
  (ADR-0004 D3).  Every program returns `0x00..0x7F` (the guest partition; the
  `0x80..0xFF` range is reserved for machine faults).
- Programs use only globals + registers: no `alloca`, no `phi`, no aggregates,
  no varargs, no `sret`, no floating point.  This keeps the host-side oracle
  (below) and the M4 codegen boundary both small and auditable.
- Loops are written with the counter in a global so the IR stays straight-line +
  branch; the host interpreter executes exactly the same arithmetic.

## Independent oracle

`expected.yaml`'s `expected_exit_code` values are re-derived on the host from
the **LLVM IR semantics** — 64-bit two's-complement integer arithmetic,
big-endian memory (`contract-abi.md` §1.7), 8-byte pointers, 48-bit effective
addresses.  `tools/testcases/validate_elf_vectors.py` implements a small
interpreter of the IR subset actually used, runs `@main` over all TUs of a
program, and rejects any mismatch.  It **never invokes** `llc`, `ld.lld` or
QEMU (no `subprocess`/`os.system`/`Popen` in the file).

## Relocation coverage

`contract-elf.md` §2–§4 (`ADR-0019`) defines four relocation types.  From an L3
(execution) vector the relevant facts are:

| Reloc | Where it comes from here | What the vector exercises |
|-------|--------------------------|---------------------------|
| `R_DADAO_ABS48` | any global address materialised in `.text` (`set.zw`/`or.w`, 3 wydes) | cross-TU / cross-section addresses (`@seed`, `@acc`, `@ro_tbl`, `@rw_acc`, `@bss_cnt`, `@buf`) |
| `R_DADAO_REL26` | `call` to a symbol **undefined in the current TU** (defined in another TU) | cross-TU direct calls (`lib_mix`, `get_ro`, `pdiff`) |
| `R_DADAO_REL20` | signed compare-branch (`br.n/nn/z/nz/p/np`, riii, `imms18`) | the `icmp slt` loop guard in `multi_section_loop` |
| `R_DADAO_REL14` | equality compare-branch (`br.eq`/`br.ne`, rrii, `imms12`) | the `icmp eq` guard in `multi_tu_call` |

> **Note (measured, not assumed).**  Conditional branches are always intra-TU and
> intra-`.text`, so the assembler resolves them **in place** at assembly time
> (`LLVM-041t`/`LLVM-055t`); they do not become link-time relocations.  What the
> vectors guarantee is that the CodeGen **instruction forms** whose fields the
> `REL20`/`REL14` relocations patch (riii / rrii compare-branches) are executed
> end-to-end.  The actual *relocation* emission for those types is covered by the
> L1 MC vectors (`TESTCASES-029t`) and by `INTEG-016t`.

## Program ↔ coverage ↔ derivation table

| Program | Category | TUs | Sections | Cross-TU | Reloc forms | Exit | Derivation |
|---------|----------|-----|----------|----------|-------------|------|------------|
| `multi_tu_call` | call | `m4_call_lib.ll`, `m4_call_main.ll` | `.text` `.rodata` `.bss` | call `lib_mix` + global `acc` | ABS48, REL26, REL14 | 42 | `lib_mix(20,11)=20+11+11=42`; read back `acc`=42; `42==42` → 42 |
| `multi_section_loop` | memory | `m4_section_data.ll`, `m4_section_main.ll` | `.text` `.rodata` `.data` `.bss` | call `get_ro` + globals `rw_acc`/`bss_cnt` | ABS48, REL26, REL20 | 30 | `acc=2+3+5+7+9=26`; return `26+4=30` |
| `cross_tu_pdiff` | arithmetic | `m4_pdiff_data.ll`, `m4_pdiff_main.ll` | `.text` `.bss` | call `pdiff` + global `buf` | ABS48, REL26 | 126 | `d=10-3=7`; `e=3-10=-7`; `e&127=121`; `7^121`=126 |

`*` Section mapping is the standard LLVM ELF mapping (`constant` → `.rodata`,
non-constant non-zero init → `.data`, non-constant zero init → `.bss`), which
matches the measured M4 section emission in `LLVM-055t`.  The definitive
per-section check is `INTEG-016t`'s `llvm-readobj` assertion.

## Validate

```
python3 tools/testcases/validate_elf_vectors.py
```

Checks schema, per-program `sources`/multi-TU shape, suite coverage
(multi-TU, multi-section, cross-TU call + global, ABS48/REL26/REL20/REL14
forms), and re-derives every `expected_exit_code` with the host oracle.  Exits
non-zero on any mismatch.
