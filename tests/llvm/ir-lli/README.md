# Upstream IR ↔ `lli` value-level differential corpus (M6)

Driver: `tools/testcases/diff_ir_lli.py` (task `TESTCASES-038t`).

This directory holds the **manifest** that drives a *value-level* differential
check of the same LLVM IR through two independent back-ends:

| side | tool | pipeline |
|------|------|----------|
| host (X86) | `.dadao/host-tools/bin/lli` (upstream LLVM, X86 JIT) | `lli <ir>` |
| target (DADAO) | `.dadao/cross-toolchain/bin/{llc,llvm-mc,llvm-objcopy}` + QEMU | `llc -march=dadao` → `llvm-mc` → crt0 → QEMU |

## Value channel (frozen, directly comparable)

The observable value is the **process exit code = low byte of the `i64` value
returned by `@main`**:

- host: `lli` runs `@main` natively and the OS truncates its `i64` return to the
  low byte (verified: `ret i64 300` ⇒ exit `44` = `300 & 0xFF`);
- target: the startup stub `tests/scripts/codegen_crt0.s` calls `@main`, then
  reports the returned value (`rd8`, the M6 ABI return register) through the
  semihosting `SYS_EXIT` service and QEMU propagates it to the host `$?` (low
  byte).

Both sides therefore expose **exactly the same** channel, so the two exit codes
are compared **directly**; no value is taken from `llc`/QEMU output to define an
expectation (the comparison is host-vs-target, not against a stored constant).

## Judgement (fail-closed)

- every `include` case: `host_exit == dadao_exit` ⇒ **PASS**, otherwise **FAIL**;
- any compile-step failure / QEMU timeout / host `lli` error ⇒ **FAIL**;
- manifest structural failure (see below) ⇒ **FAIL**.

Exit status: `0` all pass · `1` any structural/value failure · `2` setup error.

## Boundary — **value-level only** (`只做值级`)

The check is restricted to programs whose observable value is independent of
memory byte order and object layout:

- **endianness / memory-layout class modules are excluded** — the host is
  little-endian, DADAO is big-endian (`contract-abi.md §1.7`), so any module
  that observes a multi-byte value through narrower loads/stores (or otherwise
  depends on memory layout) is out of scope.
- **Excluded (registered, not silently dropped)** — see `manifest.yaml`
  `exclude`; each entry carries a class + reason:

  | class | what |
  |-------|------|
  | `endianness` | `mem_narrow_be_bytes.ll`, `mem_narrow_be_wide.ll` (byte/narrow reads of a stored i64) |
  | `memory-layout` | (reserved for struct/aggregate-layout-dependent modules) |
  | `host-unsupported` | `m6_varargs.ll`, lit `m6-varargs.ll` (host `lli` SIGSEGVs on `llvm.va_start`) |
  | `needs-linker` | `m6_indirect_call.ll` (function-pointer `R_DADAO_ABS48`, needs the ELF pipeline) |
  | `multi-tu` | m4 `*_main.ll` + lit `branch-fold-insert.ll` (external symbols / multi-TU) |
  | `no-value-entry` | m4 `*_lib/_data.ll` + lit structural FileCheck modules (no `i64 @main()`) |

  The `include` / `exclude` / `on-disk` counts are printed **live** by the driver
  every run (现场统计); no count is hard-coded in the driver, README or gate.

### **This check is NOT an execution-semantics oracle** (`不作执行语义判据`)

A green run only says "the two back-ends agree on the value channel for the
included modules" — i.e. the **IR semantics are preserved** end-to-end. It does
**not** prove the ISA execution semantics: the authoritative semantics come from
the independent oracles / execution vectors (`tests/vectors/`,
`tools/testcases/validate_*.py`, `make test-codegen` / `check-qemu-semantics`).
The `lli` result must never be used as a substitute for those.

## Structural closure (lessons §8.34 / §8.35)

- **§8.35 (set/structural):** `include` ∪ `exclude` **MUST equal** every `*.ll`
  found on disk under `corpus_roots`, and the two sets **MUST be disjoint**.
  Any unclassified `*.ll` ⇒ FAIL. ⇒ deleting a manifest entry cannot silently
  shrink coverage (the file becomes *unclassified* and the driver fails).
- **§8.34 (hits must be proven):** the driver reports a **per-case hit**
  (`host=… dadao=…`, both captured) and asserts `hits == len(include)`; a run
  that only "did not error" is not accepted.

## Corpus

`corpus_roots` = `tests/llvm/codegen` + `tests/llvm/lit/CodeGen/DADAO`.  Every
`.ll` under them is classified (include or exclude). `tests/scripts/
dadao_mem_runtime.ll` is a runtime helper (not a CodeGen vector) and is outside
the corpus.

## Run

```bash
# value-level differential over every `include` case
python3 tools/testcases/diff_ir_lli.py --work-dir /tmp/opencode/TESTCASES-038t/work

# built-in counter-example self-test (flip one host value -> must FAIL)
python3 tools/testcases/diff_ir_lli.py --inject --work-dir /tmp/opencode/TESTCASES-038t/work
```

Tools are resolved from the install root via `tools/infra/paths.py`
(ADR-0016 D7/D9); override with `--lli/--llc/--llvm-mc/--llvm-objcopy/--qemu`.
`--manifest` / `--corpus-root` allow running against a copy of the manifest
(used by the evidence script to inject counter-examples in a temp tree).
