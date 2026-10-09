# M6 CodeGen test vectors (L3 execution)

Source IR vectors that drive the **M6 (complete integer calling convention +
large frames + FP/RF)** end-to-end test.  They live in their own directory —
like `../m4/` and `../m5/` — so the M3 driver
(`tools/integ/run_codegen_e2e.py`, whose default manifest is
`tests/llvm/codegen/expected.yaml`) never picks them up.

Task: `TESTCASES-036t`（M6 新能力向量：L1 编码 + L3 执行）.
Specs: `spec/Process-05-里程碑TDD规范.md §2`（L1/L2/L3）、`§3`（一能力一向量）、
`§4`（期望值独立派生）、`§5`（反例门控）.
Contracts: `.tao/knowledge/contract-abi.md §6`（调用约定）、`contract-elf.md §2–§4`
（reloc）、`contract-fp.md`（FP/RF）.

## Two manifests (raw-bin vs ELF)

- `expected.yaml` — **raw-bin** programs (single TU, `cat crt0 prog.s` → `llvm-mc`
  → `llvm-objcopy -O binary` → `qemu -kernel`).  Run with:

  ```
  python3 tools/integ/run_codegen_e2e.py \
      --vectors-dir tests/llvm/codegen/m6 \
      --expected    tests/llvm/codegen/m6/expected.yaml \
      --work-dir    .dadao/tests/codegen-m6
  ```

- `expected-elf.yaml` — the **ELF** program (`m6_indirect_call.ll`), which needs
  the linker to resolve an `R_DADAO_ABS48` function-pointer address and therefore
  cannot use the flat-binary flow.  Run with:

  ```
  python3 tools/integ/run_elf_e2e.py \
      --vectors-dir tests/llvm/codegen/m6 \
      --expected    tests/llvm/codegen/m6/expected-elf.yaml \
      --work-dir    .dadao/tests/elf-m6
  ```

## Independent oracle

`tools/testcases/validate_m6_vectors.py` re-derives every expected value on the
host from the LLVM IR semantics (64-bit two's-complement integer arithmetic,
IEEE-754 double arithmetic, big-endian memory per `contract-abi.md §1.7`).  It
**never** invokes `llc` / `ld.lld` / QEMU.  It also validates the L1 MC vectors
in `tests/llvm/lit/MC/DADAO/m6-callconv.s` / `m6-ldst-symbol.s` by re-deriving
the instruction encodings from `contracts/opcodes.yaml` and the relocation types
from `contract-elf.md §2.2`.

## Program ↔ coverage table

| Program | Manifest | Category | Exit | Exercises |
|---------|----------|----------|------|-----------|
| `m6_multi_return.ll` | raw-bin | call | 16 | `{i64,i64}` return in rd8/rd9 (contract-abi §6.1) |
| `m6_sret.ll` | raw-bin | call | 3 | `>64 B` aggregate return via hidden sret pointer (rb16) |
| `m6_aggregate_arg.ll` | raw-bin | call | 51 | `≤64 B` aggregate in rd16/rd17; `>64 B` byval pointer in rb16 |
| `m6_varargs.ll` | raw-bin | call | 42 | variadic call + `va_start` save area |
| `m6_large_frame.ll` | raw-bin | memory | 2 | large-frame forms 2 (`rb2rb`+`add.si`) and 3 (`set.zw`/`or.w`+`add.o`) |
| `m6_fp_arith.ll` | raw-bin | fp | 42 | FP `fo{mul,div,add}` + FP compare/branch |
| `m6_fp_hfa.ll` | raw-bin | fp | 42 | HFA `{double,double}` args rf16/rf17, return rf8/rf9 |
| `m6_indirect_call.ll` | ELF | call | 42 | indirect call through a function pointer; `R_DADAO_ABS48` + `R_DADAO_REL26` |

## L1 ↔ L3 correspondence

- Calling-convention relocations → `tests/llvm/lit/MC/DADAO/m6-callconv.s`
  (`R_DADAO_REL26` for `call`/`jump`, `R_DADAO_REL20`/`R_DADAO_REL14` for the
  branches, `R_DADAO_ABS48` for function-pointer address construction).  L3:
  `m6_indirect_call.ll` (ABS48 + REL26 resolved end-to-end by the linker).
- `ld/st` symbol-offset relocations (`R_DADAO_REL12` / `R_DADAO_ABS12`) →
  `tests/llvm/lit/MC/DADAO/m6-ldst-symbol.s` (**deferred**: the assembler does
  not yet emit the fixup; LLVM-065t).
- Large-frame addressing → L2 `tests/llvm/lit/CodeGen/DADAO/m6-large-frame.ll`
  (structural form selection) + L3 `m6_large_frame.ll` (execution).
- FP/RF → L2 `tests/llvm/lit/CodeGen/DADAO/fp-codegen.ll` (register shape) +
  L3 `m6_fp_arith.ll` / `m6_fp_hfa.ll` (execution).

## Validate

```
python3 tools/testcases/validate_m6_vectors.py
```

Exits non-zero on any schema / IR-shape / expected-value / encoding / reloc
mismatch.
