# CodeGen test vectors (M3)

Source IR vectors that drive the M3 (Basic CodeGen, scalar integer/pointer)
end-to-end test built by `INTEG-012t` (`make test-codegen`).

## Conventions

- Each `*.ll` is a single self-contained translation unit (no external symbols,
  no global variables / `.data` / `.rodata`, no varargs, no aggregates, no
  `sret`, no indirect calls).
- Each program defines `define i64 @main()`.
- The crt0 stub `_start` calls `@main` and reports the returned value (`rd31`)
  through the semihosting `SYS_EXIT` service (`ADR-0020 D8`: `SYS_EXIT` replaces
  the legacy MMIO halt device, `ADR-0004 D3` superseded), then halts (`swym`).  The **guest
  process exit code** is the low byte of that value.
- To keep the exit-code comparison unambiguous, every program returns a value in
  `0x00..0x7F`, clear of the machine-fault range `0x80..0xFF` (`ADR-0004`
  D5.7/D5.8; `ISS-147`).  Programs that need masking do it explicitly in the IR
  (mask `127`).
- Inputs are read from `alloca` slots with `volatile` load/store so that `llc`'s
  default `-O2` cannot constant-fold a program down to a bare `ret`.

## Independent oracle

`expected.yaml`'s `expected_exit_code` values are derived on the host from the
LLVM IR semantics (64-bit two's-complement integer arithmetic, big-endian memory
per `contract-abi.md` §1.7).  They are **not** produced by `llc` or QEMU.
`tools/testcases/validate_codegen_vectors.py` re-derives every value with an
embedded host-side model and rejects mismatches.

## Program ↔ coverage table

Coverage points follow `SPEC-096k` §M3 / `ADR-0018` (C1/C4/C5/C12/C13/C14/C17).

| Program | Category | Coverage points | Exit | Exercises |
|---------|----------|-----------------|------|-----------|
| `arith_add_sub_neg.ll`     | arithmetic | C12, arith.add, arith.sub, arith.neg-const | 118 | negative constant materialisation (`set.ow`), `add`, `sub` |
| `arith_const_hi_wyde.ll`   | arithmetic | C12, arith.const-hi-wyde | 110 | all-four-wyde 64-bit constant (`set.ow`+`andn.w`), `lshr`/`xor` |
| `mem_store_load_offset.ll` | memory     | mem.load-store-offset | 77 | `ld.o`/`st.o` with non-zero element offset (+8) |
| `mem_narrow_be_bytes.ll`   | memory     | C13, mem.narrow-be, mem.ld-ub, mem.ld-sb | 41 | big-endian byte loads at offsets 0/3/7, sign extension (`ld.sb`) |
| `mem_narrow_be_wide.ll`    | memory     | C13, mem.narrow-be, mem.ld-uw, mem.ld-sw, mem.ld-ut, mem.ld-st | 108 | big-endian i16/i32 loads at offsets 0/2/4/6, signed + unsigned |
| `branch_loop_sum.ll`       | branch     | C17, branch.signed-loop | 45 | signed predicate (`icmp slt`) loop; taken + not-taken edges |
| `branch_eq_ne.ll`          | branch     | C17, branch.eq-ne | 16 | `==` / `!=` compare-branch |
| `branch_ptr.ll`            | branch     | C17, C14, C1, branch.ptr-null, branch.ptr-eq, ptr.cmp | 25 | `p==NULL` (`br.z/nz {rb}`), `p==q` (`cmp.uo` dbb) |
| `call_direct_ret.ll`       | call       | call.direct-ret | 9 | direct `call`/`ret`, integer return in `rd31` |
| `call_multiarg_stack.ll`   | call       | C4, call.stack-args | 43 | 18 scalar args → 2 stack spill slots in declaration order |
| `call_narrow_args.ll`      | call       | C4, call.narrow-args | 9 | i8/i16/i32 args, caller canonical extension |
| `call_ptr_bank.ll`         | call       | C1, C5, call.ptr-bank | 42 | pointer argument (`rb16`), pointer return (`rb31`) |
| `ptr_add_offset.ll`        | memory     | C14, ptr.add-offset | 43 | base pointer + runtime offset (C14 `add.o` computation) |
| `ptr_diff_pos.ll`          | arithmetic | C14, ptr.diff-pos | 7 | `ptr−ptr` positive, selected as `sub.o_orrr_dbb` |
| `ptr_diff_neg.ll`          | arithmetic | C14, ptr.diff-neg | 121 | `ptr−ptr` negative (raw −7), selected as `sub.o_orrr_dbb` |

## Validate

```
python3 tools/testcases/validate_codegen_vectors.py
```

Exits non-zero on any schema / coverage / IR-shape / expected-value mismatch.
